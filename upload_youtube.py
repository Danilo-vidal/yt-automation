import json
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

CLIENT_SECRET_FILE = "client_secret.json"
TOKEN_FILE = "youtube_token.json"


def get_youtube_service():
    creds = None

    if Path(TOKEN_FILE).exists():
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())

    if not creds or not creds.valid:
        flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_FILE, SCOPES)
        creds = flow.run_local_server(port=0)

        with open(TOKEN_FILE, "w", encoding="utf-8") as token:
            token.write(creds.to_json())

    return build("youtube", "v3", credentials=creds)


def upload_video(
    video_file: str,
    title: str,
    description: str,
    tags=None,
    category_id: str = "25",
    privacy_status: str = "private",
    thumbnail_file: str | None = None,
):
    if tags is None:
        tags = []

    youtube = get_youtube_service()

    body = {
        "snippet": {
            "title": title[:100],
            "description": description[:5000],
            "tags": tags[:500],
            "categoryId": category_id,
        },
        "status": {
            "privacyStatus": privacy_status,
            "selfDeclaredMadeForKids": False,
        },
    }

    media = MediaFileUpload(video_file, chunksize=-1, resumable=True)

    request = youtube.videos().insert(
        part="snippet,status",
        body=body,
        media_body=media,
    )

    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            print(f"[YOUTUBE] Upload {int(status.progress() * 100)}%")

    video_id = response["id"]
    print(f"[YOUTUBE] Vídeo enviado com ID: {video_id}")

    if thumbnail_file and Path(thumbnail_file).exists():
        youtube.thumbnails().set(
            videoId=video_id,
            media_body=MediaFileUpload(thumbnail_file)
        ).execute()
        print("[YOUTUBE] Thumbnail enviada com sucesso.")

    resultado = {
        "video_id": video_id,
        "title": title,
        "privacy_status": privacy_status,
    }

    out = Path("videos_gerados") / "youtube_result.json"
    out.write_text(json.dumps(resultado, ensure_ascii=False, indent=2), encoding="utf-8")

    return resultado