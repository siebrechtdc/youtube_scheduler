import os
import google_auth_oauthlib.flow
import google.oauth2.credentials
import googleapiclient.discovery
from datetime import datetime, timedelta

# --- User-configurable settings ---
CLIENT_SECRETS_FILE = 'client_secret.json'
SCOPES = ['https://www.googleapis.com/auth/youtube']
API_SERVICE_NAME = 'youtube'
API_VERSION = 'v3'

# File to store the reusable stream ID
REUSABLE_STREAM_ID_FILE = 'reusable_stream_id.txt'

# Broadcast details (can be changed for each new scheduled event)
BROADCAST_TITLE = 'My Scheduled Live Stream (Reusable)'
BROADCAST_DESCRIPTION = 'This is a test using a reusable YouTube stream key.'
BROADCAST_PRIVACY_STATUS = 'public' # Can be 'public', 'private', or 'unlisted'
SCHEDULED_TIME_OFFSET_MINUTES = 30 # Schedule the stream to start in 30 minutes

def get_authenticated_service():
    """Authenticates and returns the YouTube API service."""
    credentials = None
    if os.path.exists('token.json'):
        credentials = google.oauth2.credentials.Credentials.from_authorized_user_file('token.json', SCOPES)

    if not credentials or not credentials.valid:
        flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(CLIENT_SECRETS_FILE, SCOPES)
        credentials = flow.run_local_server(port=0)
        with open('token.json', 'w') as token:
            token.write(credentials.to_json())
    
    return googleapiclient.discovery.build(API_SERVICE_NAME, API_VERSION, credentials=credentials)

def find_or_create_reusable_stream(youtube):
    """
    Finds an existing reusable stream or creates a new one.
    Returns the stream ID.
    """
    if os.path.exists(REUSABLE_STREAM_ID_FILE):
        with open(REUSABLE_STREAM_ID_FILE, 'r') as f:
            stream_id = f.read().strip()
        print(f"Using existing reusable stream with ID: {stream_id}")
        return stream_id

    print("Creating a new reusable live stream...")
    
    # Create the live stream
    stream_request = youtube.liveStreams().insert(
        part='snippet,cdn,contentDetails',
        body={
            'snippet': {
                'title': 'My Reusable Live Stream'
            },
            'cdn': {
                'frameRate': '60fps',
                'ingestionType': 'rtmp',
                'resolution': '1080p'
            },
            'contentDetails': {
                'isReusable': True
            }
        }
    )
    stream_response = stream_request.execute()
    stream_id = stream_response['id']
    
    with open(REUSABLE_STREAM_ID_FILE, 'w') as f:
        f.write(stream_id)
        
    print(f"Reusable stream created with ID: {stream_id}")
    return stream_id

def schedule_youtube_livestream(youtube):
    """Schedules a new YouTube livestream using a reusable stream."""
    print("Scheduling new live broadcast...")

    # Get the reusable stream ID (create one if it doesn't exist)
    stream_id = find_or_create_reusable_stream(youtube)

    # Set the scheduled start time
    scheduled_start = (datetime.utcnow() + timedelta(minutes=SCHEDULED_TIME_OFFSET_MINUTES)).isoformat() + 'Z'

    # Create the live broadcast
    broadcast_request = youtube.liveBroadcasts().insert(
        part='snippet,contentDetails,status',
        body={
            'snippet': {
                'title': BROADCAST_TITLE,
                'description': BROADCAST_DESCRIPTION,
                'scheduledStartTime': scheduled_start
            },
            'status': {
                'privacyStatus': BROADCAST_PRIVACY_STATUS
            },
            'contentDetails': {
                'enableDvr': True
            }
        }
    )
    broadcast_response = broadcast_request.execute()
    broadcast_id = broadcast_response['id']
    print(f"Broadcast created with ID: {broadcast_id}")
    
    # Bind the reusable stream to the new broadcast
    bind_request = youtube.liveBroadcasts().bind(
        part='snippet,cdn',
        id=broadcast_id,
        streamId=stream_id
    )
    bind_response = bind_request.execute()
    ingestion_address = bind_response['cdn']['ingestionInfo']['ingestionAddress']
    stream_name = bind_response['cdn']['ingestionInfo']['streamName']
    
    print("Broadcast and reusable stream successfully bound.")
    print(f"\nLive stream is scheduled and ready for content to be sent to:")
    print(f"  Ingestion Address: {ingestion_address}")
    print(f"  Stream Name/Key: {stream_name}")

if __name__ == '__main__':
    youtube_service = get_authenticated_service()
    schedule_youtube_livestream(youtube_service)