import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, MessageHandler, filters, CallbackQueryHandler
from config import *
from database import *
from states import *
from keyboards.main_menu import get_main_menu

logger = logging.getLogger(__name__)

# Вспомогательная функция для проверки никнейма
def is_nickname_taken(nickname: str, exclude_user_id: int = None) -> bool:
    """Проверяет, занят ли никнейм (исключая указанного пользователя)"""
    try:
        users = get_all_users()
        for user in users:
            if exclude_user_id and user['user_id'] == exclude_user_id:
                continue
            if user.get('nickname', '').lower() == nickname.lower():
                return True
        return False
    except Exception as e:
        logger.error(f"Ошибка при проверке никнейма: {e}")
        return False

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
        [InlineKeyboardButton("📝 Сменить ник (10🪙)", callback_data="change_nickname")],
        [InlineKeyboardButton("🔄 Сменить работу", callback_data="change_job")],
        [InlineKeyboardButton("💰 Запросить премию", callback_data="request_bonus")],
        [InlineKeyboardButton("💡 Отправить предложение", callback_data="send_suggestion")],
        [InlineKeyboardButton("🎭 Мои РП персонажи", callback_data="my_rp_characters")],
        [InlineKeyboardButton("📋 Мои задания", callback_data="my_tasks")],
        [InlineKeyboardButton("💼 Мои отпуска", callback_data="my_vacations")],
        [InlineKeyboardButton("🔙 Назад", callback_data="back")]
    ]

    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def change_nickname_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    user = get_user(user_id)
    if not user:
        await query.edit_message_text(
            "❌ Вы не зарегистрированы!",
            reply_markup=get_main_menu(user_id)
        )
        return ConversationHandler.END

    # Проверяем баланс
    CHANGE_NICKNAME_COST = 10
    if user['coins'] < CHANGE_NICKNAME_COST:
        await query.edit_message_text(
            f"❌ **Недостаточно средств!**\n\n"
            f"💰 Требуется: {CHANGE_NICKNAME_COST} акойнов\n"
            f"💰 Ваш баланс: {user['coins']} акойнов\n\n"
            f"💡 Заработайте акойны, выполняя задания или играя в казино.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Назад", callback_data="profile")]
            ])
        )
        return ConversationHandler.END

    context.user_data['change_nickname_user'] = user
    context.user_data['change_nickname_cost'] = CHANGE_NICKNAME_COST

    await query.edit_message_text(
        f"👤 **СМЕНА НИКНЕЙМА**\n\n"
        f"💰 **Стоимость:** {CHANGE_NICKNAME_COST} акойнов\n"
        f"💸 **Ваш баланс:** {user['coins']} акойнов\n"
        f"👤 **Текущий никнейм:** {user['nickname']}\n\n"
        f"Введите новый никнейм (минимум 3 символа):\n"
        f"⚠️ **Правила:**\n"
        f"• Не менее 3 символов\n"
        f"• Не должен быть занят\n"
        f"• Без оскорбительных слов",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Отмена", callback_data="profile")]
        ])
    )

    return CHANGE_NICKNAME

async def change_nickname_process(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return CHANGE_NICKNAME

    new_nickname = update.message.text.strip()
    user_id = update.effective_user.id
    user = context.user_data.get('change_nickname_user')
    cost = context.user_data.get('change_nickname_cost', 10)

    if not user:
        await update.message.reply_text(
            "❌ Ошибка: данные пользователя не найдены!",
            reply_markup=get_main_menu(user_id)
        )
        return ConversationHandler.END

    # Проверка длины
    if len(new_nickname) < 3:
        await update.message.reply_text(
            "❌ Никнейм должен быть не менее 3 символов!\n"
            "Попробуйте снова:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Отмена", callback_data="profile")]
            ])
        )
        return CHANGE_NICKNAME

    # Проверка на запрещенные слова (можно добавить больше)
    forbidden_words = ['админ', 'admin', 'moderator', 'модератор', 'owner', 'владелец']
    if any(word in new_nickname.lower() for word in forbidden_words):
        await update.message.reply_text(
            "❌ Никнейм содержит запрещенные слова!\n"
            "Попробуйте снова:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Отмена", callback_data="profile")]
            ])
        )
        return CHANGE_NICKNAME

    # Проверяем, не занят ли никнейм
    if is_nickname_taken(new_nickname, exclude_user_id=user_id):
        await update.message.reply_text(
            "❌ Этот никнейм уже занят другим пользователем!\n"
            "Пожалуйста, выберите другой:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Отмена", callback_data="profile")]
            ])
        )
        return CHANGE_NICKNAME

    # Запрашиваем подтверждение
    context.user_data['new_nickname'] = new_nickname
    
    await update.message.reply_text(
        f"✅ **Подтверждение смены никнейма**\n\n"
        f"👤 **Старый никнейм:** {user['nickname']}\n"
        f"👤 **Новый никнейм:** {new_nickname}\n"
        f"💰 **Стоимость:** {cost} акойнов\n"
        f"💸 **Баланс до:** {user['coins']} акойнов\n"
        f"💸 **Баланс после:** {user['coins'] - cost} акойнов\n\n"
        f"Вы уверены, что хотите сменить никнейм?",
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ Да, сменить", callback_data="confirm_nickname_change"),
                InlineKeyboardButton("❌ Нет, отмена", callback_data="cancel_nickname_change")
            ]
        ])
    )
    
    return CHANGE_NICKNAME

async def confirm_nickname_change(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    user = context.user_data.get('change_nickname_user')
    new_nickname = context.user_data.get('new_nickname')
    cost = context.user_data.get('change_nickname_cost', 10)

    if not user or not new_nickname:
        await query.edit_message_text(
            "❌ Ошибка: данные не найдены!",
            reply_markup=get_main_menu(user_id)
        )
        context.user_data.clear()
        return ConversationHandler.END

    # Проверяем баланс еще раз
    current_user = get_user(user_id)
    if current_user['coins'] < cost:
        await query.edit_message_text(
            f"❌ **Недостаточно средств!**\n\n"
            f"💰 Требуется: {cost} акойнов\n"
            f"💰 Ваш баланс: {current_user['coins']} акойнов\n\n"
            f"Извините, баланс изменился.",
            reply_markup=get_main_menu(user_id)
        )
        context.user_data.clear()
        return ConversationHandler.END

    # Обновляем никнейм и списываем деньги
    success = update_user_nickname(user_id, new_nickname, cost)
    
    if success:
        updated_user = get_user(user_id)
        await query.edit_message_text(
            f"✅ **Никнейм успешно изменен!**\n\n"
            f"👤 **Старый никнейм:** {user['nickname']}\n"
            f"👤 **Новый никнейм:** {new_nickname}\n"
            f"💰 **Списано:** {cost} акойнов\n"
            f"💸 **Новый баланс:** {updated_user['coins']} акойнов\n\n"
            f"Никнейм обновлен во всех системах клана.",
            reply_markup=get_main_menu(user_id)
        )
        
        # Логируем смену ника
        try:
            logger.info(f"Пользователь {user_id} сменил ник с '{user['nickname']}' на '{new_nickname}' за {cost} акойнов")
        except:
            pass
    else:
        await query.edit_message_text(
            "❌ Ошибка при смене никнейма!\n"
            "Попробуйте позже или обратитесь к администратору.",
            reply_markup=get_main_menu(user_id)
        )

    context.user_data.clear()
    return ConversationHandler.END

async def cancel_nickname_change(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    await query.edit_message_text(
        "❌ Смена никнейма отменена.",
        reply_markup=get_main_menu(user_id)
    )
    
    context.user_data.clear()
    return ConversationHandler.END

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
        text += "Вы безработный в соответствии с Конституцией клана.\n\n"
        text += "💡 Чтобы получить работу:\n"
        text += "1. Нажмите 'Сменить работу'\n"
        text += "2. Выберите доступные работы\n"
        text += "3. Подтвердите выбор"
    else:
        text = f"💼 **ВАШИ РАБОТЫ** ({len(selected_jobs)}/{MAX_JOBS_PER_USER})\n\n"

        for i, job_name in enumerate(selected_jobs, 1):
            job_details = JOBS_DETAILS.get(job_name, {})
            current_count = get_users_count_by_job(job_name)
            max_count = job_details.get('max_users', 1)

            text += f"{i}. **{job_name}**\n"
            text += f"   👥 {current_count}/{max_count} мест\n"
            text += f"   📊 Доход: {job_details.get('daily_income', 0)}🪙/день\n\n"

        text += f"💰 **Общий дневной доход:** {calculate_daily_income(user_id)} акойнов"

    keyboard = [
        [InlineKeyboardButton("🔄 Сменить работу", callback_data="change_job")],
        [InlineKeyboardButton("🔙 Назад", callback_data="profile")]
    ]

    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def request_bonus_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
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

    # Проверяем, когда последний раз запрашивали премию
    last_request = get_last_bonus_request(user_id)
    if last_request:
        # Можно запрашивать раз в неделю
        from datetime import datetime
        last_date = datetime.strptime(last_request, '%Y-%m-%d %H:%M:%S')
        days_passed = (datetime.now() - last_date).days
        
        if days_passed < 7:
            await query.edit_message_text(
                f"⏳ **Слишком рано для запроса премии!**\n\n"
                f"📅 Последний запрос: {last_request[:10]}\n"
                f"⏰ Прошло дней: {days_passed}/7\n"
                f"🕐 Следующий запрос через: {7 - days_passed} дней\n\n"
                f"💡 Премии можно запрашивать раз в неделю.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Назад", callback_data="profile")]
                ])
            )
            return

    await query.edit_message_text(
        "💰 **ЗАПРОС ПРЕМИИ**\n\n"
        "📝 **Правила запроса премии:**\n"
        "• Можно запрашивать раз в неделю\n"
        "• Размер премии до 500 акойнов\n"
        "• Администратор рассматривает запрос\n"
        "• Причина должна быть обоснованной\n\n"
        "Введите причину запроса премии:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Отмена", callback_data="profile")]
        ])
    )

    return REQUEST_BONUS_REASON

async def request_bonus_process(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return REQUEST_BONUS_REASON

    reason = update.message.text.strip()
    user_id = update.effective_user.id
    user = get_user(user_id)

    if len(reason) < 10:
        await update.message.reply_text(
            "❌ Причина должна быть не менее 10 символов!\n"
            "Опишите подробно, за что вы хотите получить премию:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Отмена", callback_data="profile")]
            ])
        )
        return REQUEST_BONUS_REASON

    # Сохраняем запрос
    context.user_data['bonus_reason'] = reason

    await update.message.reply_text(
        f"✅ **Запрос премии подготовлен!**\n\n"
        f"👤 **Пользователь:** {user['nickname']}\n"
        f"💰 **Максимальная сумма:** 500 акойнов\n"
        f"📝 **Причина:** {reason}\n\n"
        f"Введите сумму премии (от 10 до 500 акойнов):",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Отмена", callback_data="profile")]
        ])
    )

    return REQUEST_BONUS_REASON

async def change_job_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    user = get_user(user_id)
    if not user:
        await query.edit_message_text(
            "❌ Вы не зарегистрированы!",
            reply_markup=get_main_menu(user_id)
        )
        return ConversationHandler.END

    # Проверяем, когда последний раз меняли работу
    last_change = get_last_job_change(user_id)
    if last_change:
        from datetime import datetime
        last_date = datetime.strptime(last_change, '%Y-%m-%d %H:%M:%S')
        days_passed = (datetime.now() - last_date).days
        
        if days_passed < 30:
            await query.edit_message_text(
                f"⏳ **Слишком рано для смены работы!**\n\n"
                f"📅 Последняя смена: {last_change[:10]}\n"
                f"⏰ Прошло дней: {days_passed}/30\n"
                f"🕐 Следующая смена через: {30 - days_passed} дней\n\n"
                f"💡 Работу можно менять раз в месяц.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Назад", callback_data="profile")]
                ])
            )
            return ConversationHandler.END

    # Получаем категории работ
    categories = get_categories()
    keyboard = []
    for category in categories:
        keyboard.append([InlineKeyboardButton(category, callback_data=f"change_cat_{category}")])

    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="profile")])

    await query.edit_message_text(
        "💼 **СМЕНА РАБОТЫ**\n\n"
        f"💡 Можно выбрать до {MAX_JOBS_PER_USER} работ\n"
        f"📅 Следующая смена через: {30 - days_passed if last_change else 0} дней\n\n"
        "Выберите категорию:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

    return CHANGE_JOB_SELECTION

def setup_profile_handlers(application):
    """Настройка обработчиков профиля"""
    profile_conv_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(change_nickname_start, pattern='^change_nickname$'),
            CallbackQueryHandler(request_bonus_start, pattern='^request_bonus$'),
            CallbackQueryHandler(change_job_start, pattern='^change_job$'),
            CallbackQueryHandler(confirm_nickname_change, pattern='^confirm_nickname_change$'),
            CallbackQueryHandler(cancel_nickname_change, pattern='^cancel_nickname_change$'),
        ],
        states={
            CHANGE_NICKNAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, change_nickname_process),
                CallbackQueryHandler(lambda u,c: ConversationHandler.END, pattern='^profile$'),
                CallbackQueryHandler(confirm_nickname_change, pattern='^confirm_nickname_change$'),
                CallbackQueryHandler(cancel_nickname_change, pattern='^cancel_nickname_change$'),
            ],
            REQUEST_BONUS_REASON: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, request_bonus_process),
                CallbackQueryHandler(lambda u,c: ConversationHandler.END, pattern='^profile$'),
            ],
            CHANGE_JOB_SELECTION: [
                CallbackQueryHandler(lambda u,c: None, pattern='^change_cat_'),
                CallbackQueryHandler(lambda u,c: ConversationHandler.END, pattern='^profile$'),
            ],
        },
        fallbacks=[
            CallbackQueryHandler(lambda u,c: ConversationHandler.END, pattern='^profile$'),
            CallbackQueryHandler(lambda u,c: ConversationHandler.END, pattern='^back$'),
        ],
        per_message=False
    )

    application.add_handler(profile_conv_handler)
    application.add_handler(CallbackQueryHandler(show_profile, pattern='^profile$'))
    application.add_handler(CallbackQueryHandler(show_my_jobs, pattern='^my_jobs$'))
