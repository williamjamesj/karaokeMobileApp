from flask import Flask, render_template, session, request, redirect, flash, url_for, jsonify, Response, logging, send_from_directory
from werkzeug.utils import secure_filename
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

project_folder = os.path.expanduser('~/karaokeMobileApp')  # adjust as appropriate
load_dotenv(os.path.join(project_folder, '.env'))

app = Flask(__name__); app.debug = True
app.secret_key = os.environ['SECRET_KEY']
app.config.from_object(__name__)
CORS(app)
DATABASE = Database(os.path.join(project_folder, os.environ['DATABASE_URL']))
FILE_STORAGE = os.path.join(os.path.dirname(os.path.abspath(__file__)),"filestorage/")
app.config["UPLOAD_FOLDER"] = FILE_STORAGE
EXEMPT_PATHS = ["/", "/login","/2fa","/favicon.ico", "/token_login", "/register"] # All of the paths that are not protected by authentication.


# Before accessing ANY page (other than sign in pages), check if the user is logged in, as there is no public facing functionality for this website.
@app.before_request
def check_login():
    exempt_page = request.path in EXEMPT_PATHS or request.path.startswith("/static") # Check if it is one of the pages that is allowed (login and 2fa especially, to avoid a loop) or if it is a static file.
    for i in session:
        print(i)
    logged_in = 'userID' in session
    if not (logged_in or exempt_page or True): # To access a page, the user must either be logged in or be accessing a resource that does not require authentication.
        print("redirect")
        return redirect("/") # Redirect to the login if the user has not logged in
    else:
        print(request.path)

@app.route("/snippets/<snippetID>")
def uploaded_file(snippetID): # Checks if a snippet is private, and if not, serves it to the user.
    snippetData = DATABASE.ViewQuery("SELECT * FROM snippets INNER JOIN files ON snippets.fileID = files.fileID WHERE snippetID = ?", (snippetID,))
    if not snippetData:
        return jsonify({"error": "Snippet not found"})
    visibility = snippetData[0]["visibility"]
    if visibility == "1":
        return send_from_directory(app.config["UPLOAD_FOLDER"], snippetData[0]["filename"])
    return jsonify({"error": "This snippet is not public."})

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/login", methods=["GET","POST"])
def login(): # This login is used when the user does not already have an issued token.
    if request.method == "POST": # The react mobile app will send the user's credentials as a JSON object over POST.
        credentials = request.get_json() # Doesn't use a form, uses JSON.
        emailUsername = credentials["emailUsername"]
        password = credentials["password"]
        userDetails = DATABASE.ViewQuery("SELECT * FROM users WHERE email = ? OR name = ?", (emailUsername, emailUsername))
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

@app.route("/upload_audio", methods=["POST"])
def upload_audio():
    if request.method == "POST":
        if 'file' not in request.files:
            print("No file part")
            return jsonify({"status":"error"})
        title = request.form.get("title")
        description = request.form.get("description")
        visibility = request.form.get("visibility")
        if visibility == "true":
            print("visible")
            visibility = 1
        else:
            visibility = 0
        print(title,description)
        file = request.files['file']
        if file.filename != '':
            filename = file.filename
            if filename.endswith((".mp3", ".wav", ".flac", ".aac", ".m4a", ".ogg", ".wma")):
                number = DATABASE.ViewQuery("SELECT MAX(fileID) AS filename FROM files")[0]["filename"]
                if not number:
                    number = 0
                filename = secure_filename(str(number)+"."+filename.split(".")[-1])
                print(filename)
                try:
                    file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                except Exception as e:
                    print(e)
                    return({"status":"error saving file"})
                DATABASE.ModifyQuery("INSERT INTO files (filename) VALUES (?)", (filename,))
                fileID = DATABASE.ViewQuery("SELECT fileID FROM files WHERE filename = ?", (filename,))[0]["fileID"]
                DATABASE.ModifyQuery("INSERT INTO snippets (title, author, description, fileID, visibility) VALUES (?,?,?,?,?)", (title, session["userID"], description, fileID, visibility))
                return jsonify({"status":"success"})
            else:
                return jsonify({"status":"unsupported format"})
    return jsonify({"status":"error"})

@app.route("/snippets", methods=["GET", "POST"])
def snippetData():
    if request.method == "POST":
        snippetID = request.get_json()["snippetID"]
        print(snippetID)
        snippetData = DATABASE.ViewQuery("SELECT snippets.snippetID, title, author, visibility, description, name, COUNT(interactions.like) AS likes, COUNT(interactions.comment) AS comments, COUNT(interactions.view) AS views FROM (snippets INNER JOIN users ON snippets.author = users.userID) LEFT JOIN interactions ON interactions.snippetID = snippets.snippetID WHERE snippets.snippetID = ?", (snippetID,))
        comments = DATABASE.ViewQuery("SELECT interactionID, users.userID, comment, name FROM interactions INNER JOIN users ON interactions.userID = users.userID WHERE interactions.snippetID = ? AND comment NOT null", (snippetID,))
        print(snippetData)
        print(comments)
        if snippetData[0]["visibility"] != "1" and not snippetData[0]["visibility"] != "1": # If the snippet is not public, prevent a user from seeing it.
            return(jsonify({"status":"private"}))
        DATABASE.ModifyQuery("INSERT INTO interactions (snippetID, view) VALUES (?,?)", (snippetID, 1)) # When the user requests data about a snippet, it is considered to be a view.
        return jsonify({"snippetData":snippetData, "comments":comments})
    return(jsonify({}))

@app.route("/snippetsList", methods=["GET", "POST"])
def snippetList():
    if request.method == "POST":
        print("post")
        snippetData = DATABASE.ViewQuery("SELECT snippets.snippetID, title, author, description, name, COUNT(interactions.like) AS likes, COUNT(interactions.comment) AS comments, COUNT(interactions.view) AS views FROM (snippets INNER JOIN users ON snippets.author = users.userID) LEFT JOIN interactions ON interactions.snippetID = snippets.snippetID WHERE visibility = 1 GROUP BY snippets.snippetID") # Returns all of the snippets, which is not a long term solution as it could be a very large list. Pagination would be a good solution.
        print(snippetData)
        return jsonify(snippetData)
    return(jsonify({}))

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        credentials = request.get_json()
        print(credentials)
        checkEmail = DATABASE.ViewQuery("SELECT * FROM users WHERE email = ?", (credentials["email"],))
        if checkEmail:
            return(jsonify({"status":"emailDuplication"}))
        checkUsername = DATABASE.ViewQuery("SELECT * FROM users WHERE name = ?", (credentials["username"],))
        if checkUsername:
            return(jsonify({"status":"usernameDuplication"}))
        password = sha256_crypt.hash(credentials["password"]) # If no duplication of either usernames or emails are found, encrypt the password and insert the user into the database.
        insertSuccess = DATABASE.ModifyQuery("INSERT INTO users (name, email, password) VALUES (?, ?, ?)", (credentials["username"], credentials["email"], password))
        if insertSuccess:
            userID = DATABASE.ViewQuery("SELECT * FROM users WHERE email = ?", (credentials["email"],))[0]["userID"]
            token = issue_token(userID)
            return(jsonify({"status":"authenticated", "userID":userID, "token":token}))
        else:
            return(jsonify({"status":"failed"}))

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
        print(startTime)
        eventID = DATABASE.ModifyQuery("INSERT INTO events (creatorID, latitude, longitude, startTime, title, description) VALUES (?, ?, ?, ?, ?, ?)", (creatorID, latitude, longitude, startTime, title, description))
        return(jsonify({"status":"success","eventID":eventID}))
    return(jsonify({}))

@app.route("/events_list", methods=["GET","POST"])
def eventsList():
    if request.method == "POST":
        events = DATABASE.ViewQuery("SELECT * FROM events")
        return(jsonify({"status":"success","events":events}))
    return(jsonify({}))

@app.route("/event_details", methods=["GET","POST"])
def eventDetails():
    if request.method == "POST":
        eventID = request.get_json()["eventID"]
        DATABASE.ModifyQuery("INSERT INTO interactions (eventID, userID, view) VALUES (?, ?, ?)", (eventID, session["userID"], 1)) # Register the view, then retrieve, so the view is counted towards the figure the user sees.
        eventDetails = DATABASE.ViewQuery("SELECT events.eventID, creatorID, latitude, longitude, startTime, title, description, name, COUNT(like) AS likes, COUNT(view) AS views FROM (events INNER JOIN users ON events.creatorID = users.userID) LEFT JOIN interactions ON events.eventID = interactions.eventID WHERE events.eventID = ?", (eventID,))
        return(jsonify({"status":"success","event":eventDetails[0]}))
    return(jsonify({}))

@app.route("/event_like", methods=["GET","POST"])
def eventLike():
    if request.method == "POST":
        eventID = request.get_json()["eventID"]
        userID = session["userID"]
        likeCheck = DATABASE.ViewQuery("SELECT * FROM interactions WHERE eventID = ? AND userID = ? AND like = 1", (eventID, userID))
        print(likeCheck)
        if likeCheck:
            return(jsonify({"status":"already liked"}))
        DATABASE.ModifyQuery("INSERT INTO interactions (eventID, userID, like) VALUES (?, ?, ?)", (eventID, userID, 1))
        return(jsonify({"status":"success"}))

@app.route("/user_events", methods=["GET","POST"])
def userEvents():
    if request.method == "POST":
        userID = session["userID"]
        events = DATABASE.ViewQuery("SELECT title, description, startTime, COUNT(view) AS views, COUNT(like) AS likes, name FROM (events INNER JOIN interactions on events.eventID = interactions.eventID) INNER JOIN users on users.userID = events.creatorID WHERE (like = 1 AND interactions.userID = ?) OR creatorID = ? GROUP BY events.eventID", (userID, userID))
        print(events)
        return(jsonify({"status":"success","events": events}))
    return(jsonify({}))

@app.route("/submit_comment", methods=["GET","POST"])
def submitComments():
    if request.method == "POST":
        comment = request.get_json()
        userID = session["userID"]
        snippetID = comment["snippetID"]
        commentText = comment["commentText"]
        commentID = DATABASE.ModifyQuery("INSERT INTO interactions (userID, snippetID, comment) VALUES (?, ?, ?)", (userID, snippetID, commentText))
        return(jsonify({"status":"success"}))
    return(jsonify({}))

@app.route("/like_snippet", methods=["GET","POST"])
def likeComment():
    if request.method == "POST":
        like = request.get_json()
        userID = session["userID"]
        snippetID = like["snippetID"]
        interactions = DATABASE.ViewQuery("SELECT * FROM interactions WHERE userID = ? AND snippetID = ? AND like NOT null", (userID, snippetID))
        if interactions:
            return(jsonify({"status":"alreadyLiked"}))
        DATABASE.ModifyQuery("INSERT INTO interactions (userID, snippetID, like) VALUES (?, ?, ?)", (userID, snippetID, 1))
        return(jsonify({"status":"success"}))
    return(jsonify({}))

@app.route("/2fagenerate", methods=["GET","POST"])
def twoFactorGenerate():
    if request.method == "POST":
        userID = session["userID"]
        email = DATABASE.ViewQuery("SELECT email FROM users WHERE userID = ?", (userID,))[0]["email"]
        secret = pyotp.random_base32()
        url = pyotp.totp.TOTP(secret).provisioning_uri(email, issuer_name="singKaraoke")
        print(url)
        return(jsonify({"status":"success","secret":url, "actualSecret": secret}))
    return(jsonify({}))

@app.route("/2faconfirm", methods=["GET","POST"])
def twoFactorConfig():
    if request.method == "POST":
        data = request.get_json()
        code = data["code"]
        secret = data["secret"]
        if pyotp.TOTP(secret).verify(code):
            DATABASE.ModifyQuery("UPDATE users SET OTPCode = ? WHERE userID = ?", (secret, session["userID"]))
            return jsonify({"status":"success"})
        else:
            print("invalid token")
            return jsonify({"status":"failed"})
    return jsonify({})


if __name__ == '__main__':
    # print(getPowerLyrics("radioactive", "imagine dragons"))
    app.run(host='0.0.0.0', port=5000)