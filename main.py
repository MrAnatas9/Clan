#!/usr/bin/env python3
import logging
from telegram import Update
from telegram.ext import Application
from config import *
from database import initialize_database

# Импортируем хендлеры
from handlers.common import setup_common_handlers
from handlers.registration import setup_registration_handlers
from handlers.profile import setup_profile_handlers
from handlers.credits import setup_credit_handlers
from handlers.transfers import setup_transfer_handlers
from handlers.admin import setup_admin_handlers
from handlers.tasks import setup_task_handlers
from handlers.casino import setup_casino_handlers
from handlers.rp_characters import setup_rp_handlers
from handlers.vacations import setup_vacation_handlers
from handlers.suggestions import setup_suggestion_handlers
from handlers.group_commands import setup_group_handlers

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO  # Вернем на INFO чтобы не было шума
)

logger = logging.getLogger(__name__)

def main():
    print("🔄 Инициализация базы данных...")
    if not initialize_database():
        print("❌ Не удалось инициализировать базы данных!")
        return

    # Создаем приложение
    application = Application.builder().token(BOT_TOKEN).build()

    print("🤖 Настройка обработчиков...")
    
    # КРИТИЧЕСКИ ВАЖНЫЙ ПОРЯДОК:
    # 1. Сначала ВСЕ ConversationHandler'ы (они должны обрабатываться первыми)
    print("📝 Регистрация ConversationHandler'ов...")
    setup_registration_handlers(application)
    setup_profile_handlers(application)
    setup_credit_handlers(application)
    setup_transfer_handlers(application)
    setup_admin_handlers(application)
    setup_task_handlers(application)
    setup_casino_handlers(application)
    setup_rp_handlers(application)
    setup_vacation_handlers(application)
    setup_suggestion_handlers(application)

    # 2. Потом групповые обработчики
    print("👥 Регистрация групповых обработчиков...")
    setup_group_handlers(application)

    # 3. В САМОМ КОНЦЕ общие обработчики (команды и callback'и)
    print("🔧 Регистрация общих обработчиков...")
    setup_common_handlers(application)

    print("✅ Все обработчики зарегистрированы!")
    print(f"✅ Админ ID: {ADMIN_ID}")
    print(f"✅ Ссылка на чат: {CLAN_LINK}")
    print("🤖 Бот запускается...")

    # Запускаем бота с подробным логированием
    application.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True
    )

if __name__ == '__main__':
    main()
