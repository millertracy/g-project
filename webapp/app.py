from flask import Flask, render_template, request, jsonify
from sklearn.externals import joblib
from sklearn.metrics.pairwise import linear_kernel
import numpy as np

app = Flask(__name__)


#import dictionary to extract posts
md = joblib.load("../md.pkl")

#get users and docs
users = [key for key in md]
documents = [md[user] for user in users]
docs = [" ".join(doc) for doc in documents]

#import vectorizer
vectorizer = joblib.load("../vectorizer.pkl")

#import fit vectorizer - it was created from user and doc structure above
vect = joblib.load("../vect.pkl")

#get query
query = ['i have a lot of anxiety, especially at night']

@app.route('/')
def get_sim_users():
    query_vect = vectorizer.transform(query)
    cos_sim = linear_kernel(vect, query_vect)
    top_sims = np.argsort(cos_sim, axis = None)[-1:-4:-1]
    top_posts = [docs[sim] for sim in top_sims]
    return render_template('demo.html', top_posts = top_posts)

if __name__ == "__main__":
    app.run()
