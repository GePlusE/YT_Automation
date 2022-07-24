import csv
import json
import os
import pickle
import re
import requests

from bs4 import BeautifulSoup
from google.auth import credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from re import sub
from time import sleep

# Add channel url to list if videos should be liked
url_list = [
    "https://youtube.com/c/freerideflo",
    "https://www.youtube.com/c/JasperJauch",
    "https://www.youtube.com/c/KevinChromik",
    "https://www.youtube.com/c/KalleHallden",
    "https://www.youtube.com/c/MattJones"
    ]

# only used once to get the credentials
credentials = None

# token.pickle stores the user's credentials from previously successful logins
if os.path.exists("token.pickle"):
    with open("token.pickle", "rb") as token:
        credentials = pickle.load(token)

flow = InstalledAppFlow.from_client_secrets_file(
    "client_secret.json", scopes=["https://www.googleapis.com/auth/youtube"]
)

# If there are no valid credentials available, then either refresh the token or log in.
if not credentials or not credentials.valid:
    print("credentials don't exist or are not valid")
    flow = InstalledAppFlow.from_client_secrets_file(
        "client_secret.json", scopes=["https://www.googleapis.com/auth/youtube"]
    )

    flow.run_local_server(port=8080, prompt="consent", authorization_prompt_message="")
    credentials = flow.credentials

    # Save the credentials for the next run
    with open("token.pickle", "wb") as f:
        print("Saving Credentials for Future Use...")
        pickle.dump(credentials, f)
    if credentials and credentials.expired and credentials.refresh_token:
        print("credentials expired")
        credentials.refresh(Request())
    else:
        flow = InstalledAppFlow.from_client_secrets_file(
            "client_secret.json", scopes=["https://www.googleapis.com/auth/youtube"]
        )

        flow.run_local_server(
            port=8080, prompt="consent", authorization_prompt_message=""
        )
        credentials = flow.credentials

        # Save the credentials for the next run
        with open("token.pickle", "wb") as f:
            print("Saving Credentials for Future Use...")
            pickle.dump(credentials, f)

youtube = build("youtube", "v3", credentials=credentials)

# get channel_ids from channel_urls
id_set = set()
for url in url_list:
    soup = BeautifulSoup(requests.get(url, cookies={'CONSENT': 'YES+1'}).text, "html.parser")
    data = re.search(r"var ytInitialData = ({.*});", str(soup.prettify())).group(1)
    json_data = json.loads(data)

    channel_id = json_data['header']['c4TabbedHeaderRenderer']['channelId']
    id_set.add(channel_id)
channel_ids = list(id_set)

# load already liked video ids into set, to decrease amount of requests to YouTube
with open("video_ids.csv", "r") as f:
    reader = csv.reader(f, delimiter=";", quotechar="'")
    ids = list(reader)
old_vid_ids = set([tuple(x) for x in ids])

# loop through channels to get video ids
for channel_id in channel_ids:
    vid_ids = []
    request = youtube.channels().list(part="contentDetails", id=channel_id)
    response = request.execute()

    # add playlist_id of latest uploads
    uploads_id = []
    for item in response["items"]:  # neccessary if user has more than one channel
        uploads_id.append(item["contentDetails"]["relatedPlaylists"]["uploads"])

    # loop through playlists to get video ids
    for id in uploads_id:
        request = youtube.playlistItems().list(
            part="snippet, contentDetails", playlistId=id
        )
        response = request.execute()
        for item in response["items"]:
            channel_id = item["snippet"]["channelId"]
            video_id = item["contentDetails"]["videoId"]
            vid_ids.append((video_id, channel_id))


    # loop throuh videos and like + add new ones to set
    for vid_id in vid_ids:
        if vid_id not in old_vid_ids:
            try:
                youtube.videos().rate(rating="like", id=vid_id[0]).execute()
                print("liked video")
                sleep(0.5)
            except:
                continue

            old_vid_ids.update([vid_id])

    # write new set to csv
    with open("video_ids.csv", "w") as f:
        writer = csv.writer(f, delimiter=";", quotechar="'")
        writer.writerows(old_vid_ids)
