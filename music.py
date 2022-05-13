import json
import os
import requests
import xml.etree.ElementTree as ElementTree # Used to process the XML reponse, given by the ChartLyrics API.


urls = {"geniusSearch":"https://genius.p.rapidapi.com/search",
        "chartLyrics":"http://api.chartlyrics.com/apiv1.asmx/SearchLyricDirect",
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
    else:
        print("Something went wrong.")
    return(response)

def getChartLyrics(title, artist):
    response = requests.get(urls["chartLyrics"], params={"artist":artist, "song":title})
    lyrics = ""
    if response.status_code == 200:
        data = ElementTree.fromstring(response.text)
        for lyric in data.iter("{http://api.chartlyrics.com/}Lyric"): # Iterate through the XML response, finding all of the lyrics, of which there should only be one.
            lyrics = lyric.text
    else:
        print("Something went wrong.")
    return lyrics