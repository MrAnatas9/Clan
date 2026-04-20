import logging
import requests
import re
import random
from datetime import datetime, timezone, timedelta
from telegram import Update, BotCommand
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from groq import Groq

# Ключи напрямую в коде
TELEGRAM_TOKEN = "8626951455:AAED7EIVu45vrpDxFkMDzVHYh7ymK77WWgw"
GROQ_API_KEY = "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"
ADMIN_ID = 6495178643
ADMIN_NAME = "Анатас"
GROQ_MODEL = "llama-3.3-70b-versatile"
BOT_USERNAME = "@agent_bot"

groq_client = Groq(api_key=GROQ_API_KEY)

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

MSK = timezone(timedelta(hours=3))
bot_silent = False

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

async def set_reaction(chat_id, message_id, emoji):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/setMessageReaction"
        payload = {"chat_id": chat_id, "message_id": message_id, "reaction": [{"type": "emoji", "emoji": emoji}]}
        requests.post(url, json=payload)
    except:
        pass

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
        return "Не понял"

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global bot_silent
    
    if bot_silent:
        return
    
    message = update.message
    if not message or not message.text:
        return
        
    chat_id = str(message.chat_id)
    user_id = str(message.from_user.id)
    user_name = message.from_user.first_name
    user_text = message.text
    
    if message.from_user.is_bot:
        return
    
    if user_id == str(ADMIN_ID):
        if user_text.lower() in ["молчать", "молчи"]:
            bot_silent = True
            await message.reply_text("😶 Молчу")
            return
        if user_text.lower() in ["говорить", "проснись"]:
            bot_silent = False
            await message.reply_text("✅ Я здесь")
            return
        
        match = re.search(r'репутацию\s+(\w+)\s+(\d+)', user_text.lower())
        if match:
            name = match.group(1)
            new_rep = int(match.group(2))
            for uid, data in USERS.items():
                if data["name"].lower() == name:
                    USERS[uid]["reputation"] = new_rep
                    await message.reply_text(f"✅ Репутация {name} изменена на {new_rep}")
                    return
    
    is_private = str(message.chat_id) == user_id
    is_reply = message.reply_to_message and message.reply_to_message.from_user and message.reply_to_message.from_user.is_bot
    is_mention = "@agent_bot" in user_text or "агент" in user_text.lower()
    
    if not (is_private or is_reply or is_mention):
        return
    
    reaction = get_reaction_emoji(user_text)
    if reaction:
        await set_reaction(chat_id, message.message_id, reaction)
    
    await context.bot.send_chat_action(chat_id=chat_id, action="typing")
    
    clean_text = user_text.replace("@agent_bot", "").replace("агент", "").strip()
    if not clean_text:
        await message.reply_text("Слушаю")
        return
    
    if clean_text.lower() in ["дата", "какое сегодня число"]:
        await message.reply_text(datetime.now(MSK).strftime("%d.%m.%Y"))
        return
    if clean_text.lower() in ["время", "который час"]:
        await message.reply_text(datetime.now(MSK).strftime("%H:%M"))
        return
    if clean_text.lower() == "кто я":
        user = USERS.get(user_id, {"name": user_name, "role": "новичок", "reputation": 50})
        await message.reply_text(f"Ты {user['name']}, {user['role']}, реп {user['reputation']}")
        return
    if "погода" in clean_text.lower():
        city_match = re.search(r'погода\s+в\s+(\w+)', clean_text.lower())
        city = city_match.group(1) if city_match else "Москва"
        weather = get_weather(city)
        if weather:
            await message.reply_text(weather)
            return
    
    search_info = None
    if any(w in clean_text.lower() for w in ["найди", "что такое", "кто такой", "новости"]):
        status = await message.reply_text("🔍")
        search_info = search_web(clean_text)
        await status.delete()
    
    is_admin = (user_id == str(ADMIN_ID))
    response = get_ai_response(clean_text, user_name, is_admin)
    await message.reply_text(response)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🤖 Агент Ада здесь! Пиши @agent_bot")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("/start /help /who /me\n\nАнатас: молчать, говорить, репутацию [имя] [число]")

async def who_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = "📊 Участники:\n"
    for uid, data in USERS.items():
        text += f"• {data['name']} - {data['role']}, реп {data['reputation']}\n"
    await update.message.reply_text(text)

async def me_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    user = USERS.get(user_id, {"name": update.message.from_user.first_name, "role": "новичок", "reputation": 50})
    await update.message.reply_text(f"{user['name']}, {user['role']}, реп {user['reputation']}")

async def set_commands(app):
    await app.bot.set_my_commands([
        BotCommand("start", "Начать"),
        BotCommand("help", "Помощь"),
        BotCommand("who", "Участники"),
        BotCommand("me", "Досье"),
    ])

def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("who", who_command))
    app.add_handler(CommandHandler("me", me_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.post_init = set_commands
    app.run_polling()

if __name__ == "__main__":
    main()
