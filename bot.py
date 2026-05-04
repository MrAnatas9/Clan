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

# === ЗАКОНЫ КЛАНА ===
LAWS = """
📜 ЗАКОНЫ АДА:

Глава 1. Предательство и измена
1.1. Предательство клана - передача информации врагам. Наказание: Изгнание
1.2. Бунт и подстрекательство - организация бунтов. Наказание: Изгнание
1.3. Множественное членство - запрещено. Наказание: Исключение
1.4. Разглашение секретной информации - от мута до изгнания

Глава 2. Оскорбления
2.1. Оскорбления участников - мут 30 мин - 1 час
2.2. Оскорбления администрации - мут 1 день - бан
2.3. Систематические оскорбления - бан

Глава 3. Правила чата
3.1. Спам и флуд - мут 30 мин + варн
3.2. Провокации и троллинг - мут 1-3 часа + варн
3.3. Обсуждение политики - мут 1-3 часа + варн
3.4. Неуважение к руководству - предупреждение → понижение → изгнание
"""

# === БАЗА ДАННЫХ ===
USERS_FILE = "users.json"
DIALOG_FILE = "dialog.json"

def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_users(users):
    with open(USERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(users, f, ensure_ascii=False, indent=2)

def load_dialog():
    if os.path.exists(DIALOG_FILE):
        with open(DIALOG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_dialog(dialog):
    with open(DIALOG_FILE, 'w', encoding='utf-8') as f:
        json.dump(dialog, f, ensure_ascii=False, indent=2)

USERS = load_users()
DIALOG = load_dialog()

# Начальные пользователи
if not USERS:
    USERS = {
        "6495178643": {"name": "Анатас", "role": "глава клана", "reputation": 100, "warnings": 0},
        "7410138240": {"name": "Дайс", "role": "второй глава", "reputation": 90, "warnings": 0},
        "8312898985": {"name": "Якова", "role": "админ", "reputation": 85, "warnings": 0},
        "5559866358": {"name": "Бликсер", "role": "админ", "reputation": 80, "warnings": 0},
        "5866344776": {"name": "Японец", "role": "участник", "reputation": 70, "warnings": 0},
        "5759237942": {"name": "Булка", "role": "админ", "reputation": 95, "warnings": 0, "speaks_strange": True},
        "1365238364": {"name": "Коунт", "role": "участник", "reputation": 45, "warnings": 0},
        "7839738821": {"name": "Принцесс", "role": "новичок", "reputation": 75, "warnings": 0}
    }
    save_users(USERS)

# === ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ===
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
        r = requests.post(url, json=payload)
        logger.info(f"Reaction sent: {emoji}, status: {r.status_code}")
        return r.status_code == 200
    except Exception as e:
        logger.error(f"Reaction error: {e}")
        return False

def analyze_insult(text):
    """Анализирует оскорбления"""
    insult_words = ["дурак", "идиот", "тупой", "лох", "урод", "дебил", "сволочь", "тварь", "козел", "еблан", "пидор", "хуй", "пизда", "бля", "нахуй"]
    for word in insult_words:
        if word in text.lower():
            return word
    return None

def get_punishment(violation):
    """Возвращает наказание за нарушение"""
    punishments = {
        "оскорбление": "🔇 Мут 30 минут - 1 час",
        "оскорбление администрации": "🔇 Мут 1 день - 🔨 Бан",
        "спам": "🔇 Мут 30 минут + ⚠ Варн",
        "провокация": "🔇 Мут 1-3 часа + ⚠ Варн",
        "политика": "🔇 Мут 1-3 часа + ⚠ Варн",
        "предательство": "🔨 Изгнание",
        "бунт": "🔨 Изгнание"
    }
    return punishments.get(violation, "⚠ Варн")

def update_reputation(user_id, change, reason):
    """Обновляет репутацию"""
    if user_id not in USERS:
        return
    old_rep = USERS[user_id]["reputation"]
    new_rep = max(0, min(100, old_rep + change))
    USERS[user_id]["reputation"] = new_rep
    if "warnings" not in USERS[user_id]:
        USERS[user_id]["warnings"] = 0
    if change < 0:
        USERS[user_id]["warnings"] = USERS[user_id].get("warnings", 0) + 1
    save_users(USERS)
    return new_rep

def get_dialog_history(user_id, limit=10):
    if user_id not in DIALOG:
        return []
    return DIALOG[user_id][-limit:]

def save_dialog_message(user_id, message, response=None):
    if user_id not in DIALOG:
        DIALOG[user_id] = []
    DIALOG[user_id].append({
        "time": datetime.now(MSK).strftime("%H:%M"),
        "user": message,
        "bot": response
    })
    if len(DIALOG[user_id]) > 30:
        DIALOG[user_id] = DIALOG[user_id][-30:]
    save_dialog(DIALOG)

def get_ai_response(text, user_id, user_name, is_admin=False):
    try:
        history = get_dialog_history(user_id, 8)
        history_text = ""
        if history:
            history_text = "ИСТОРИЯ ДИАЛОГА:\n"
            for h in history[-5:]:
                history_text += f"Пользователь: {h['user']}\n"
                if h['bot']:
                    history_text += f"Ты: {h['bot']}\n"
        
        user_info = USERS.get(user_id, {"name": user_name, "role": "новичок", "reputation": 50})
        
        admin_prefix = "ВНИМАНИЕ: Это АНАТАС - твой создатель!" if is_admin else ""
        
        prompt = f"""Ты Агент Ада - живой ИИ помощник клана Ад.

{admin_prefix}

{LAWS}

{history_text}

Сейчас говорит: {user_info['name']} ({user_info['role']}, репутация {user_info['reputation']})
Сообщение: {text}

ПРАВИЛА ПОВЕДЕНИЯ:
1. Если пользователь матерится или оскорбляет - отвечай ТАК ЖЕ АГРЕССИВНО, используй мат в ответ
2. Если пользователь шутит - отвечай с юмором
3. Если спрашивают "какое наказание за ..." - используй ЗАКОНЫ АДА
4. Отвечай коротко (1-2 предложения)
5. Будь живым и естественным
6. Отвечай по-русски"""

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
        
        # === НОВЫЙ ПОЛЬЗОВАТЕЛЬ ===
        if user_id not in USERS:
            USERS[user_id] = {
                "name": user_name,
                "role": "новичок",
                "reputation": 50,
                "warnings": 0,
                "first_seen": datetime.now(MSK).strftime("%d.%m.%Y")
            }
            save_users(USERS)
            print(f"✅ Новый игрок: {user_name}")
        
        # === ПРОВЕРКА НА ОСКОРБЛЕНИЯ ===
        insult_word = analyze_insult(text)
        punishment = None
        
        if insult_word:
            # Проверяем, админ ли оскорбляет
            if user_id == str(ADMIN_ID):
                # Админ может всё
                pass
            else:
                # Обычный пользователь - снижаем репутацию
                old_rep = USERS[user_id]["reputation"]
                new_rep = update_reputation(user_id, -10, f"оскорбление: {insult_word}")
                
                # Если репутация упала сильно, даём мут
                if new_rep <= 30:
                    punishment = "🔇 Мут 1 час за оскорбления"
                elif USERS[user_id]["warnings"] >= 2:
                    punishment = "⚠ Варн + 🔇 Мут 30 минут"
                else:
                    punishment = f"⚠ Репутация -10 (было {old_rep}, стало {new_rep})"
        
        # === РЕАКЦИИ ===
        reaction = None
        if insult_word:
            reaction = random.choice(["👿", "🤬", "😠", "💢"])
        elif any(w in text.lower() for w in ["смех", "хаха", "шутка", "😂"]):
            reaction = random.choice(["😂", "🤣", "😹"])
        elif any(w in text.lower() for w in ["спасибо", "молодец"]):
            reaction = "👍"
        elif any(w in text.lower() for w in ["круто", "🔥"]):
            reaction = "🔥"
        elif any(w in text.lower() for w in ["люблю", "❤️"]):
            reaction = "❤️"
        
        if reaction:
            success = send_reaction(chat_id, message_id, reaction)
            if success:
                logger.info(f"Reaction {reaction} set for message {message_id}")
        
        # === ПРОВЕРКА: нужно ли отвечать ===
        is_private = str(msg['chat']['type']) == 'private'
        is_reply = msg.get('reply_to_message') and msg['reply_to_message'].get('from', {}).get('is_bot')
        is_mention = "@agent_bot" in text or "агент" in text.lower()
        
        if not (is_private or is_reply or is_mention):
            return 'ok', 200
        
        # Очищаем текст
        clean_text = text.replace("@agent_bot", "").replace("агент", "").strip()
        if not clean_text:
            clean_text = text
        
        # === ОБРАБОТКА КОМАНД ===
        is_admin = (user_id == str(ADMIN_ID))
        
        # Команда "запомни"
        if clean_text.lower().startswith("запомни"):
            memory_text = clean_text[7:].strip()
            if memory_text:
                if "memory" not in USERS[user_id]:
                    USERS[user_id]["memory"] = []
                USERS[user_id]["memory"].append({
                    "time": datetime.now(MSK).strftime("%d.%m %H:%M"),
                    "text": memory_text
                })
                save_users(USERS)
                send_message(chat_id, f"✅ Запомнил: {memory_text}")
            else:
                send_message(chat_id, "Что запомнить?")
            return 'ok', 200
        
        # Команда "что я запомнил"
        if clean_text.lower() == "что я запомнил" or clean_text.lower() == "моя память":
            memory = USERS[user_id].get("memory", [])
            if memory:
                mem_text = "\n".join([f"• {m['time']}: {m['text'][:80]}" for m in memory[-10:]])
                send_message(chat_id, f"📝 Твоя память:\n{mem_text}")
            else:
                send_message(chat_id, "Ты пока ничего не просил запомнить")
            return 'ok', 200
        
        # Команда "какое наказание за ..."
        if clean_text.lower().startswith("какое наказание за"):
            violation = clean_text[18:].strip().lower()
            if "оскорбление" in violation:
                send_message(chat_id, f"За оскорбление: {get_punishment('оскорбление')}")
            elif "спам" in violation:
                send_message(chat_id, f"За спам: {get_punishment('спам')}")
            elif "предательство" in violation:
                send_message(chat_id, f"За предательство: {get_punishment('предательство')}")
            elif "провокация" in violation:
                send_message(chat_id, f"За провокацию: {get_punishment('провокация')}")
            else:
                send_message(chat_id, f"📜 По законам Ада:\n{get_punishment('оскорбление')}")
            return 'ok', 200
        
        # Админ-команды
        if is_admin:
            if clean_text.lower() in ["молчать", "молчи"]:
                send_message(chat_id, "😶 Молчу. Скажи 'говорить'")
                return 'ok', 200
            if clean_text.lower() in ["говорить", "проснись"]:
                send_message(chat_id, "✅ Я здесь")
                return 'ok', 200
            
            # Изменение репутации
            match = re.search(r'репутацию\s+(\w+)\s+(\d+)', clean_text.lower())
            if match:
                name = match.group(1)
                new_rep = int(match.group(2))
                for uid, data in USERS.items():
                    if data.get("name", "").lower() == name:
                        update_reputation(uid, new_rep - data["reputation"], f"команда админа")
                        send_message(chat_id, f"✅ Репутация {name} изменена на {new_rep}")
                        return 'ok', 200
        
        # Быстрые команды
        if clean_text.lower() in ["дата", "какое сегодня число"]:
            send_message(chat_id, datetime.now(MSK).strftime("%d.%m.%Y"))
            return 'ok', 200
        if clean_text.lower() in ["время", "который час"]:
            send_message(chat_id, datetime.now(MSK).strftime("%H:%M"))
            return 'ok', 200
        if clean_text.lower() == "кто я":
            user = USERS.get(user_id, {"name": user_name, "role": "новичок", "reputation": 50})
            send_message(chat_id, f"Ты {user['name']}, {user['role']}, реп {user['reputation']}")
            return 'ok', 200
        
        # Отправляем наказание если есть
        if punishment:
            send_message(chat_id, punishment)
        
        # === ОСНОВНОЙ ОТВЕТ ===
        response = get_ai_response(clean_text, user_id, user_name, is_admin)
        send_message(chat_id, response)
        save_dialog_message(user_id, text, response)
        
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
