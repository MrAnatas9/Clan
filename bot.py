import logging
import requests
import re
import random
from datetime import datetime, timezone, timedelta
from telegram import Update, BotCommand
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from groq import Groq
import os

TELEGRAM_TOKEN = "8626951455:AAED7EIVu45vrpDxFkMDzVHYh7ymK77WWgw"
GROQ_API_KEY = "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"
ADMIN_ID = 6495178643

groq_client = Groq(api_key=GROQ_API_KEY)
logging.basicConfig(level=logging.INFO)
MSK = timezone(timedelta(hours=3))

USERS = {
    "6495178643": {"name": "Анатас", "role": "глава клана", "reputation": 100},
    "7410138240": {"name": "Дайс", "role": "второй глава", "reputation": 90},
    "8312898985": {"name": "Якова", "role": "админ", "reputation": 85},
    "5559866358": {"name": "Бликсер", "role": "админ", "reputation": 80},
    "5866344776": {"name": "Японец", "role": "участник", "reputation": 70},
    "5759237942": {"name": "Булка", "role": "админ", "reputation": 95},
    "1365238364": {"name": "Коунт", "role": "участник", "reputation": 45},
    "7839738821": {"name": "Принцесс", "role": "новичок", "reputation": 75}
}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🤖 Агент Ада здесь! Пиши /help")

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("/start /help /who /me\n\nАнатас: молчать, говорить, репутацию [имя] [число]")

async def who(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = "📊 Участники:\n"
    for uid, data in USERS.items():
        text += f"• {data['name']} - {data['role']}, реп {data['reputation']}\n"
    await update.message.reply_text(text)

async def me(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.message.from_user.id)
    user = USERS.get(uid, {"name": update.message.from_user.first_name, "role": "новичок", "reputation": 50})
    await update.message.reply_text(f"{user['name']}, {user['role']}, реп {user['reputation']}")

def main():
    print("🚀 Бот запущен на Render.com")
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("who", who))
    app.add_handler(CommandHandler("me", me))
    app.run_polling()

if __name__ == "__main__":
    main()
