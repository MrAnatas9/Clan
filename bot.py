import os
import logging
import requests
import re
import random
from datetime import datetime, timezone, timedelta
from flask import Flask, request
from telegram import Update, Bot
from telegram.ext import Dispatcher, CommandHandler, MessageHandler, filters
from groq import Groq
import threading
import time

# Конфигурация
TELEGRAM_TOKEN = "8626951455:AAED7EIVu45vrpDxFkMDzVHYh7ymK77WWgw"
GROQ_API_KEY = "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"
ADMIN_ID = 6495178643
ADMIN_NAME = "Анатас"
GROQ_MODEL = "llama-3.3-70b-versatile"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Flask приложение
app = Flask(__name__)
bot = Bot(token=TELEGRAM_TOKEN)
dispatcher = Dispatcher(bot, None, use_context=True)

# Время
MSK = timezone(timedelta(hours=3))
bot_active = True

# Участники
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

# Инициализация Groq
groq_client = Groq(api_key=GROQ_API_KEY)

# === РЕАКЦИИ ===
def get_reaction_emoji(text):
    if any(w in text.lower() for w in ["смех", "хаха", "шутка"]):
        return "😂"
    if any(w in text.lower() for w in ["спасибо", "молодец"]):
        return "👍"
    if any(w in text.lower() for w in ["круто", "🔥"]):
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
        admin_prefix = "ВНИМАНИЕ: Это АНАТАС - твой создатель!" if is_admin else ""
        system_prompt = f"""Ты Агент Ада - помощник.

{admin_prefix}

Сегодня {datetime.now(MSK).strftime("%d.%m.%Y")}, сейчас {datetime.now(MSK).year} год.

Говорит: {user_name}
Вопрос: {user_text}

Отвечай КОРОТКО (1-2 предложения) по-русски."""
        
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

# === ОБРАБОТЧИКИ КОМАНД ===
async def start(update, context):
    await update.message.reply_text("🤖 Агент Ада здесь! Пиши /help")

async def help_cmd(update, context):
    await update.message.reply_text("""Команды:
/start - начать
/help - помощь
/who - участники
/me - моё досье

Анатас: молчать, говорить, репутацию [имя] [число]""")

async def who(update, context):
    text = "📊 Участники:\n"
    for uid, data in USERS.items():
        text += f"• {data['name']} - {data['role']}, реп {data['reputation']}\n"
    await update.message.reply_text(text)

async def me(update, context):
    uid = str(update.message.from_user.id)
    user = USERS.get(uid, {"name": update.message.from_user.first_name, "role": "новичок", "reputation": 50})
    await update.message.reply_text(f"{user['name']}, {user['role']}, реп {user['reputation']}")

async def handle_message(update, context):
    user_id = str(update.message.from_user.id)
    user_name = update.message.from_user.first_name
    user_text = update.message.text
    
    # Админ-команды
    if user_id == str(ADMIN_ID):
        if user_text.lower() in ["молчать", "молчи"]:
            global bot_active
            bot_active = False
            await update.message.reply_text("😶 Молчу")
            return
        if user_text.lower() in ["говорить", "проснись"]:
            bot_active = True
            await update.message.reply_text("✅ Я здесь")
            return
        
        match = re.search(r'репутацию\s+(\w+)\s+(\d+)', user_text.lower())
        if match:
            name = match.group(1)
            new_rep = int(match.group(2))
            for uid, data in USERS.items():
                if data["name"].lower() == name:
                    USERS[uid]["reputation"] = new_rep
                    await update.message.reply_text(f"✅ Репутация {name} изменена на {new_rep}")
                    return
    
    if not bot_active:
        return
    
    # Реакция
    reaction = get_reaction_emoji(user_text)
    if reaction:
        try:
            await update.message.reply_text(reaction)
        except:
            pass
    
    # Быстрые команды
    if user_text.lower() in ["дата", "какое сегодня число"]:
        await update.message.reply_text(datetime.now(MSK).strftime("%d.%m.%Y"))
        return
    if user_text.lower() in ["время", "который час"]:
        await update.message.reply_text(datetime.now(MSK).strftime("%H:%M"))
        return
    if "погода" in user_text.lower():
        city_match = re.search(r'погода\s+в\s+(\w+)', user_text.lower())
        city = city_match.group(1) if city_match else "Москва"
        weather = get_weather(city)
        if weather:
            await update.message.reply_text(weather)
            return
    
    # Поиск
    search_info = None
    if any(w in user_text.lower() for w in ["найди", "что такое", "кто такой", "новости"]):
        search_info = search_web(user_text)
    
    is_admin = (user_id == str(ADMIN_ID))
    response = get_ai_response(user_text, user_name, is_admin)
    await update.message.reply_text(response)

# Регистрация обработчиков
dispatcher.add_handler(CommandHandler("start", start))
dispatcher.add_handler(CommandHandler("help", help_cmd))
dispatcher.add_handler(CommandHandler("who", who))
dispatcher.add_handler(CommandHandler("me", me))
dispatcher.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

# === ФЛАСК СЕРВЕР ===
@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        update = Update.de_json(request.get_json(force=True), bot)
        dispatcher.process_update(update)
        return 'ok', 200
    except Exception as e:
        logger.error(f"Webhook ошибка: {e}")
        return 'error', 500

@app.route('/health')
def health():
    return 'ok', 200

@app.route('/')
def index():
    return 'Agent bot is running!', 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    print(f"🚀 Бот запущен на порту {port}")
    app.run(host='0.0.0.0', port=port)
