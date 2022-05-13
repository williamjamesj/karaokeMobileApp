import json
import os
import requests
from string import Template # Used for having a template for GET API requests.

urls = {"geniusSearch":"https://genius.p.rapidapi.com/search",
        "chartLyrics":Template("http://api.chartlyrics.com/apiv1.asmx/SearchLyricDirect?artist=$artist&song=$title"),
        }

def retriveSong(lyrics):
    queryString = {"q":lyrics}
    headers = {
        "X-RapidAPI-Host": "genius.p.rapidapi.com",
        "X-RapidAPI-Key": f"{os.environ['GENIUS_KEY']}"
    }
    print (headers)
    # response = requests.request("GET", urls["search"], headers=headers, params=queryString)
    response = json.loads(response.text)
    if response["meta"]["status"] == 200:
        data = response["response"]["hits"][0]["result"]
        print("Song Name:",data["title"])
        print("Artist(s)", data["artist_names"])
    return(response)

def get_lyrics():
    pass