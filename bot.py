import os
import logging
import requests
import re
import random
from datetime import datetime, timezone, timedelta
from flask import Flask, request
from groq import Groq

# Конфигурация
TELEGRAM_TOKEN = "8626951455:AAED7EIVu45vrpDxFkMDzVHYh7ymK77WWgw"
GROQ_API_KEY = "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"
ADMIN_ID = 6495178643
ADMIN_NAME = "Анатас"
GROQ_MODEL = "llama-3.3-70b-versatile"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
MSK = timezone(timedelta(hours=3))
bot_active = True

# Участники
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

# === ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ===
def get_reaction_emoji(text):
    if any(w in text.lower() for w in ["смех", "хаха", "шутка"]):
        return "😂"
    if any(w in text.lower() for w in ["спасибо", "молодец"]):
        return "👍"
    if any(w in text.lower() for w in ["круто", "🔥"]):
        return "🔥"
    if any(w in text.lower() for w in ["люблю", "❤️"]):
        return "❤️"
    return None

def search_web(query):
    try:
        url = "https://api.duckduckgo.com/"
        params = {"q": query, "format": "json", "no_html": 1}
        r = requests.get(url, params=params, timeout=8)
        if r.status_code == 200 and r.json().get("AbstractText"):
            return r.json()["AbstractText"][:400]
    except:
        pass
    return None

def get_weather(city):
    try:
        url = f"https://wttr.in/{city}?format=%t+%c"
        r = requests.get(url, timeout=8)
        if r.status_code == 200:
            return r.text.strip()
    except:
        pass
    return None

def get_ai_response(user_text, user_name, is_admin=False):
    try:
        admin_prefix = "ВНИМАНИЕ: Это АНАТАС - твой создатель!" if is_admin else ""
        system_prompt = f"""Ты Агент Ада - помощник.

{admin_prefix}

Сегодня {datetime.now(MSK).strftime("%d.%m.%Y")}, сейчас {datetime.now(MSK).year} год.

Говорит: {user_name}
Вопрос: {user_text}

Отвечай КОРОТКО (1-2 предложения) по-русски."""
        
        response = groq_client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_text}],
            temperature=0.9,
            max_tokens=300
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"AI ошибка: {e}")
        return "Не понял"

def send_message(chat_id, text):
    """Отправка сообщения через Telegram API"""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    try:
        requests.post(url, json=payload)
    except Exception as e:
        logger.error(f"Ошибка отправки: {e}")

def send_reaction(chat_id, message_id, emoji):
    """Отправка реакции"""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/setMessageReaction"
    payload = {"chat_id": chat_id, "message_id": message_id, "reaction": [{"type": "emoji", "emoji": emoji}]}
    try:
        requests.post(url, json=payload)
    except:
        pass

def process_message(chat_id, user_id, user_name, text, message_id):
    """Обработка сообщения"""
    global bot_active
    
    if not bot_active:
        return
    
    # Админ-команды
    if user_id == str(ADMIN_ID):
        if text.lower() in ["молчать", "молчи"]:
            bot_active = False
            send_message(chat_id, "😶 Молчу")
            return
        if text.lower() in ["говорить", "проснись"]:
            bot_active = True
            send_message(chat_id, "✅ Я здесь")
            return
        
        match = re.search(r'репутацию\s+(\w+)\s+(\d+)', text.lower())
        if match:
            name = match.group(1)
            new_rep = int(match.group(2))
            for uid, data in USERS.items():
                if data["name"].lower() == name:
                    USERS[uid]["reputation"] = new_rep
                    send_message(chat_id, f"✅ Репутация {name} изменена на {new_rep}")
                    return
    
    # Реакция
    reaction = get_reaction_emoji(text)
    if reaction:
        send_reaction(chat_id, message_id, reaction)
    
    # Быстрые команды
    if text.lower() in ["дата", "какое сегодня число"]:
        send_message(chat_id, datetime.now(MSK).strftime("%d.%m.%Y"))
        return
    if text.lower() in ["время", "который час"]:
        send_message(chat_id, datetime.now(MSK).strftime("%H:%M"))
        return
    if text.lower() == "кто я":
        user = USERS.get(user_id, {"name": user_name, "role": "новичок", "reputation": 50})
        send_message(chat_id, f"Ты {user['name']}, {user['role']}, реп {user['reputation']}")
        return
    if text.lower() == "кто ты":
        send_message(chat_id, "Я Агент Ада, ИИ-помощник")
        return
    if "погода" in text.lower():
        city_match = re.search(r'погода\s+в\s+(\w+)', text.lower())
        city = city_match.group(1) if city_match else "Москва"
        weather = get_weather(city)
        if weather:
            send_message(chat_id, weather)
            return
    
    # Поиск
    search_info = None
    if any(w in text.lower() for w in ["найди", "что такое", "кто такой", "новости"]):
        search_info = search_web(text)
    
    is_admin = (user_id == str(ADMIN_ID))
    response = get_ai_response(text, user_name, is_admin)
    send_message(chat_id, response)

# === ФЛАСК ВЕБХУК ===
@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        data = request.get_json()
        if not data:
            return 'ok', 200
        
        # Обработка сообщения
        if 'message' in data:
            msg = data['message']
            chat_id = str(msg['chat']['id'])
            user_id = str(msg['from']['id'])
            user_name = msg['from'].get('first_name', 'User')
            text = msg.get('text', '')
            message_id = msg.get('message_id')
            
            if text:
                process_message(chat_id, user_id, user_name, text, message_id)
        
        return 'ok', 200
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        return 'ok', 200

@app.route('/health')
def health():
    return 'ok', 200

@app.route('/')
def index():
    return 'Agent bot is running!', 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    print(f"🚀 Бот запущен на порту {port}")
    app.run(host='0.0.0.0', port=port)
