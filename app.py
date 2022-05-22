from flask import Flask, render_template, session, request, redirect, flash, url_for, jsonify, Response, logging
from databaseinterface import Database
import json
import os
from flask_cors import CORS
from music import retriveSong, getChartLyrics
from passlib.hash import sha256_crypt
from dotenv import load_dotenv
import time
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
        credentials = request.get_json()
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
                name = userDetails[0]["name"]
                session["userID"] = userID
                return(jsonify({"status":"authenticated", "userID":userID, "name":name}))
        else:
            return(jsonify({"status":"Invalid Credentials"}))
    return jsonify({})

@app.route("/2fa", methods=["GET","POST"])
def twofactor():
    if request.method == "POST":
        code = request.get_json()["code"]
        userID = session["tempUserID"]
        userDetails = DATABASE.ViewQuery("SELECT * FROM users where userID = ?", (userID,))
        OTPCode = userDetails[0]['OTPCode']
        print(code)
        if pyotp.TOTP(OTPCode).verify(code):
            session["userID"] = userID
            return(jsonify({"status":"authenticated"}))
        else:
            return(jsonify({"status":"Invalid Code"}))
    return jsonify({})

    
# retriveSong("Lyrics.")
# print(getLyrics("", ""))

if __name__ == '__main__':
      app.run(host='0.0.0.0', port=5000)