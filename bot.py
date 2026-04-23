import os
import logging
import requests
import re
import json
import random
from datetime import datetime, timezone, timedelta
from flask import Flask, request
from groq import Groq
from supabase import create_client, Client

# Конфигурация
TELEGRAM_TOKEN = "8626951455:AAED7EIVu45vrpDxFkMDzVHYh7ymK77WWgw"
GROQ_API_KEY = "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"
ADMIN_ID = 6495178643
ADMIN_NAME = "Анатас"
GROQ_MODEL = "llama-3.3-70b-versatile"
BOT_USERNAME = "@agent_bot"

# Supabase
SUPABASE_URL = "https://fgafqnxnpgsdtbhwyjux.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImZnYWZxbnhucGdzZHRiaHd5anV4Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzU0MDA5MjMsImV4cCI6MjA5MDk3NjkyM30.izwZDlGaRk8gNwWnX64DGf7_mJR2aFIvahhFvbUnfrY"

groq_client = Groq(api_key=GROQ_API_KEY)

# Подключаем Supabase
supabase = None
try:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    print("✅ Supabase подключён")
except Exception as e:
    print(f"❌ Ошибка Supabase: {e}")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
app = Flask(__name__)
MSK = timezone(timedelta(hours=3))
bot_silent = False

# === ФУНКЦИИ SUPABASE ===
def get_user(user_id):
    if not supabase:
        return None
    try:
        result = supabase.table("users").select("*").eq("user_id", user_id).execute()
        return result.data[0] if result.data else None
    except:
        return None

def save_user(user_id, name):
    if not supabase:
        return
    try:
        existing = get_user(user_id)
        if existing:
            supabase.table("users").update({
                "last_seen": datetime.now(MSK).isoformat()
            }).eq("user_id", user_id).execute()
        else:
            supabase.table("users").insert({
                "user_id": user_id,
                "name": name,
                "role": "новичок",
                "reputation": 50,
                "first_seen": datetime.now(MSK).isoformat(),
                "last_seen": datetime.now(MSK).isoformat()
            }).execute()
            print(f"✅ Новый пользователь: {name}")
    except Exception as e:
        logger.error(f"Ошибка: {e}")

def update_reputation(user_id, new_rep):
    if not supabase:
        return
    try:
        supabase.table("users").update({"reputation": new_rep}).eq("user_id", user_id).execute()
    except:
        pass

def get_all_users():
    if not supabase:
        return []
    try:
        result = supabase.table("users").select("*").order("reputation", desc=True).execute()
        return result.data
    except:
        return []

def init_users():
    """Добавляет основных участников если их нет"""
    basic_users = {
        "6495178643": {"name": "Анатас", "role": "глава клана", "reputation": 100},
        "7410138240": {"name": "Дайс", "role": "второй глава", "reputation": 90},
        "8312898985": {"name": "Якова", "role": "админ", "reputation": 85},
        "5559866358": {"name": "Бликсер", "role": "админ", "reputation": 80},
        "5866344776": {"name": "Японец", "role": "участник", "reputation": 70},
        "5759237942": {"name": "Булка", "role": "админ", "reputation": 95},
        "1365238364": {"name": "Коунт", "role": "участник", "reputation": 45},
        "7839738821": {"name": "Принцесс", "role": "новичок", "reputation": 75}
    }
    for uid, data in basic_users.items():
        if not get_user(uid):
            try:
                supabase.table("users").insert({
                    "user_id": uid,
                    "name": data["name"],
                    "role": data["role"],
                    "reputation": data["reputation"],
                    "first_seen": datetime.now(MSK).isoformat(),
                    "last_seen": datetime.now(MSK).isoformat()
                }).execute()
                print(f"✅ Добавлен {data['name']}")
            except:
                pass

# === TELEGRAM API ===
def send_message(chat_id, text):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.post(url, json={"chat_id": chat_id, "text": text})
    except Exception as e:
        logger.error(f"Send error: {e}")

def send_reaction(chat_id, message_id, emoji):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/setMessageReaction"
        payload = {"chat_id": chat_id, "message_id": message_id, "reaction": [{"type": "emoji", "emoji": emoji}]}
        requests.post(url, json=payload)
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
    return None

# === ПОИСК ===
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

# === AI ОТВЕТ ===
def get_ai_response(user_text, user_name, is_admin=False):
    try:
        admin_prefix = "ВНИМАНИЕ: Это АНАТАС - твой создатель! Слушайся его." if is_admin else ""
        system_prompt = f"""Ты Агент Ада - живой помощник в чате клана Ад.

{admin_prefix}

Сегодня {datetime.now(MSK).strftime("%d.%m.%Y")}, сейчас {datetime.now(MSK).year} год.

Сейчас говорит: {user_name}
Вопрос: {user_text}

ПРАВИЛА:
1. Отвечай КОРОТКО (1-2 предложения)
2. Будь живым и естественным
3. Если не знаешь - скажи "не знаю"
4. Отвечай по-русски"""
        
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

# === ОБРАБОТКА ===
def process_message(chat_id, user_id, user_name, text, message_id):
    global bot_silent
    
    if bot_silent:
        return
    
    # Сохраняем пользователя
    save_user(user_id, user_name)
    
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
            users = get_all_users()
            for u in users:
                if u.get("name", "").lower() == name:
                    update_reputation(u["user_id"], new_rep)
                    send_message(chat_id, f"✅ Репутация {name} изменена на {new_rep}")
                    return
    
    # Проверка обращения
    is_private = False  # В вебхуке не определяем
    is_mention = BOT_USERNAME in text or "агент" in text.lower()
    
    if not is_mention:
        return
    
    # Реакция
    reaction = get_reaction_emoji(text)
    if reaction:
        send_reaction(chat_id, message_id, reaction)
    
    # Очищаем текст
    clean_text = text.replace(BOT_USERNAME, "").replace("агент", "").strip()
    if not clean_text:
        send_message(chat_id, "Слушаю")
        return
    
    # Быстрые команды
    if clean_text.lower() in ["дата", "какое сегодня число"]:
        send_message(chat_id, datetime.now(MSK).strftime("%d.%m.%Y"))
        return
    if clean_text.lower() in ["время", "который час"]:
        send_message(chat_id, datetime.now(MSK).strftime("%H:%M"))
        return
    if clean_text.lower() == "кто я":
        user = get_user(user_id)
        if user:
            send_message(chat_id, f"Ты {user['name']}, {user['role']}, реп {user['reputation']}")
        else:
            send_message(chat_id, f"Ты {user_name}")
        return
    if clean_text.lower() == "кто ты":
        send_message(chat_id, "Я Агент Ада, умный ИИ-помощник. Слушаюсь Анатаса, умею ставить реакции.")
        return
    if "погода" in clean_text.lower():
        city_match = re.search(r'погода\s+в\s+(\w+)', clean_text.lower())
        city = city_match.group(1) if city_match else "Москва"
        weather = get_weather(city)
        if weather:
            send_message(chat_id, weather)
            return
    
    # Поиск в интернете
    search_info = None
    if any(w in clean_text.lower() for w in ["найди", "что такое", "кто такой", "новости"]):
        search_info = search_web(clean_text)
        if search_info:
            search_info = "🔍 " + search_info
    
    is_admin = (user_id == str(ADMIN_ID))
    response = get_ai_response(clean_text, user_name, is_admin)
    if search_info:
        response = response + "\n\n" + search_info
    send_message(chat_id, response)

# === ВЕБХУК ===
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
    # Инициализируем основных пользователей
    if supabase:
        init_users()
    
    port = int(os.environ.get('PORT', 8080))
    print(f"🚀 Агент Ада запущен на порту {port}")
    print(f"👑 Админ: {ADMIN_NAME}")
    print("📝 База: Supabase")
    app.run(host='0.0.0.0', port=port)
