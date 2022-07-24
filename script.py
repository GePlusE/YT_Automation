
import os
import pickle
import csv
from re import sub

from google.auth import credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from time import sleep

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

# Collect subscripted channel ids
sub_ids = []
request = youtube.subscriptions().list(part="snippet", maxResults=50, mine=True)
response = request.execute()
for item in response["items"]:
    sub_ids.append(item["snippet"]["resourceId"]["channelId"])

# # only for testing purpose
# sub_ids = ["UCCezIgC97PvUuR4_gbFUs5g,UCEqCu7uFzlXaDKnfQeY5s-g"]

# load already liked video ids into set, to decrease amount of requests to YouTube
with open("video_ids.csv", "r") as f:
    reader = csv.reader(f, delimiter=";", quotechar="'")
    ids = list(reader)
old_vid_ids = set([tuple(x) for x in ids])

# loop through subscriped channels to get video ids
for sub_id in sub_ids:
    vid_ids = []
    request = youtube.channels().list(part="contentDetails", id=sub_id)
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
                sleep(1)
            except:
                continue

            old_vid_ids.update([vid_id])

    # write new set to csv
    with open("video_ids.csv", "w") as f:
        writer = csv.writer(f, delimiter=";", quotechar="'")
        writer.writerows(old_vid_ids)
