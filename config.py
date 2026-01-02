import os
from dotenv import load_dotenv

# Пытаемся загрузить .env файл, но если его нет - не падаем
try:
    load_dotenv()
except:
    pass

# Берем значения из переменных окружения или используем значения по умолчанию
BOT_TOKEN = os.getenv("BOT_TOKEN", "7944193433:AAFGectPqnwW9yXnHrzLAPU71GnOmhyrS6A")
ADMIN_ID = int(os.getenv("ADMIN_ID", "6495178643"))
CLAN_LINK = os.getenv("CLAN_LINK", "https://t.me/+ytVpfVJ_5rk1ODQy")

# Только предупреждение, но не падение
if not BOT_TOKEN or BOT_TOKEN == "ваш_токен_бота":
    print("⚠️ ВНИМАНИЕ: BOT_TOKEN не установлен в переменных окружения!")
    print("⚠️ Используется значение по умолчанию. Проверьте настройки Render.")
