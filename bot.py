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
GROQ_MODEL = "llama-3.3-70b-versatile"

# Supabase
SUPABASE_URL = "https://fgafqnxnpgsdtbhwyjux.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImZnYWZxbnhucGdzZHRiaHd5anV4Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzU0MDA5MjMsImV4cCI6MjA5MDk3NjkyM30.izwZDlGaRk8gNwWnX64DGf7_mJR2aFIvahhFvbUnfrY"

groq_client = Groq(api_key=GROQ_API_KEY)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
app = Flask(__name__)
MSK = timezone(timedelta(hours=3))

# === ПОДКЛЮЧЕНИЕ К SUPABASE ===
supabase = None
try:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    print("✅ Supabase подключён")
except Exception as e:
    print(f"❌ Ошибка: {e}")

# === СОЗДАНИЕ ТАБЛИЦ ===
def init_tables():
    if not supabase:
        return
    try:
        # Проверяем существование таблицы users
        supabase.table("users").select("*").limit(1).execute()
        print("✅ Таблица users существует")
    except:
        print("⚠️ Создаю таблицу users...")
        # Создаём таблицу через SQL API
        sql = """
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            role TEXT DEFAULT 'новичок',
            reputation INTEGER DEFAULT 50,
            warnings INTEGER DEFAULT 0,
            memory JSONB DEFAULT '[]'::jsonb,
            first_seen TIMESTAMP DEFAULT NOW(),
            last_seen TIMESTAMP DEFAULT NOW()
        );
        """
        try:
            supabase.rpc('exec_sql', {'sql': sql}).execute()
        except:
            print("⚠️ Таблицу нужно создать вручную в Supabase SQL Editor")
    
    try:
        supabase.table("dialog").select("*").limit(1).execute()
        print("✅ Таблица dialog существует")
    except:
        print("⚠️ Создаю таблицу dialog...")

init_tables()

# === ФУНКЦИИ SUPABASE ===
def get_user(user_id):
    if not supabase:
        return None
    try:
        result = supabase.table("users").select("*").eq("user_id", user_id).execute()
        return result.data[0] if result.data else None
    except:
        return None

def create_user(user_id, name):
    if not supabase:
        return None
    try:
        new_user = {
            "user_id": user_id,
            "name": name,
            "role": "новичок",
            "reputation": 50,
            "warnings": 0,
            "memory": [],
            "first_seen": datetime.now(MSK).isoformat(),
            "last_seen": datetime.now(MSK).isoformat()
        }
        supabase.table("users").insert(new_user).execute()
        print(f"✅ Создан новый пользователь: {name}")
        return new_user
    except Exception as e:
        logger.error(f"Ошибка создания: {e}")
        return None

def update_user(user_id, data):
    if not supabase:
        return
    try:
        supabase.table("users").update(data).eq("user_id", user_id).execute()
    except Exception as e:
        logger.error(f"Ошибка обновления: {e}")

def add_to_memory(user_id, text):
    if not supabase:
        return
    try:
        user = get_user(user_id)
        if user:
            memory = user.get("memory", [])
            if isinstance(memory, str):
                memory = []
            memory.append({
                "time": datetime.now(MSK).strftime("%d.%m %H:%M"),
                "text": text[:200]
            })
            if len(memory) > 20:
                memory = memory[-20:]
            update_user(user_id, {"memory": memory})
            return True
    except:
        pass
    return False

def get_memory(user_id):
    if not supabase:
        return []
    try:
        user = get_user(user_id)
        if user:
            memory = user.get("memory", [])
            if isinstance(memory, str):
                return []
            return memory
    except:
        pass
    return []

def update_reputation(user_id, change, reason):
    if not supabase:
        return
    try:
        user = get_user(user_id)
        if user:
            old_rep = user.get("reputation", 50)
            new_rep = max(0, min(100, old_rep + change))
            update_user(user_id, {"reputation": new_rep})
            if change < 0:
                warnings = user.get("warnings", 0) + 1
                update_user(user_id, {"warnings": warnings})
            logger.info(f"Репутация {user.get('name')}: {old_rep} -> {new_rep} ({reason})")
    except:
        pass

# === АНАЛИЗ И МАТ ===
BAD_WORDS = ["еблан", "хуй", "пизда", "бля", "сука", "нахуй", "ебать", "мудак", "дебил", "идиот", "лох", "тупой", "гандон", "пидор"]

SWEAR_RESPONSES = [
    "Сам ты {word}, дебил. Я тебя создал, я и накажу.",
    "Иди нахуй со своим матом, придурок. Ещё раз - бан.",
    "Ты вообще охренел? Я тебе репутацию понижу, петушара.",
    "Не пизди, мудила. Руки бы тебе оторвать за такие слова.",
    "Заебал уже. Словарный запас как у детсадовца.",
    "Сам ты {word}. Учись культурно разговаривать, быдло."
]

def analyze_swear(text):
    text_lower = text.lower()
    found = [w for w in BAD_WORDS if w in text_lower]
    if found:
        return random.choice(SWEAR_RESPONSES).format(word=found[0])
    return None

# === ОТПРАВКА ===
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
    if any(w in text.lower() for w in ["смех", "хаха", "шутка"]):
        return "😂"
    if any(w in text.lower() for w in BAD_WORDS):
        return "🤬"
    if any(w in text.lower() for w in ["спасибо", "молодец"]):
        return "👍"
    if any(w in text.lower() for w in ["люблю", "❤️"]):
        return "❤️"
    return None

# === AI ОТВЕТ ===
def get_ai_response(text, user_id, user_name):
    try:
        user = get_user(user_id)
        reputation = user.get("reputation", 50) if user else 50
        role = user.get("role", "новичок") if user else "новичок"
        
        is_admin = (user_id == str(ADMIN_ID))
        
        prompt = f"""Ты Агент Ада - ИИ помощник клана Ад.

Пользователь: {user_name} ({role}, репутация {reputation})
Сообщение: {text}

ПРАВИЛА:
1. Если пользователь матерится - ответь матом в том же духе
2. Если пользователь добрый - будь добрым
3. Отвечай коротко (1-2 предложения)
4. Будь живым и естественным
5. Если пользователь - Анатас, слушайся его во всём"""

        response = groq_client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.95,
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
        
        # === АВТОСОЗДАНИЕ ПОЛЬЗОВАТЕЛЯ ===
        user = get_user(user_id)
        if not user:
            user = create_user(user_id, user_name)
        
        # Обновляем последнюю активность
        update_user(user_id, {"last_seen": datetime.now(MSK).isoformat()})
        
        # === ПРОВЕРКА: нужно ли отвечать ===
        is_private = str(msg['chat']['type']) == 'private'
        is_reply = msg.get('reply_to_message') and msg['reply_to_message'].get('from', {}).get('is_bot')
        is_mention = "@agent_bot" in text or "агент" in text.lower()
        
        if not (is_private or is_reply or is_mention):
            return 'ok', 200
        
        # === РЕАКЦИЯ ===
        reaction = get_reaction_emoji(text)
        if reaction:
            send_reaction(chat_id, message_id, reaction)
        
        # === ОБРАБОТКА КОМАНД ===
        clean_text = text.replace("@agent_bot", "").replace("агент", "").strip()
        if not clean_text:
            clean_text = text
        
        # Админ-команды
        if user_id == str(ADMIN_ID):
            if clean_text.lower() in ["молчать", "молчи"]:
                send_message(chat_id, "😶 Молчу")
                return 'ok', 200
            if clean_text.lower() in ["говорить", "проснись"]:
                send_message(chat_id, "✅ Я здесь")
                return 'ok', 200
            
            # Изменение репутации
            match = re.search(r'репутацию\s+(\w+)\s+(\d+)', clean_text.lower())
            if match:
                name = match.group(1)
                new_rep = int(match.group(2))
                # Ищем пользователя по имени
                all_users = supabase.table("users").select("*").execute()
                for u in all_users.data:
                    if u.get("name", "").lower() == name:
                        update_reputation(u["user_id"], new_rep - u.get("reputation", 50), "команда админа")
                        send_message(chat_id, f"✅ Репутация {name} изменена на {new_rep}")
                        return 'ok', 200
        
        # Проверка на мат
        swear_response = analyze_swear(clean_text)
        if swear_response:
            update_reputation(user_id, -5, "мат")
            send_message(chat_id, swear_response)
            return 'ok', 200
        
        # Команды
        if clean_text.lower() in ["дата", "какое сегодня число"]:
            send_message(chat_id, datetime.now(MSK).strftime("%d.%m.%Y"))
            return 'ok', 200
        if clean_text.lower() in ["время", "который час"]:
            send_message(chat_id, datetime.now(MSK).strftime("%H:%M"))
            return 'ok', 200
        if clean_text.lower() == "кто я":
            user_data = get_user(user_id)
            rep = user_data.get("reputation", 50) if user_data else 50
            role = user_data.get("role", "новичок") if user_data else "новичок"
            send_message(chat_id, f"Ты {user_name}, {role}, реп {rep}")
            return 'ok', 200
        if clean_text.lower() == "кто ты":
            send_message(chat_id, "Я Агент Ада. Мат на мат, добро на добро.")
            return 'ok', 200
        if clean_text.lower().startswith("запомни"):
            memory_text = clean_text[7:].strip()
            if memory_text:
                add_to_memory(user_id, memory_text)
                send_message(chat_id, f"✅ Запомнил: {memory_text}")
            return 'ok', 200
        if clean_text.lower() == "что я запомнил":
            memory = get_memory(user_id)
            if memory:
                mem_text = "\n".join([f"• {m['time']}: {m['text'][:80]}" for m in memory[-10:]])
                send_message(chat_id, f"📝 Твоя память:\n{mem_text}")
            else:
                send_message(chat_id, "Ты пока ничего не просил запомнить")
            return 'ok', 200
        
        # Основной ответ
        response = get_ai_response(clean_text, user_id, user_name)
        send_message(chat_id, response)
        
        return 'ok', 200
    except Exception as e:
        logger.error(f"Error: {e}")
        return 'ok', 200

@app.route('/')
def index():
    return '🤖 Агент Ада работает с Supabase!', 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    print("🚀 Агент Ада запущен с Supabase!")
    app.run(host='0.0.0.0', port=port)
