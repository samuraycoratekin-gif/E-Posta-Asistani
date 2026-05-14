import logging
import json
from openai import OpenAI

logger = logging.getLogger(__name__)

CLASSIFICATION_PROMPT = """Sen bir e-posta asistanisin. Asagidaki e-postayi analiz et ve JSON formatinda yanit ver.

Gorevin:
1. E-postanin "gereksiz" mi yoksa "onemli" mi oldugunu belirle.
2. Eger onemliyse, kullanici adina profesyonel ve nazik bir taslak yanit yaz.

"Gereksiz" sayilan e-postalar:
- Promosyon, kampanya, indirim bildirimleri
- Newsletter / bulten abonelikleri
- Otomatik sistem bildirimleri
- Reklam veya spam
- Sosyal medya bildirim e-postalari
- Toplu gonderim (bulk mail)

"Onemli" sayilan e-postalar:
- Gercek bir kisiden gelen ve cevap bekleyen mesajlar
- Is teklifi, is birligi onerisi
- Fatura, sozlesme veya resmi yazismalar
- Kisisel sorular veya talepler
- Musteri veya is ortagindan gelen mesajlar

E-Posta Bilgileri:
- Gonderen: {sender}
- Konu: {subject}
- Tarih: {date}
- Icerik:
{body}

Yanit formati (saf JSON, baska bir sey yazma):
{{
  "classification": "gereksiz" veya "onemli",
  "reason": "Kisa bir aciklama",
  "draft_reply": "Yanit metni (sadece 'onemli' ise doldur, 'gereksiz' ise null)"
}}
"""

def classify_email(client, model, email):
    prompt = CLASSIFICATION_PROMPT.format(sender=email["sender"], subject=email["subject"], date=email["date"], body=email["body"])
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "Sen bir e-posta yonetim asistanisin. Yanitlarini yalnizca saf JSON olarak ver."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            response_format={"type": "json_object"},
        )
        result = json.loads(response.choices[0].message.content)
        logger.info(f"   Siniflandirma: {result.get('classification', '?')} - {result.get('reason', '')[:80]}")
        return result
    except Exception as e:
        logger.error(f"   AI analiz hatasi: {e}")
        return {"classification": "onemli", "reason": f"AI analiz sirasinda hata olustu: {str(e)}", "draft_reply": None}
