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
VIOLATIONS_FILE = "violations.json"

def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_users(users):
    with open(USERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(users, f, ensure_ascii=False, indent=2)

def load_violations():
    if os.path.exists(VIOLATIONS_FILE):
        with open(VIOLATIONS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_violations(violations):
    with open(VIOLATIONS_FILE, 'w', encoding='utf-8') as f:
        json.dump(violations, f, ensure_ascii=False, indent=2)

USERS = load_users()
VIOLATIONS = load_violations()

# Начальные пользователи
if not USERS:
    USERS = {
        "6495178643": {"name": "Анатас", "role": "глава клана", "reputation": 100, "warnings": 0, "banned": False, "muted_until": None},
        "7410138240": {"name": "Дайс", "role": "второй глава", "reputation": 90, "warnings": 0, "banned": False},
        "8312898985": {"name": "Якова", "role": "админ", "reputation": 85, "warnings": 0, "banned": False},
        "5559866358": {"name": "Бликсер", "role": "админ", "reputation": 80, "warnings": 0, "banned": False},
        "5866344776": {"name": "Японец", "role": "участник", "reputation": 70, "warnings": 0, "banned": False},
        "5759237942": {"name": "Булка", "role": "админ", "reputation": 95, "warnings": 0, "banned": False, "speaks_strange": True},
        "1365238364": {"name": "Коунт", "role": "участник", "reputation": 45, "warnings": 0, "banned": False},
        "7839738821": {"name": "Принцесс", "role": "новичок", "reputation": 75, "warnings": 0, "banned": False}
    }
    save_users(USERS)

# === КОНСТИТУЦИЯ И ЗАКОНЫ ===
CONSTITUTION = """
КОНСТИТУЦИЯ КЛАНА АД

Статья 1.1. Предательство и измена:
- Передача информации врагам, переход во враждебный клан → Вечное изгнание
- Бунт и подстрекательство → Изгнание
- Разглашение секретной информации → От мута до изгнания

Статья 1.2. Оскорбления:
- Оскорбление сотрудников клана → Мут 30 мин - 1 час
- Оскорбление правительства → Мут 1 день - Бан
- Публичное оспаривание действий администрации → Мут 30 мин - 1 час

Статья 1.3. Запрещённый контент:
- Насилие, экстремизм, наркотики, порнография → Без права апелляции
- Разжигание розни → Бан без предупреждения
- Доксинг → Бан

Статья 1.4. Другие нарушения:
- Спам и флуд → Мут 30 мин + варн
- Провокации → Мут 1-3 часа + варн
- Неуважение к вышестоящим → Предупреждение → понижение → изгнание
"""

def get_punishment(violation):
    """Возвращает наказание за нарушение"""
    punishments = {
        "оскорбление": "🔇 Мут 30 минут - 1 час",
        "оскорбление правительства": "🔨 Бан или длительный мут",
        "спам": "🔇 Мут 30 минут + ⚠️ Варн",
        "провокация": "🔇 Мут 1-3 часа + ⚠️ Варн",
        "предательство": "⚰️ Вечное изгнание",
        "разглашение": "🔇 Мут до изгнания",
        "неуважение": "⚠️ Предупреждение → Понижение → Изгнание"
    }
    
    for key, punishment in punishments.items():
        if key in violation.lower():
            return punishment
    return "⚠️ На усмотрение администрации"

# === ФУНКЦИИ ===
def send_message(chat_id, text):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.post(url, json={"chat_id": chat_id, "text": text})
    except Exception as e:
        logger.error(f"Send error: {e}")

def send_reaction(chat_id, message_id, emoji):
    """Ставит реальную реакцию Telegram"""
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/setMessageReaction"
        payload = {
            "chat_id": chat_id,
            "message_id": message_id,
            "reaction": [{"type": "emoji", "emoji": emoji}]
        }
        response = requests.post(url, json=payload)
        logger.info(f"Reaction sent: {emoji} -> {response.status_code}")
        return response.status_code == 200
    except Exception as e:
        logger.error(f"Reaction error: {e}")
        return False

def analyze_insults(text):
    """Анализирует оскорбления и возвращает степень агрессии"""
    insults = {
        "легкие": ["дурак", "глупый", "тупой"],
        "средние": ["идиот", "кретин", "дебил", "придурок"],
        "тяжелые": ["еблан", "пидор", "хуесос", "мудак", "уебан"],
        "ультра": ["иди нахуй", "пошел нахуй", "соси хуй"]
    }
    
    text_lower = text.lower()
    for level, words in insults.items():
        for word in words:
            if word in text_lower:
                return level
    return None

def get_aggressive_response(insult_level, user_name):
    """Возвращает агрессивный ответ на оскорбление"""
    responses = {
        "легкие": [
            f"Сам ты {random.choice(['дурак', 'глупый', 'тупой'])}, {user_name}",
            f"Яйца вонючие, быдло необразованное",
            f"Заткнись, {user_name}, а то в бан полетишь"
        ],
        "средние": [
            f"Идиот, блять, сам таких идей",
            f"Ты в своем уме, {user_name}? Охуел?",
            f"Пошел нахуй, дебил ебаный"
        ],
        "тяжелые": [
            f"Ебанутый на всю голову, {user_name}? Схлопочешь бан",
            f"Пидор, завали ебало, пока не выебали",
            f"Хуесос, ты охерел? Я тебя сейчас выебу в рот"
        ],
        "ультра": [
            f"Иди нахуй, {user_name}, пизда тебе ебаная",
            f"Сам пошел нахуй, ублюдок конченый",
            f"Ты ебнутый? Я тебя выебу в жопу, понял?"
        ]
    }
    return random.choice(responses.get(insult_level, responses["тяжелые"]))

def update_reputation(user_id, change, reason):
    """Обновляет репутацию и выдаёт наказание"""
    if user_id not in USERS:
        return
    old_rep = USERS[user_id]["reputation"]
    new_rep = max(0, min(100, old_rep + change))
    USERS[user_id]["reputation"] = new_rep
    
    if "warnings" not in USERS[user_id]:
        USERS[user_id]["warnings"] = 0
    
    # Накапливаем предупреждения
    if change < 0:
        USERS[user_id]["warnings"] += 1
        # Записываем нарушение
        if user_id not in VIOLATIONS:
            VIOLATIONS[user_id] = []
        VIOLATIONS[user_id].append({
            "time": datetime.now(MSK).strftime("%d.%m %H:%M"),
            "reason": reason,
            "reputation_change": change
        })
        save_violations(VIOLATIONS)
        
        # Если 3 варна - бан
        if USERS[user_id]["warnings"] >= 3:
            USERS[user_id]["banned"] = True
            save_users(USERS)
            return f"🔨 {USERS[user_id]['name']} получил бан за 3 нарушения!"
    
    save_users(USERS)
    return None

def register_violation(user_id, violation_text):
    """Регистрирует нарушение по законам"""
    if user_id not in VIOLATIONS:
        VIOLATIONS[user_id] = []
    VIOLATIONS[user_id].append({
        "time": datetime.now(MSK).strftime("%d.%m %H:%M"),
        "violation": violation_text
    })
    save_violations(VIOLATIONS)

def get_user_violations(user_id):
    """Возвращает список нарушений пользователя"""
    if user_id in VIOLATIONS:
        return VIOLATIONS[user_id]
    return []

def get_punishment_advice(question):
    """Совет по наказанию на основе законов"""
    for keyword, punishment in PUNISHMENT_DICT.items():
        if keyword in question.lower():
            return punishment
    return "⚖️ Нарушение не найдено в законах. На усмотрение администрации."

PUNISHMENT_DICT = {
    "предательство": "⚰️ Вечное изгнание без права апелляции (ст. 1.1)",
    "измена": "⚰️ Вечное изгнание без права апелляции (ст. 1.1)",
    "шпионаж": "⚰️ Вечное изгнание (ст. 1.1)",
    "оскорбление правительства": "🔨 Бан или 🔇 Мут 1 день (ст. 1.2)",
    "оскорбление": "🔇 Мут 30 минут - 1 час (ст. 1.2)",
    "спам": "🔇 Мут 30 минут + ⚠️ Варн (ст. 1.3)",
    "флуд": "🔇 Мут 30 минут + ⚠️ Варн (ст. 1.3)",
    "провокация": "🔇 Мут 1-3 часа + ⚠️ Варн (ст. 1.4)",
    "троллинг": "🔇 Мут 1-3 часа + ⚠️ Варн (ст. 1.4)",
    "неуважение": "⚠️ Предупреждение → Понижение → Изгнание (ст. 2.4)",
    "разглашение": "🔇 Мут до изгнания (ст. 1.6)",
    "бунт": "⚰️ Изгнание (ст. 1.2)",
    "революция": "⚰️ Немедленное и вечное изгнание (ст. 2.6)"
}

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
        
        # Автоматическое досье
        if user_id not in USERS:
            USERS[user_id] = {
                "name": user_name,
                "role": "новичок",
                "reputation": 50,
                "warnings": 0,
                "banned": False,
                "first_seen": datetime.now(MSK).strftime("%d.%m.%Y")
            }
            save_users(USERS)
        
        # Проверка бана
        if USERS.get(user_id, {}).get("banned", False):
            send_message(chat_id, f"🔨 {user_name}, ты забанен. Апелляции не принимаются.")
            return 'ok', 200
        
        # Проверка на оскорбления
        insult_level = analyze_insults(text)
        
        # Обработка оскорблений с агрессивным ответом
        if insult_level and user_id != str(ADMIN_ID):
            # Снижаем репутацию
            rep_change = -5 if insult_level in ["легкие", "средние"] else -10 if insult_level == "тяжелые" else -15
            ban_msg = update_reputation(user_id, rep_change, f"оскорбление: {insult_level}")
            
            # Регистрируем нарушение
            register_violation(user_id, f"оскорбление ({insult_level}): {text[:50]}")
            
            # Ставим реакцию гнева
            send_reaction(chat_id, message_id, "🤬")
            
            # Агрессивный ответ
            response = get_aggressive_response(insult_level, user_name)
            if ban_msg:
                response += f"\n\n{ban_msg}"
            send_message(chat_id, response)
            return 'ok', 200
        
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
        
        is_admin = (user_id == str(ADMIN_ID))
        
        # === КОМАНДЫ ===
        
        # Консультация по наказанию
        if clean_text.lower().startswith("как наказать") or clean_text.lower().startswith("что нарушил"):
            question = clean_text.lower()
            advice = get_punishment_advice(question)
            send_message(chat_id, advice)
            return 'ok', 200
        
        # Показать конституцию
        if clean_text.lower() == "конституция":
            send_message(chat_id, CONSTITUTION[:900])
            return 'ok', 200
        
        # Показать нарушения пользователя
        if clean_text.lower().startswith("нарушения"):
            parts = clean_text.split()
            if len(parts) > 1:
                target_name = parts[1]
                for uid, data in USERS.items():
                    if data.get("name", "").lower() == target_name.lower():
                        violations = get_user_violations(uid)
                        if violations:
                            v_text = "\n".join([f"• {v['time']}: {v.get('violation', v.get('reason', '?'))}" for v in violations[-10:]])
                            send_message(chat_id, f"📋 Нарушения {target_name}:\n{v_text}")
                        else:
                            send_message(chat_id, f"✅ У {target_name} нет нарушений")
                        return 'ok', 200
            # Свои нарушения
            violations = get_user_violations(user_id)
            if violations:
                v_text = "\n".join([f"• {v['time']}: {v.get('violation', v.get('reason', '?'))}" for v in violations[-10:]])
                send_message(chat_id, f"📋 Твои нарушения:\n{v_text}")
            else:
                send_message(chat_id, "✅ У тебя нет нарушений")
            return 'ok', 200
        
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
        
        # Что запомнил
        if clean_text.lower() == "что я запомнил" or clean_text.lower() == "моя память":
            memory = USERS.get(user_id, {}).get("memory", [])
            if memory:
                mem_text = "\n".join([f"• {m['time']}: {m['text'][:80]}" for m in memory[-10:]])
                send_message(chat_id, f"📝 Твоя память:\n{mem_text}")
            else:
                send_message(chat_id, "Ты пока ничего не просил запомнить")
            return 'ok', 200
        
        # Поставить реакцию на сообщение
        if "поставь реакцию" in clean_text.lower() and is_admin:
            emoji = re.search(r'[\U0001F600-\U0001F64F]', clean_text)
            if emoji:
                reaction_emoji = emoji.group(0)
                if msg.get('reply_to_message'):
                    target_msg = msg['reply_to_message']
                    send_reaction(chat_id, target_msg['message_id'], reaction_emoji)
                    send_message(chat_id, f"✅ Поставил реакцию на сообщение {target_msg['from']['first_name']}")
                else:
                    send_message(chat_id, "Ответь на сообщение, чтобы поставить реакцию")
            else:
                # Случайная реакция
                if msg.get('reply_to_message'):
                    target_msg = msg['reply_to_message']
                    random_reaction = random.choice(["👍", "❤️", "🔥", "😂", "😲"])
                    send_reaction(chat_id, target_msg['message_id'], random_reaction)
                    send_message(chat_id, f"✅ Поставил реакцию {random_reaction}")
                else:
                    send_message(chat_id, "Ответь на сообщение, чтобы поставить реакцию")
            return 'ok', 200
        
        # Админ-команды
        if is_admin:
            if clean_text.lower() in ["молчать", "молчи"]:
                send_message(chat_id, "😶 Молчу. Скажи 'говорить'")
                return 'ok', 200
            if clean_text.lower() in ["говорить", "проснись"]:
                send_message(chat_id, "✅ Я здесь")
                return 'ok', 200
            
            # Выдать варн
            match = re.search(r'варн\s+(\w+)(?:\s+(\d+))?', clean_text.lower())
            if match:
                name = match.group(1)
                for uid, data in USERS.items():
                    if data.get("name", "").lower() == name:
                        USERS[uid]["warnings"] = USERS[uid].get("warnings", 0) + 1
                        save_users(USERS)
                        send_message(chat_id, f"⚠️ {name} получил варн. Всего: {USERS[uid]['warnings']}")
                        if USERS[uid]["warnings"] >= 3:
                            USERS[uid]["banned"] = True
                            save_users(USERS)
                            send_message(chat_id, f"🔨 {name} забанен за 3 варна!")
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
            send_message(chat_id, "Я Агент Ада - помощник клана Ад. Разбираюсь в законах, ставлю реакции, выдаю наказания.")
            return 'ok', 200
        if clean_text.lower() == "мои варны":
            user = USERS.get(user_id, {})
            send_message(chat_id, f"⚠️ У тебя {user.get('warnings', 0)} варнов. При 3 - бан.")
            return 'ok', 200
        
        # === ДРУЖЕЛЮБНЫЙ ОТВЕТ ПО УМОЛЧАНИЮ ===
        friendly_responses = [
            f"Да, {user_name}? Чем помочь?",
            f"Слушаю, {user_name}",
            f"Что нужно, {user_name}?"
        ]
        
        if len(clean_text) < 30:
            send_message(chat_id, random.choice(friendly_responses))
            return 'ok', 200
        
        # Основной ответ через AI
        try:
            prompt = f"""Ты Агент Ада. {user_name} говорит: {clean_text}
            
Ответь коротко (1-2 предложения) по-русски, дружелюбно. Без мата, если не оскорбляют."""
            
            response = groq_client.chat.completions.create(
                model=GROQ_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.9,
                max_tokens=150
            )
            answer = response.choices[0].message.content
        except Exception as e:
            logger.error(f"AI error: {e}")
            answer = random.choice(friendly_responses)
        
        send_message(chat_id, answer)
        return 'ok', 200
        
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return 'ok', 200

@app.route('/')
def index():
    return '🤖 Агент Ада работает по законам клана!', 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    print("🚀 Агент Ада запущен!")
    print(f"👥 В базе: {len(USERS)} человек")
    print("⚖️ Работает по законам клана")
    app.run(host='0.0.0.0', port=port)
