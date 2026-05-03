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
GROQ_MODEL = "llama-3.3-70b-versatile"

groq_client = Groq(api_key=GROQ_API_KEY)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
app = Flask(__name__)
MSK = timezone(timedelta(hours=3))

USERS = {}

def send_message(chat_id, text):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.post(url, json={"chat_id": chat_id, "text": text})
    except Exception as e:
        logger.error(f"Send error: {e}")

def send_reaction(chat_id, message_id, emoji):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/setMessageReaction"
        requests.post(url, json={"chat_id": chat_id, "message_id": message_id, "reaction": [{"type": "emoji", "emoji": emoji}]})
    except:
        pass

def get_reaction_emoji(text):
    if any(w in text.lower() for w in ["смех", "хаха", "шутка"]):
        return random.choice(["😂", "🤣"])
    if any(w in text.lower() for w in ["спасибо", "молодец"]):
        return "👍"
    if any(w in text.lower() for w in ["круто", "🔥"]):
        return "🔥"
    if any(w in text.lower() for w in ["люблю", "❤️"]):
        return "❤️"
    return None

def get_ai_response(text, user_name):
    try:
        prompt = f"""Ты Агент Ада - умный помощник. Сегодня {datetime.now(MSK).strftime('%d.%m.%Y')}.

Пользователь {user_name} спрашивает: {text}

Отвечай коротко (1-2 предложения) по-русски, будь дружелюбным."""
        
        response = groq_client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.9,
            max_tokens=200
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"AI error: {e}")
        return "Не понял"

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
            message_id = msg.get('message_id')
            
            if text:
                # Реакция
                reaction = get_reaction_emoji(text)
                if reaction and random.random() < 0.3:
                    send_reaction(chat_id, message_id, reaction)
                
                # Команды
                if text.lower() == "/start":
                    send_message(chat_id, "🤖 Агент Ада здесь! Задавай вопросы.")
                    return 'ok', 200
                if text.lower() == "/help":
                    send_message(chat_id, "/start - начать\n/help - помощь")
                    return 'ok', 200
                if text.lower() in ["дата", "какое сегодня число"]:
                    send_message(chat_id, datetime.now(MSK).strftime("%d.%m.%Y"))
                    return 'ok', 200
                if text.lower() in ["время", "который час"]:
                    send_message(chat_id, datetime.now(MSK).strftime("%H:%M"))
                    return 'ok', 200
                if text.lower() == "кто я":
                    send_message(chat_id, f"Ты {user_name}")
                    return 'ok', 200
                
                # Админ-команды
                if user_id == str(ADMIN_ID):
                    if text.lower() in ["молчать", "молчи"]:
                        send_message(chat_id, "😶 Молчу")
                        return 'ok', 200
                    if text.lower() in ["говорить", "проснись"]:
                        send_message(chat_id, "✅ Я здесь")
                        return 'ok', 200
                
                # Обычный ответ
                response = get_ai_response(text, user_name)
                send_message(chat_id, response)
        return 'ok', 200
    except Exception as e:
        logger.error(f"Error: {e}")
        return 'ok', 200

@app.route('/')
def index():
    return 'Agent bot is running!', 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    print("🚀 Агент Ада запущен")
    app.run(host='0.0.0.0', port=port)
