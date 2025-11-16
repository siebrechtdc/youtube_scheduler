import os
import platform
import datetime
import pytz
import requests
import tempfile
from dotenv import load_dotenv
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload

# -------------------- Clear Screen --------------------
def clear_screen():
    command = "cls" if platform.system().lower() == "windows" else "clear"
    os.system(command)

clear_screen()
print("🔧 Starting YouTube Scheduler...\n")

# -------------------- Load Environment --------------------
load_dotenv()

CHANNEL_ID = os.getenv("CHANNEL_ID")
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
REFRESH_TOKEN = os.getenv("REFRESH_TOKEN")

if not all([CHANNEL_ID, CLIENT_ID, CLIENT_SECRET, REFRESH_TOKEN]):
    raise ValueError("Please set CHANNEL_ID, CLIENT_ID, CLIENT_SECRET, and REFRESH_TOKEN in .env")

# -------------------- Authenticate YouTube --------------------
creds = Credentials(
    None,
    refresh_token=REFRESH_TOKEN,
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    token_uri="https://oauth2.googleapis.com/token"
)
youtube = build("youtube", "v3", credentials=creds)

# -------------------- Helper: Get Last Broadcast --------------------
def get_last_broadcast(youtube):
    """Get last broadcast to reuse settings."""
    try:
        response = youtube.liveBroadcasts().list(
            part="id,snippet,status,contentDetails",
            mine=True,
            maxResults=10
        ).execute()

        if not response["items"]:
            print("⚠️ No previous broadcasts found — using default settings.")
            return {
                "title": "Bethel Livestream",
                "description": "Join us live this Sunday at 9:20 AM CST!",
                "thumbnail": None,
                "privacy": "public",
                "auto_start": True,
                "auto_stop": True,
                "streamId": None
            }

        # Sort broadcasts by publish date descending
        last_broadcasts = sorted(
            response["items"],
            key=lambda x: x["snippet"]["publishedAt"],
            reverse=True
        )
        last = last_broadcasts[0]

        thumbnails = last["snippet"].get("thumbnails", {})
        thumbnail_url = (
            thumbnails.get("maxres", {}).get("url") or
            thumbnails.get("high", {}).get("url") or
            thumbnails.get("medium", {}).get("url") or
            thumbnails.get("default", {}).get("url")
        )

        return {
            "title": last["snippet"].get("title", "Bethel Livestream"),
            "description": last["snippet"].get("description", "Join us live this Sunday at 9:20 AM CST!"),
            "thumbnail": thumbnail_url,
            "privacy": last["status"].get("privacyStatus", "public"),
            "auto_start": last.get("contentDetails", {}).get("enableAutoStart", True),
            "auto_stop": last.get("contentDetails", {}).get("enableAutoStop", True),
            "streamId": last.get("contentDetails", {}).get("boundStreamId")
        }

    except Exception as e:
        print(f"⚠️ Could not fetch previous broadcast info: {e}")
        return {
            "title": "Bethel Livestream",
            "description": "Join us live this Sunday at 9:20 AM CST!",
            "thumbnail": None,
            "privacy": "public",
            "auto_start": True,
            "auto_stop": True,
            "streamId": None
        }

# -------------------- Helper: Get Next Sunday 9:20 AM CST --------------------
def get_next_sunday_920am_cst():
    tz = pytz.timezone("America/Chicago")
    now = datetime.datetime.now(tz)
    days_ahead = 6 - now.weekday()
    if days_ahead <= 0:
        days_ahead += 7
    next_sunday = now + datetime.timedelta(days=days_ahead)
    scheduled_time_local = next_sunday.replace(hour=9, minute=20, second=0, microsecond=0)
    scheduled_time_utc = scheduled_time_local.astimezone(pytz.utc).isoformat()
    return scheduled_time_utc, scheduled_time_local

scheduled_start_time, local_scheduled_time = get_next_sunday_920am_cst()

# -------------------- Helper: Get Upcoming Broadcast --------------------
def get_upcoming_broadcast(youtube):
    try:
        response = youtube.liveBroadcasts().list(
            part="id,snippet,status,contentDetails",
            mine=True,
            maxResults=10
        ).execute()

        upcoming = [
            b for b in response["items"]
            if b["status"]["lifeCycleStatus"] == "upcoming"
        ]
        if upcoming:
            return sorted(upcoming, key=lambda x: x["snippet"]["scheduledStartTime"])[0]
        return None
    except Exception as e:
        print(f"⚠️ Could not fetch upcoming broadcast: {e}")
        return None

# -------------------- Helper: Set Thumbnail --------------------
def set_thumbnail(youtube, video_id, thumbnail_url):
    if not thumbnail_url:
        return
    tmp_file_path = None
    try:
        response_img = requests.get(thumbnail_url)
        response_img.raise_for_status()
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp_file:
            tmp_file_path = tmp_file.name
            tmp_file.write(response_img.content)
        media = MediaFileUpload(tmp_file_path)
        youtube.thumbnails().set(videoId=video_id, media_body=media).execute()
        print("📸 Thumbnail set successfully!")
        del media
    except Exception as e:
        print(f"⚠️ Failed to set thumbnail: {e}")
    finally:
        if tmp_file_path and os.path.exists(tmp_file_path):
            try:
                os.remove(tmp_file_path)
            except Exception:
                pass

# -------------------- Main --------------------
last_broadcast = get_last_broadcast(youtube)
upcoming = get_upcoming_broadcast(youtube)

# Create title: remove previous date if present, keep scheduled date only
base_title = last_broadcast['title'].split('-')[0].strip()  # e.g., "Bethel Livestream"
title = f"{base_title} - {local_scheduled_time.strftime('%Y %m %d')}"

if upcoming:
    video_id = upcoming["id"]
    print("🔄 Updating existing upcoming broadcast...")
    request_body = {
        "id": video_id,
        "snippet": {
            "title": title,
            "description": last_broadcast["description"],
            "scheduledStartTime": scheduled_start_time
        },
        "status": {"privacyStatus": last_broadcast["privacy"]},
        "contentDetails": {
            "enableAutoStart": last_broadcast["auto_start"],
            "enableAutoStop": last_broadcast["auto_stop"]
        }
    }
    try:
        youtube.liveBroadcasts().update(
            part="snippet,status,contentDetails",
            body=request_body
        ).execute()
        print(f"✅ Livestream updated successfully! (ID: {video_id})")
    except HttpError as e:
        print(f"❌ Failed to update livestream: {e}")
else:
    request_body = {
        "snippet": {
            "title": title,
            "description": last_broadcast["description"],
            "scheduledStartTime": scheduled_start_time
        },
        "status": {"privacyStatus": last_broadcast["privacy"]},
        "contentDetails": {
            "enableAutoStart": last_broadcast["auto_start"],
            "enableAutoStop": last_broadcast["auto_stop"]
        }
    }
    try:
        response = youtube.liveBroadcasts().insert(
            part="snippet,status,contentDetails",
            body=request_body
        ).execute()
        video_id = response["id"]
        print("✅ Livestream scheduled successfully!")
        print(f"Title: {title}")
        print(f"Scheduled Start (UTC): {scheduled_start_time}")
        print(f"Video ID: {video_id}")
    except HttpError as e:
        print(f"❌ Failed to schedule livestream: {e}")
        exit(1)

# -------------------- Reuse Existing Stream --------------------
if last_broadcast.get("streamId"):
    try:
        youtube.liveBroadcasts().bind(
            part="id,contentDetails",
            id=video_id,
            streamId=last_broadcast["streamId"]
        ).execute()
        print(f"🔁 Reusing existing stream: {last_broadcast['streamId']}")
        print(f"🔗 Bound broadcast {video_id} to stream {last_broadcast['streamId']}")
    except HttpError as e:
        print(f"⚠️ Failed to bind existing stream: {e}")

# -------------------- Set Thumbnail --------------------
set_thumbnail(youtube, video_id, last_broadcast.get("thumbnail"))

print("🎉 All done!")
