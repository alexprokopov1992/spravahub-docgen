from pathlib import Path
import os

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/drive"]
MIME_DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

TOKEN = Path(os.getenv("GOOGLE_TOKEN_FILE", "secrets/google-token.json"))
OUT = Path(os.getenv("LOCAL_TEMPLATE_DIR_HOST", "local_templates"))

TEMPLATES = {
    "application_recalc.docx": os.getenv(
        "TEMPLATE_APPLICATION_RECALC_ID",
        "13pl29xCjmo4fDtbHH8Cug5_ssGOqq_reyDW-k4dnjHg",
    ),
    "claim_indexation.docx": os.getenv(
        "TEMPLATE_CLAIM_INDEXATION_ID",
        "157jeX1I3HERMeiFozpc-wtYOkExPdS4dXHfY2CKGQgY",
    ),
    "claim_recalc.docx": os.getenv(
        "TEMPLATE_CLAIM_RECALC_ID",
        "1bu4hcNQnE9hWx4j6mmYSWTS0j3W4RkiUg2elqheO_OM",
    ),
}

if not TOKEN.exists():
    raise SystemExit(f"Google token not found: {TOKEN}")

creds = Credentials.from_authorized_user_file(str(TOKEN), SCOPES)
if creds.expired and creds.refresh_token:
    creds.refresh(Request())
if not creds.valid:
    raise SystemExit("Invalid Google OAuth token")

drive = build("drive", "v3", credentials=creds, cache_discovery=False)
OUT.mkdir(parents=True, exist_ok=True)

for filename, file_id in TEMPLATES.items():
    data = drive.files().export(fileId=file_id, mimeType=MIME_DOCX).execute()
    path = OUT / filename
    path.write_bytes(data)
    print(f"{filename}: {len(data)} bytes")

print("\nLocal master templates synchronized.")
print("Runtime Local DOCX mode no longer needs Google for personal data.")
