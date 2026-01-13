import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, MessageHandler, filters, CallbackQueryHandler
from config import *
from database import *
from states import *
from keyboards.main_menu import get_main_menu

logger = logging.getLogger(__name__)

# Вспомогательная функция для проверки никнейма
def is_nickname_taken(nickname: str) -> bool:
    """Проверяет, занят ли никнейм"""
    try:
        users = get_all_users()
        for user in users:
            if user.get('nickname', '').lower() == nickname.lower():
                return True
        return False
    except Exception as e:
        logger.error(f"Ошибка при проверке никнейма: {e}")
        return False

async def start_registration(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user = query.from_user

    # Проверяем, не зарегистрирован ли уже пользователь
    try:
        user_data = get_user(user.id)
        if user_data:
            await query.edit_message_text(
                "✅ Вы уже являетесь членом клана!",
                reply_markup=get_main_menu(user.id)
            )
            return ConversationHandler.END
    except Exception as e:
        logger.error(f"Ошибка при проверке пользователя: {e}")
        await query.answer("❌ Ошибка при проверке данных")
        return ConversationHandler.END

    await query.edit_message_text(
        "📝 **ПОДАЧА ЗАЯВКИ В КЛАН АД**\n\n"
        "Введите ваш игровой никнейм (минимум 3 символа):"
    )

    context.user_data['selected_jobs'] = []
    return ASKING_NICKNAME

async def ask_nickname(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return ASKING_NICKNAME

    nickname = update.message.text.strip()
    if len(nickname) < 3:
        await update.message.reply_text("❌ Никнейм должен быть не менее 3 символов.\nПопробуйте снова:")
        return ASKING_NICKNAME

    # Проверяем, не занят ли никнейм
    try:
        if is_nickname_taken(nickname):
            await update.message.reply_text("❌ Этот никнейм уже занят. Пожалуйста, выберите другой:")
            return ASKING_NICKNAME
    except Exception as e:
        logger.error(f"Ошибка при проверке никнейма: {e}")
        await update.message.reply_text("❌ Ошибка при проверке никнейма. Попробуйте снова:")
        return ASKING_NICKNAME

    context.user_data['nickname'] = nickname
    await update.message.reply_text(
        "📌 **Откуда вы узнали о клане?**\n"
        "(друг, поиск, реклама и т.д.)"
    )

    return ASKING_SOURCE

async def ask_source(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return ASKING_SOURCE

    source = update.message.text.strip()
    context.user_data['source'] = source

    categories = get_categories()
    keyboard = []
    for category in categories:
        keyboard.append([InlineKeyboardButton(category, callback_data=f"cat_{category}")])

    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_to_menu")])

    await update.message.reply_text(
        "💼 **ВЫБОР РАБОТ**\n\n"
        f"💡 Все работы доступны с **1 уровня**!\n"
        f"📊 Можно выбрать до **{MAX_JOBS_PER_USER}** работ\n\n"
        "Выберите категорию:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

    return SELECTING_JOBS

async def show_category_jobs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data.startswith("cat_"):
        category = query.data.replace("cat_", "")
    elif query.data == "back_to_categories":
        # Показываем список категорий
        categories = get_categories()
        keyboard = []
        for cat in categories:
            keyboard.append([InlineKeyboardButton(cat, callback_data=f"cat_{cat}")])
        
        keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_to_menu")])
        
        await query.edit_message_text(
            "💼 **ВЫБОР РАБОТ**\n\n"
            f"💡 Все работы доступны с **1 уровня**!\n"
            f"📊 Можно выбрать до **{MAX_JOBS_PER_USER}** работ\n\n"
            "Выберите категорию:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return SELECTING_JOBS
    else:
        return

    try:
        jobs = get_jobs_by_category(category)
        selected_jobs = context.user_data.get('selected_jobs', [])
        selected_count = len(selected_jobs)

        text = f"💼 **{category}**\n\n"
        text += f"📊 Выбрано: {selected_count}/{MAX_JOBS_PER_USER} работ\n\n"
        text += "Список работ:\n\n"

        keyboard = []

        for job_name, job_details in jobs.items():
            available = is_job_available(job_name)
            current_count = get_users_count_by_job(job_name)
            max_count = job_details['max_users']

            # Статус выбранной работы
            if job_name in selected_jobs:
                status = "✅ ✓"  # Галочка для выбранных
            else:
                status = "✅" if available else "❌"
            
            availability = f"({current_count}/{max_count})"

            # Отображаем в тексте
            if job_name in selected_jobs:
                text += f"{status} **{job_name}** {availability} (ВЫБРАНО)\n"
            else:
                text += f"{status} {job_name} {availability}\n"

            # Кнопки
            if job_name in selected_jobs:
                keyboard.append([InlineKeyboardButton(f"❌ Убрать {job_name}", callback_data=f"job_toggle_{job_name}")])
            elif available and selected_count < MAX_JOBS_PER_USER:
                keyboard.append([InlineKeyboardButton(f"✅ Выбрать {job_name}", callback_data=f"job_toggle_{job_name}")])
            else:
                if not available:
                    keyboard.append([InlineKeyboardButton(f"❌ {job_name} (нет мест)", callback_data="no_action")])
                elif selected_count >= MAX_JOBS_PER_USER:
                    keyboard.append([InlineKeyboardButton(f"❌ {job_name} (лимит {MAX_JOBS_PER_USER})", callback_data="no_action")])

        keyboard.append([InlineKeyboardButton("📋 Мои выбранные работы", callback_data="show_selected")])
        keyboard.append([InlineKeyboardButton("✅ Завершить выбор", callback_data="finish_selection")])
        keyboard.append([InlineKeyboardButton("🔙 Назад к категориям", callback_data="back_to_categories")])

        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Ошибка в show_category_jobs: {e}", exc_info=True)
        await query.answer("❌ Ошибка!")

async def toggle_job_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "no_action":
        await query.answer("❌ Невозможно выбрать")
        return

    data = query.data
    if not data.startswith("job_toggle_"):
        return

    job_name = data.replace("job_toggle_", "")
    selected_jobs = context.user_data.get('selected_jobs', [])

    if job_name in selected_jobs:
        selected_jobs.remove(job_name)
        await query.answer(f"❌ {job_name} удалена")
    else:
        if len(selected_jobs) >= MAX_JOBS_PER_USER:
            await query.answer(f"❌ Максимум {MAX_JOBS_PER_USER} работ!")
            return

        if not is_job_available(job_name):
            await query.answer("❌ Нет свободных мест!")
            return

        selected_jobs.append(job_name)
        await query.answer(f"✅ {job_name} добавлена")

    context.user_data['selected_jobs'] = selected_jobs

    # Находим категорию для этой работы
    category = None
    for name, details in JOBS_DETAILS.items():
        if name == job_name:
            category = details.get('category', 'Общие')
            break

    if category:
        # Получаем работы по категории и показываем заново
        jobs = get_jobs_by_category(category)

        text = f"💼 **{category}**\n\n"
        text += f"📊 Выбрано: {len(selected_jobs)}/{MAX_JOBS_PER_USER} работ\n\n"
        text += "Список работ:\n\n"

        keyboard = []
        selected_count = len(selected_jobs)

        for j_name, j_details in jobs.items():
            available = is_job_available(j_name)
            current_count = get_users_count_by_job(j_name)
            max_count = j_details['max_users']

            # Статус выбранной работы
            if j_name in selected_jobs:
                status = "✅ ✓"  # Галочка для выбранных
            else:
                status = "✅" if available else "❌"
            
            availability = f"({current_count}/{max_count})"

            # Отображаем в тексте
            if j_name in selected_jobs:
                text += f"{status} **{j_name}** {availability} (ВЫБРАНО)\n"
            else:
                text += f"{status} {j_name} {availability}\n"

            # Кнопки
            if j_name in selected_jobs:
                keyboard.append([InlineKeyboardButton(f"❌ Убрать {j_name}", callback_data=f"job_toggle_{j_name}")])
            elif available and selected_count < MAX_JOBS_PER_USER:
                keyboard.append([InlineKeyboardButton(f"✅ Выбрать {j_name}", callback_data=f"job_toggle_{j_name}")])
            else:
                if not available:
                    keyboard.append([InlineKeyboardButton(f"❌ {j_name} (нет мест)", callback_data="no_action")])
                elif selected_count >= MAX_JOBS_PER_USER:
                    keyboard.append([InlineKeyboardButton(f"❌ {j_name} (лимит {MAX_JOBS_PER_USER})", callback_data="no_action")])

        keyboard.append([InlineKeyboardButton("📋 Мои выбранные работы", callback_data="show_selected")])
        keyboard.append([InlineKeyboardButton("✅ Завершить выбор", callback_data="finish_selection")])
        keyboard.append([InlineKeyboardButton("🔙 Назад к категориям", callback_data="back_to_categories")])

        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

async def show_selected_jobs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    selected_jobs = context.user_data.get('selected_jobs', [])

    if not selected_jobs:
        await query.edit_message_text(
            "❌ Вы не выбрали ни одной работы!\n\n"
            "Пожалуйста, выберите хотя бы одну работу.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Назад", callback_data="back_to_categories")]
            ])
        )
        return

    text = "📋 **ВАШИ ВЫБРАННЫЕ РАБОТЫ:**\n\n"
    for i, job_name in enumerate(selected_jobs, 1):
        text += f"{i}. {job_name}\n"

    text += f"\nВсего: {len(selected_jobs)}/{MAX_JOBS_PER_USER}"

    keyboard = [
        [InlineKeyboardButton("🔄 Изменить выбор", callback_data="back_to_categories")],
        [InlineKeyboardButton("✅ Подтвердить", callback_data="confirm_selection")]
    ]

    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def confirm_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    selected_jobs = context.user_data.get('selected_jobs', [])

    if not selected_jobs:
        await query.edit_message_text(
            "❌ Вы не выбрали ни одной работы!",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Назад", callback_data="back_to_categories")]
            ])
        )
        return CONFIRM_REGISTRATION

    text = "📋 **ПОДТВЕРЖДЕНИЕ ЗАЯВКИ**\n\n"
    text += f"👤 **Никнейм:** {context.user_data['nickname']}\n"
    text += f"📌 **Источник:** {context.user_data['source']}\n\n"
    text += "💼 **Выбранные работы:**\n"

    for job_name in selected_jobs:
        text += f"• {job_name}\n"

    text += f"\nВсего выбрано работ: {len(selected_jobs)}/{MAX_JOBS_PER_USER}\n\n"
    text += "Всё верно?"

    keyboard = [
        [
            InlineKeyboardButton("✅ Да, отправить", callback_data="submit_registration"),
            InlineKeyboardButton("❌ Нет, изменить", callback_data="back_to_categories")
        ]
    ]

    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    return CONFIRM_REGISTRATION

async def submit_registration(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user = query.from_user
    selected_jobs = context.user_data.get('selected_jobs', [])

    try:
        app_id = create_application(
            user.id,
            user.username,
            context.user_data['nickname'],
            context.user_data['source'],
            selected_jobs
        )

        if app_id and app_id > 0:
            await query.edit_message_text(
                f"✅ **ЗАЯВКА ОТПРАВЛЕНА!**\n\n"
                f"📋 Ваша заявка #{app_id} отправлена на рассмотрение.\n"
                f"⏳ Администратор рассмотрит её в ближайшее время.\n\n"
                f"📊 **Данные заявки:**\n"
                f"👤 Никнейм: {context.user_data['nickname']}\n"
                f"💼 Работ: {len(selected_jobs)}\n"
                f"📌 Источник: {context.user_data['source']}\n\n"
                f"Ожидайте одобрения!",
                reply_markup=get_main_menu(user.id)
            )

            jobs_text = "\n".join([f"• {job}" for job in selected_jobs])
            try:
                await context.bot.send_message(
                    ADMIN_ID,
                    f"📋 **НОВАЯ ЗАЯВКА НА ВСТУПЛЕНИЕ!**\n\n"
                    f"🆔 **ID заявки:** #{app_id}\n"
                    f"👤 **Пользователь:** {context.user_data['nickname']}\n"
                    f"📱 **TG:** @{user.username or 'нет'}\n"
                    f"🆔 **User ID:** {user.id}\n"
                    f"📌 **Источник:** {context.user_data['source']}\n\n"
                    f"💼 **Выбранные работы:**\n{jobs_text}\n\n"
                    f"🔗 **Ссылка на пользователя:** tg://user?id={user.id}",
                    reply_markup=InlineKeyboardMarkup([
                        [
                            InlineKeyboardButton("✅ Одобрить", callback_data=f"approve_app_{app_id}"),
                            InlineKeyboardButton("❌ Отклонить", callback_data=f"reject_app_{app_id}")
                        ],
                        [InlineKeyboardButton("📋 Посмотреть все заявки", callback_data="view_applications")]
                    ])
                )
            except Exception as e:
                logger.error(f"Ошибка уведомления админа: {e}")
        else:
            await query.edit_message_text(
                "❌ Ошибка при отправке заявки! Возможно, у вас уже есть активная заявка.",
                reply_markup=get_main_menu(user.id)
            )
    except Exception as e:
        logger.error(f"Ошибка при создании заявки: {e}")
        await query.edit_message_text(
            "❌ Ошибка при отправке заявки! Попробуйте позже.",
            reply_markup=get_main_menu(user.id)
        )

    context.user_data.clear()
    return ConversationHandler.END

# ОТДЕЛЬНЫЕ ОБРАБОТЧИКИ ДЛЯ ЗАЯВОК (не в ConversationHandler)
async def view_applications(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.from_user.id != ADMIN_ID:
        await query.edit_message_text("⛔ Нет доступа!")
        return

    pending_apps = get_pending_applications()

    if not pending_apps:
        await query.edit_message_text(
            "📭 **Нет ожидающих заявок**",
            reply_markup=get_main_menu(ADMIN_ID)
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

async def view_application_detail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.from_user.id != ADMIN_ID:
        await query.edit_message_text("⛔ Нет доступа!")
        return

    if query.data.startswith("view_app_"):
        app_id = int(query.data.replace("view_app_", ""))

    app = get_application(app_id)
    if not app:
        await query.edit_message_text("❌ Заявка не найдена!")
        return

    jobs = app.get('jobs', [])
    jobs_text = "\n".join([f"• {job}" for job in jobs]) if jobs else "Не указаны"

    text = (
        f"📋 **ЗАЯВКА НА ВСТУПЛЕНИЕ #{app_id}**\n\n"
        f"👤 **Никнейм:** {app['nickname']}\n"
        f"📱 **Telegram:** @{app.get('username', 'нет')}\n"
        f"🆔 **User ID:** {app['user_id']}\n"
        f"📌 **Источник:** {app['source']}\n"
        f"📅 **Подана:** {app.get('created_at', 'N/A')[:10]}\n\n"
        f"💼 **Выбранные работы:**\n{jobs_text}"
    )

    keyboard = [
        [
            InlineKeyboardButton("✅ Одобрить", callback_data=f"approve_app_{app_id}"),
            InlineKeyboardButton("❌ Отклонить", callback_data=f"reject_app_{app_id}")
        ],
        [InlineKeyboardButton("🔙 К списку заявок", callback_data="view_applications")]
    ]

    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def approve_application_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.from_user.id != ADMIN_ID:
        await query.edit_message_text("⛔ Нет доступа!")
        return

    if query.data.startswith("approve_app_"):
        app_id = int(query.data.replace("approve_app_", ""))

    if approve_application(app_id):
        app = get_application(app_id)
        await query.edit_message_text(
            f"✅ **ЗАЯВКА #{app_id} ОДОБРЕНА!**\n\n"
            f"👤 Пользователь: {app['nickname']}\n"
            f"💼 Статус: Член клана\n"
            f"💰 Баланс: {START_COINS} акойнов\n\n"
            f"Пользователь уведомлен.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 К заявкам", callback_data="view_applications")]
            ])
        )
    else:
        await query.edit_message_text(
            "❌ Ошибка при одобрении заявки!",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 К заявкам", callback_data="view_applications")]
            ])
        )

async def reject_application_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.from_user.id != ADMIN_ID:
        await query.edit_message_text("⛔ Нет доступа!")
        return

    if query.data.startswith("reject_app_"):
        app_id = int(query.data.replace("reject_app_", ""))

    context.user_data['rejecting_app'] = app_id
    context.user_data['waiting_for_rejection_reason'] = True

    await query.edit_message_text(
        f"❌ **ОТКЛОНЕНИЕ ЗАЯВКИ #{app_id}**\n\n"
        f"Введите причину отклонения:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Отмена", callback_data=f"view_app_{app_id}")]
        ])
    )

async def process_rejection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Проверяем, что это личное сообщение
    if update.message and update.message.chat.type != 'private':
        return

    # Проверяем, ожидаем ли мы причину отклонения
    if not context.user_data.get('waiting_for_rejection_reason'):
        return

    reason = update.message.text.strip()
    app_id = context.user_data.get('rejecting_app')
    
    if not app_id:
        await update.message.reply_text("❌ Ошибка! Нет активной заявки для отклонения.")
        context.user_data.clear()
        return

    if reject_application(app_id, reason):
        await update.message.reply_text(
            f"✅ **ЗАЯВКА #{app_id} ОТКЛОНЕНА!**\n"
            f"📝 Причина: {reason}",
            reply_markup=get_main_menu(ADMIN_ID)
        )
    else:
        await update.message.reply_text(
            "❌ Ошибка при отклонении заявки!",
            reply_markup=get_main_menu(ADMIN_ID)
        )

    # Очищаем состояние
    context.user_data.clear()

def setup_registration_handlers(application):
    """Настройка обработчиков регистрации"""
    reg_conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(start_registration, pattern='^register$')],
        states={
            ASKING_NICKNAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, ask_nickname),
            ],
            ASKING_SOURCE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, ask_source),
            ],
            SELECTING_JOBS: [
                CallbackQueryHandler(show_category_jobs, pattern='^cat_'),
                CallbackQueryHandler(show_category_jobs, pattern='^back_to_categories$'),
                CallbackQueryHandler(toggle_job_selection, pattern='^job_toggle_'),
                CallbackQueryHandler(show_selected_jobs, pattern='^show_selected$'),
                CallbackQueryHandler(confirm_selection, pattern='^finish_selection$'),
                CallbackQueryHandler(confirm_selection, pattern='^confirm_selection$'),
            ],
            CONFIRM_REGISTRATION: [
                CallbackQueryHandler(submit_registration, pattern='^submit_registration$'),
                CallbackQueryHandler(show_category_jobs, pattern='^back_to_categories$')
            ],
        },
        fallbacks=[
            CallbackQueryHandler(lambda u,c: ConversationHandler.END, pattern='^back_to_menu$'),
            CallbackQueryHandler(lambda u,c: ConversationHandler.END, pattern='^back$')
        ],
        per_message=False
    )

    # Регистрируем обработчики заявок ОТДЕЛЬНО
    application.add_handler(reg_conv_handler)
    application.add_handler(CallbackQueryHandler(view_applications, pattern='^view_applications$'))
    application.add_handler(CallbackQueryHandler(view_application_detail, pattern='^view_app_'))
    application.add_handler(CallbackQueryHandler(approve_application_action, pattern='^approve_app_'))
    application.add_handler(CallbackQueryHandler(reject_application_action, pattern='^reject_app_'))
    
    # Обработчик для ввода причины отклонения
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE,
        process_rejection
    ))
