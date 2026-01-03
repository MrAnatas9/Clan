import os
import sys
import subprocess

# Устанавливаем переменные окружения для Bothost
os.environ.setdefault('BOT_TOKEN', '7944193433:AAFGectPqnwW9yXnHrzLAPU71GnOmhyrS6A')
os.environ.setdefault('ADMIN_ID', '6495178643')
os.environ.setdefault('CLAN_LINK', 'https://t.me/+ytVpfVJ_5rk1ODQy')
os.environ.setdefault('SUPABASE_URL', 'https://oomxbawrjmqczezdpaqp.supabase.co')
os.environ.setdefault('SUPABASE_KEY', 'sb_secret_yF3kBESRC2YLxW4427qUjQ_gs1hG5LD')

# Проверяем зависимости
try:
    import telebot
    print("✅ python-telegram-bot установлен")
except ImportError:
    print("❌ python-telegram-bot не установлен")
    sys.exit(1)

try:
    from supabase import create_client
    print("✅ supabase установлен")
except ImportError:
    print("❌ supabase не установлен")
    sys.exit(1)

try:
    from dotenv import load_dotenv
    print("✅ python-dotenv установлен")
except ImportError:
    print("❌ python-dotenv не установлен")
    sys.exit(1)

# Запускаем бота
if __name__ == '__main__':
    try:
        from bot import main
        print("🚀 Запуск бота...")
        main()
    except Exception as e:
        print(f"❌ Ошибка запуска: {e}")
        sys.exit(1)
