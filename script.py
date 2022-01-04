import os
import pickle
import csv

from google.auth import credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

credentials = None

# token.pickle stores the user's credentials from previously successful logins
if os.path.exists("token.pickle"):
    print("Loading Credentials From File...")
    with open("token.pickle", "rb") as token:
        credentials = pickle.load(token)

flow = InstalledAppFlow.from_client_secrets_file(
    "client_secret.json", scopes=["https://www.googleapis.com/auth/youtube"]
)

# If there are no valid credentials available, then either refresh the token or log in.
if not credentials or not credentials.valid:
    if credentials and credentials.expired and credentials.refresh_token:
        print("Refreshing Access Token...")
        credentials.refresh(Request())
    else:
        print("Fetching New Tokens...")
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
print(sub_ids)
sub_ids = ".".join(sub_ids)

# only for testing purpose
sub_ids = ["UCCezIgC97PvUuR4_gbFUs5g,UCEqCu7uFzlXaDKnfQeY5s-g"]

# load already liked video ids into set, to decrease amount of requests to YouTube
with open("video_ids.csv", "r") as f:
    reader = csv.reader(f, delimiter=";", quotechar="'")
    ids = list(reader)
old_vid_ids = set([tuple(x) for x in ids])

# loop through channels
for sub_id in sub_ids:
    # request = youtube.channels().list(part="statistics", id=sub_id)
    # response = request.execute()
    vid_ids = []
    channelId = sub_id
    maxResults = 1  # maxResults how many video will be liked per channel
    request = youtube.search().list(
        part="snippet",
        channelId=channelId,
        maxResults=maxResults,
        order="date",
        type="video",
    )
    response = request.execute()
    for item in response["items"]:
        print(item["snippet"]["title"])
        vid_ids.append((item["id"]["videoId"], item["snippet"]["channelId"]))

    # loop throuh videos and like + add new ones to set
    for vid_id in vid_ids:
        if vid_id not in old_vid_ids:
            youtube.videos().rate(rating="like", id=vid_id[0]).execute()
            old_vid_ids.update(vid_id)

    # write new set to csv
    with open("test.csv", "w") as f:
        writer = csv.writer(f, delimiter=";", quotechar="'")
        writer.writerows(old_vid_ids)
