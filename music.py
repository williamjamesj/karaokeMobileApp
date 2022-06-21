import json
import os
import requests
import xml.etree.ElementTree as ElementTree # Used to process the XML reponse, given by the ChartLyrics API.


urls = {"geniusSearch":"https://genius.p.rapidapi.com/search",
        "chartLyrics":"http://api.chartlyrics.com/apiv1.asmx/SearchLyricDirect",
        "powerLyricsArtist":"https://powerlyrics.p.rapidapi.com/getlyricsfromtitleandartist",
        }

def retriveSong(lyrics):
    queryString = {"q":lyrics}
    headers = {
        "X-RapidAPI-Host": "genius.p.rapidapi.com",
        "X-RapidAPI-Key": f"{os.environ['GENIUS_KEY']}"
    }
    response = requests.request("GET", urls["geniusSearch"], headers=headers, params=queryString)
    response = json.loads(response.text)
    if response["meta"]["status"] == 200:
        subset = response["response"]["hits"]
        if len(subset):
            data = response["response"]["hits"][0]["result"]
            print("Song Name:",data["title"])
            print("Artist(s)", data["artist_names"])
        else:
            print("No songs found.")
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
        if not lyrics:
            return False
        artist = data.find("{http://api.chartlyrics.com/}LyricArtist").text
        title = data.find("{http://api.chartlyrics.com/}LyricSong").text
    else:
        return False
    return {"artist":artist, "title":title, "lyrics":lyrics}

def getPowerLyrics(title, artist):
    headers = {
        "X-RapidAPI-Host": "powerlyrics.p.rapidapi.com",
	    "X-RapidAPI-Key": os.environ["POWERLYRICS_KEY"]
    }
    response = requests.get(urls["powerLyricsArtist"], headers=headers, params={"artist":artist, "title":title})
    responsedata = json.loads(response.text)
    if responsedata["success"]:
        artist = responsedata["resolvedartist"]
        title = responsedata["resolvedtitle"]
        lyrics = responsedata["lyrics"]
    else:
        return False
    return {"artist":artist, "title":title, "lyrics":lyrics}

def getLyrics(title, artist): # This function tries chartLyrics first, then powerLyrics, then gives up.
    chartLyrics = getChartLyrics(title, artist)
    if chartLyrics:
        print("ChartLyrics")
        return chartLyrics
    powerLyrics = getPowerLyrics(title,artist)
    if powerLyrics:
        print("PowerLyrics")
        return powerLyrics
    else:
        return False
