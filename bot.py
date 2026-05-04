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

# === ЗАГРУЗКА И СОХРАНЕНИЕ ПОЛЬЗОВАТЕЛЕЙ ===
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
# Если нет начальных данных - добавляем
if not USERS:
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
    save_users(USERS)

# === ПАМЯТЬ ===
clan_info = []  # Важная информация о клане
recent_chat = []  # Последние сообщения в чате (до 50)

def add_to_memory(text, user_name):
    """Запоминает важную информацию"""
    global recent_chat
    recent_chat.append({"user": user_name, "text": text, "time": datetime.now(MSK).strftime("%H:%M")})
    if len(recent_chat) > 50:
        recent_chat.pop(0)
    
    # Запоминаем важное (новости, события, планы)
    important_keywords = ["новости", "событие", "план", "война", "битва", "набор", "шпион"]
    if any(kw in text.lower() for kw in important_keywords):
        clan_info.append({"time": datetime.now(MSK).strftime("%d.%m"), "user": user_name, "text": text[:200]})
        if len(clan_info) > 30:
            clan_info.pop(0)
        save_users(USERS)  # Сохраняем вместе с пользователями

def get_memory_context():
    """Возвращает контекст из памяти"""
    context = ""
    if clan_info:
        context += "📝 Важные события в клане:\n"
        for mem in clan_info[-10:]:
            context += f"• {mem['time']}: {mem['user']}: {mem['text'][:100]}\n"
    return context

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

def get_ai_response(text, user_name, user_id):
    try:
        # Получаем информацию о пользователе
        user_info = USERS.get(user_id, {"name": user_name, "role": "новичок", "reputation": 50})
        
        # Получаем память чата
        memory_context = get_memory_context()
        
        prompt = f"""Ты Агент Ада - умный помощник клана Ад.

Сегодня {datetime.now(MSK).strftime('%d.%m.%Y')}, {datetime.now(MSK).year} год.

ИНФОРМАЦИЯ О КЛАНЕ:
- Анатас - глава клана (ID: 6495178643)
- Якова - админ
- Дайс - второй глава
- Арми - главный враг
- Булка - добрый админ, говорит странно

{memory_context}

Сейчас пишет: {user_info['name']} ({user_info['role']}, репутация {user_info['reputation']})
Вопрос: {text}

ПРАВИЛА ОТВЕТА:
1. Отвечай КОРОТКО (1-2 предложения)
2. Используй информацию из памяти, если она есть
3. Если не знаешь - скажи честно "не знаю"
4. Отвечай по-русски, естественно"""

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
        
        # === АВТОМАТИЧЕСКОЕ СОЗДАНИЕ ДОСЬЕ НА НОВЫХ ===
        if user_id not in USERS:
            USERS[user_id] = {
                "name": user_name,
                "role": "новичок",
                "reputation": 50,
                "first_seen": datetime.now(MSK).strftime("%d.%m.%Y"),
                "about": ""
            }
            save_users(USERS)
            print(f"✅ Создано досье на {user_name} (ID: {user_id})")
            send_message(chat_id, f"📝 Запомнил нового игрока - {user_name}! Добро пожаловать в клан Ад!")
        
        # Обновляем последнюю активность
        USERS[user_id]["last_seen"] = datetime.now(MSK).strftime("%d.%m.%Y %H:%M")
        save_users(USERS)
        
        # Впитываем информацию в память
        add_to_memory(text, user_name)
        
        # === ПРОВЕРКА: нужно ли отвечать ===
        # 1. Личка - отвечаем всегда
        is_private = str(msg['chat']['type']) == 'private'
        # 2. Ответ на сообщение бота
        is_reply = msg.get('reply_to_message') and msg['reply_to_message'].get('from', {}).get('is_bot')
        # 3. Упоминание @agent_bot или "агент"
        is_mention = "@agent_bot" in text or "агент" in text.lower()
        
        if not (is_private or is_reply or is_mention):
            return 'ok', 200
        
        # Реакция (30% шанс)
        reaction = get_reaction_emoji(text)
        if reaction and random.random() < 0.3:
            send_reaction(chat_id, message_id, reaction)
        
        # Админ-команды
        if user_id == str(ADMIN_ID):
            if text.lower() in ["молчать", "молчи"]:
                send_message(chat_id, "😶 Молчу. Скажи 'говорить'")
                return 'ok', 200
            if text.lower() in ["говорить", "проснись"]:
                send_message(chat_id, "✅ Я здесь")
                return 'ok', 200
            
            # Изменение репутации
            match = re.search(r'репутацию\s+(\w+)\s+(\d+)', text.lower())
            if match:
                name = match.group(1)
                new_rep = int(match.group(2))
                for uid, data in USERS.items():
                    if data.get("name", "").lower() == name:
                        USERS[uid]["reputation"] = new_rep
                        save_users(USERS)
                        send_message(chat_id, f"✅ Репутация {name} изменена на {new_rep}")
                        return 'ok', 200
            
            # Показать кого знаю
            if text.lower() == "кто есть кто":
                user_list = "\n".join([f"{data['name']} - {data['role']}, реп {data['reputation']}" for uid, data in USERS.items()])
                send_message(chat_id, f"📊 Знаю таких:\n{user_list}")
                return 'ok', 200
        
        # Быстрые команды
        if text.lower() in ["дата", "какое сегодня число"]:
            send_message(chat_id, datetime.now(MSK).strftime("%d.%m.%Y"))
            return 'ok', 200
        if text.lower() in ["время", "который час"]:
            send_message(chat_id, datetime.now(MSK).strftime("%H:%M"))
            return 'ok', 200
        if text.lower() == "кто я":
            user = USERS.get(user_id, {"name": user_name, "role": "новичок", "reputation": 50})
            send_message(chat_id, f"Ты {user['name']}, {user['role']}, реп {user['reputation']}")
            return 'ok', 200
        if text.lower() == "кто ты":
            send_message(chat_id, "Я Агент Ада, помощник клана Ад. Запоминаю всех игроков и важные события.")
            return 'ok', 200
        if text.lower() == "память":
            if clan_info:
                mem_text = "\n".join([f"{m['time']}: {m['user']}: {m['text'][:80]}" for m in clan_info[-10:]])
                send_message(chat_id, f"📝 Что я помню:\n{mem_text}")
            else:
                send_message(chat_id, "Пока ничего важного не запомнил")
            return 'ok', 200
        
        # Обычный ответ
        clean_text = text.replace("@agent_bot", "").replace("агент", "").strip()
        response = get_ai_response(clean_text if clean_text else text, user_name, user_id)
        send_message(chat_id, response)
        
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
    print(f"👥 В базе: {len(USERS)} человек")
    app.run(host='0.0.0.0', port=port)
