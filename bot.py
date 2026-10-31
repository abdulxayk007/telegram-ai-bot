import logging
import os
from collections import defaultdict, deque

from dotenv import load_dotenv
from google import genai
from google.genai import types
from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

load_dotenv()

TELEGRAM_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]
MODEL = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")
MAX_HISTORY = int(os.getenv("MAX_HISTORY", "20"))  # saqlanadigan xabarlar soni
SYSTEM_PROMPT = os.getenv(
    "SYSTEM_PROMPT",
    "Siz foydali va do'stona yordamchisiz. Foydalanuvchi qaysi tilda yozsa, shu tilda javob bering.",
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
# So'rov manzillarida token chiqib qolmasligi uchun
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

client = genai.Client(api_key=GEMINI_API_KEY)

# Har bir chat uchun suhbat tarixi (xotirada saqlanadi)
histories: dict[int, deque] = defaultdict(lambda: deque(maxlen=MAX_HISTORY))


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Salom! 👋 Men AI yordamchiman. Savolingizni yozing.\n\n"
        "/reset — suhbat tarixini tozalash"
    )


async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    histories[update.effective_chat.id].clear()
    await update.message.reply_text("Suhbat tarixi tozalandi ✅")


def split_message(text: str, limit: int = 4000):
    for i in range(0, len(text), limit):
        yield text[i : i + limit]


def build_contents(history):
    return [
        types.Content(role=role, parts=[types.Part(text=text)])
        for role, text in history
    ]


async def chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_text = update.message.text

    history = histories[chat_id]
    history.append(("user", user_text))
    # Tarix doim "user" xabari bilan boshlanishi kerak
    while history and history[0][0] != "user":
        history.popleft()

    await context.bot.send_chat_action(chat_id, ChatAction.TYPING)

    try:
        response = await client.aio.models.generate_content(
            model=MODEL,
            contents=build_contents(history),
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                max_output_tokens=1500,
            ),
        )
        answer = (response.text or "").strip()
        if not answer:
            answer = "Javob olinmadi, qayta urinib ko'ring."
        history.append(("model", answer))
    except Exception as e:
        logger.exception("AI so'rovida xatolik")
        history.pop()  # muvaffaqiyatsiz so'rovni tarixdan olib tashlaymiz
        if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
            answer = "Tekin limit vaqtincha tugadi. Bir daqiqadan keyin qayta urinib ko'ring."
        else:
            answer = "Kechirasiz, xatolik yuz berdi. Birozdan keyin qayta urinib ko'ring."

    for part in split_message(answer):
        await update.message.reply_text(part)


def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("reset", reset))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, chat))
    logger.info("Bot ishga tushdi...")
    app.run_polling()


if __name__ == "__main__":
    main()
