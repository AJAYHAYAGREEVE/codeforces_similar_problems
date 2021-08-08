import numpy as np
import pandas as pd
import json
import requests
import datetime
import pickle
import os

from flask import Flask, redirect, url_for, request, render_template


class NpEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        else:
            return super(NpEncoder, self).default(obj)


class Similarity:
    
    def __init__(self, problems = None):
        
        if(problems is None):
        	self.problems = self.load()
        else:
        	self.problems = problems 
        self.MIN_SIMILARITY = 0.5
    
    def load(self):
        
        problems = requests.get("https://codeforces.com/api/problemset.problems").json()["result"]["problems"]

        tags = []
        for problem in problems:
            tags.extend(problem["tags"])
        tags = list(set(tags))

        for problem in problems:
            problem["tags_num"] = np.zeros(len(tags)).astype('int')
            for tag in problem["tags"]:
                problem["tags_num"][tags.index(tag)] = 1
            problem["id"] = str(problem["contestId"]) + problem["index"]
            problem["url"] =  "https://codeforces.com/problemset/problem/" + str(problem["contestId"]) + "/" + problem["index"]
        
        return problems
    
    
    def similar_util(self, question, rating_bounds = None):
        
        if(rating_bounds is None):
            rating_bounds = (question["rating"] - 500, question["rating"] + 500)
        
        scores = []
        for problem in self.problems:
            if("rating" not in problem or question["id"] == problem["id"]):
                continue
            a = question["tags_num"]
            b = problem["tags_num"]
            score = round(np.dot(a, b)/(np.linalg.norm(a) * np.linalg.norm(b)), 3)
            scores.append((score, problem))
        
        scores.sort(key = lambda x : x[0], reverse = True)
        
        valid = []
        
        for tup in scores:
            if(tup[0] < self.MIN_SIMILARITY): 
                break
#             print(tup[1])
            if(tup[1]["rating"] < rating_bounds[0] or tup[1]["rating"] > rating_bounds[1]):
                continue
            
            valid.append((tup[0], tup[1]))
        
        valid.sort(key = lambda x : (x[0], x[1]["contestId"]), reverse = True)
        return valid[:20]

    
    def similar(self, problem_name = None,  rating_bounds = None, tags = None):
        
        if(problem_name == None and tags == None):
            return None
        
        if(problem_name is not None):
            question = None
            for problem in self.problems:
                if(problem["id"] == problem_name):
                    question = problem
                    break;

            if(question is None):
                return None
            
            return {"question" : question, "result" : self.similar_util(question, rating_bounds), "rating" : rating_bounds}
        
        
similar = Similarity()
# last_loaded = datetime.datetime.now()

app = Flask(__name__)

@app.route('/')
def index():
	return render_template("index.html")

@app.route('/similar-problems', methods = ['POST'])
def similars():
    

    last_loaded = datetime.datetime.min
    try:
        with open('problems.pickle', 'rb') as f:
            problems = pickle.load(f)
        last_loaded = problems["last_loaded"]
    except:
        pass    

    cur_date = datetime.datetime.now()
    

    if((cur_date - last_loaded).total_seconds() > 100000):
        similar = Similarity()
        problems = {"problems" : similar.problems, "last_loaded" : cur_date}

        with open('problems.pickle', 'wb') as f:
            pickle.dump(problems, f)  

    problems = problems["problems"]

    similar = Similarity(problems)
    # 

    problem_name = request.form["problem_name"]
    rating_range = (request.form["rating_from"], request.form["rating_to"])
    try:
    	rating_range = (int(rating_range[0]), int(rating_range[1]))
    except:
    	rating_range = None

    result = similar.similar(problem_name, rating_range)

    if(result is None):
        result = {"question" : problem_name, "error" : True}

    with open("result.json", "w") as f:
    	json.dump(result, f, cls = NpEncoder)

    return render_template("result.html", result = result)

if __name__ == '__main__':
    app.run(debug = True, port = 5004)


    