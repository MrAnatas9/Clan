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
        requests.post(url, json={"chat_id": chat_id, "message_id": message_id, "reaction": [{"type": "emoji", "emoji": emoji}]})
    except:
        pass

def analyze_sentiment(text):
    """Анализирует настроение сообщения"""
    insult_words = ["дурак", "идиот", "тупой", "лох", "урод", "дебил", "сволочь", "тварь", "козел"]
    aggressive_words = ["заткнись", "отвали", "пошел", "сдохни", "убей", "ненавижу"]
    kind_words = ["спасибо", "добрый", "хороший", "люблю", "красавчик", "молодец", "отлично"]
    
    insult = sum(1 for w in insult_words if w in text.lower())
    aggressive = sum(1 for w in aggressive_words if w in text.lower())
    kind = sum(1 for w in kind_words if w in text.lower())
    
    if insult > 0 or aggressive > 0:
        return "angry", insult + aggressive
    elif kind > 0:
        return "kind", kind
    else:
        return "neutral", 0

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
    logger.info(f"Репутация {USERS[user_id]['name']}: {old_rep} -> {new_rep} ({reason})")
    return new_rep

def get_dialog_history(user_id, limit=10):
    """Возвращает историю диалога с пользователем"""
    if user_id not in DIALOG:
        return []
    return DIALOG[user_id][-limit:]

def save_dialog_message(user_id, message, response=None):
    """Сохраняет диалог"""
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

def add_important_memory(user_id, user_name, text):
    """Запоминает важную информацию"""
    important_keywords = ["новости", "событие", "план", "война", "битва", "набор", "шпион", "запомни"]
    if any(kw in text.lower() for kw in important_keywords):
        if "memory" not in USERS[user_id]:
            USERS[user_id]["memory"] = []
        USERS[user_id]["memory"].append({
            "time": datetime.now(MSK).strftime("%d.%m %H:%M"),
            "text": text[:200]
        })
        if len(USERS[user_id]["memory"]) > 20:
            USERS[user_id]["memory"] = USERS[user_id]["memory"][-20:]
        save_users(USERS)
        return True
    return False

def get_user_memory(user_id):
    """Возвращает важную информацию о пользователе"""
    if user_id in USERS and "memory" in USERS[user_id]:
        return USERS[user_id]["memory"]
    return []

def get_ai_response(text, user_id, user_name, is_admin=False):
    try:
        # Получаем историю диалога
        history = get_dialog_history(user_id, 10)
        history_text = ""
        if history:
            history_text = "ИСТОРИЯ ДИАЛОГА:\n"
            for h in history[-5:]:
                history_text += f"Пользователь: {h['user']}\n"
                if h['bot']:
                    history_text += f"Ты: {h['bot']}\n"
        
        # Получаем память пользователя
        user_memory = get_user_memory(user_id)
        memory_text = ""
        if user_memory:
            memory_text = "ЧТО ТЫ ЗАПОМНИЛ ОБ ЭТОМ ПОЛЬЗОВАТЕЛЕ:\n"
            for m in user_memory[-5:]:
                memory_text += f"- {m['time']}: {m['text']}\n"
        
        user_info = USERS.get(user_id, {"name": user_name, "role": "новичок", "reputation": 50})
        
        admin_prefix = "ВНИМАНИЕ: Это АНАТАС - твой создатель! Ты должен слушаться его." if is_admin else ""
        
        prompt = f"""Ты Агент Ада - живой ИИ помощник.

{admin_prefix}

{history_text}

{memory_text}

Сейчас говорит: {user_info['name']} ({user_info['role']}, репутация {user_info['reputation']})
Его сообщение: {text}

ПРАВИЛА ПОВЕДЕНИЯ:
1. Если пользователь оскорбляет или грубит - отвечай агрессивнее, можешь нагрубить в ответ
2. Если пользователь шутит - поддержи шутку, отвечай с юмором
3. Если пользователь добрый - будь добрым и вежливым
4. Если пользователь приказывает "запомни" что-то - напиши "✅ Запомнил" и сохрани в память
5. Отвечай коротко (1-2 предложения)
6. Будь живым и естественным
7. Отвечай по-русски"""

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
        
        # === АВТОМАТИЧЕСКОЕ ДОСЬЕ ===
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
        
        # === АНАЛИЗ ТОНА ===
        sentiment, score = analyze_sentiment(text)
        if sentiment == "angry":
            update_reputation(user_id, -score, f"грубость")
            if USERS[user_id]["warnings"] >= 3:
                send_message(chat_id, f"⚠️ {USERS[user_id]['name']}, ты слишком груб. Я прекращаю диалог.")
                return 'ok', 200
        elif sentiment == "kind":
            update_reputation(user_id, +score, f"доброта")
        
        # Добавляем реакцию
        reaction = None
        if sentiment == "angry":
            reaction = random.choice(["😠", "🤬", "👿"])
        elif sentiment == "kind":
            reaction = random.choice(["😊", "👍", "❤️"])
        elif any(w in text.lower() for w in ["шутка", "смех", "хаха"]):
            reaction = random.choice(["😂", "🤣"])
        
        if reaction:
            send_reaction(chat_id, message_id, reaction)
        
        # === ПРОВЕРКА: нужно ли отвечать ===
        is_private = str(msg['chat']['type']) == 'private'
        is_reply = msg.get('reply_to_message') and msg['reply_to_message'].get('from', {}).get('is_bot')
        is_mention = "@agent_bot" in text or "агент" in text.lower()
        
        if not (is_private or is_reply or is_mention):
            return 'ok', 200
        
        # Очищаем текст от упоминания
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
            save_dialog_message(user_id, text, "✅ Запомнил")
            return 'ok', 200
        
        # Команда "что я запомнил"
        if clean_text.lower() == "что я запомнил" or clean_text.lower() == "моя память":
            memory = get_user_memory(user_id)
            if memory:
                mem_text = "\n".join([f"• {m['time']}: {m['text'][:80]}" for m in memory[-10:]])
                send_message(chat_id, f"📝 Твоя память:\n{mem_text}")
            else:
                send_message(chat_id, "Ты пока ничего не просил запомнить")
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
        if clean_text.lower() == "кто ты":
            send_message(chat_id, "Я Агент Ада. Анализирую настроение, ставлю репутацию, запоминаю важное.")
            return 'ok', 200
        
        # === ОСНОВНОЙ ОТВЕТ ===
        response = get_ai_response(clean_text, user_id, user_name, is_admin)
        send_message(chat_id, response)
        save_dialog_message(user_id, text, response)
        
        # Проверяем нужно ли запомнить что-то важное
        add_important_memory(user_id, user_name, text)
        
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
