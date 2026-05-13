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
BOT_USERNAME = "@agentHell_bot"

groq_client = Groq(api_key=GROQ_API_KEY)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
app = Flask(__name__)
MSK = timezone(timedelta(hours=3))
bot_mute = False

# === ПАМЯТЬ ДИАЛОГА ===
CHAT_HISTORY = {}  # {chat_id: [{"user":, "text":, "time":, "user_id":}]}
USER_CONTEXT = {}  # {user_id: {"last_messages": [], "insult_count": 0}}

# === БАЗА УЧАСТНИКОВ ===
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
    strong_insults = ["еблан", "мудак", "пидор", "хуй", "пизда", "бля", "сука", "сволочь", "тварь", "козел"]
    light_insults = ["дурак", "идиот", "тупой", "лох", "урод", "дебил"]
    
    for word in strong_insults:
        if word in text.lower():
            return "strong", word
    for word in light_insults:
        if word in text.lower():
            return "light", word
    return None, None

def update_reputation(user_id, change, reason):
    if user_id not in USERS:
        return
    old = USERS[user_id]["reputation"]
    new_rep = max(0, min(100, old + change))
    USERS[user_id]["reputation"] = new_rep
    save_users(USERS)
    return new_rep

def get_chat_history(chat_id, limit=15):
    if chat_id not in CHAT_HISTORY:
        return []
    return CHAT_HISTORY[chat_id][-limit:]

def save_chat_message(chat_id, user_id, user_name, text):
    if chat_id not in CHAT_HISTORY:
        CHAT_HISTORY[chat_id] = []
    CHAT_HISTORY[chat_id].append({
        "time": datetime.now(MSK).strftime("%H:%M:%S"),
        "user_id": user_id,
        "user": user_name,
        "text": text
    })
    if len(CHAT_HISTORY[chat_id]) > 50:
        CHAT_HISTORY[chat_id] = CHAT_HISTORY[chat_id][-50:]

def get_user_context(user_id):
    if user_id not in USER_CONTEXT:
        USER_CONTEXT[user_id] = {"last_messages": [], "insult_count": 0}
    return USER_CONTEXT[user_id]

def get_ai_response(text, user_id, user_name, is_admin=False, chat_context=""):
    try:
        user_info = USERS.get(user_id, {"name": user_name, "role": "участник", "reputation": 50})
        user_ctx = get_user_context(user_id)
        
        # Разный тон для админа и обычных
        if is_admin:
            tone = "УВАЖИТЕЛЬНО. Ты общаешься с Анатасом, главой клана."
        elif user_ctx["insult_count"] >= 2:
            tone = "АГРЕССИВНО. Пользователь тебя оскорблял. Отвечай резко, можешь материться в ответ."
        else:
            tone = "НЕЙТРАЛЬНО. Отвечай вежливо, но без лишнего поклонения."
        
        prompt = f"""Ты Агент Ада - ИИ помощник клана Ад.

ВОТ ЧТО ПРОИСХОДИТ В ЧАТЕ (читай внимательно):
{chat_context}

Сейчас пишет: {user_info['name']} ({user_info['role']}, репутация {user_info['reputation']})
Сообщение: {text}

ПРАВИЛА:
1. УЧИТЫВАЙ КОНТЕКСТ - ты должен помнить что было сказано ранее
2. Если пользователь матерится - ОТВЕЧАЙ МАТОМ в ответ (но не перебарщивай)
3. НЕ БУДЬ СЛИШКОМ ПОКОРНЫМ перед админом - отвечай естественно
4. Не используй *действия в звёздочках* без необходимости
5. Отвечай коротко (1-3 предложения)
6. Тон: {tone}
7. Отвечай по-русски"""

        response = groq_client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.95,
            max_tokens=250
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"AI error: {e}")
        return "Не понял"

@app.route('/webhook', methods=['POST'])
def webhook():
    global bot_mute
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
        
        # Сохраняем в историю чата
        save_chat_message(chat_id, user_id, user_name, text)
        
        # Новый пользователь
        if user_id not in USERS:
            USERS[user_id] = {"name": user_name, "role": "новичок", "reputation": 50, "insult_count": 0}
            save_users(USERS)
        
        is_admin = (user_id == str(ADMIN_ID))
        
        # Админ-команды
        if is_admin:
            if text.lower() in ["молчать", "молчи"]:
                bot_mute = True
                send_message(chat_id, "😶 Молчу", message_id)
                return 'ok', 200
            if text.lower() in ["говорить", "проснись"]:
                bot_mute = False
                send_message(chat_id, "✅ Я здесь", message_id)
                return 'ok', 200
            
            rep_match = re.search(r'репутацию\s+(\w+)\s+(\d+)', text.lower())
            if rep_match:
                name = rep_match.group(1)
                new_rep = int(rep_match.group(2))
                for uid, data in USERS.items():
                    if data["name"].lower() == name.lower():
                        update_reputation(uid, new_rep - data["reputation"], "команда")
                        send_message(chat_id, f"✅ Репутация {name}: {new_rep}", message_id)
                        return 'ok', 200
        
        if bot_mute:
            return 'ok', 200
        
        # Проверка обращения
        is_private = str(msg['chat']['type']) == 'private'
        is_reply = msg.get('reply_to_message') and msg['reply_to_message'].get('from', {}).get('is_bot')
        is_mention = BOT_USERNAME in text or "агент" in text.lower() or "бот" in text.lower()
        
        if not (is_private or is_reply or is_mention):
            return 'ok', 200
        
        # Очищаем текст
        clean_text = text.replace(BOT_USERNAME, "").replace("агент", "").replace("бот", "").strip()
        if not clean_text:
            clean_text = text
        
        # === ОБРАБОТКА ОСКОРБЛЕНИЙ ===
        user_ctx = get_user_context(user_id)
        insult_type, insult_word = analyze_insult(clean_text)
        
        if insult_type and not is_admin:
            user_ctx["insult_count"] += 1
            update_reputation(user_id, -3, f"оскорбление: {insult_word}")
            send_reaction(chat_id, message_id, "👿")
            
            # Агрессивный ответ за оскорбление
            aggressive_responses = [
                f"Сам ты {insult_word}, {user_name}!",
                f"Пошёл нахуй, {user_name}",
                f"Завали ебало, {user_name}",
                f"Ты бы потише, {insult_word} ебаный"
            ]
            send_message(chat_id, random.choice(aggressive_responses), message_id)
            save_chat_message(chat_id, "bot", "Агент Ада", random.choice(aggressive_responses))
            return 'ok', 200
        
        # Реакции
        if any(w in clean_text.lower() for w in ["спасибо", "молодец"]):
            send_reaction(chat_id, message_id, "👍")
        elif any(w in clean_text.lower() for w in ["круто", "🔥"]):
            send_reaction(chat_id, message_id, "🔥")
        
        # Быстрые команды
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
        
        # Получаем контекст чата
        chat_context = get_chat_history(chat_id, 15)
        context_text = ""
        if chat_context:
            context_text = "ПОСЛЕДНИЕ СООБЩЕНИЯ В ЧАТЕ:\n"
            for msg in chat_context[-10:]:
                context_text += f"{msg['user']}: {msg['text']}\n"
        
        # Основной ответ
        response = get_ai_response(clean_text, user_id, user_name, is_admin, context_text)
        send_message(chat_id, response, message_id)
        save_chat_message(chat_id, "bot", "Агент Ада", response)
        
        return 'ok', 200
    except Exception as e:
        logger.error(f"Error: {e}")
        return 'ok', 200

@app.route('/ping')
def ping():
    return 'pong', 200

@app.route('/')
def index():
    return '🤖 Агент Ада работает!', 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    print("🚀 Агент Ада запущен!")
    app.run(host='0.0.0.0', port=port)
