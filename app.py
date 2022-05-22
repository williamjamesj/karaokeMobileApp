from flask import Flask, render_template, session, request, redirect, flash, url_for, jsonify, Response, logging
from databaseinterface import Database
import json
import os
from flask_cors import CORS
from music import retriveSong, getChartLyrics
from passlib.hash import sha256_crypt
from dotenv import load_dotenv
import time

load_dotenv()

app = Flask(__name__); app.debug = True
app.secret_key = os.environ['SECRET_KEY']
app.config.from_object(__name__)
CORS(app)
DATABASE = Database(os.environ['DATABASE_URL'])

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/login", methods=["GET","POST"])
def login(): # This login is used when the user does not already have an issued token.
    if request.method == "POST": # The react mobile app will send the user's credentials as a JSON object over POST.
        credentials = request.get_json()
        email = credentials["email"]
        password = credentials["password"]
        print(request.get_json())
        userDetails = DATABASE.ViewQuery("SELECT * FROM users where email = ?", (email,))
        if userDetails and sha256_crypt.verify(password, userDetails[0]['password']):
            time.sleep(5)
            userID = userDetails[0]["userID"]
            name = userDetails[0]["name"]
            session["userID"] = userID
            return(jsonify({"status":"authenticated", "userID":userID, "name":name}))
        else:
            return(jsonify({"status":"Invalid Credentials"}))
    return jsonify({})


# retriveSong("Lyrics.")
# print(getLyrics("", ""))

if __name__ == '__main__':
      app.run(host='0.0.0.0', port=5000)