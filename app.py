from flask import Flask, render_template, session, request, redirect, flash, url_for, jsonify, Response, logging
import json
from music import retrive_song
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__); app.debug = True
app.config.from_object(__name__)

@app.route("/")
def index():
    return render_template("index.html")


retriveSong("Lyrics.")