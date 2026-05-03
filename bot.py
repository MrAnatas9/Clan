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

TELEGRAM_TOKEN = "8626951455:AAED7EIVu45vrpDxFkMDzVHYh7ymK77WWgw"
GROQ_API_KEY = "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"
ADMIN_ID = 6495178643
ADMIN_NAME = "Анатас"
GROQ_MODEL = "llama-3.3-70b-versatile"
BOT_USERNAME = "@agent_bot"

SUPABASE_URL = "https://fgafqnxnpgsdtbhwyjux.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImZnYWZxbnhucGdzZHRiaHd5anV4Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzU0MDA5MjMsImV4cCI6MjA5MDk3NjkyM30.izwZDlGaRk8gNwWnX64DGf7_mJR2aFIvahhFvbUnfrY"

groq_client = Groq(api_key=GROQ_API_KEY)

supabase = None
try:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    print("✅ Supabase подключён")
except Exception as e:
    print(f"❌ Ошибка: {e}")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
app = Flask(__name__)
MSK = timezone(timedelta(hours=3))

# === SUPABASE ФУНКЦИИ ===
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
            supabase.table("users").update({"last_seen": datetime.now(MSK).isoformat()}).eq("user_id", user_id).execute()
        else:
            supabase.table("users").insert({
                "user_id": user_id, "name": name, "role": "новичок", "reputation": 50,
                "first_seen": datetime.now(MSK).isoformat(), "last_seen": datetime.now(MSK).isoformat()
            }).execute()
            print(f"✅ Новый пользователь: {name}")
    except Exception as e:
        logger.error(f"Ошибка: {e}")

def get_all_users():
    if not supabase:
        return []
    try:
        result = supabase.table("users").select("*").order("reputation", desc=True).execute()
        return result.data
    except:
        return []

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
        prompt = f"Ты Агент Ада. Сегодня {datetime.now(MSK).strftime('%d.%m.%Y')}. {user_name} спрашивает: {text}. Отвечай коротко по-русски."
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
                save_user(user_id, user_name)
                
                # Реакция
                reaction = get_reaction_emoji(text)
                if reaction and random.random() < 0.3:
                    send_reaction(chat_id, message_id, reaction)
                
                # Ответ
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
