import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, CallbackQueryHandler, filters, MessageHandler
from config import *
from database import get_user, get_active_credits
from keyboards.main_menu import get_main_menu

logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    logger.info(f"Command /start from user {user.id} in chat type: {update.message.chat.type if update.message else 'callback'}")

    # Если команда в группе, показываем справку о групповых командах
    if update.message and update.message.chat.type != 'private':
        help_text = (
            "ℹ️ Команда /start работает только в личных сообщениях с ботом.\n\n"
            "📋 **ДОСТУПНЫЕ ГРУППОВЫЕ КОМАНДЫ (без /):**\n\n"
            "📊 **Информационные (все):**\n"
            "• статистика\n"
            "• богачи\n"
            "• должники\n"
            "• налоги\n"
            "• бюджет\n"
            "• работники\n"
            "• пинг\n"
            "• мой долг\n\n"
            "👑 **Админские (ответом):**\n"
            "• премия <сумма> <причина>\n"
            "• штраф <сумма> <причина>\n"
            "• уволить <причина>\n"
            "• отпуск одобрить\n"
            "• отпуск отклонить <причина>\n"
            "• собрать налоги\n\n"
            "💼 **Общие:**\n"
            "• отпуск заявление <дни> <причина>\n"
            "• сын мой\n"
            "• забрать <сумма> (ответом)\n"
            "• выдать <сумма> (ответом)\n"
            "• игра казино\n\n"
            "💡 **Для личных функций:**\n"
            "Напишите /start в личных сообщениях с ботом"
        )
        await update.message.reply_text(help_text)
        return

    # Только для личных сообщений или callback-запросов
    if update.message:
        await update.message.reply_text(
            f"👋 Привет, {user.first_name}!\n"
            f"👹 Добро пожаловать в бот клана АД!\n\n"
            f"💰 Стартовый баланс: {START_COINS} акойнов\n"
            f"💼 Можно выбрать до {MAX_JOBS_PER_USER} работ\n"
            f"🏦 Максимальный долг: {MAX_DEBT} акойнов\n"
            f"📈 Проценты по долгу: {int(DEBT_INTEREST_RATE * 100)}% в месяц\n\n"
            f"Выберите действие:",
            reply_markup=get_main_menu(user.id)
        )
    else:
        # Для callback-запросов
        query = update.callback_query
        await query.answer()
        await query.edit_message_text(
            f"👋 Привет, {user.first_name}!\n"
            f"👹 Добро пожаловать в бот клана АД!\n\n"
            f"Выберите действие:",
            reply_markup=get_main_menu(user.id)
        )

async def back_to_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await start(update, context)
    return ConversationHandler.END

async def show_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    user = get_user(user_id)
    if not user:
        await query.edit_message_text(
            "❌ Вы не являетесь членом клана!",
            reply_markup=get_main_menu(user_id)
        )
        return

    debt_status = "✅" if user['coins'] >= 0 else "⚠️"
    debt_text = f"Долг: {abs(user['coins'])}🪙" if user['coins'] < 0 else "Без долгов"
    banned_status = "\n⛔ **ЗАБАНЕН**" if user.get('is_banned', False) else ""

    active_credits = get_active_credits(user_id)
    total_debt = 0
    if active_credits:
        for credit in active_credits:
            total_debt += credit.get('total_to_pay', 0)

    text = (
        f"👤 **ПРОФИЛЬ ИГРОКА**{banned_status}\n\n"
        f"🎮 **Никнейм:** {user['nickname']}\n"
        f"📱 **Telegram:** @{user.get('username', 'нет')}\n"
        f"👑 **Уровень:** {user['level']}\n"
        f"📈 **Опыт:** {user['exp']}/{user['level'] * 100}\n"
        f"💰 **Акойны:** {user['coins']}🪙 {debt_status}\n"
        f"📊 **{debt_text}**\n"
        f"🏦 **Кредиты к возврату:** {total_debt} акойнов\n"
        f"💼 **Основная работа:** {user['job']}\n"
        f"📅 **Регистрация:** {user.get('registration_date', 'N/A')[:10]}\n"
        f"🆔 **ID:** {user['user_id']}"
    )

    keyboard = [
        [InlineKeyboardButton("💼 Мои работы", callback_data="my_jobs")],
        [InlineKeyboardButton("📝 Сменить ник", callback_data="change_nickname")],
        [InlineKeyboardButton("🔄 Сменить работу", callback_data="change_job")],
        [InlineKeyboardButton("💰 Запросить премию", callback_data="request_bonus")],
        [InlineKeyboardButton("💡 Отправить предложение", callback_data="send_suggestion")],
        [InlineKeyboardButton("🔙 Назад", callback_data="back")]
    ]

    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def show_my_jobs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    user = get_user(user_id)

    if not user:
        await query.edit_message_text(
            "❌ Вы не зарегистрированы!",
            reply_markup=get_main_menu(user_id)
        )
        return

    selected_jobs = user.get('selected_jobs', [])

    if not selected_jobs:
        text = "💼 **У ВАС НЕТ РАБОТ**\n\n"
        text += "Вы безработный в соответствии с Конституцией клана."
    else:
        text = f"💼 **ВАШИ РАБОТЫ** ({len(selected_jobs)}/{MAX_JOBS_PER_USER})\n\n"

        for i, job_name in enumerate(selected_jobs, 1):
            from database import JOBS_DETAILS, get_users_count_by_job
            job_details = JOBS_DETAILS.get(job_name, {})
            current_count = get_users_count_by_job(job_name)
            max_count = job_details.get('max_users', 1)

            text += f"{i}. **{job_name}**\n"
            text += f"   👥 {current_count}/{max_count} мест\n\n"

    keyboard = [
        [InlineKeyboardButton("🔙 Назад", callback_data="profile")]
    ]

    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

def setup_common_handlers(application):
    """Настройка общих обработчиков"""
    # Важно: команда /start должна быть зарегистрирована БЕЗ фильтра ChatType.PRIVATE
    # чтобы она работала и в группе, и в личных сообщениях
    application.add_handler(CommandHandler("start", start))

    # Callback-обработчики
    application.add_handler(CallbackQueryHandler(back_to_menu, pattern='^back$'))
    application.add_handler(CallbackQueryHandler(show_profile, pattern='^profile$'))
    application.add_handler(CallbackQueryHandler(show_my_jobs, pattern='^my_jobs$'))

    # Временно убираем обработчик неизвестных сообщений
    # application.add_handler(MessageHandler(
    #     filters.TEXT & filters.ChatType.PRIVATE & ~filters.COMMAND,
    #     handle_unknown_message
    # ))
