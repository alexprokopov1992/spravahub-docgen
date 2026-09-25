from pathlib import Path
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/drive"]

CLIENT_FILE = Path("secrets/client_secret.json")
TOKEN_FILE = Path("secrets/google-token.json")

if not CLIENT_FILE.exists():
    raise SystemExit(
        "Put Google OAuth Desktop App credentials into secrets/client_secret.json"
    )

flow = InstalledAppFlow.from_client_secrets_file(str(CLIENT_FILE), SCOPES)
creds = flow.run_local_server(port=0, access_type="offline", prompt="consent")

TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
TOKEN_FILE.write_text(creds.to_json(), encoding="utf-8")
print(f"Saved token to {TOKEN_FILE}")
