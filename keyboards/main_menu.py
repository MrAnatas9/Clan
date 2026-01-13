from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from database import get_user
from config import ADMIN_ID

def get_main_menu(user_id):
    """Получить главное меню в зависимости от пользователя"""
    user = get_user(user_id)

    if user_id == ADMIN_ID:
        keyboard = [
            [InlineKeyboardButton("📋 Заявки", callback_data="view_applications"),
             InlineKeyboardButton("🏦 Кредиты", callback_data="pending_credits")],
            [InlineKeyboardButton("📊 Статистика", callback_data="stats"),
             InlineKeyboardButton("👑 Админ", callback_data="admin_panel")],
            [InlineKeyboardButton("📝 Задания", callback_data="tasks_list"),
             InlineKeyboardButton("🎭 РП Персонажи", callback_data="admin_rp_pending")],
            [InlineKeyboardButton("💼 Отпуска", callback_data="vacations_list"),
             InlineKeyboardButton("💡 Предложения", callback_data="suggestions_list")],
            [InlineKeyboardButton("💰 Квота", callback_data="quota_menu"),
             InlineKeyboardButton("🎰 Казино", callback_data="casino_menu")]
        ]
    elif user:
        keyboard = [
            [InlineKeyboardButton("👤 Профиль", callback_data="profile"),
             InlineKeyboardButton("💰 Кредит", callback_data="credit_menu")],
            [InlineKeyboardButton("💸 Перевод", callback_data="transfer_menu"),
             InlineKeyboardButton("💼 Мои работы", callback_data="my_jobs")],
            [InlineKeyboardButton("🎰 Казино", callback_data="casino_menu"),
             InlineKeyboardButton("📝 Задания", callback_data="tasks_list")],
            [InlineKeyboardButton("🎭 РП Персонаж", callback_data="rp_character_menu"),
             InlineKeyboardButton("💰 Квота", callback_data="quota_menu")],
            [InlineKeyboardButton("💼 Отпуск", callback_data="vacation_menu"),
             InlineKeyboardButton("💡 Предложения", callback_data="suggestions_list")],
            [InlineKeyboardButton("📞 Поддержка", url="https://t.me/MrAnatas")]
        ]
    else:
        keyboard = [
            [InlineKeyboardButton("🚀 Регистрация", callback_data="register")],
            [InlineKeyboardButton("📞 Поддержка", url="https://t.me/MrAnatas")]
        ]

    return InlineKeyboardMarkup(keyboard)

def get_back_button(target="back"):
    """Получить кнопку назад"""
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data=target)]])
