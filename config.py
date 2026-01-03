import os
from dotenv import load_dotenv

load_dotenv()

# Настройки бота
BOT_TOKEN = os.getenv("BOT_TOKEN", "7944193433:AAFGectPqnwW9yXnHrzLAPU71GnOmhyrS6A")
ADMIN_ID = int(os.getenv("ADMIN_ID", "6495178643"))
CLAN_LINK = os.getenv("CLAN_LINK", "https://t.me/+ytVpfVJ_5rk1ODQy")

# Supabase
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://oomxbawrjmqczezdpaqp.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "sb_secret_yF3kBESRC2YLxW4427qUjQ_gs1hG5LD")

# Экономика
START_COINS = 25
CLAN_CREDIT_RATE = 1.10  # +10%
MAX_DEBT = 500

# Задания
TASK_DEADLINE_HOURS = 72
TASK_PENALTY_PERCENT = 0.25  # 25% штраф
TASK_FAIL_PENALTY_EXP = 50

# Уровни
EXP_PER_LEVEL = 100

# Логирование
import logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

if not BOT_TOKEN or BOT_TOKEN == "ваш_токен_бота":
    print("⚠️ ВНИМАНИЕ: Проверьте BOT_TOKEN!")
