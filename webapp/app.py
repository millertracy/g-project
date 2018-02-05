from flask import Flask, render_template, request, jsonify
from sklearn.externals import joblib
from sklearn.metrics.pairwise import linear_kernel
import numpy as np

app = Flask(__name__)


#import dataframe to extract posts
df_personal = joblib.load("../df_personal.pkl")

#get docs
docs = [df_personal['post'][i] for i in df_personal.index]

#import vectorizer
vectorizer = joblib.load("../vectorizer.pkl")

#import fit vectorizer - it was created from user and doc structure above
vect = joblib.load("../vect.pkl")

# #get query
# query = ['i have a lot of anxiety, especially at night']


@app.route('/')
def render():
    return render_template('index.html')

@app.route('/solve', methods = ['POST'])
def solve():
    query = request.json
    doc = [query]
    query_vect = vectorizer.transform(doc)
    cos_sim = linear_kernel(vect, query_vect)
    top_sims = np.argsort(cos_sim, axis = None)[-1:-7:-1]
    top_posts = [docs[sim] for sim in top_sims]
    return jsonify(top_posts)

if __name__ == "__main__":
    app.run()
