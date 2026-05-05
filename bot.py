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

# === ПОЛНЫЕ ЗАКОНЫ КЛАНА (для справки, не для постоянного цитирования) ===
RULES = """
КОНСТИТУЦИЯ КЛАНА АД:

ГЛАВА 1: ОСНОВНЫЕ ПРАВА
- Право на уважение и защиту от буллинга
- Право на справедливое разбирательство
- Право на неприкосновенность виртуальной собственности
- Гражданство клана является единственным и постоянным

ГЛАВА 2: ВЛАСТЬ
- Правительство из трёх Глав: Верховный (Анатас), Обычный, Избранный
- Прокуратория следит за соблюдением законов
- Суд - заседание Правительства

ГЛАВА 3: ПРЕСТУПЛЕНИЯ И НАКАЗАНИЯ
- Предательство (переход во вражеский клан, шпионаж) → вечное изгнание
- Бунт и подстрекательство → изгнание
- Оскорбления участников → мут 30 мин - 1 час
- Оскорбления администрации → мут 1 день - бан
- Спам и флуд → мут 30 мин + варн
- Провокации → мут 1-3 часа + варн
- Неуважение к руководству → предупреждение → понижение → изгнание

ПРАВИЛА ЧАТА:
- Запрещены оскорбления
- Запрещены спам и флуд
- Запрещена политика и межнациональные конфликты
- Запрещён NSFW-контент
- Уважайте гостей
- Вопросы к администрации в ЛС

ВОЗМОЖНЫЕ НАКАЗАНИЯ:
⚠ Варн (предупреждение) - 3 варна = бан
🔇 Мут (запрет на отправку сообщений)
🔨 Бан (полная блокировка)
"""

# === БАЗА ДАННЫХ ===
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

# Начальные пользователи клана
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
    insult_words = ["дурак", "идиот", "тупой", "лох", "урод", "дебил", "еблан", "мудак", "пидор", "хуй", "пизда", "бля", "сука", "сволочь", "тварь", "козел"]
    for word in insult_words:
        if word in text.lower():
            return word
    return None

def update_reputation(user_id, change, reason):
    if user_id not in USERS:
        return
    old_rep = USERS[user_id]["reputation"]
    new_rep = max(0, min(100, old_rep + change))
    USERS[user_id]["reputation"] = new_rep
    save_users(USERS)
    logger.info(f"Реп {USERS[user_id]['name']}: {old_rep} -> {new_rep} ({reason})")
    return new_rep

def get_ai_response(text, user_id, user_name, is_admin=False, insult_count=0):
    try:
        user_info = USERS.get(user_id, {"name": user_name, "role": "участник", "reputation": 50})
        
        # Определяем тон ответа
        if is_admin:
            tone = """УВАЖИТЕЛЬНО. Ты общаешься с Анатасом - главой клана и своим создателем.
            ОБЯЗАН:
            - Выполнять все команды: молчать, говорить, репутацию [имя] [число]
            - Не грубить и не оскорблять Анатаса
            - Отвечать вежливо, но можешь шутить"""
        elif insult_count >= 3:
            tone = """АГРЕССИВНО. Пользователь тебя много раз оскорблял.
            - Можешь отвечать резко и грубо
            - Можешь использовать лёгкий мат
            - Ставь на место обидчика"""
        else:
            tone = """ДРУЖЕЛЮБНО. Пользователь ведёт себя нормально.
            - Отвечай вежливо
            - Можешь шутить
            - Помогай с вопросами"""
        
        prompt = f"""Ты Агент Ада - ИИ помощник клана Ад.

Вот законы клана (используй ТОЛЬКО когда прямо спрашивают о законах или наказаниях, НЕ используй в обычном разговоре):
{RULES}

Сейчас говорит: {user_info['name']} ({user_info['role']}, репутация {user_info['reputation']})
Сообщение: {text}

ВАЖНЫЕ ПРАВИЛА:
1. НЕ упоминай законы в обычном разговоре, только если спросили про наказание
2. Если не знаешь ответа - скажи "не знаю", НЕ ВРИ
3. Отвечай коротко (1-2 предложения)
4. Тон: {tone}
5. Не выдумывай несуществующих игроков
6. Отвечай по-русски"""

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
        
        # === АДМИН-КОМАНДЫ (выполняются в первую очередь, даже при mute) ===
        is_admin = (user_id == str(ADMIN_ID))
        
        if is_admin:
            if text.lower() in ["молчать", "молчи"]:
                bot_mute = True
                send_message(chat_id, "😶 Понял, молчу. Скажи 'говорить' чтобы я заговорил", message_id)
                return 'ok', 200
            if text.lower() in ["говорить", "проснись"]:
                bot_mute = False
                send_message(chat_id, "✅ Я здесь", message_id)
                return 'ok', 200
            
            # Изменение репутации
            rep_match = re.search(r'репутацию\s+(\w+)\s+(\d+)', text.lower())
            if rep_match:
                name = rep_match.group(1)
                new_rep = int(rep_match.group(2))
                for uid, data in USERS.items():
                    if data["name"].lower() == name.lower():
                        update_reputation(uid, new_rep - data["reputation"], "команда админа")
                        send_message(chat_id, f"✅ Репутация {name} изменена на {new_rep}", message_id)
                        return 'ok', 200
        
        # Если бот в режиме mute - не отвечаем
        if bot_mute:
            return 'ok', 200
        
        # === ПРОВЕРКА ОБРАЩЕНИЯ ===
        is_private = str(msg['chat']['type']) == 'private'
        is_reply = msg.get('reply_to_message') and msg['reply_to_message'].get('from', {}).get('is_bot')
        is_mention = "@agent_bot" in text or "агент" in text.lower()
        
        if not (is_private or is_reply or is_mention):
            return 'ok', 200
        
        # Очищаем текст
        clean_text = text.replace("@agent_bot", "").replace("агент", "").strip()
        if not clean_text:
            clean_text = text
        
        # === ПРОВЕРКА НА ОСКОРБЛЕНИЯ ===
        insult_word = None
        if not is_admin:
            insult_word = analyze_insult(clean_text)
            if insult_word:
                USERS[user_id]["insult_count"] = USERS[user_id].get("insult_count", 0) + 1
                update_reputation(user_id, -2, f"оскорбление")
                send_reaction(chat_id, message_id, "👿")
        
        # === РЕАКЦИИ ===
        if insult_word:
            send_reaction(chat_id, message_id, random.choice(["👿", "🤬"]))
        elif any(w in clean_text.lower() for w in ["спасибо", "молодец"]):
            send_reaction(chat_id, message_id, "👍")
        elif any(w in clean_text.lower() for w in ["круто", "🔥"]):
            send_reaction(chat_id, message_id, "🔥")
        elif any(w in clean_text.lower() for w in ["шутка", "хаха", "смех"]):
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
        if clean_text.lower() == "кто ты":
            send_message(chat_id, "Я Агент Ада, твой ИИ-помощник. Задавай вопросы.", message_id)
            return 'ok', 200
        if clean_text.lower().startswith("кто такой") or clean_text.lower().startswith("кто такая"):
            name_query = clean_text.lower().replace("кто такой", "").replace("кто такая", "").strip()
            found = False
            for uid, data in USERS.items():
                if data["name"].lower() == name_query:
                    send_message(chat_id, f"{data['name']} - {data['role']}, реп {data['reputation']}", message_id)
                    found = True
                    break
            if not found:
                send_message(chat_id, f"Не знаю такого игрока. Спроси у главы клана.", message_id)
            return 'ok', 200
        if clean_text.lower().startswith("какое наказание за"):
            violation = clean_text.lower().replace("какое наказание за", "").strip()
            if "оскорбление" in violation:
                send_message(chat_id, "За оскорбление по законам Ада: 🔇 Мут 30 минут - 1 час", message_id)
            elif "спам" in violation:
                send_message(chat_id, "За спам: 🔇 Мут 30 минут + ⚠ Варн", message_id)
            elif "предательство" in violation:
                send_message(chat_id, "За предательство: 🔨 Вечное изгнание", message_id)
            else:
                send_message(chat_id, "По законам Ада наказание зависит от тяжести нарушения. Подробнее у администрации.", message_id)
            return 'ok', 200
        
        # === ОСНОВНОЙ ОТВЕТ ===
        insult_count = USERS[user_id].get("insult_count", 0)
        response = get_ai_response(clean_text, user_id, user_name, is_admin, insult_count)
        send_message(chat_id, response, message_id)
        
        return 'ok', 200
    except Exception as e:
        logger.error(f"Error: {e}")
        return 'ok', 200

@app.route('/')
def index():
    return '🤖 Агент Ада работает!', 200

if __name__ == '__main__':
    bot_mute = False
    port = int(os.environ.get('PORT', 8080))
    print("🚀 Агент Ада запущен!")
    print(f"👥 В базе: {len(USERS)} человек")
    app.run(host='0.0.0.0', port=port)
