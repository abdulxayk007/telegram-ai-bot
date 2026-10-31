import logging
import os
from collections import defaultdict, deque

from anthropic import AsyncAnthropic
from dotenv import load_dotenv
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
ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-5-5")
MAX_HISTORY = int(os.getenv("MAX_HISTORY", "20"))  # saqlanadigan xabarlar soni
SYSTEM_PROMPT = os.getenv(
    "SYSTEM_PROMPT",
    "Siz foydali va do'stona yordamchisiz. Foydalanuvchi qaysi tilda yozsa, shu tilda javob bering.",
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

client = AsyncAnthropic(api_key=ANTHROPIC_API_KEY)

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


async def chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_text = update.message.text

    history = histories[chat_id]
    history.append({"role": "user", "content": user_text})
    # Tarix doim "user" xabari bilan boshlanishi kerak
    while history and history[0]["role"] != "user":
        history.popleft()

    await context.bot.send_chat_action(chat_id, ChatAction.TYPING)

    try:
        response = await client.messages.create(
            model=MODEL,
            max_tokens=1500,
            system=SYSTEM_PROMPT,
            messages=list(history),
        )
        answer = "".join(b.text for b in response.content if b.type == "text").strip()
        if not answer:
            answer = "Javob olinmadi, qayta urinib ko'ring."
        history.append({"role": "assistant", "content": answer})
    except Exception:
        logger.exception("AI so'rovida xatolik")
        history.pop()  # muvaffaqiyatsiz so'rovni tarixdan olib tashlaymiz
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
