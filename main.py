import os
import sys
import logging
from datetime import datetime
from dotenv import load_dotenv
from openai import OpenAI
from gmail_service import get_gmail_service, fetch_unread_emails, mark_as_read, create_draft_reply
from ai_analyzer import classify_email

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
CREDENTIALS_PATH = os.getenv("GMAIL_CREDENTIALS_PATH", "credentials.json")
TOKEN_PATH = os.getenv("GMAIL_TOKEN_PATH", "token.json")
LOG_FILE = os.getenv("LOG_FILE", "email_assistant.log")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.FileHandler(LOG_FILE, encoding="utf-8"), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

def run_email_assistant():
    start = datetime.now()
    logger.info("=" * 60)
    logger.info(f"E-Posta Asistani baslatildi - {start.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 60)
    gmail = get_gmail_service(CREDENTIALS_PATH, TOKEN_PATH)
    ai_client = OpenAI(api_key=OPENAI_API_KEY)
    emails = fetch_unread_emails(gmail)
    if not emails:
        logger.info("Islenecek mail yok. Cikiliyor.")
        return
    stats = {"toplam": len(emails), "gereksiz": 0, "onemli": 0, "hata": 0}
    for i, email in enumerate(emails, 1):
        logger.info(f"\n[{i}/{len(emails)}] Gonderen: {email['sender']}")
        logger.info(f"   Konu: {email['subject']}")
        try:
            result = classify_email(ai_client, OPENAI_MODEL, email)
            classification = result.get("classification", "onemli")
            if classification == "gereksiz":
                mark_as_read(gmail, email["id"])
                stats["gereksiz"] += 1
                logger.info(f"   Gereksiz -> okundu. Sebep: {result.get('reason', '')[:60]}")
            else:
                stats["onemli"] += 1
                draft_reply = result.get("draft_reply")
                if draft_reply:
                    create_draft_reply(gmail, email, draft_reply)
                    logger.info("   Onemli -> taslak yanit hazirlandi.")
                else:
                    logger.info("   Onemli ama yanit uretilemedi. Manuel kontrol gerekli.")
        except Exception as e:
            stats["hata"] += 1
            logger.error(f"   Hata: {e}")
    elapsed = (datetime.now() - start).total_seconds()
    logger.info("\n" + "=" * 60)
    logger.info("GUNLUK OZET RAPOR")
    logger.info(f"   Toplam mail     : {stats['toplam']}")
    logger.info(f"   Gereksiz (okundu): {stats['gereksiz']}")
    logger.info(f"   Onemli (taslak) : {stats['onemli']}")
    logger.info(f"   Hata            : {stats['hata']}")
    logger.info(f"   Sure            : {elapsed:.1f} saniye")
    logger.info("=" * 60)

if __name__ == "__main__":
    run_email_assistant()
