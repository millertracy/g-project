from flask import Flask, render_template, request, jsonify
from sklearn.externals import joblib
from sklearn.metrics.pairwise import linear_kernel
from nltk.stem.porter import PorterStemmer
import string
import numpy as np


app = Flask(__name__)

#setting to shorter var
punc = string.punctuation

#adding contractions to check for
contract = ['arent', 'wasnt', 'shouldnt', 'isnt', 'cant', 'hadnt', 'wouldnt', 'havent',
            'didnt', 'doesnt', 'dont', 'hasnt', 'couldnt', 'never']

# remove punctuation from string
def doc_remove_punc(doc):
    doc = "".join([letter for letter in doc if letter not in punc])
    inter = set(contract) & set(doc.split())
    if inter:
        for w in inter:
            doc = doc.replace(w+' ', w+'-')
    return doc

#create Porter instance
porter = PorterStemmer()

#stem string with porter
def lem(string, porter):
    return " ".join([porter.stem(word)for word in string.split()])

#get posts
docs = joblib.load("posts.pkl")

#import vectorizer
vectorizer = joblib.load("vectorizer.pkl")

#import fit vectorizer - it was created from user and doc structure above
vect = joblib.load("vect.pkl")


@app.route('/')
def render():
    return render_template('index.html')

@app.route('/solve', methods = ['POST'])
def solve():
    query = request.json
    doc = doc_remove_punc(query)
    doc = [lem(doc, porter)]
    query_vect = vectorizer.transform(doc)
    cos_sim = linear_kernel(vect, query_vect)
    top_sims = np.argsort(cos_sim, axis = None)[-1:-4:-1]
    top_posts = [docs[sim] for sim in top_sims]
    return jsonify(top_posts)

if __name__ == "__main__":
    app.run()
