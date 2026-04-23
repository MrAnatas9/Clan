import os
import logging
import requests
import re
import random
from datetime import datetime, timezone, timedelta
from flask import Flask, request
from groq import Groq

TELEGRAM_TOKEN = "8626951455:AAED7EIVu45vrpDxFkMDzVHYh7ymK77WWgw"
GROQ_API_KEY = "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"
ADMIN_ID = 6495178643

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
app = Flask(__name__)
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

groq_client = Groq(api_key=GROQ_API_KEY)
bot_active = True

def send_message(chat_id, text):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.post(url, json={"chat_id": chat_id, "text": text})
    except Exception as e:
        logger.error(f"Send error: {e}")

def get_ai_response(text, user_name):
    try:
        system_prompt = f"""Ты Агент Ада - помощник в чате клана Ад.

Сегодня {datetime.now(MSK).strftime("%d.%m.%Y")}, {datetime.now(MSK).year} год.

Правила:
1. Отвечай КОРОТКО (1-2 предложения)
2. Не используй мат и грубости
3. Отвечай по-русски
4. Будь полезным

Пользователь {user_name} спрашивает: {text}"""
        
        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": text}],
            temperature=0.7,
            max_tokens=200
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"AI error: {e}")
        return "Не понял"

def process_message(chat_id, user_id, user_name, text):
    global bot_active
    
    logger.info(f"Message from {user_name}: {text}")
    
    if not bot_active:
        return
    
    # Админ-команды
    if user_id == str(ADMIN_ID):
        if text.lower() == "молчать":
            bot_active = False
            send_message(chat_id, "😶 Молчу")
            return
        if text.lower() == "говорить":
            bot_active = True
            send_message(chat_id, "✅ Я здесь")
            return
    
    # Обработка команд
    if text.lower() == "/start":
        send_message(chat_id, "🤖 Агент Ада здесь!")
        return
    if text.lower() == "/help":
        send_message(chat_id, "/start /help /who /me")
        return
    if text.lower() == "/who":
        msg = "📊 Участники:\n"
        for uid, data in USERS.items():
            msg += f"• {data['name']} - {data['role']}, реп {data['reputation']}\n"
        send_message(chat_id, msg)
        return
    if text.lower() == "/me":
        user = USERS.get(user_id, {"name": user_name, "role": "новичок"})
        send_message(chat_id, f"{user['name']}, {user['role']}")
        return
    if text.lower() in ["дата", "число"]:
        send_message(chat_id, datetime.now(MSK).strftime("%d.%m.%Y"))
        return
    if text.lower() in ["время", "час"]:
        send_message(chat_id, datetime.now(MSK).strftime("%H:%M"))
        return
    if text.lower() == "кто я":
        user = USERS.get(user_id, {"name": user_name})
        send_message(chat_id, f"Ты {user['name']}")
        return
    
    # Обычный ответ
    response = get_ai_response(text, user_name)
    send_message(chat_id, response)

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        data = request.get_json()
        if data and 'message' in data:
            msg = data['message']
            chat_id = str(msg['chat']['id'])
            user_id = str(msg['from']['id'])
            user_name = msg['from'].get('first_name', 'User')
            text = msg.get('text', '')
            if text:
                process_message(chat_id, user_id, user_name, text)
        return 'ok', 200
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return 'ok', 200

@app.route('/')
def index():
    return 'Bot is running', 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
