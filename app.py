from flask import Flask, render_template, session, request, redirect, flash, url_for, jsonify, Response, logging
from databaseinterface import Database
import json
import os
from flask_cors import CORS
from music import retriveSong, getChartLyrics
from passlib.hash import sha256_crypt
from dotenv import load_dotenv
import time
import secrets
import pyotp

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
        credentials = request.get_json() # Doesn't use a form, uses JSON.
        email = credentials["email"]
        password = credentials["password"]
        print(request.get_json())
        userDetails = DATABASE.ViewQuery("SELECT * FROM users where email = ?", (email,))
        if userDetails and sha256_crypt.verify(password, userDetails[0]['password']):
            time.sleep(1) # Gives time for react native to do animations, TESTING ONLY.
            userID = userDetails[0]["userID"]
            if userDetails[0]['OTPCode'] != None:
                session["tempUserID"] = userID # Temporarily assign the userID to the session, which still prevents any use, but allows the user to proceed to the 2fa challenge.
                return jsonify({"status": "2fa"})
            else:
                token = issue_token(userID)
                name = userDetails[0]["name"]
                session["userID"] = userID
                return(jsonify({"status":"authenticated", "userID":userID, "token":token}))
        else:
            return(jsonify({"status":"Invalid Credentials"}))
    return jsonify({})

def issue_token(userID):
    token = secrets.token_urlsafe(32)
    yearOfSeconds = 60*60*24*365 # 1 year in seconds, the default expiry for a user's token.
    DATABASE.ModifyQuery("INSERT INTO tokens (userID, token, expiry) VALUES (?, ?, ?)", (userID, token, time.time() + yearOfSeconds))
    return token # The client recieves the authentication token.
    
@app.route("/token_login", methods=["GET","POST"])
def tokenLogin(): # This login is used when the user already has an issued token.
    time.sleep(5)
    if request.method == "POST":
        token = request.get_json()["token"]
        userDetails = DATABASE.ViewQuery("SELECT * FROM users INNER JOIN tokens on users.userID = tokens.userID WHERE tokens.token = ?", (token,))
        if userDetails: # If the token is valid, the user's details can be found.
            session["userID"] = userDetails[0]["userID"]
            return(jsonify({"status":"authenticated"}))
    return(jsonify({"status":"Invalid Token"}))

@app.route("/2fa", methods=["GET","POST"])
def twoFactor():
    if request.method == "POST":
        code = request.get_json()["code"]
        userID = session["tempUserID"]
        userDetails = DATABASE.ViewQuery("SELECT * FROM users where userID = ?", (userID,))
        OTPCode = userDetails[0]['OTPCode']
        print(code)
        if pyotp.TOTP(OTPCode).verify(code):
            session["userID"] = userID
            token = issue_token(userID)
            return(jsonify({"status":"authenticated", "token":token}))
        else:
            return(jsonify({"status":"Invalid Code"}))
    return jsonify({})

    
# retriveSong("Lyrics.")
# print(getLyrics("", ""))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)