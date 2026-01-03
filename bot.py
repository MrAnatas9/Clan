import logging
import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler, ConversationHandler
from config import *
from database_supabase import *

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Состояния
(
    ASKING_NICKNAME, ASKING_SOURCE, SELECTING_JOBS, 
    CONFIRM_REGISTRATION, CHANGING_NICKNAME, SENDING_MESSAGE,
    CREATING_TASK_TITLE, CREATING_TASK_DESC, CREATING_TASK_REWARD_COINS, 
    CREATING_TASK_REWARD_EXP, BAN_REASON, MESSAGE_REASON,
    GIVING_COINS, CHANGING_JOBS, VIEWING_APPS, VIEWING_MSGS,
    VIEWING_USERS, TASK_DESCRIPTION, TASK_DEADLINE, TASK_PROOF
) = range(20)

def get_main_menu(user_id):
    user = get_user(user_id)
    
    if user_id == ADMIN_ID:
        keyboard = [
            [InlineKeyboardButton("📊 Статистика", callback_data="stats")],
            [InlineKeyboardButton("📝 Заявки", callback_data="applications")],
            [InlineKeyboardButton("📋 Задания", callback_data="admin_tasks")],
            [InlineKeyboardButton("👥 Пользователи", callback_data="users_list")],
            [InlineKeyboardButton("💌 Сообщения", callback_data="admin_messages")],
            [InlineKeyboardButton("⚙️ Настройки", callback_data="admin_settings")]
        ]
    elif user:
        keyboard = [
            [InlineKeyboardButton("👤 Профиль", callback_data="profile")],
            [InlineKeyboardButton("📋 Задания", callback_data="tasks")],
            [InlineKeyboardButton("💼 Мои работы", callback_data="my_jobs")],
            [InlineKeyboardButton("🏆 Топ", callback_data="top")],
            [InlineKeyboardButton("💰 Перевод", callback_data="transfer")],
            [InlineKeyboardButton("✉️ Сообщение админу", callback_data="send_message")],
            [
                InlineKeyboardButton("🔄 Ник", callback_data="change_nick"),
                InlineKeyboardButton("🔄 Работы", callback_data="change_jobs")
            ],
            [InlineKeyboardButton("📞 Поддержка", url="https://t.me/MrAnatas")]
        ]
    else:
        keyboard = [
            [InlineKeyboardButton("🚀 Регистрация", callback_data="register")],
            [InlineKeyboardButton("📞 Поддержка", url="https://t.me/MrAnatas")]
        ]
    
    return InlineKeyboardMarkup(keyboard)

# ========== ОСНОВНЫЕ КОМАНДЫ ==========

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    if update.message:
        await update.message.reply_text(
            f"👋 Привет, {user.first_name}!\n"
            f"👹 Добро пожаловать в клан АД!\n\n"
            f"Выберите действие:",
            reply_markup=get_main_menu(user.id)
        )
    else:
        await update.callback_query.edit_message_text(
            f"👋 Привет, {user.first_name}!\n"
            f"👹 Добро пожаловать в клан АД!\n\n"
            f"Выберите действие:",
            reply_markup=get_main_menu(user.id)
        )

# ========== РЕГИСТРАЦИЯ ==========

async def start_registration(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    if get_user(user.id):
        await query.edit_message_text(
            "✅ Вы уже зарегистрированы!",
            reply_markup=get_main_menu(user.id)
        )
        return
    
    await query.edit_message_text(
        "📝 **РЕГИСТРАЦИЯ В КЛАНЕ**\n\n"
        "Введите ваш игровой никнейм:"
    )
    
    context.user_data['selected_jobs'] = []
    return ASKING_NICKNAME

async def ask_nickname(update: Update, context: ContextTypes.DEFAULT_TYPE):
    nickname = update.message.text.strip()
    
    if len(nickname) < 3:
        await update.message.reply_text("❌ Никнейм должен быть не менее 3 символов.\nПопробуйте снова:")
        return ASKING_NICKNAME
    
    context.user_data['nickname'] = nickname
    await update.message.reply_text(
        "📌 **Откуда вы узнали о клане?**"
    )
    
    return ASKING_SOURCE

async def ask_source(update: Update, context: ContextTypes.DEFAULT_TYPE):
    source = update.message.text.strip()
    context.user_data['source'] = source
    
    categories = get_categories()
    keyboard = []
    for category in categories:
        keyboard.append([InlineKeyboardButton(category, callback_data=f"cat_{category}")])
    
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back")])
    
    await update.message.reply_text(
        "💼 **ВЫБОР РАБОТ**\n\n"
        "Вы можете выбрать до 3 работ.\n"
        "Все работы доступны с 1 уровня!\n"
        "Выберите категорию:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    
    return SELECTING_JOBS

async def show_category_jobs(update: Update, context: ContextTypes.DEFAULT_TYPE, category):
    query = update.callback_query
    await query.answer()
    
    jobs = get_jobs_by_category(category)
    
    text = f"💼 **{category}**\n\n"
    text += "Выберите работу (можно до 3):\n\n"
    
    keyboard = []
    for job_name, job_details in jobs.items():
        available = is_job_available(job_name)
        current_count = get_users_count_by_job(job_name)
        max_count = job_details['max_users']
        
        status = "✅" if available else "❌"
        availability = f"({current_count}/{max_count})"
        
        if job_name in context.user_data.get('selected_jobs', []):
            text += f"✓ {job_name} {availability}\n"
        else:
            text += f"{status} {job_name} {availability}\n"
        
        if job_name in context.user_data.get('selected_jobs', []):
            keyboard.append([InlineKeyboardButton(f"❌ Убрать {job_name}", callback_data=f"job_toggle_{job_name}")])
        elif available and len(context.user_data.get('selected_jobs', [])) < 3:
            keyboard.append([InlineKeyboardButton(f"✅ Выбрать {job_name}", callback_data=f"job_toggle_{job_name}")])
        else:
            if not available:
                keyboard.append([InlineKeyboardButton(f"❌ {job_name} (нет мест)", callback_data="no_action")])
            elif len(context.user_data.get('selected_jobs', [])) >= 3:
                keyboard.append([InlineKeyboardButton(f"❌ {job_name} (лимит 3)", callback_data="no_action")])
    
    keyboard.append([InlineKeyboardButton("📋 Мои выбранные работы", callback_data="show_selected")])
    keyboard.append([InlineKeyboardButton("✅ Завершить выбор", callback_data="finish_selection")])
    keyboard.append([InlineKeyboardButton("🔙 Назад к категориям", callback_data="back_to_categories")])
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def toggle_job_selection(update: Update, context: ContextTypes.DEFAULT_TYPE, job_name):
    query = update.callback_query
    await query.answer()
    
    selected_jobs = context.user_data.get('selected_jobs', [])
    
    if job_name in selected_jobs:
        selected_jobs.remove(job_name)
        await query.answer(f"❌ {job_name} удалена из выбранных")
    else:
        if len(selected_jobs) >= 3:
            await query.answer("❌ Можно выбрать максимум 3 работы!")
            return
        
        if not is_job_available(job_name):
            await query.answer("❌ Эта работа уже занята!")
            return
        
        selected_jobs.append(job_name)
        await query.answer(f"✅ {job_name} добавлена в выбранных")
    
    context.user_data['selected_jobs'] = selected_jobs
    
    job_details = JOBS_DETAILS.get(job_name)
    if job_details:
        await show_category_jobs(update, context, job_details['category'])

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
    
    keyboard = [
        [InlineKeyboardButton("🔄 Изменить выбор", callback_data="back_to_categories")],
        [InlineKeyboardButton("✅ Подтвердить", callback_data="confirm_selection")]
    ]
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

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
        return
    
    text = "📋 **ПОДТВЕРЖДЕНИЕ РЕГИСТРАЦИИ**\n\n"
    text += f"👤 **Никнейм:** {context.user_data['nickname']}\n"
    text += f"📌 **Источник:** {context.user_data['source']}\n\n"
    text += "💼 **Выбранные работы:**\n"
    
    for job_name in selected_jobs:
        text += f"• {job_name}\n"
    
    text += f"\nВсего выбрано работ: {len(selected_jobs)}/3\n\n"
    text += "Всё верно?"
    
    keyboard = [
        [
            InlineKeyboardButton("✅ Да, отправить", callback_data="submit_registration"),
            InlineKeyboardButton("❌ Нет, изменить", callback_data="back_to_categories")
        ]
    ]
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    
    return CONFIRM_REGISTRATION

async def submit_registration(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    selected_jobs = context.user_data.get('selected_jobs', [])
    
    save_user(user.id, user.username, context.user_data['nickname'], selected_jobs)
    
    await query.edit_message_text(
        f"✅ **РЕГИСТРАЦИЯ УСПЕШНА!**\n\n"
        f"👤 **Ваш никнейм:** {context.user_data['nickname']}\n"
        f"💼 **Выбранные работы:** {len(selected_jobs)}\n"
        f"💰 **Стартовые акойны:** {START_COINS}\n\n"
        f"🔗 **Ссылка на чат клана:** {CLAN_LINK}\n"
        f"📞 **Поддержка:** @MrAnatas\n\n"
        f"Слава Аду! 👹",
        reply_markup=get_main_menu(user.id)
    )
    
    context.user_data.clear()
    return ConversationHandler.END

# ========== ГРУППОВЫЕ КОМАНДЫ ==========

async def handle_group_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка команд в группе"""
    if not update.message or not update.message.text:
        return
    
    text = update.message.text.strip()
    user = update.effective_user
    reply_to = update.message.reply_to_message
    
    # Команда "забрать"
    if text.startswith("забрать"):
        if not reply_to:
            await update.message.reply_text("❌ Ответьте на сообщение пользователя, у которого нужно забрать акойны!")
            return
        
        target_user = reply_to.from_user
        current_user = get_user(user.id)
        target_user_data = get_user(target_user.id)
        
        if not current_user:
            await update.message.reply_text("❌ Вы не зарегистрированы в боте!")
            return
        
        if not target_user_data:
            await update.message.reply_text("❌ Этот пользователь не зарегистрирован в боте!")
            return
        
        # Парсим сумму
        try:
            amount = int(text.split()[1])
            if amount <= 0:
                await update.message.reply_text("❌ Сумма должна быть положительной!")
                return
        except:
            await update.message.reply_text("❌ Используйте: забрать <сумма>")
            return
        
        # Проверяем баланс
        if target_user_data['coins'] < amount:
            await update.message.reply_text(f"❌ У пользователя только {target_user_data['coins']} акойнов!")
            return
        
        # Выполняем перевод
        success, message = transfer_coins(target_user.id, user.id, amount, "Забрать в группе")
        if success:
            await update.message.reply_text(
                f"✅ {user.first_name} забрал {amount} акойнов у {target_user.first_name}\n"
                f"💰 Новый баланс:\n"
                f"👤 {user.first_name}: {get_user(user.id)['coins']} акойнов\n"
                f"👤 {target_user.first_name}: {get_user(target_user.id)['coins']} акойнов"
            )
        else:
            await update.message.reply_text(f"❌ {message}")
    
    # Команда "выдать"
    elif text.startswith("выдать"):
        target_username = None
        
        # Ищем упоминание
        if update.message.entities:
            for entity in update.message.entities:
                if entity.type == "mention":
                    target_username = text[entity.offset:entity.offset + entity.length]
                    break
        
        if not target_username and reply_to:
            target_user = reply_to.from_user
        elif target_username:
            # Нужно найти пользователя по username
            await update.message.reply_text("❌ Для выдачи нужно ответить на сообщение пользователя!")
            return
        else:
            await update.message.reply_text("❌ Ответьте на сообщение пользователя или укажите @username!")
            return
        
        current_user = get_user(user.id)
        target_user_data = get_user(target_user.id)
        
        if not current_user:
            await update.message.reply_text("❌ Вы не зарегистрированы в боте!")
            return
        
        if not target_user_data:
            await update.message.reply_text("❌ Этот пользователь не зарегистрирован в боте!")
            return
        
        # Парсим сумму
        try:
            amount = int(text.split()[-1])
            if amount <= 0:
                await update.message.reply_text("❌ Сумма должна быть положительной!")
                return
        except:
            await update.message.reply_text("❌ Используйте: выдать <сумма>")
            return
        
        # Проверяем баланс
        if current_user['coins'] < amount:
            await update.message.reply_text(f"❌ У вас только {current_user['coins']} акойнов!")
            return
        
        # Выполняем перевод
        success, message = transfer_coins(user.id, target_user.id, amount, "Выдать в группе")
        if success:
            await update.message.reply_text(
                f"✅ {user.first_name} выдал {amount} акойнов {target_user.first_name}\n"
                f"💰 Новый баланс:\n"
                f"👤 {user.first_name}: {get_user(user.id)['coins']} акойнов\n"
                f"👤 {target_user.first_name}: {get_user(target_user.id)['coins']} акойнов"
            )
        else:
            await update.message.reply_text(f"❌ {message}")
    
    # Команда "уволить" (только админ)
    elif text.startswith("уволить") and user.id == ADMIN_ID:
        if not reply_to:
            await update.message.reply_text("❌ Ответьте на сообщение пользователя!")
            return
        
        target_user = reply_to.from_user
        target_user_data = get_user(target_user.id)
        
        if not target_user_data:
            await update.message.reply_text("❌ Этот пользователь не зарегистрирован!")
            return
        
        # Увольняем (очищаем работы)
        update_user_jobs(target_user.id, [])
        
        await update.message.reply_text(
            f"⛔ Администратор уволил {target_user.first_name}!\n"
            f"💼 Все работы сняты."
        )
    
    # Команда "долг"
    elif text == "долг":
        user_data = get_user(user.id)
        if not user_data:
            await update.message.reply_text("❌ Вы не зарегистрированы!")
            return
        
        if user_data['coins'] >= 0:
            await update.message.reply_text(f"✅ Ваш баланс: {user_data['coins']} акойнов (без долга)")
        else:
            debt = -user_data['coins']
            await update.message.reply_text(
                f"⚠️ ВЫ В ДОЛГАХ!\n"
                f"💰 Долг: {debt} акойнов\n"
                f"📈 Максимальный долг: {MAX_DEBT} акойнов\n\n"
                f"Чтобы взять кредит у клана:\n"
                f"Напишите админу @MrAnatas"
            )

# ========== ЗАДАНИЯ ==========

async def show_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
    
    active_tasks = get_active_tasks()
    
    if not active_tasks:
        await query.edit_message_text(
            "📭 **Нет активных заданий**\n\n"
            "Задания создает администратор.",
            reply_markup=get_main_menu(user_id)
        )
        return
    
    text = "📋 **ДОСТУПНЫЕ ЗАДАНИЯ**\n\n"
    
    for task in active_tasks[:5]:
        assigned = "✅ Взято" if task['assigned_to'] else "⏳ Свободно"
        text += f"📌 **{task['title']}**\n"
        text += f"📝 {task['description'][:50]}...\n"
        text += f"🎁 Награда: {task['reward_coins']}🪙 + {task['reward_exp']} опыта\n"
        text += f"⏰ Статус: {assigned}\n"
        
        if not task['assigned_to']:
            text += f"🔘 [Взять задание](https://t.me/your_bot?start=task_{task['id']})\n"
        
        text += "\n"
    
    keyboard = []
    for task in active_tasks[:3]:
        if not task['assigned_to']:
            keyboard.append([
                InlineKeyboardButton(f"📋 {task['title'][:15]}", callback_data=f"take_task_{task['id']}")
            ])
    
    if keyboard:
        keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back")])
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown',
            disable_web_page_preview=True
        )
    else:
        await query.edit_message_text(
            "📭 **Нет свободных заданий**\n\n"
            "Все задания уже взяты.",
            reply_markup=get_main_menu(user_id)
        )

async def take_task(update: Update, context: ContextTypes.DEFAULT_TYPE, task_id):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    success, message = assign_task(task_id, user_id)
    
    if success:
        task = get_task(task_id)
        await query.edit_message_text(
            f"✅ **ЗАДАНИЕ ВЗЯТО!**\n\n"
            f"📋 **Задание:** {task['title']}\n"
            f"📝 **Описание:** {task['description']}\n"
            f"⏰ **Срок:** {TASK_DEADLINE_HOURS} часов\n"
            f"🎁 **Награда:** {task['reward_coins']}🪙 + {task['reward_exp']} опыта\n\n"
            f"⚠️ **Внимание:**\n"
            f"- При просрочке штраф {TASK_PENALTY_PERCENT*100}% от награды\n"
            f"- При невыполнении штраф {TASK_FAIL_PENALTY_EXP} опыта\n\n"
            f"После выполнения отправьте скриншоты сюда.",
            reply_markup=get_main_menu(user_id)
        )
    else:
        await query.edit_message_text(
            f"❌ {message}",
            reply_markup=get_main_menu(user_id)
        )

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка фото для proof заданий"""
    user_id = update.effective_user.id
    user = get_user(user_id)
    
    if not user:
        return
    
    # Проверяем, есть ли активные задания у пользователя
    response = supabase.table('tasks').select('*').eq('assigned_to', user_id).eq('status', 'assigned').execute()
    
    if not response.data:
        await update.message.reply_text(
            "У вас нет активных заданий для отправки proof!",
            reply_markup=get_main_menu(user_id)
        )
        return
    
    # Получаем самое новое задание
    task = response.data[0]
    photo = update.message.photo[-1]
    photo_file = await photo.get_file()
    
    # В реальном боте нужно сохранить фото и получить URL
    # Здесь просто имитируем
    await update.message.reply_text(
        f"📸 **ФОТО ПРИНЯТО ДЛЯ ЗАДАНИЯ**\n\n"
        f"📋 Задание: {task['title']}\n"
        f"✅ Proof отправлен на проверку админу.\n\n"
        f"Ожидайте одобрения!",
        reply_markup=get_main_menu(user_id)
    )
    
    # Уведомляем админа
    try:
        await context.bot.send_message(
            ADMIN_ID,
            f"📸 **НОВЫЙ PROOF ЗАДАНИЯ**\n\n"
            f"👤 Пользователь: {user['nickname']}\n"
            f"📋 Задание: {task['title']}\n"
            f"🆔 ID задания: {task['id']}\n\n"
            f"Проверьте proof!",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("✅ Одобрить", callback_data=f"approve_task_{task['id']}"),
                    InlineKeyboardButton("❌ Отклонить", callback_data=f"reject_task_{task['id']}")
                ]
            ])
        )
    except Exception as e:
        logger.error(f"Ошибка уведомления админа: {e}")

# ========== ПРОФИЛЬ И ПЕРЕВОДЫ ==========

async def show_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
    
    debt_status = "✅" if user['coins'] >= 0 else "⚠️"
    debt_text = f"Долг: {-user['coins']}🪙" if user['coins'] < 0 else "Без долгов"
    
    text = (
        f"👤 **ПРОФИЛЬ**\n\n"
        f"🎮 **Никнейм:** {user['nickname']}\n"
        f"📱 **TG:** @{user.get('username', 'нет')}\n"
        f"👑 **Уровень:** {user['level']}\n"
        f"📈 **Опыт:** {user['exp']}/{user['level'] * EXP_PER_LEVEL}\n"
        f"💰 **Акойны:** {user['coins']}🪙 {debt_status}\n"
        f"📊 **{debt_text}**\n"
        f"💼 **Основная работа:** {user['job']}\n"
        f"💌 **Сообщений:** {user.get('messages_sent', 0)}\n"
        f"🆔 **ID:** {user['user_id']}"
    )
    
    keyboard = [
        [InlineKeyboardButton("💸 Перевод игроку", callback_data="transfer_to_user")],
        [InlineKeyboardButton("🏦 Кредит у клана", callback_data="clan_credit")],
        [InlineKeyboardButton("🔙 Назад", callback_data="back")]
    ]
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def transfer_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        "💸 **ПЕРЕВОД АКОЙНОВ**\n\n"
        "Введите в формате:\n"
        "<ID_получателя> <сумма>\n\n"
        "Пример: 123456789 50",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Назад", callback_data="profile")]
        ])
    )
    
    return GIVING_COINS

async def process_transfer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = update.effective_user.id
        text = update.message.text.strip()
        
        parts = text.split()
        if len(parts) != 2:
            await update.message.reply_text("❌ Формат: <ID_получателя> <сумма>")
            return GIVING_COINS
        
        target_id = int(parts[0])
        amount = int(parts[1])
        
        if amount <= 0:
            await update.message.reply_text("❌ Сумма должна быть положительной!")
            return GIVING_COINS
        
        success, message = transfer_coins(user_id, target_id, amount, "Перевод через бота")
        
        await update.message.reply_text(
            f"{'✅' if success else '❌'} {message}",
            reply_markup=get_main_menu(user_id)
        )
        
        return ConversationHandler.END
        
    except ValueError:
        await update.message.reply_text("❌ Неверный формат чисел!")
        return GIVING_COINS
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {str(e)}")
        return GIVING_COINS

# ========== CALLBACK ОБРАБОТЧИК ==========

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    
    await query.answer()
    
    # Основные команды
    if data == "back":
        await start(update, context)
    elif data == "profile":
        await show_profile(update, context)
    elif data == "transfer":
        await transfer_menu(update, context)
        return GIVING_COINS
    elif data == "tasks":
        await show_tasks(update, context)
    elif data == "register":
        await start_registration(update, context)
        return ASKING_NICKNAME
    
    # Регистрация
    elif data.startswith("cat_"):
        category = data.replace("cat_", "")
        await show_category_jobs(update, context, category)
    elif data.startswith("job_toggle_"):
        job_name = data.replace("job_toggle_", "")
        await toggle_job_selection(update, context, job_name)
    elif data in ["show_selected", "finish_selection"]:
        await show_selected_jobs(update, context)
    elif data == "back_to_categories":
        categories = get_categories()
        keyboard = [[InlineKeyboardButton(cat, callback_data=f"cat_{cat}")] for cat in categories]
        keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back")])
        await query.edit_message_text(
            "💼 **ВЫБОР РАБОТ**\n\nВыберите категорию:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return SELECTING_JOBS
    elif data == "confirm_selection":
        await confirm_selection(update, context)
        return CONFIRM_REGISTRATION
    elif data == "submit_registration":
        await submit_registration(update, context)
        return ConversationHandler.END
    
    # Задания
    elif data.startswith("take_task_"):
        task_id = int(data.replace("take_task_", ""))
        await take_task(update, context, task_id)
    
    # Админ задачи
    elif data.startswith("approve_task_"):
        task_id = int(data.replace("approve_task_", ""))
        success, message = approve_task(task_id)
        await query.edit_message_text(f"{'✅' if success else '❌'} {message}")
    elif data.startswith("reject_task_"):
        task_id = int(data.replace("reject_task_", ""))
        context.user_data['rejecting_task'] = task_id
        await query.edit_message_text("📝 Введите причину отклонения:")
        return MESSAGE_REASON

# ========== ОСНОВНОЙ ЗАПУСК ==========

def main():
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Регистрация
    reg_conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(start_registration, pattern='^register$')],
        states={
            ASKING_NICKNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_nickname)],
            ASKING_SOURCE: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_source)],
            SELECTING_JOBS: [CallbackQueryHandler(handle_callback, pattern='^cat_|^job_toggle_|^show_selected|^finish_selection|^back_to_categories|^confirm_selection|^submit_registration')],
            CONFIRM_REGISTRATION: [CallbackQueryHandler(handle_callback, pattern='^submit_registration|^back_to_categories')],
        },
        fallbacks=[CommandHandler("start", start)],
        per_message=False
    )
    
    # Перевод денег
    transfer_conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(transfer_menu, pattern='^transfer$')],
        states={
            GIVING_COINS: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_transfer)],
        },
        fallbacks=[CommandHandler("start", start)],
        per_message=False
    )
    
    # Основные хендлеры
    application.add_handler(CommandHandler("start", start))
    application.add_handler(reg_conv_handler)
    application.add_handler(transfer_conv_handler)
    
    # Групповые команды
    application.add_handler(MessageHandler(filters.TEXT & filters.ChatType.GROUPS, handle_group_message))
    
    # Фото для proof
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    
    # Callback хендлер
    application.add_handler(CallbackQueryHandler(handle_callback))
    
    # Запуск проверки дедлайнов каждые 10 минут
    job_queue = application.job_queue
    if job_queue:
        job_queue.run_repeating(lambda ctx: check_task_deadlines(), interval=600, first=10)
    
    logger.info("Бот запускается...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
