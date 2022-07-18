from click import getchar
from flask import Flask, render_template, session, request, redirect, flash, url_for, jsonify, Response, logging
from databaseinterface import Database
import json
import os
from flask_cors import CORS
from music import retriveSong, getChartLyrics, getPowerLyrics, getLyrics
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
EXEMPT_PATHS = ["/", "/login","/2fa","/favicon.ico", "/token_login"] # All of the paths that are not protected by authentication.


# Before accessing ANY page (other than sign in pages), check if the user is logged in, as there is no public facing functionality for this website.
@app.before_request
def check_login():
    exempt_page = request.path in EXEMPT_PATHS or request.path.startswith("/static") # Check if it is one of the pages that is allowed (login and 2fa especially, to avoid a loop) or if it is a static file.
    logged_in = 'userid' in session
    if not (logged_in or exempt_page): # To access a page, the user must either be logged in or be accessing a resource that does not require authentication.
        return redirect("/") # Redirect to the login if the user has not logged in.

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/login", methods=["GET","POST"])
def login(): # This login is used when the user does not already have an issued token.
    if request.method == "POST": # The react mobile app will send the user's credentials as a JSON object over POST. 
        credentials = request.get_json() # Doesn't use a form, uses JSON.
        email = credentials["email"]
        password = credentials["password"]
        userDetails = DATABASE.ViewQuery("SELECT * FROM users where email = ?", (email,))
        if userDetails and sha256_crypt.verify(password, userDetails[0]['password']):
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
        if "tempUserID" not in session:
            print("No tempUserID")
            return jsonify({})
        code = request.get_json()["code"]
        userID = session["tempUserID"]
        userDetails = DATABASE.ViewQuery("SELECT * FROM users where userID = ?", (userID,))
        OTPCode = userDetails[0]['OTPCode']
        if pyotp.TOTP(OTPCode).verify(code):
            session["userID"] = userID
            token = issue_token(userID)
            return(jsonify({"status":"authenticated", "token":token}))
        else:
            return(jsonify({"status":"Invalid Code"}))
    return jsonify({})

@app.route("/get_lyrics", methods=["GET","POST"])
def retrieveLyrics():
    if request.method == "POST":
        time.sleep(2)
        response = request.get_json()
        song = response["song"]
        artist = response["artist"]
        lyrics = getLyrics(song, artist)
        if lyrics:
            return(jsonify({"status":"success","lyrics":lyrics}))
        else:
            return(jsonify({"status":"failed"}))
    return jsonify({})

@app.route("/find_song", methods=["GET","POST"])
def findSong():
    if request.method == "POST":
        lyrics = request.get_json()["lyrics"]
        if lyrics != "":
            song = retriveSong(lyrics)
            if song:
                return(jsonify({"status":"success","song":song}))
            else:
                return(jsonify({"status":"Song Not Found."}))
        else:
            return(jsonify({"status":"No Lyrics."}))
    return(jsonify({}))

@app.route("/create_event", methods=["GET","POST"])
def createEvent():
    if request.method == "POST":
        event = request.get_json()
        creatorID = session["userID"]
        latitude = event["latitude"]
        longitude = event["longitude"]
        startTime = event["startTime"]
        title = event["title"]
        description = event["description"]
        eventID = DATABASE.ModifyQuery("INSERT INTO events (creatorID, latitude, longitude, startTime, title, description) VALUES (?, ?, ?, ?, ?, ?)", (creatorID, latitude, longitude, startTime, title, description))
        return(jsonify({"status":"success","eventID":eventID}))
    return(jsonify({}))

if __name__ == '__main__':
    # print(getPowerLyrics("radioactive", "imagine dragons"))
    app.run(host='0.0.0.0', port=5000)