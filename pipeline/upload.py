"""Upload to YouTube as PRIVATE (optionally scheduled with publishAt).

Needs client_secret.json (OAuth Desktop client) in the project root.
The first run opens a browser to log in; the token is saved to token.json.
"""
from __future__ import annotations

import time
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload

from .common import ROOT, Script, to_utc_iso

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
SECRET = ROOT / "client_secret.json"
TOKEN = ROOT / "token.json"


def youtube():
    creds = None
    if TOKEN.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN), SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not SECRET.exists():
                raise SystemExit("client_secret.json not found in the project folder. See README step 4.")
            flow = InstalledAppFlow.from_client_secrets_file(str(SECRET), SCOPES)
            creds = flow.run_local_server(port=0)
        TOKEN.write_text(creds.to_json(), encoding="utf-8")
    return build("youtube", "v3", credentials=creds)


def upload(script: Script, video: Path, thumb: Path | None, cfg: dict) -> str:
    ycfg = cfg.get("youtube", {})
    status = {
        "privacyStatus": "private",
        "selfDeclaredMadeForKids": bool(ycfg.get("made_for_kids", False)),
        "containsSyntheticMedia": script.synthetic_media,
    }
    if script.publish_at:
        status["publishAt"] = to_utc_iso(script.publish_at)
    body = {
        "snippet": {
            "title": script.title[:100],
            "description": script.description[:5000],
            "tags": script.tags,
            "categoryId": script.category_id,
            "defaultLanguage": ycfg.get("language", "en"),
            "defaultAudioLanguage": ycfg.get("language", "en"),
        },
        "status": status,
    }
    yt = youtube()
    media = MediaFileUpload(str(video), mimetype="video/mp4", chunksize=8 * 1024 * 1024, resumable=True)
    req = yt.videos().insert(part="snippet,status", body=body, media_body=media)
    resp, tries = None, 0
    while resp is None:
        try:
            st, resp = req.next_chunk()
            if st:
                print(f"  upload: {int(st.progress() * 100)}%")
        except HttpError as e:
            if e.resp.status in (500, 502, 503, 504) and tries < 5:
                tries += 1
                time.sleep(2 ** tries)
                continue
            raise
    vid = resp["id"]
    print(f"  upload: done -> https://studio.youtube.com/video/{vid}/edit")
    if thumb and thumb.exists():
        try:
            yt.thumbnails().set(videoId=vid, media_body=MediaFileUpload(str(thumb), mimetype="image/png")).execute()
            print("  upload: thumbnail set")
        except HttpError as e:
            print(f"  upload: thumbnail not set ({e.resp.status}). Custom thumbnails need a phone-verified channel.")
    return vid
