# Telegram AI Bot

Google Gemini (tekin API) bilan ishlaydigan oddiy Telegram bot. Har bir chat uchun suhbat tarixini eslab qoladi.

## O'rnatish

1. [@BotFather](https://t.me/BotFather) orqali bot yarating va tokenni oling.
2. [Google AI Studio](https://aistudio.google.com/apikey) dan tekin Gemini API kalit oling.
3. Loyihani sozlang:

```bash
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env          # .env faylini tokenlar bilan to'ldiring
python bot.py
```

## Buyruqlar

- `/start` — botni boshlash
- `/reset` — suhbat tarixini tozalash

## Docker

```bash
docker build -t telegram-ai-bot .
docker run --env-file .env telegram-ai-bot
```

## Eslatma

`.env` faylini hech qachon GitHub'ga yuklamang (`.gitignore` da allaqachon bor).
