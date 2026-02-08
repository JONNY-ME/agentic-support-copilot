import os
import logging

import httpx
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("telegram_bot")


API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000").rstrip("/")
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")


async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (
        "Hi! Send a message and I will route it to the support copilot.\n"
        "Example: Where is my order ETH-1001?\n"
        "Example: ቅሬታ አለኝ እቃው ተሰብሯል"
    )
    if update.message:
        await update.message.reply_text(text)


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (
        "Try:\n"
        "- Order status: ETH-1001\n"
        "- Complaint: describe the issue\n"
        "- Callback: 'call me' or 'ደውሉልኝ'\n"
        "- Human: 'human agent' or 'ሰው ኤጀንት'"
    )
    if update.message:
        await update.message.reply_text(text)


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return

    msg = (update.message.text or "").strip()
    if not msg:
        return

    user = update.effective_user
    external_id = f"telegram:{user.id}" if user else "telegram:unknown"

    payload = {
        "external_id": external_id,
        "channel": "telegram",
        "message": msg,
    }

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            r = await client.post(f"{API_BASE_URL}/chat", json=payload)
            r.raise_for_status()
            data = r.json()

        reply = data.get("reply") or "Sorry, I had trouble generating a reply."
        await update.message.reply_text(reply)

    except Exception as e:
        logger.exception("Failed to call API /chat: %s", e)
        await update.message.reply_text(
            "Sorry, the service is temporarily unavailable. Please try again."
        )


def main() -> None:
    if not BOT_TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is not set")

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    logger.info("Telegram bot started. Using API_BASE_URL=%s", API_BASE_URL)
    app.run_polling(close_loop=False)


if __name__ == "__main__":
    main()
