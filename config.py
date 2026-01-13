import os
from dotenv import load_dotenv

load_dotenv()

# ========== ТЕЛЕГРАМ ==========
BOT_TOKEN = os.getenv("BOT_TOKEN", "7944193433:AAFGectPqnwW9yXnHrzLAPU71GnOmhyrS6A")
ADMIN_ID = int(os.getenv("ADMIN_ID", "6495178643"))
CLAN_LINK = 'https://t.me/+DlaVUJubNdI0OTky'

# ========== SUPABASE ==========
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://oomxbawrjmqczezdpaqp.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9vbXhiYXdyam1xY3plemRwYXFwIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTczNjEwNjEzMSwiZXhwIjoyMDUxNjgyMTMxfQ.sb_publishable_3dpGXVYib4_5cFttwrgK_Q_NQrSk0JP")

# ========== НАСТРОЙКИ ==========
MAX_JOBS_PER_USER = 3
START_COINS = 25
START_LEVEL = 1
START_EXP = 0
MAX_DEBT = 500
CLAN_CREDIT_RATE = 1.50  # +50% за кредит у клана (было 10%)
P2P_TRANSFER_TAX = 0.05  # 5% комиссия за переводы между игроками
DEBT_INTEREST_RATE = 0.50  # 50% в месяц за долг (было 10%)
MIN_CREDIT_AMOUNT = 10
MAX_CREDIT_AMOUNT = 1000
SALARY_DAY = 6  # 6 = воскресенье (0-6 где 0 понедельник, 6 воскресенье)

# ========== КВОТЫ ==========
MIN_WORK_FOR_QUOTA = 1
MIN_EVENTS_FOR_QUOTA = 1
MIN_RP_FOR_QUOTA = 1
QUOTA_BASE_REWARD = 100
QUOTA_BONUS_PER_JOB = 20

# ========== CASINO ==========
CASINO_MIN_BET = 10
CASINO_MAX_BET = 1000
CASINO_WIN_MULTIPLIER = 1.5  # Выигрыш x1.5 (было x2)
CASINO_JACKPOT_MULTIPLIER = 5  # Джекпот x5 (было x10)
CASINO_JACKPOT_CHANCE = 0.005  # 0.5% шанс (было 1%)

# ========== РП ПЕРСОНАЖ ==========
RP_CHARACTER_MIN_PRICE = 100
RP_CHARACTER_MAX_PRICE = 5000
RP_SALE_TO_CLAN_RATE = 0.30  # 30% от стоимости при продаже клану

# ========== ЗАДАНИЯ ==========
TASK_MIN_REWARD_COINS = 10
TASK_MAX_REWARD_COINS = 500
TASK_MIN_REWARD_EXP = 5
TASK_MAX_REWARD_EXP = 100

# ========== ПРОВЕРКА ==========
if not BOT_TOKEN:
    print("❌ ОШИБКА: BOT_TOKEN не установлен!")
    exit(1)

if not SUPABASE_URL or not SUPABASE_KEY:
    print("⚠️ ВНИМАНИЕ: SUPABASE данные не настроены!")