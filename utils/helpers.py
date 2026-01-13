import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from database import get_user, get_all_users

logger = logging.getLogger(__name__)

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
             InlineKeyboardButton("🎭 РП Персонажи", callback_data="rp_character_admin")],
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
             InlineKeyboardButton("💼 Работы", callback_data="my_jobs")],
            [InlineKeyboardButton("🎰 Казино", callback_data="casino_menu"),
             InlineKeyboardButton("📝 Задания", callback_data="tasks_list")],
            [InlineKeyboardButton("🎭 РП Персонаж", callback_data="rp_character_menu"),
             InlineKeyboardButton("💰 Квота", callback_data="quota_menu")],
            [InlineKeyboardButton("📞 Поддержка", url="https://t.me/MrAnatas")]
        ]
    else:
        keyboard = [
            [InlineKeyboardButton("🚀 Регистрация", callback_data="register")],
            [InlineKeyboardButton("📞 Поддержка", url="https://t.me/MrAnatas")]
        ]
    
    return InlineKeyboardMarkup(keyboard)

def get_user_by_username(username: str):
    """Найти пользователя по username"""
    if not username or username == '':
        return None
    
    username = username.lstrip('@')
    users = get_all_users()
    
    for user in users:
        if user.get('username', '').lower() == username.lower():
            return user
        
        # Также проверяем по nickname если username не указан
        if user.get('nickname', '').lower() == username.lower():
            return user
    
    return None

def get_active_casino_games():
    """Получить активные игры в казино в группе"""
    try:
        # Это временное хранилище для игр
        return []
    except:
        return []

def format_user_info(user):
    """Форматировать информацию о пользователе"""
    banned_status = "⛔ ЗАБАНЕН" if user.get('is_banned', False) else "✅ Активен"
    ban_reason = f"\n📝 Причина бана: {user.get('ban_reason', '')}" if user.get('is_banned', False) else ""
    
    text = (
        f"👤 **ИНФОРМАЦИЯ О ПОЛЬЗОВАТЕЛЕ**\n\n"
        f"🎮 **Никнейм:** {user['nickname']}\n"
        f"🆔 **ID:** {user['user_id']}\n"
        f"📱 **Telegram:** @{user.get('username', 'нет')}\n"
        f"💰 **Баланс:** {user['coins']} акойнов\n"
        f"💼 **Основная работа:** {user['job']}\n"
        f"👑 **Уровень:** {user['level']}\n"
        f"📈 **Опыт:** {user['exp']}\n"
        f"📅 **Регистрация:** {user.get('registration_date', 'N/A')[:10]}\n"
        f"🔒 **Статус:** {banned_status}{ban_reason}"
    )
    
    return text
