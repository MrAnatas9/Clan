import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, MessageHandler, filters, CallbackQueryHandler
from config import *
from database import *
from states import *
from keyboards.main_menu import get_main_menu
from utils.helpers import format_user_info

logger = logging.getLogger(__name__)

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.from_user.id != ADMIN_ID:
        await query.edit_message_text("⛔ Нет доступа!")
        return

    stats = get_statistics()

    text = "👑 **АДМИН ПАНЕЛЬ**\n\n"
    text += "📊 **Статистика:**\n"
    text += f"   📋 Заявки: {stats['pending_applications']}\n"
    text += f"   🏦 Кредиты: {stats['pending_credits']}\n"
    text += f"   📝 Задания: {stats['pending_tasks']}\n"
    text += f"   🎭 РП персонажи: {stats['pending_rp_characters']}\n"
    text += f"   💼 Отпуска: {stats['pending_vacations']}\n"
    text += f"   💡 Предложения: {stats['pending_suggestions']}\n\n"
    text += "Выберите действие:"
    
    keyboard = [
        [InlineKeyboardButton("📋 Заявки на вступление", callback_data="admin_view_applications")],
        [InlineKeyboardButton("🏦 Заявки на кредит", callback_data="admin_view_credits")],
        [InlineKeyboardButton("📝 Задания на проверку", callback_data="admin_view_tasks")],
        [InlineKeyboardButton("🎭 РП персонажи на одобрение", callback_data="admin_view_rp")],
        [InlineKeyboardButton("💼 Заявления на отпуск", callback_data="admin_view_vacations")],
        [InlineKeyboardButton("💡 Предложения на рассмотрение", callback_data="admin_view_suggestions")],
        [InlineKeyboardButton("🔍 Найти пользователя", callback_data="admin_search")],
        [InlineKeyboardButton("📊 Статистика клана", callback_data="stats")],
        [InlineKeyboardButton("➕ Создать задание", callback_data="admin_create_task")],
        [InlineKeyboardButton("🔙 Главное меню", callback_data="back")]
    ]
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def admin_view_applications(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.from_user.id != ADMIN_ID:
        await query.edit_message_text("⛔ Нет доступа!")
        return
    
    pending_apps = get_pending_applications()
    
    if not pending_apps:
        await query.edit_message_text(
            "📭 **Нет ожидающих заявок**",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Назад", callback_data="admin_panel")]
            ])
        )
        return
    
    text = "📋 **ОЖИДАЮЩИЕ ЗАЯВКИ НА ВСТУПЛЕНИЕ**\n\n"
    keyboard = []
    
    for app in pending_apps[:10]:
        text += f"🆔 **#{app['id']}**\n"
        text += f"👤 {app['nickname']}\n"
        text += f"📱 @{app.get('username', 'нет')}\n"
        text += f"📅 {app.get('created_at', 'N/A')[:10]}\n\n"
        keyboard.append([
            InlineKeyboardButton(f"👁️ Посмотреть #{app['id']}", callback_data=f"view_app_{app['id']}")
        ])
    
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="admin_panel")])

    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def admin_view_credits(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.from_user.id != ADMIN_ID:
        await query.edit_message_text("⛔ Нет доступа!")
        return
    
    pending_credits = get_pending_credits()
    
    if not pending_credits:
        await query.edit_message_text(
            "🏦 **Нет ожидающих заявок на кредит**",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Назад", callback_data="admin_panel")]
            ])
        )
        return
    
    text = "🏦 **ОЖИДАЮЩИЕ ЗАЯВКИ НА КРЕДИТ**\n\n"
    keyboard = []
    
    for credit in pending_credits[:10]:
        user = get_user(credit['borrower_id'])
        username = f"@{user.get('username', 'нет')}" if user else "неизвестен"
        text += f"🆔 **#{credit['id']}**\n"
        text += f"👤 {username}\n"
        text += f"💰 Сумма: {credit['amount']} акойнов\n"
        text += f"📝 Причина: {credit.get('reason', 'не указана')[:50]}...\n\n"
        keyboard.append([
            InlineKeyboardButton(f"👁️ Кредит #{credit['id']}", callback_data=f"view_credit_{credit['id']}")
        ])
    
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="admin_panel")])
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def admin_view_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.from_user.id != ADMIN_ID:
        await query.edit_message_text("⛔ Нет доступа!")
        return
    
    pending_tasks = get_pending_tasks()
    
    if not pending_tasks:
        await query.edit_message_text(
            "📝 **Нет заданий на проверку**",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Назад", callback_data="admin_panel")]
            ])
        )
        return
    
    text = "📝 **ЗАДАНИЯ НА ПРОВЕРКУ**\n\n"
    keyboard = []
    
    for task in pending_tasks[:10]:
        text += f"🆔 **#{task['id']}**\n"
        text += f"📌 {task['title']}\n"
        text += f"💰 Награда: {task['reward_coins']} акойнов\n"
        text += f"📈 Опыт: {task['reward_exp']}\n\n"
        keyboard.append([
            InlineKeyboardButton(f"👁️ Задание #{task['id']}", callback_data=f"view_task_{task['id']}")
        ])
    
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="admin_panel")])
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def admin_search_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.from_user.id != ADMIN_ID:
        await query.edit_message_text("⛔ Нет доступа!")
        return ConversationHandler.END

    await query.edit_message_text(
        "🔍 **ПОИСК ПОЛЬЗОВАТЕЛЯ**\n\n"
        "Введите username или часть ника пользователя:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Отмена", callback_data="admin_panel")]
        ])
    )

    return ADMIN_SEARCH_USER

async def admin_process_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return ADMIN_SEARCH_USER

    search_term = update.message.text.strip().lstrip('@')
    users = search_users_by_nickname(search_term)

    if not users:
        # Ищем по username
        all_users = get_all_users()
        users = []
        for user in all_users:
            if search_term.lower() in user.get('username', '').lower():
                users.append(user)

    if not users:
        await update.message.reply_text(
            "❌ Пользователи не найдены!",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 Попробовать снова", callback_data="admin_search")],
                [InlineKeyboardButton("🔙 Назад", callback_data="admin_panel")]
            ])
        )
        return ConversationHandler.END

    text = "👤 **НАЙДЕННЫЕ ПОЛЬЗОВАТЕЛИ:**\n\n"

    keyboard = []

    for user in users[:10]:
        banned_status = "⛔" if user.get('is_banned', False) else "✅"
        text += f"{banned_status} **{user['nickname']}**\n"
        text += f"   🆔 ID: {user['user_id']}\n"
        text += f"   📱 @{user.get('username', 'нет')}\n"
        text += f"   💰 Баланс: {user['coins']} акойнов\n"
        text += f"   💼 Работа: {user['job']}\n\n"

        keyboard.append([
            InlineKeyboardButton(f"👁️ {user['nickname']}", callback_data=f"admin_user_{user['user_id']}")
        ])
    
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="admin_panel")])
    
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    return ConversationHandler.END

async def admin_manage_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.from_user.id != ADMIN_ID:
        await query.edit_message_text("⛔ Нет доступа!")
        return

    if query.data.startswith("admin_user_"):
        user_id = int(query.data.replace("admin_user_", ""))
    elif context.user_data.get('admin_target_user'):
        user_id = context.user_data.get('admin_target_user')

    if not user_id:
        await query.edit_message_text("❌ Пользователь не указан!")
        return

    user = get_user(user_id)
    if not user:
        await query.edit_message_text("❌ Пользователь не найден!")
        return

    banned_status = "⛔ ЗАБАНЕН" if user.get('is_banned', False) else "✅ Активен"
    ban_reason = f"\n📝 Причина бана: {user.get('ban_reason', '')}" if user.get('is_banned', False) else ""
    
    active_credits = get_active_credits(user_id)
    total_credit_debt = 0
    if active_credits:
        for credit in active_credits:
            total_credit_debt += credit.get('total_to_pay', 0) - (credit.get('paid_amount', 0) or 0)

    text = f"👤 **ИНФОРМАЦИЯ О ПОЛЬЗОВАТЕЛЕ**\n\n"
    text += f"🎮 **Никнейм:** {user['nickname']}\n"
    text += f"🆔 **ID:** {user['user_id']}\n"
    text += f"📱 **Telegram:** @{user.get('username', 'нет')}\n"
    text += f"💰 **Баланс:** {user['coins']} акойнов\n"
    text += f"🏦 **Долг по кредитам:** {total_credit_debt} акойнов\n"
    text += f"💼 **Основная работа:** {user['job']}\n"
    text += f"👑 **Уровень:** {user['level']}\n"
    text += f"📈 **Опыт:** {user['exp']}\n"
    text += f"📅 **Регистрация:** {user.get('registration_date', 'N/A')[:10]}\n"
    text += f"🔒 **Статус:** {banned_status}{ban_reason}"

    keyboard = []

    if not user.get('is_banned', False):
        keyboard.append([
            InlineKeyboardButton("➕ Добавить деньги", callback_data=f"admin_add_{user_id}"),
            InlineKeyboardButton("➖ Забрать деньги", callback_data=f"admin_remove_{user_id}")
        ])
        keyboard.append([
            InlineKeyboardButton("⛔ Забанить", callback_data=f"admin_ban_{user_id}"),
            InlineKeyboardButton("🗑️ Удалить навсегда", callback_data=f"admin_delete_{user_id}")
        ])
    else:
        keyboard.append([
            InlineKeyboardButton("✅ Разбанить", callback_data=f"admin_unban_{user_id}"),
            InlineKeyboardButton("🗑️ Удалить навсегда", callback_data=f"admin_delete_{user_id}")
        ])
    
    keyboard.append([
        InlineKeyboardButton("🔙 Назад к поиску", callback_data="admin_search")
    ])

    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.from_user.id != ADMIN_ID:
        await query.edit_message_text("⛔ Нет доступа!")
        return

    stats = get_statistics()
    top_rich = get_top_rich_users(5)
    top_debtors = get_top_debtors(5)
    weekly_taxes = calculate_weekly_taxes()
    
    text = (
        f"📊 **СТАТИСТИКА КЛАНА**\n\n"
        f"👥 **Всего пользователей:** {stats['total_users']}\n"
        f"💰 **Всего акойнов в системе:** {stats['total_coins']}\n"
        f"🏦 **Общий долг:** {stats['total_debt']}\n"
        f"💸 **Налоги за неделю:** {weekly_taxes} акойнов\n\n"
        f"📋 **Ожидающие:**\n"
        f"   📋 Заявки: {stats['pending_applications']}\n"
        f"   🏦 Кредиты: {stats['pending_credits']}\n"
        f"   📝 Задания: {stats['pending_tasks']}\n"
        f"   🎭 РП персонажи: {stats['pending_rp_characters']}\n"
        f"   💼 Отпуска: {stats['pending_vacations']}\n"
        f"   💡 Предложения: {stats['pending_suggestions']}\n\n"
        f"⛔ **Забаненных:** {stats.get('banned_users', 0)}\n\n"
        f"💰 **ТОП 5 БОГАЧЕЙ:**\n"
    )

    for i, user in enumerate(top_rich, 1):
        text += f"{i}. {user['nickname']}: {user['coins']} акойнов\n"

    text += f"\n🏦 **ТОП 5 ДОЛЖНИКОВ:**\n"

    for i, user in enumerate(top_debtors, 1):
        text += f"{i}. {user['nickname']}: {abs(user['coins'])} акойнов\n"

    await query.edit_message_text(text, reply_markup=get_main_menu(ADMIN_ID))

async def admin_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await admin_panel(update, context)
    return ConversationHandler.END

def setup_admin_handlers(application):
    """Настройка обработчиков админ-панели"""
    # Обычные callback обработчики
    application.add_handler(CallbackQueryHandler(admin_panel, pattern='^admin_panel$'))
    application.add_handler(CallbackQueryHandler(admin_stats, pattern='^stats$'))
    application.add_handler(CallbackQueryHandler(admin_view_applications, pattern='^admin_view_applications$'))
    application.add_handler(CallbackQueryHandler(admin_view_credits, pattern='^admin_view_credits$'))
    application.add_handler(CallbackQueryHandler(admin_view_tasks, pattern='^admin_view_tasks$'))
    application.add_handler(CallbackQueryHandler(admin_manage_user, pattern='^admin_user_'))
    
    # ConversationHandler ТОЛЬКО для поиска
    admin_search_conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(admin_search_start, pattern='^admin_search$'),
        ],
        states={
            ADMIN_SEARCH_USER: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, admin_process_search),
                CallbackQueryHandler(admin_cancel, pattern='^admin_panel$'),
                CallbackQueryHandler(admin_cancel, pattern='^back$'),
            ],
        },
        fallbacks=[
            CallbackQueryHandler(admin_cancel, pattern='^admin_panel$'),
            CallbackQueryHandler(admin_cancel, pattern='^back$'),
        ],
        per_message=False
    )
    
    application.add_handler(admin_search_conv)
