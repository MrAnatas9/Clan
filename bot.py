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
BOT_USERNAME = "@agent_bot"

# База пользователей (в памяти + файл)
USERS_FILE = "users.json"

def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'r') as f:
            return json.load(f)
    return {
        "6495178643": {"name": "Анатас", "role": "глава клана", "reputation": 100},
        "7410138240": {"name": "Дайс", "role": "второй глава", "reputation": 90},
        "8312898985": {"name": "Якова", "role": "админ", "reputation": 85},
        "5559866358": {"name": "Бликсер", "role": "админ", "reputation": 80},
        "5866344776": {"name": "Японец", "role": "участник", "reputation": 70},
        "5759237942": {"name": "Булка", "role": "админ", "reputation": 95},
        "1365238364": {"name": "Коунт", "role": "участник", "reputation": 45},
        "7839738821": {"name": "Принцесс", "role": "новичок", "reputation": 75}
    }

def save_users(users):
    with open(USERS_FILE, 'w') as f:
        json.dump(users, f, ensure_ascii=False, indent=2)

USERS = load_users()

groq_client = Groq(api_key=GROQ_API_KEY)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
app = Flask(__name__)
MSK = timezone(timedelta(hours=3))
bot_silent = False

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
    if any(w in text.lower() for w in ["смех", "хаха", "шутка", "анекдот"]):
        return random.choice(["😂", "🤣"])
    if any(w in text.lower() for w in ["спасибо", "молодец", "отлично"]):
        return "👍"
    if any(w in text.lower() for w in ["круто", "🔥", "имба"]):
        return "🔥"
    if any(w in text.lower() for w in ["люблю", "❤️"]):
        return "❤️"
    if any(w in text.lower() for w in ["ого", "вау"]):
        return "😲"
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
        system_prompt = f"""Ты Агент Ада - живой помощник.

{admin_prefix}

Сегодня {datetime.now(MSK).strftime("%d.%m.%Y")}, сейчас {datetime.now(MSK).year} год.

Говорит: {user_name}
Вопрос: {user_text}

Отвечай КОРОТКО (1-2 предложения) по-русски, будь живым и естественным."""
        
        response = groq_client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_text}],
            temperature=0.9,
            max_tokens=300
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"AI error: {e}")
        return "Не понял"

def process_message(chat_id, user_id, user_name, text, message_id):
    global bot_silent
    
    if bot_silent:
        return
    
    # Сохраняем пользователя если новый
    if user_id not in USERS:
        USERS[user_id] = {"name": user_name, "role": "новичок", "reputation": 50}
        save_users(USERS)
        print(f"✅ Новый пользователь: {user_name}")
    
    # Админ-команды
    if user_id == str(ADMIN_ID):
        if text.lower() in ["молчать", "молчи"]:
            bot_silent = True
            send_message(chat_id, "😶 Молчу. Скажи 'говорить' чтобы я заговорил")
            return
        if text.lower() in ["говорить", "проснись"]:
            bot_silent = False
            send_message(chat_id, "✅ Я здесь")
            return
        
        match = re.search(r'репутацию\s+(\w+)\s+(\d+)', text.lower())
        if match:
            name = match.group(1)
            new_rep = int(match.group(2))
            for uid, data in USERS.items():
                if data.get("name", "").lower() == name:
                    USERS[uid]["reputation"] = new_rep
                    save_users(USERS)
                    send_message(chat_id, f"✅ Репутация {name} изменена на {new_rep}")
                    return
    
    # Реакция (30% шанс)
    reaction = get_reaction_emoji(text)
    if reaction and random.random() < 0.3:
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
        send_message(chat_id, "Я Агент Ада, умный ИИ-помощник. Ставлю реакции, отвечаю на вопросы.")
        return
    if "погода" in text.lower():
        city_match = re.search(r'погода\s+в\s+(\w+)', text.lower())
        city = city_match.group(1) if city_match else "Москва"
        weather = get_weather(city)
        if weather:
            send_message(chat_id, weather)
            return
    
    # Поиск в интернете
    search_info = None
    if any(w in text.lower() for w in ["найди", "что такое", "кто такой", "новости"]):
        search_info = search_web(text)
    
    is_admin = (user_id == str(ADMIN_ID))
    response = get_ai_response(text, user_name, is_admin)
    if search_info:
        response = response + "\n\n🔍 " + search_info[:200]
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
            message_id = msg.get('message_id')
            
            if text:
                process_message(chat_id, user_id, user_name, text, message_id)
        return 'ok', 200
    except Exception as e:
        logger.error(f"Error: {e}")
        return 'ok', 200

@app.route('/')
def index():
    return 'Agent bot is running!', 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    print(f"🚀 Агент Ада запущен")
    print(f"👑 Админ: {ADMIN_NAME}")
    print("💬 Отвечает на все сообщения в ЛС и @упоминания")
    app.run(host='0.0.0.0', port=port)
