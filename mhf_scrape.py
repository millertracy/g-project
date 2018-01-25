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
    CREATE TABLE mh_anx_user (
        users varchar(80) PRIMARY KEY,
        member_since varchar(20)
        );

        """

    create_post_table = """
    CREATE TABLE mh_anx_post (
        pid   varchar(20) primary key,
        users varchar(80),
        posts text,
        mood varchar(20),
        post_type varchar(10),
        post_title text,
        title text
        );"""


    cur.execute(create_user_table)
    cur.execute(create_post_table)
    conn.commit()
    conn.close()

def forum_scrape(html):
    #get response
    response = get_request(html)

    #get soup object
    soup = soupify(response)

    #get list of threads and links
    threads = parse_thread_page(soup)

    #add all threads and sub-threads to the database w/ multiprocessing
    p = Pool()
    p.map(add_to_db, threads)

    #while there is a next button
    if soup.find("a", rel="next") != None:
        next_page = soup.find("a", rel="next")

    page = 248
    print("page:", page)
    while next_page:
        href = next_page['href']
        response = get_request(href)
        page +=1
        print("----")
        print("page:", page)
        soup = soupify(response)
        threads = parse_thread_page(soup)
        p = Pool()
        p.map(add_to_db,threads)
        next_page = soup.find("a", {"rel": "next"})


def parse_thread_page(soup):
    """
    Input: Soup object
    Output: list of tuples
        - title
        - link to thread

    Ex: [("Anxiety issues", "https://anxiety_issues.com")]
    """

    #create list to store thread titles and links
    links = []

    # capture thread list
    thread_list = soup.find("ol", {"class": "threads"}).findAll("li", {"id": re.compile("thread_\d+") })

    for thread in thread_list:
        title = (thread.find("a", {"class": "title"}).text)
        link = (thread.find("a", {"class": "title"})['href'])
        links.append((title,link))
    return links



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

    #get title and link
    title = thd[0]
    link = thd[1]

    response = get_request(link)

    # while not reponse:
    #     time.sleep(np.random.uniform(1,3))
    #     response = get_request(link)

    soup = soupify(response)

    #insert user and post info into database
    insert_post(soup,title)

    if soup.find("a", rel="next") != None:
        next_page = soup.find("a", rel="next")

        while next_page:
            href = next_page['href']
            response = get_request(href)
            # while not reponse:
            #     time.sleep(np.random.uniform(1,3))
            #     response = get_request(link)
            soup = soupify(response)
            insert_post(soup,title)
            time.sleep(np.random.uniform(1,6))
            next_page = soup.find("a", {"rel": "next"})




def insert_post(soup, title):
    """
    Input: Soup object
    Output: pandas df
    """

    # grab all post tables
    tables = soup.findAll("div", {'class':"postdetails", 'id' : False})


    #connect to the database
    conn = psycopg2.connect("dbname = mh")
    cur = conn.cursor()

    # grab username, date of join, mood, post, and post_type
    for table in tables:

        #get post id
        elem = table.find("div", {"id": re.compile("post_message_\d+") })
        pid = elem['id'].split("_")[-1]


        # get username
        guest = table.find("span", {"class": "username guest"})
        if guest:
            user = table.find("span", {"class": "username guest"}).text
        else:
            user = (table.find("a")['title'].split("is")[0])

        #get join date and mood
        info = table.find("dl", {"class": "userinfo_extra"})
        if not info:
            date = 'nan'
            mood = 'nan'
        else:  #info.find("dt").text == "Join Date":
            date = info.find("dd").text
            if info.find("dd", {"class": "vmood-dd-legacy"}) != None:
                mood = info.find("dd", {"class": "vmood-dd-legacy"}).find("img")["alt"]
            else:
                mood = 'nan'

        # get post

            #if there is a repost, remove it and return text
        if table.find("blockquote", {"class": "postcontent restore "}).find("div", {"class" : "bbcode_container"}) != None:
            table.find("blockquote", {"class": "postcontent restore "}).find("div", {"class" : "bbcode_container"}).extract()
            post = table.find("blockquote", {"class": "postcontent restore "}).text.strip()
            post = " ".join([letter for letter in post if letter in printable])

            #if not return normal text
        else:
            post = table.find("blockquote", {"class": "postcontent restore "}).text.strip()
            post = " ".join([letter for letter in post if letter in printable])

        #get post_title
        post_title = (table.find("div", {"class": "postbody"}).find("h2", {"class": "title icon"}).text.strip())
        if len(post_title) == 0:
            post_title = 'nan'


        #get post_type
        if post_title == title:
            post_type = 'author'
        else:
            post_type = 'responder'

        #check if pid is already in database
        query_pid = ("""
        SELECT pid
        FROM   mh_anx_post
        WHERE  pid = %s;
        """,(pid,))

        #move to next if pid is already in the database
        cur.execute(query_pid[0], query_pid[1])
        tbl_pid = cur.fetchone()
        if tbl_pid:
            print("c")
            continue


        #input information into pc_post table
        #commit to the database
        query_insert = ("""
        INSERT INTO mh_anx_post (pid, users, posts, mood, post_title, post_type, title)
        VALUES (%s, %s, %s, %s, %s, %s, %s);
        """,
        (pid, user,  post, mood, post_title, post_type, title))

        cur.execute(query_insert[0], query_insert[1])
        conn.commit()

        #check if user is in pc_user table
        query_user = ("""
        SELECT users
        FROM   mh_anx_user
        WHERE  users = %s;
        """,(user,))


        cur.execute(query_user[0], query_user[1])
        tbl_user = cur.fetchone()

        # if user not already in user table, get user info
        if tbl_user != None:
            if tbl_user[0] == user:
                continue


        query_insert = ("""
        INSERT INTO mh_anx_user (users, member_since)
        VALUES (%s, %s);
        """,
        (user, date))

        # insert information above into user table
        # commit to the database

        cur.execute(query_insert[0], query_insert[1])
        conn.commit()





def get_request(url):
    """
    Takes in a url
    Outputs a list of html for each user's posts
    """

    headers = {"User-Agent": generate_user_agent()}
    response = requests.get(url, headers)
    return response


def soupify(response):
    return BeautifulSoup(response.text, "html.parser")
