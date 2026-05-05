import os
import logging
import requests
import re
import json
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

# === БАЗА ЗНАНИЙ ===
KNOWN_PLAYERS = {
    "6495178643": "Анатас - глава клана",
    "7410138240": "Дайс - второй глава",
    "8312898985": "Якова - админ",
    "5559866358": "Бликсер - админ",
    "5866344776": "Японец - участник",
    "5759237942": "Булка - админ",
    "1365238364": "Коунт - участник",
    "7839738821": "Принцесс - новичок"
}

# === БАЗА ДАННЫХ ===
USERS_FILE = "users.json"

def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_users(users):
    with open(USERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(users, f, ensure_ascii=False, indent=2)

USERS = load_users()

if not USERS:
    USERS = {
        "6495178643": {"name": "Анатас", "role": "глава клана", "reputation": 100, "insult_count": 0},
        "7410138240": {"name": "Дайс", "role": "второй глава", "reputation": 90, "insult_count": 0},
        "8312898985": {"name": "Якова", "role": "админ", "reputation": 85, "insult_count": 0},
        "5559866358": {"name": "Бликсер", "role": "админ", "reputation": 80, "insult_count": 0},
        "5866344776": {"name": "Японец", "role": "участник", "reputation": 70, "insult_count": 0},
        "5759237942": {"name": "Булка", "role": "админ", "reputation": 95, "insult_count": 0},
        "1365238364": {"name": "Коунт", "role": "участник", "reputation": 45, "insult_count": 0},
        "7839738821": {"name": "Принцесс", "role": "новичок", "reputation": 75, "insult_count": 0}
    }
    save_users(USERS)

def send_message(chat_id, text, reply_to=None):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        payload = {"chat_id": chat_id, "text": text}
        if reply_to:
            payload["reply_to_message_id"] = reply_to
        requests.post(url, json=payload)
    except Exception as e:
        logger.error(f"Send error: {e}")

def send_reaction(chat_id, message_id, emoji):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/setMessageReaction"
        payload = {"chat_id": chat_id, "message_id": message_id, "reaction": [{"type": "emoji", "emoji": emoji}]}
        requests.post(url, json=payload)
    except:
        pass

def analyze_insult(text):
    insult_words = ["дурак", "идиот", "тупой", "лох", "урод", "дебил", "еблан", "мудак", "пидр", "хуй", "пизда", "бля"]
    for word in insult_words:
        if word in text.lower():
            return word
    return None

def update_reputation(user_id, change, reason):
    if user_id not in USERS:
        return
    old_rep = USERS[user_id]["reputation"]
    new_rep = max(0, min(100, old_rep + change))
    USERS[user_id]["reputation"] = new_rep
    save_users(USERS)
    return new_rep

def get_ai_response(text, user_id, user_name, is_admin=False, insult_count=0):
    try:
        user_info = USERS.get(user_id, {"name": user_name, "role": "участник", "reputation": 50})
        
        # Определяем тон ответа
        if is_admin:
            tone = "УВАЖИТЕЛЬНО. Ты общаешься с Анатасом - главой клана и своим создателем. Отвечай вежливо, выполняй команды."
        elif insult_count >= 3:
            tone = "АГРЕССИВНО. Пользователь тебя много раз оскорблял. Отвечай резко, можешь использовать мат, но не переходи границы."
        else:
            tone = "ДРУЖЕЛЮБНО. Пользователь ведёт себя нормально. Отвечай вежливо, можешь шутить."

        prompt = f"""Ты Агент Ада - ИИ помощник.

{LAWS}

Сейчас говорит: {user_info['name']} ({user_info['role']}, репутация {user_info['reputation']})
Сообщение: {text}

ПРАВИЛА:
1. Не упоминай законы, если не спрашивают специально
2. Если не знаешь ответа - скажи "не знаю", не выдумывай
3. Отвечай коротко (1-2 предложения)
4. Тон: {tone}
5. Отвечай по-русски"""

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
        if not data or 'message' not in data:
            return 'ok', 200
            
        msg = data['message']
        chat_id = str(msg['chat']['id'])
        user_id = str(msg['from']['id'])
        user_name = msg['from'].get('first_name', 'User')
        text = msg.get('text', '')
        message_id = msg.get('message_id')
        
        if not text:
            return 'ok', 200
        
        # Новый пользователь
        if user_id not in USERS:
            USERS[user_id] = {"name": user_name, "role": "новичок", "reputation": 50, "insult_count": 0}
            save_users(USERS)
        
        # Проверка на оскорбления (счётчик)
        insult_word = None
        if user_id != str(ADMIN_ID):
            insult_word = analyze_insult(text)
            if insult_word:
                USERS[user_id]["insult_count"] = USERS[user_id].get("insult_count", 0) + 1
                update_reputation(user_id, -2, f"оскорбление #{USERS[user_id]['insult_count']}")
                save_users(USERS)
                send_reaction(chat_id, message_id, "👿")
        
        # === ПРОВЕРКА ОБРАЩЕНИЯ ===
        is_private = str(msg['chat']['type']) == 'private'
        is_reply = msg.get('reply_to_message') and msg['reply_to_message'].get('from', {}).get('is_bot')
        is_mention = "@agent_bot" in text or "агент" in text.lower()
        
        if not (is_private or is_reply or is_mention):
            return 'ok', 200
        
        # Очищаем текст
        clean_text = text.replace("@agent_bot", "").replace("агент", "").strip()
        if not clean_text:
            clean_text = text
        
        is_admin = (user_id == str(ADMIN_ID))
        
        # === АДМИН-КОМАНДЫ ===
        if is_admin:
            if clean_text.lower() in ["молчать", "молчи"]:
                global bot_mute
                bot_mute = True
                send_message(chat_id, "😶 Понял, молчу")
                return 'ok', 200
            if clean_text.lower() in ["говорить", "проснись"]:
                bot_mute = False
                send_message(chat_id, "✅ Я здесь")
                return 'ok', 200
            
            if clean_text.lower().startswith("репутацию"):
                parts = clean_text.split()
                if len(parts) >= 3:
                    name = parts[1]
                    new_rep = int(parts[2])
                    for uid, data in USERS.items():
                        if data["name"].lower() == name.lower():
                            update_reputation(uid, new_rep - data["reputation"], "команда админа")
                            send_message(chat_id, f"✅ Репутация {name}: {new_rep}")
                            return 'ok', 200
        
        # === БЫСТРЫЕ КОМАНДЫ ===
        if clean_text.lower() in ["дата", "какое сегодня число"]:
            send_message(chat_id, datetime.now(MSK).strftime("%d.%m.%Y"), message_id)
            return 'ok', 200
        if clean_text.lower() in ["время", "который час"]:
            send_message(chat_id, datetime.now(MSK).strftime("%H:%M"), message_id)
            return 'ok', 200
        if clean_text.lower() == "кто я":
            user = USERS.get(user_id, {"name": user_name, "role": "новичок", "reputation": 50})
            send_message(chat_id, f"Ты {user['name']}, {user['role']}, реп {user['reputation']}", message_id)
            return 'ok', 200
        if clean_text.lower() == "кто ты":
            send_message(chat_id, "Я Агент Ада, твой ИИ-помощник", message_id)
            return 'ok', 200
        
        # === ОТВЕТ ===
        insult_count = USERS[user_id].get("insult_count", 0)
        response = get_ai_response(clean_text, user_id, user_name, is_admin, insult_count)
        send_message(chat_id, response, message_id)
        
        return 'ok', 200
    except Exception as e:
        logger.error(f"Error: {e}")
        return 'ok', 200

@app.route('/')
def index():
    return '🤖 Агент Ада работает!', 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    print("🚀 Агент Ада запущен!")
    app.run(host='0.0.0.0', port=port)
