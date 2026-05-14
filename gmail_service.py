import os
import base64
import logging
from email.mime.text import MIMEText
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

logger = logging.getLogger(__name__)
SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.compose",
]

def _ensure_file_from_env(file_path, env_var):
    if not os.path.exists(file_path):
        content = os.getenv(env_var)
        if content:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            logger.info(f"{file_path} env'den olusturuldu ({env_var})")

def get_gmail_service(credentials_path, token_path):
    _ensure_file_from_env(credentials_path, "GMAIL_CREDENTIALS_JSON")
    _ensure_file_from_env(token_path, "GMAIL_TOKEN_JSON")
    creds = None
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            with open(token_path, "w") as f:
                f.write(creds.to_json())
            logger.info("Token yenilendi.")
        else:
            if os.getenv("RAILWAY_ENVIRONMENT"):
                raise RuntimeError("Gmail OAuth token gecersiz. Lokalde yenileyin.")
            flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
            creds = flow.run_local_server(port=3000)
        with open(token_path, "w") as f:
            f.write(creds.to_json())
    service = build("gmail", "v1", credentials=creds)
    logger.info("Gmail API servisine basariyla baglandi.")
    return service

def fetch_unread_emails(service, max_results=50):
    results = service.users().messages().list(userId="me", labelIds=["INBOX", "UNREAD"], maxResults=max_results).execute()
    messages = results.get("messages", [])
    if not messages:
        logger.info("Okunmamis mail bulunamadi.")
        return []
    logger.info(f"{len(messages)} okunmamis mail bulundu.")
    emails = []
    for msg_meta in messages:
        msg = service.users().messages().get(userId="me", id=msg_meta["id"], format="full").execute()
        headers = msg.get("payload", {}).get("headers", [])
        subject = next((h["value"] for h in headers if h["name"] == "Subject"), "(Konu yok)")
        sender = next((h["value"] for h in headers if h["name"] == "From"), "(Bilinmeyen)")
        date = next((h["value"] for h in headers if h["name"] == "Date"), "")
        body = _extract_body(msg.get("payload", {}))
        emails.append({"id": msg_meta["id"], "thread_id": msg.get("threadId"), "subject": subject, "sender": sender, "date": date, "body": body[:3000]})
    return emails

def _extract_body(payload):
    if payload.get("body", {}).get("data"):
        return base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8", errors="replace")
    parts = payload.get("parts", [])
    for part in parts:
        if part.get("mimeType") == "text/plain" and part.get("body", {}).get("data"):
            return base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8", errors="replace")
    for part in parts:
        if part.get("mimeType") == "text/html" and part.get("body", {}).get("data"):
            html = base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8", errors="replace")
            try:
                from bs4 import BeautifulSoup
                return BeautifulSoup(html, "html.parser").get_text(separator="\n", strip=True)
            except ImportError:
                return html
    for part in parts:
        if part.get("parts"):
            result = _extract_body(part)
            if result:
                return result
    return "(Icerik okunamadi)"

def mark_as_read(service, message_id):
    service.users().messages().modify(userId="me", id=message_id, body={"removeLabelIds": ["UNREAD"]}).execute()
    logger.info(f"   Okundu isaretlendi: {message_id}")

def create_draft_reply(service, original_email, reply_body):
    message = MIMEText(reply_body)
    message["to"] = original_email["sender"]
    message["subject"] = f"Re: {original_email['subject']}"
    message["In-Reply-To"] = original_email["id"]
    message["References"] = original_email["id"]
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
    draft = service.users().drafts().create(userId="me", body={"message": {"raw": raw, "threadId": original_email["thread_id"]}}).execute()
    logger.info(f"   Taslak olusturuldu: {original_email['subject']}")
    return draft
