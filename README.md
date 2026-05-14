# E-Posta Asistani

Her gun sabah 09:00'da (TR) gelen kutunuzu otonom olarak yoneten AI destekli e-posta asistani.

## Ne Yapar?
1. Gmail API ile okunmamis mailleri tarar
2. OpenAI GPT-4.1-mini ile siniflandirir (gereksiz/onemli)
3. Gereksiz mailleri otomatik okundu isaretler
4. Onemli maillere taslak yanit hazirlayip Gmail Taslaklar'a kaydeder
5. Asla kendiligindan gondermez

## Railway Deploy
Environment variables olarak ayarlayin:
- `OPENAI_API_KEY`
- `GMAIL_CREDENTIALS_JSON` (credentials.json icerigi)
- `GMAIL_TOKEN_JSON` (token.json icerigi)
