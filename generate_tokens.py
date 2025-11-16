# generate_tokens.py
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/youtube.force-ssl"]

flow = InstalledAppFlow.from_client_secrets_file(
    "client_secret.json",  # your downloaded OAuth file
    SCOPES
)
creds = flow.run_local_server(port=0)

print("\n✅ COPY THESE VALUES INTO YOUR .env FILE:\n")
print(f"CLIENT_ID={creds.client_id}")
print(f"CLIENT_SECRET={creds.client_secret}")
print(f"ACCESS_TOKEN={creds.token}")
print(f"REFRESH_TOKEN={creds.refresh_token}")
