""" This is a py file to scrape a psych central forum """

import requests
from bs4 import BeautifulSoup
import re
import pandas as pd
from collections import defaultdict
import time
import psycopg2
from user_agent import generate_user_agent
import numpy as np
import string
from multiprocessing import Pool


# set up some variables for removing characters that aren't unicode

printable = set(string.printable)
#punctuation = set(string.punctuation)


#Connect to the database and set up the cursor
conn = psycopg2.connect("dbname = mh")
cur = conn.cursor()


def create_db_tables():

    """
    Creates database tables
    """

    create_user_table = """
    CREATE TABLE pc_anx_user (
        users varchar(80) PRIMARY KEY,
        member_since varchar(20)
        );

        """

    create_post_table = """
    CREATE TABLE pc_anx_post (
        pid   varchar(20) primary key,
        users varchar(80),
        mood varchar(30),
        posts text,
        post_type varchar(10),
        title text,
        forum_name text
        );"""


    cur.execute(create_user_table)
    cur.execute(create_post_table)
    conn.commit()
    conn.close()


def parse_forum(html):

    """
    Takes in the html of a forum page
    Updates a SQL database with forum info
    """

    # get request for forum
    response = get_request(html)

    #create a soup object of request
    soup = soupify(response)

    #get links for all threads
    threads = parse_thread_page(soup)

    #add all threads and sub-threads to the database w/ multiprocessing
    p = Pool()
    p.map(add_to_db,threads)

    #see if a navigation bar exists
    nav_page = soup.find('div', {'class': 'pagenav'})
        # if a next button exists, get the link for the next thread page
    if nav_page != None:
        next_page = soup.find("a", {"rel": "next"})

        # while a next button exits, loop through all thread listing pages and add
        #each thread (and its sub_threads) to the database
        while next_page:
            href = next_page['href']
            response = get_request(href)
            soup = soupify(response)
            threads = parse_thread_page(soup)
            p = Pool()
            p.map(add_to_db,threads)
            next_page = soup.find("a", {"rel": "next"})



def parse_thread_page(soup):
    """
    Takes in a soup object
    Returns a list of dictionaries containing all of the
        threads on a page

    ____________________________
    dictionary:
        title: title of thread
        link: html of the thread
    """
    threads = []
    form = soup.find("form", {"method" : "post", "id": "inlinemodform"})
    tds = form.find_all("td", {"id": re.compile("td_threadtitle_\d+")})
    for td in tds:
        if td.find("img", {"alt": "Sticky Thread"}):
            continue
        else:
            title = td.find("a").text
            hyperlink = td.find("a")['href']
            #threads.append({"thread": title, "link": hyperlink})
            threads.append(hyperlink)
    return threads



def add_to_db(thd):
    """
    Takes in a thread
    Updates 2 tables in sql database
        - pc_user
        - pc_post
    _________________________
    Input:
        - thread: thread hyperlink

    Output:
        None

    """

    #for thd in threads:
        # for each thread, get the thread link and response
        # and turn the text into a soup object
    #link = thd['link']
    response = get_request(thd)
    soup = soupify(response)

    #get title of thread
    title = soup.find("h1", {"class": "post_title"}).text.strip()

    #get all of the post tables in a thread
    tables = get_tables(soup)
    insert_user_post(tables, title, ptype = "author")

    # check if a thread has a navigation panel
    nav_page = soup.find('div', {'class': 'pagenav'})

    # if a thread has navigation panel check if it has a next button
    if nav_page != None:
        next_page = soup.find("a", {"rel": "next"})

        # while a next button exists,
        # go to that next page, get soup object, and find all posts
        # Insert user and post information into the database tables
        while next_page != None:
            href = next_page['href']
            response = get_request(href)
            soup = soupify(response)
            title = soup.find("h1", {"class": "post_title"}).text.strip()
            tables = get_tables(soup)
            insert_user_post(tables, title)
            next_page = soup.find("a", {"rel": "next"})

    # once the entire thread has been parsed and data uploaded, sleep for a random time (2-5 s) and
    # repeat for the next thread
    time.sleep(np.random.uniform(2,6))
#print post_count

def insert_user_post(tables, title, ptype = "responder"):
    """
    Takes in a list of html elements and thread title
    Updates the sql user table (pc_user) and sql post table (pc_post)
    Returns None
    ________________________________________
    pc_user
        users: list of usernames
        member_since: list dates became a member for each user
        num_posts: list of total number of posts for each user

    pc_post
        users: username for each user
        posts: post for each user
        post_type: author or responder
        url:  url of the page
    """
    conn2 = psycopg2.connect("dbname = mh")
    cur = conn2.cursor()
    for i,table in enumerate(tables):
        # get the post id:
        pid = table["id"]
        pid = "".join([letter for letter in pid if letter in string.digits])

        # check if it's a moderator or user
        # if its a moderator, continue until find a user
        if  "moderator" in table.find('div', {'class': 'smallfont'}).text.lower():
            continue
        if "admin" in table.find('div', {'class': 'smallfont'}).text.lower():
            continue


        #grab username
        if table.find("a", {"class": "bigusername"}) == None:
            user = table.find("div", {"id": re.compile("postmenu_\d+")}).text.strip()
        else:
            user = table.find("a", {"class": "bigusername"}).text

        #get mood
        if table.find('img', {'src': re.compile("^/images/mood")}):
            mood = tables[1].find('img', {'src': re.compile("^/images/mood")})['src'].split("/")[-1].split(".")[0].lower()
        else:
            mood = 'nan'

        #grab post and strip out characters that can't be encoded into unicode
        if table.find("div", {"id": re.compile("post_message_\d+")}).find("table"):
            table.find("div", {"id": re.compile("post_message_\d+")}).find("div", {"class": "smallfont"}).extract()
            table.find("div", {"id": re.compile("post_message_\d+")}).find("table").extract()
            post = table.find(("div", {"id": re.compile("post_message_\d+")})).text.strip()
            post = "".join([letter for letter in post if letter in printable])
        else:
            post = table.find_all("div", {"id": re.compile("post_message_\d+")})[0].text.strip()
            post = "".join([letter for letter in post if letter in printable])
        if "http" in post:
            post = re.sub(r'http\S+', '', post)


        # add post as author or responder
        post_type = ptype

        #add a forum name
        fname = ''



        #input information into pc_post table
        #commit to the database
        query_insert = ("""
        INSERT INTO dep_post (pid, users, mood, posts, post_type, title, forum_name)
        VALUES (%s, %s, %s, %s, %s, %s, %s);
        """,
        (pid, user, mood, post, post_type, title, fname))

        cur.execute(query_insert[0], query_insert[1])
        conn2.commit()

        #check if user is in pc_user table
        query_user = ("""
        SELECT users
        FROM   dep_user
        WHERE  users = %s;
        """,(user,))


        cur.execute(query_user[0], query_user[1])
        tbl_user = cur.fetchone()

        # if user not already in user table, get user info
        if tbl_user != None:
            if tbl_user[0] == user:
                continue

        # images affect where information is positioned, intially set location parameter
        # to 0.
        n = 0

        # if there is no image change location parameter to 1
        if table.find("img").findNext("img").has_attr("alt") and user in table.find("img").findNext("img")['alt']:
            n = 1

        # if user is a guest, they have no member_date, set to nan
        # else find date
        if table.find_all("div", {"class":"smallfont"})[0].text.lower() == "guest":
            member_since = "nan"
        else:
            member_since = table.findAll('br')[n].findNext('div').text.split(":")[-1].strip()

        query_insert = ("""
        INSERT INTO dep_user (users, member_since)
        VALUES (%s, %s);
        """,
        (user, member_since))

        # insert information above into user table
        # commit to the database

        cur.execute(query_insert[0], query_insert[1])
        conn2.commit()


def get_request(url):
    """
    Takes in a url
    Outputs a list of html for each user's posts
    """

    headers = {"User-Agent": generate_user_agent()}
    response = requests.get(url, headers)
    return response

def get_tables(soup):
    tables = soup.find_all("table", {"id": re.compile("post\d+")})
    return tables

def soupify(response):
    return BeautifulSoup(response.text, "html.parser")
