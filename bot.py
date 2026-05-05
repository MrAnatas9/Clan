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
bot_mute = False

# === ПОЛНЫЕ ЗАКОНЫ КЛАНА ===
RULES = """
Законы Ада:
- Предательство → вечное изгнание
- Оскорбления → мут 30 мин - 1 час
- Спам и флуд → мут 30 мин + варн
- Бунт → изгнание
"""

# === БАЗА ДАННЫХ ===
USERS_FILE = "users.json"
MEMORY_FILE = "memory.json"

def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_users(users):
    with open(USERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(users, f, ensure_ascii=False, indent=2)

def load_memory():
    if os.path.exists(MEMORY_FILE):
        with open(MEMORY_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_memory(memory):
    with open(MEMORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(memory, f, ensure_ascii=False, indent=2)

USERS = load_users()
CHAT_MEMORY = load_memory()

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
    insult_words = ["дурак", "идиот", "тупой", "лох", "урод", "дебил", "еблан", "мудак", "пидор"]
    for word in insult_words:
        if word in text.lower():
            return word
    return None

def update_reputation(user_id, change, reason):
    if user_id not in USERS:
        return
    old = USERS[user_id]["reputation"]
    new_rep = max(0, min(100, old + change))
    USERS[user_id]["reputation"] = new_rep
    save_users(USERS)
    return new_rep

def get_dialog_history(user_id, limit=8):
    """Возвращает историю диалога с пользователем"""
    if user_id not in CHAT_MEMORY:
        return []
    return CHAT_MEMORY[user_id][-limit:]

def save_dialog_message(user_id, user_msg, bot_response):
    if user_id not in CHAT_MEMORY:
        CHAT_MEMORY[user_id] = []
    CHAT_MEMORY[user_id].append({
        "time": datetime.now(MSK).strftime("%H:%M"),
        "user": user_msg,
        "bot": bot_response
    })
    if len(CHAT_MEMORY[user_id]) > 30:
        CHAT_MEMORY[user_id] = CHAT_MEMORY[user_id][-30:]
    save_memory(CHAT_MEMORY)

def get_ai_response(text, user_id, user_name, is_admin=False, insult_count=0):
    try:
        user_info = USERS.get(user_id, {"name": user_name, "role": "участник", "reputation": 50})
        
        # Получаем историю диалога
        history = get_dialog_history(user_id, 6)
        history_text = ""
        if history:
            history_text = "ИСТОРИЯ ДИАЛОГА (ПОСЛЕДНИЕ СООБЩЕНИЯ):\n"
            for h in history[-4:]:
                history_text += f"Пользователь: {h['user']}\nБот: {h['bot']}\n"
        
        # Определяем тон
        if is_admin:
            tone = "УВАЖИТЕЛЬНО. Ты общаешься с Анатасом - главой и создателем. Выполняй команды, не груби."
        elif insult_count >= 3:
            tone = "АГРЕССИВНО. Пользователь тебя оскорблял. Отвечай резко."
        else:
            tone = "ДРУЖЕЛЮБНО. Отвечай вежливо, помогай."
        
        prompt = f"""Ты Агент Ада. Вот законы (используй ТОЛЬКО когда спрашивают):
{RULES}

{history_text}

Сейчас пишет: {user_info['name']} ({user_info['role']}, реп {user_info['reputation']})
Сообщение: {text}

ПРАВИЛА:
1. Учитывай ИСТОРИЮ ДИАЛОГА - помни что говорил пользователь и ты
2. Не повторяйся, будь естественным
3. Если не знаешь - скажи "не знаю"
4. Тон: {tone}
5. Отвечай коротко (1-2 предложения)
6. Не упоминай законы без необходимости"""

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
        
        # Новый пользователь
        if user_id not in USERS:
            USERS[user_id] = {"name": user_name, "role": "новичок", "reputation": 50, "insult_count": 0}
            save_users(USERS)
        
        is_admin = (user_id == str(ADMIN_ID))
        
        # === АДМИН-КОМАНДЫ ===
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
        
        # === ПРОВЕРКА ОБРАЩЕНИЯ ===
        is_private = str(msg['chat']['type']) == 'private'
        is_reply = msg.get('reply_to_message') and msg['reply_to_message'].get('from', {}).get('is_bot')
        is_mention = "@agent_bot" in text or "агент" in text.lower()
        
        if not (is_private or is_reply or is_mention):
            return 'ok', 200
        
        clean_text = text.replace("@agent_bot", "").replace("агент", "").strip()
        if not clean_text:
            clean_text = text
        
        # === ОСКОРБЛЕНИЯ ===
        if not is_admin:
            insult_word = analyze_insult(clean_text)
            if insult_word:
                USERS[user_id]["insult_count"] = USERS[user_id].get("insult_count", 0) + 1
                update_reputation(user_id, -2, "оскорбление")
                send_reaction(chat_id, message_id, "👿")
        
        # === РЕАКЦИИ ===
        if any(w in clean_text.lower() for w in ["спасибо", "молодец"]):
            send_reaction(chat_id, message_id, "👍")
        elif any(w in clean_text.lower() for w in ["круто", "🔥"]):
            send_reaction(chat_id, message_id, "🔥")
        elif any(w in clean_text.lower() for w in ["шутка", "хаха"]):
            send_reaction(chat_id, message_id, "😂")
        
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
        if clean_text.lower() == "память":
            history = get_dialog_history(user_id, 10)
            if history:
                mem_text = "\n".join([f"{h['time']}: {h['user'][:50]}" for h in history[-5:]])
                send_message(chat_id, f"📝 Последние темы разговора:\n{mem_text}", message_id)
            else:
                send_message(chat_id, "Пока ничего не помню", message_id)
            return 'ok', 200
        
        # === ОСНОВНОЙ ОТВЕТ ===
        insult_count = USERS[user_id].get("insult_count", 0)
        response = get_ai_response(clean_text, user_id, user_name, is_admin, insult_count)
        send_message(chat_id, response, message_id)
        
        # Сохраняем в память
        save_dialog_message(user_id, clean_text, response)
        
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
