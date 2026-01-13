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
        [InlineKeyboardButton("📋 Заявки на вступление", callback_data="admin_view_applications")],  # ИЗМЕНЕНИЕ: префикс admin_
        [InlineKeyboardButton("🏦 Заявки на кредит", callback_data="pending_credits")],
        [InlineKeyboardButton("📝 Задания на проверку", callback_data="admin_tasks_pending")],
        [InlineKeyboardButton("🎭 РП персонажи на одобрение", callback_data="admin_rp_pending")],
        [InlineKeyboardButton("💼 Заявления на отпуск", callback_data="vacations_list")],
        [InlineKeyboardButton("💡 Предложения на рассмотрение", callback_data="suggestions_list")],
        [InlineKeyboardButton("🔍 Найти пользователя", callback_data="admin_search")],
        [InlineKeyboardButton("📊 Статистика клана", callback_data="stats")],
        [InlineKeyboardButton("➕ Создать задание", callback_data="admin_create_task")],
        [InlineKeyboardButton("🔙 Главное меню", callback_data="back")]
    ]

    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

# Добавим функцию для просмотра заявок из админки
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
        return ADMIN_SEARCH_USER

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
    return ADMIN_MANAGE_USER

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
        keyboard.append([
            InlineKeyboardButton("👑 Сменить себе имя", callback_data=f"admin_change_name_{user_id}"),
            InlineKeyboardButton("💼 Изменить работу", callback_data=f"admin_change_job_{user_id}")
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
    return ADMIN_MANAGE_USER

async def admin_add_money_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.from_user.id != ADMIN_ID:
        await query.edit_message_text("⛔ Нет доступа!")
        return ADMIN_MANAGE_USER

    if query.data.startswith("admin_add_"):
        user_id = int(query.data.replace("admin_add_", ""))

    context.user_data['admin_target_user'] = user_id
    context.user_data['admin_action'] = 'add'
    user = get_user(user_id)

    await query.edit_message_text(
        f"➕ **ДОБАВЛЕНИЕ ДЕНЕГ**\n\n"
        f"👤 Пользователь: {user['nickname']}\n"
        f"💰 Текущий баланс: {user['coins']} акойнов\n\n"
        f"Введите сумму для добавления:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Отмена", callback_data=f"admin_user_{user_id}")]
        ])
    )

    return ADMIN_ADD_MONEY

async def admin_remove_money_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.from_user.id != ADMIN_ID:
        await query.edit_message_text("⛔ Нет доступа!")
        return ADMIN_MANAGE_USER

    if query.data.startswith("admin_remove_"):
        user_id = int(query.data.replace("admin_remove_", ""))

    context.user_data['admin_target_user'] = user_id
    context.user_data['admin_action'] = 'remove'
    user = get_user(user_id)

    await query.edit_message_text(
        f"➖ **ИЗЪЯТИЕ ДЕНЕГ**\n\n"
        f"👤 Пользователь: {user['nickname']}\n"
        f"💰 Текущий баланс: {user['coins']} акойнов\n\n"
        f"Введите сумму для изъятия:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Отмена", callback_data=f"admin_user_{user_id}")]
        ])
    )

    return ADMIN_ADD_MONEY

async def admin_process_money(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return ADMIN_ADD_MONEY

    try:
        amount = int(update.message.text.strip())

        if amount <= 0:
            await update.message.reply_text("❌ Сумма должна быть положительной!")
            return ADMIN_ADD_MONEY

        user_id = context.user_data.get('admin_target_user')
        if not user_id:
            await update.message.reply_text("❌ Ошибка: пользователь не выбран!")
            return ADMIN_MANAGE_USER

        action = context.user_data.get('admin_action', 'add')

        if action == 'add':
            success = add_user_coins(user_id, amount)
            action_text = "добавлено"
        else:
            success = add_user_coins(user_id, -amount)
            action_text = "изъято"

        if success:
            user = get_user(user_id)
            await update.message.reply_text(
                f"✅ **{abs(amount)} акойнов {action_text} пользователю {user['nickname']}**\n"
                f"💰 Новый баланс: {user['coins']} акойнов",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 К управлению", callback_data=f"admin_user_{user_id}")]
                ])
            )
        else:
            await update.message.reply_text(
                "❌ Ошибка при изменении баланса!",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 К управлению", callback_data=f"admin_user_{user_id}")]
                ])
            )

        context.user_data.clear()
        return ADMIN_MANAGE_USER

    except ValueError:
        await update.message.reply_text("❌ Введите корректную сумму (число)!")
        return ADMIN_ADD_MONEY

async def admin_ban_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.from_user.id != ADMIN_ID:
        await query.edit_message_text("⛔ Нет доступа!")
        return ADMIN_MANAGE_USER

    if query.data.startswith("admin_ban_"):
        user_id = int(query.data.replace("admin_ban_", ""))

    context.user_data['admin_target_user'] = user_id
    user = get_user(user_id)

    await query.edit_message_text(
        f"⛔ **БАН ПОЛЬЗОВАТЕЛЯ**\n\n"
        f"👤 Пользователь: {user['nickname']}\n\n"
        f"Введите причину бана:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Отмена", callback_data=f"admin_user_{user_id}")]
        ])
    )

    return ADMIN_BAN_REASON

async def admin_process_ban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return ADMIN_BAN_REASON

    reason = update.message.text.strip()

    if not reason:
        await update.message.reply_text("❌ Введите причину бана!")
        return ADMIN_BAN_REASON

    user_id = context.user_data.get('admin_target_user')
    if not user_id:
        await update.message.reply_text("❌ Ошибка: пользователь не выбран!")
        return ADMIN_MANAGE_USER

    if user_id == ADMIN_ID:
        await update.message.reply_text("❌ Нельзя забанить администратора!")
        return ADMIN_MANAGE_USER

    success = ban_user(user_id, reason)

    if success:
        user = get_user(user_id)
        await update.message.reply_text(
            f"⛔ **ПОЛЬЗОВАТЕЛЬ ЗАБАНЕН!**\n\n"
            f"👤 Пользователь: {user['nickname']}\n"
            f"📝 Причина: {reason}\n"
            f"💰 Баланс сохранен\n"
            f"💼 Все работы сняты",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 К поиску", callback_data="admin_search")]
            ])
        )

        try:
            await context.bot.send_message(
                user_id,
                f"⛔ **ВЫ БЫЛИ ЗАБАНЕНЫ!**\n\n"
                f"📝 Причина: {reason}\n"
                f"💰 Ваш баланс сохранен\n"
                f"💼 Все работы сняты\n\n"
                f"Для разблокировки обратитесь к администратору."
            )
        except Exception as e:
            logger.error(f"Ошибка уведомления пользователя: {e}")
    else:
        await update.message.reply_text(
            "❌ Ошибка при бане пользователя!",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 К поиску", callback_data="admin_search")]
            ])
        )

    context.user_data.clear()
    return ADMIN_MANAGE_USER

async def admin_unban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.from_user.id != ADMIN_ID:
        await query.edit_message_text("⛔ Нет доступа!")
        return ADMIN_MANAGE_USER

    if query.data.startswith("admin_unban_"):
        user_id = int(query.data.replace("admin_unban_", ""))

    success = unban_user(user_id)

    if success:
        user = get_user(user_id)
        await query.edit_message_text(
            f"✅ **ПОЛЬЗОВАТЕЛЬ РАЗБАНЕН!**\n\n"
            f"👤 Пользователь: {user['nickname']}\n"
            f"💼 Статус: Безработный",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 К управлению", callback_data=f"admin_user_{user_id}")]
            ])
        )

        try:
            await context.bot.send_message(
                user_id,
                f"✅ **ВЫ РАЗБАНЕНЫ!**\n\n"
                f"💼 Статус: Безработный\n\n"
                f"Вы можете снова выбрать работы через бота."
            )
        except Exception as e:
            logger.error(f"Ошибка уведомления пользователя: {e}")
    else:
        await query.edit_message_text(
            "❌ Ошибка при разбане пользователя!",
            reply_markup=get_main_menu(ADMIN_ID)
        )

async def admin_delete_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.from_user.id != ADMIN_ID:
        await query.edit_message_text("⛔ Нет доступа!")
        return ADMIN_MANAGE_USER

    if query.data.startswith("admin_delete_"):
        user_id = int(query.data.replace("admin_delete_", ""))

    if user_id == ADMIN_ID:
        await query.edit_message_text("❌ Нельзя удалить администратора!")
        return ADMIN_MANAGE_USER

    user = get_user(user_id)
    if not user:
        await query.edit_message_text("❌ Пользователь не найден!")
        return ADMIN_MANAGE_USER

    # Запрашиваем подтверждение
    context.user_data['delete_user_id'] = user_id

    await query.edit_message_text(
        f"🗑️ **ПОЛНОЕ УДАЛЕНИЕ ПОЛЬЗОВАТЕЛЯ**\n\n"
        f"👤 Пользователь: {user['nickname']}\n"
        f"🆔 ID: {user_id}\n\n"
        f"⚠️ **ВНИМАНИЕ:** Это действие необратимо!\n"
        f"• Все данные пользователя будут удалены\n"
        f"• Персонажи будут перемещены в архив\n"
        f"• Пользователь сможет зарегистрироваться заново\n\n"
        f"Вы уверены, что хотите удалить пользователя?",
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ Да, удалить", callback_data="confirm_delete_user"),
                InlineKeyboardButton("❌ Нет, отмена", callback_data=f"admin_user_{user_id}")
            ]
        ])
    )

async def admin_confirm_delete_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.from_user.id != ADMIN_ID:
        await query.edit_message_text("⛔ Нет доступа!")
        return

    user_id = context.user_data.get('delete_user_id')
    if not user_id:
        await query.edit_message_text("❌ Ошибка: пользователь не выбран!")
        return ADMIN_MANAGE_USER

    user = get_user(user_id)

    if delete_user_completely(user_id):
        await query.edit_message_text(
            f"🗑️ **ПОЛЬЗОВАТЕЛЬ ПОЛНОСТЬЮ УДАЛЕН!**\n\n"
            f"👤 Пользователь: {user['nickname']}\n"
            f"🆔 ID: {user_id}\n\n"
            f"✅ Все данные удалены\n"
            f"📦 Персонажи перемещены в архив\n"
            f"🔄 Пользователь может зарегистрироваться заново",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 К поиску", callback_data="admin_search")]
            ])
        )

        try:
            await context.bot.send_message(
                user_id,
                f"🗑️ **ВАШ АККАУНТ БЫЛ УДАЛЕН АДМИНИСТРАТОРОМ**\n\n"
                f"Ваш аккаунт и все данные были полностью удалены из системы клана.\n\n"
                f"Вы можете подать новую заявку на вступление, если хотите вернуться."
            )
        except Exception as e:
            logger.error(f"Ошибка уведомления пользователя: {e}")
    else:
        await query.edit_message_text(
            "❌ Ошибка при удалении пользователя!",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 К поиску", callback_data="admin_search")]
            ])
        )

    context.user_data.clear()
    return ADMIN_MANAGE_USER

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

def setup_admin_handlers(application):
    """Настройка обработчиков админ-панели"""
    admin_conv_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(admin_search_start, pattern='^admin_search$'),
            CallbackQueryHandler(admin_manage_user, pattern='^admin_user_'),
            CallbackQueryHandler(admin_add_money_start, pattern='^admin_add_'),
            CallbackQueryHandler(admin_remove_money_start, pattern='^admin_remove_'),
            CallbackQueryHandler(admin_ban_start, pattern='^admin_ban_'),
            CallbackQueryHandler(admin_unban_user, pattern='^admin_unban_'),
            CallbackQueryHandler(admin_delete_user, pattern='^admin_delete_'),
            CallbackQueryHandler(admin_confirm_delete_user, pattern='^confirm_delete_user$'),
        ],
        states={
            ADMIN_SEARCH_USER: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, admin_process_search),
            ],
            ADMIN_MANAGE_USER: [
                CallbackQueryHandler(admin_manage_user, pattern='^admin_user_'),
                CallbackQueryHandler(admin_add_money_start, pattern='^admin_add_'),
                CallbackQueryHandler(admin_remove_money_start, pattern='^admin_remove_'),
                CallbackQueryHandler(admin_ban_start, pattern='^admin_ban_'),
                CallbackQueryHandler(admin_unban_user, pattern='^admin_unban_'),
                CallbackQueryHandler(admin_delete_user, pattern='^admin_delete_'),
                CallbackQueryHandler(admin_confirm_delete_user, pattern='^confirm_delete_user$'),
                CallbackQueryHandler(admin_panel, pattern='^admin_panel$'),
            ],
            ADMIN_ADD_MONEY: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, admin_process_money),
                CallbackQueryHandler(admin_manage_user, pattern='^admin_user_')
            ],
            ADMIN_BAN_REASON: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, admin_process_ban),
                CallbackQueryHandler(admin_manage_user, pattern='^admin_user_')
            ],
        },
        fallbacks=[CallbackQueryHandler(admin_panel, pattern='^admin_panel$')],
        per_message=False
    )

    application.add_handler(CallbackQueryHandler(admin_panel, pattern='^admin_panel$'))
    application.add_handler(CallbackQueryHandler(admin_stats, pattern='^stats$'))
    application.add_handler(CallbackQueryHandler(admin_view_applications, pattern='^admin_view_applications$'))  # ДОБАВИЛИ
    application.add_handler(admin_conv_handler)
