import psycopg2
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import string
import re
import scipy.stats as scs
from collections import defaultdict
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import linear_kernel
plt.style.use("ggplot")

#for cleaning documents
punc = string.punctuation
alt_punc = "".join([char for char in string.punctuation if char not in ['?', '.', '-' ]])
contract = ['arent', 'wasnt', 'shouldnt', 'isnt', 'cant', 'hadnt', 'wouldnt', 'havent',
            'didnt', 'doesnt', 'dont', 'hasnt', 'couldnt', 'never']

# connect to db and create cursor object
conn = psycopg2.connect('dbname = mh')
cur = conn.cursor()

def close_conn():
    """
    Close db connection
    """
    conn.close()
    return None


def doc_remove_punc(doc):
    doc = "".join([letter for letter in doc if letter not in punc])
    inter = set(contract) & set(doc.split())
    if inter:
        for w in inter:
            doc = doc.replace(w+' ', w+'-')
    return doc


def doc_keep_punc(doc):
    doc = "".join([letter for letter in doc if letter not in alt_punc])
    inter = set(contract) & set(doc.split())
    if inter:
        for w in inter:
            doc = doc.replace(w+' ', w+'-')
    return doc



def make_mh_df(func):
    """
    Query a sql post table and a sql user table from mh forum and convert them into
    dataframes. Create a dictionary with users as keys and posts as values.

    Input: cursor object and db connection

    Output: df for post info, df for user info, md - dictionary used for nlp
    """

    # queries for mh_anx forum tables
    query_post = """
        Select * from mh_anx_post;
        """

    query_user = """
        Select * from mh_anx_user;
        """

    # capture both tables
    cur.execute(query_post)
    thread = cur.fetchall()

    cur.execute(query_user)
    members = cur.fetchall()

    #commit the queries
    conn.commit()

    # for pandas df
    pid = []
    user_p = []
    post = []
    mood = []
    post_type = []
    post_title = []
    title = []
    forum_name = []

    #for nlp matrix
    md = defaultdict(list)

    #post info
    for info in thread:
        pid.append(info[0])
        user_p.append(info[1])

        #remove extra space in document and remove punctuation and append to dictionary
        doc = info[2]
        doc = "".join(re.sub(r'\s\s', '|', doc).split())
        doc = doc.replace("|", " ")
        doc = doc.replace('...', '.')
        doc = func(doc)
        doc = ("".join(doc).lower())
        md[info[1]].append(doc)

        post.append(doc)
        mood.append(info[3])
        post_type.append(info[4])
        post_title.append(info[5])
        title.append(info[6])
        forum_name.append(info[7])

    mh_anx_post = pd.DataFrame({'pid':pid, 'user': user_p, 'post': post, 'mood': mood, 'post_type': post_type, 'post_title': post_title, 'thread_title': title, 'forum_name': forum_name})
    mh_anx_post = mh_anx_post[['pid', 'user', 'post_title', 'post', 'post_type', 'mood', 'thread_title', 'forum_name']]


    #user info
    user_u = []
    join_date = []

    for member in members:
        user_u.append(member[0])
        join_date.append(member[1])

    mh_anx_user = pd.DataFrame({'user': user_u, 'member_since': join_date})
    mh_anx_user = mh_anx_user[['user', 'member_since']]


    return mh_anx_post, mh_anx_user, md



def make_pc_df(func, md):
    """
    Query a sql post table and a sql user table from pc forum and convert them into
    dataframes. Create a dictionary with users as keys and posts as values.

    Input: None

    Output: df for post info, df for user info, updated md
    """

    # queries for pc forum tables
    query_post = """
        Select * from pc_anx_post;
        """

    query_user = """
        Select * from pc_anx_user;
        """

    #grab post and user information from pc tables
    cur.execute(query_post)
    thread = cur.fetchall()

    cur.execute(query_user)
    members = cur.fetchall()

    pid = []
    user_p = []
    mood = []
    post = []
    post_type = []
    post_title = []
    forum_name = []
    title = []


    for info in thread:
        pid.append(info[0])
        user_p.append(info[1])
        mood.append(info[2])

        doc = info[3]
        doc = " ".join([word.strip().lower() for word in doc.split()])
        doc.replace('...', '.')
        doc = func(doc)
        doc = "".join(doc)
        md['user'].append(doc) #appending to dictionary of users and docs from above

        post.append(doc)
        post_type.append(info[4])
        post_title.append(info[5])
        forum_name.append(info[6])
        title.append(info[7])

    pc_anx_post = pd.DataFrame({'pid': pid, 'user': user_p, 'mood': mood, 'post': post, 'post_type': post_type, 'post_title': post_title, 'thread_title': title, 'forum_name': forum_name})
    pc_anx_post = pc_anx_post[['pid', 'user', 'post_title', 'post', 'post_type', 'mood', 'thread_title', 'forum_name']]


    user_u = []
    join_date = []

    for member in members:
        user_u.append(member[0])
        join_date.append(member[1])

    pc_anx_user = pd.DataFrame({'user': user_u, 'member_since': join_date})
    pc_anx_user = pc_anx_user[['user', 'member_since']]

    return pc_anx_post, pc_anx_user, md


def merge_df(df1_post, df2_post, df1_user, df2_user):
    """
    Input:
        - 2 post dataframes to be merged
        - 2 user dataframes to be merged

    Output:
        - 1 merged post df
        - 1 merged user df
    """

    anx_post = pd.concat([df1_post, df2_post])
    anx_post.reset_index(drop = True, inplace = True)

    anx_user = pd.concat([df1_user, df2_user])
    anx_user.reset_index(drop = True, inplace = True)

    return anx_post, anx_user


def make_docs_labels(d):
    """
    Input:
        - d: dictionary
            keys - labels
            values - list of posts for that label

    Output:
        - list of labels
        - list of posts to use as documents for tfidfvectorizing
    """

    labels = [key for key in d]
    documents = [d[lab] for lab in labels]
    docs = [" ".join(doc) for doc in documents]
    return labels, docs


def top_n_others(vect, ri, n, users):
    """
    Inputs:
        - sim_mat: tfidf vector matrix
        - ri: list of row indices which define users to pick from
        - n: top n most similar users
        - matches: list of users
    Outputs:
        - user, that user's top n most similar matches starting with most similar
    """

    cos_sim = linear_kernel(vect, vect)
    sim_sort = np.argsort(cos_sim, axis = 1)
    sim_sort = sim_sort[:, 0:-1]
    top_n = list(range(-1,-n-1,-1))
    doc = sim_sort[ri, :]
    user = users[ri]
    sim_users = list(doc[top_n])
    return user, [users[sim] for sim in sim_users]

def top_n_posts(vect, ri, n, users, posts):

    cos_sim = linear_kernel(vect, vect)
    sim_sort = np.argsort(cos_sim, axis = 1)
    sim_sort = sim_sort[:, 0:-1]
    top_n = list(range(-1,-n-1,-1))
    doc = sim_sort[ri, :]
    user = users[ri]
    sim_users = list(doc[top_n])
    return (user, posts[ri]), [(users[sim], posts[sim]) for sim in sim_users]



def print_user_sims_posts(ri, users, posts):
    """
    Takes output of top_n_others and prints the user post and most similar users and their posts

    Input:
        - pint: (string) person of interest, the first item return from top_n_others
        - sims: list of users that are most similar to the user, 2nd item returned
                from top_n_others

    Ouput:
        None

    """

    print(pint)
    print ("-"*((len(pint))))
    print("doc:", " ".join(md[pint]))
    print("-"*100)

    for p in sims:
        print(p)
        print ("-"*((len(p))))
        print("doc:", " ".join(md[p]))
        print("-"*100)


def top_words(vect, ri, n, lst, vocab):
    """
    Inputs:
        vect - tfidf vectorized matrix
        ri - row index of the matrix that represent different labels
        n - number of top words
        lst - list of docs to get top words for
        vocab - list of vocabularly that corresponds to the indices of the vectorized matrix
    Outputs:
        tuple with label, list of top words

        Ex:
        ('andy', ['hello', 'how', 'doing'])
        ('anxiety', ['dread', 'scarred', 'worried'])
        """

    row = vect[ri]
    srow = np.argsort(row)
    top_w = srow[-1:-n-1:-1]
    return (lst[ri], [vocab[i] for i in top_w])


# creating the way to manually label data
def manlab_p(df_pkl, rx,  col):
    """
    Takes in pkl file, regex query, and column. Reads in pkl file
    as a pandas df. Subsets the regex query, and manually changes labels
    to df['col'] based on the post. Resaves the pkl file to update labels.

    Inputs:
        - pkl file
        - regex query
        - column

    Outputs:
        - pandas df

    """

    pd.set_option('max_colwidth' , 200)
    df = pd.read_pickle(df_pkl)
    df_res = df[df['post_type']== "responder"]
    df_lab = df_res[df_res['post'].str.contains(rx , regex = True)]
    proceed = input("Proceed: ")
    n = 1
    while proceed  == 'y':
        if n%10 == 0:
            proceed = input("Proceed: ")
        ind = int(np.random.choice(df_lab.index, size = 1))
        label = (input("Personal(0) {} / {}: ".format(n, df['post'].iloc[ind])))
        if label == 'x':
            break
        label = int(label)
        df[col][ind] = label
        n += 1
    #safety saving
    df.to_pickle('df_man.pkl')
    return df
