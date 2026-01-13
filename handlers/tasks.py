import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, MessageHandler, filters, CallbackQueryHandler
from config import *
from database import *
from states import *
from keyboards.main_menu import get_main_menu

logger = logging.getLogger(__name__)

async def tasks_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    tasks = get_active_tasks()

    if not tasks:
        await query.edit_message_text(
            "📭 **Нет активных заданий**\n\n"
            "Задания будут появляться по мере их создания администратором.",
            reply_markup=get_main_menu(user_id)
        )
        return VIEWING_TASKS

    text = "📝 **АКТИВНЫЕ ЗАДАНИЯ**\n\n"
    keyboard = []

    for task in tasks[:5]:
        deadline = task.get('deadline', 'Не ограничено')
        if deadline != 'Не ограничено':
            deadline_dt = datetime.fromisoformat(deadline)
            deadline_str = deadline_dt.strftime("%d.%m.%Y")
        else:
            deadline_str = deadline

        text += f"🆔 **#{task['id']}** - {task['title']}\n"
        text += f"💰 Награда: {task['reward_coins']} акойнов + {task['reward_exp']} опыта\n"
        text += f"📅 До: {deadline_str}\n\n"

        keyboard.append([
            InlineKeyboardButton(f"👁️ Посмотреть #{task['id']}", callback_data=f"view_task_{task['id']}")
        ])

    if user_id == ADMIN_ID:
        keyboard.append([InlineKeyboardButton("➕ Создать задание", callback_data="admin_create_task")])
        keyboard.append([InlineKeyboardButton("📋 На проверку", callback_data="admin_tasks_pending")])

    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back")])

    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    return VIEWING_TASKS

async def task_view(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data.startswith("view_task_"):
        task_id = int(query.data.replace("view_task_", ""))

    task = get_task(task_id)
    if not task or task['status'] != 'active':
        await query.edit_message_text("❌ Задание не найдено или не активно!")
        return VIEWING_TASKS

    completed_by_user = is_task_completed_by_user(query.from_user.id, task_id) if query.from_user.id != ADMIN_ID else False

    deadline = task.get('deadline', 'Не ограничено')
    if deadline != 'Не ограничено':
        deadline_dt = datetime.fromisoformat(deadline)
        deadline_str = deadline_dt.strftime("%d.%m.%Y %H:%M")
    else:
        deadline_str = deadline

    text = f"📝 **ЗАДАНИЕ #{task['id']}**\n\n"
    text += f"📌 **Название:** {task['title']}\n"
    text += f"📋 **Описание:** {task['description']}\n\n"
    text += f"💰 **Награда:** {task['reward_coins']} акойнов + {task['reward_exp']} опыта\n"
    text += f"📅 **Срок:** {deadline_str}\n"
    text += f"👤 **Создал:** Администратор\n"

    if completed_by_user:
        text += "\n✅ **Вы уже выполнили это задание!**\n"
        text += "⏳ Ожидайте проверки администратором."

    keyboard = []

    if query.from_user.id != ADMIN_ID and not completed_by_user:
        keyboard.append([InlineKeyboardButton("✅ Выполнить задание", callback_data=f"complete_task_{task_id}")])

    keyboard.append([InlineKeyboardButton("🔙 К списку заданий", callback_data="tasks_list")])

    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    return COMPLETING_TASK if query.from_user.id != ADMIN_ID and not completed_by_user else VIEWING_TASKS

async def admin_tasks_pending(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.from_user.id != ADMIN_ID:
        await query.edit_message_text("⛔ Нет доступа!")
        return

    pending_tasks = get_pending_tasks()

    if not pending_tasks:
        await query.edit_message_text(
            "📭 **Нет заданий на проверку**",
            reply_markup=get_main_menu(ADMIN_ID)
        )
        return

    text = "📝 **ЗАДАНИЯ НА ПРОВЕРКУ**\n\n"

    keyboard = []
    for task in pending_tasks[:5]:
        text += f"🆔 **#{task['id']}** - {task['title']}\n"
        text += f"💰 Награда: {task['reward_coins']} акойнов + {task['reward_exp']} опыта\n\n"

        keyboard.append([
            InlineKeyboardButton(f"👁️ Посмотреть #{task['id']}", callback_data=f"admin_view_task_{task['id']}")
        ])

    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="admin_panel")])

    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def admin_task_view(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.from_user.id != ADMIN_ID:
        await query.edit_message_text("⛔ Нет доступа!")
        return

    if query.data.startswith("admin_view_task_"):
        task_id = int(query.data.replace("admin_view_task_", ""))
    task = get_task(task_id)

    if not task:
        await query.edit_message_text("❌ Задание не найдено!")
        return

    text = f"📝 **ЗАДАНИЕ #{task_id}**\n\n"
    text += f"📌 **Название:** {task['title']}\n"
    text += f"📋 **Описание:** {task['description']}\n\n"
    text += f"💰 **Награда:** {task['reward_coins']} акойнов + {task['reward_exp']} опыта\n"
    text += f"📅 **Создано:** {task.get('created_at', '')[:10]}\n"
    text += f"📊 **Статус:** {task['status']}\n\n"
    completions = get_task_completions(task_id)
    if completions:
        text += f"✅ **Выполнили:** {len(completions)} человек\n"
        for comp in completions[:3]:
            user = get_user(comp['user_id'])
            if user:
                text += f"• {user['nickname']} ({comp.get('status', 'pending')})\n"

    keyboard = [
        [
            InlineKeyboardButton("✅ Одобрить задание", callback_data=f"admin_approve_task_{task_id}"),
            InlineKeyboardButton("❌ Отклонить", callback_data=f"admin_reject_task_{task_id}")
        ]
    ]

    if completions:
        keyboard.append([InlineKeyboardButton("👥 Проверить выполнения", callback_data=f"admin_check_completions_{task_id}")])

    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="admin_tasks_pending")])

    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def admin_create_task_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.from_user.id != ADMIN_ID:
        await query.edit_message_text("⛔ Нет доступа!")
        return

    await query.edit_message_text(
        "📝 **СОЗДАНИЕ ЗАДАНИЯ**\n\n"
        "Введите название задания:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Отмена", callback_data="tasks_list")]
        ])
    )

    return CREATING_TASK_TITLE

async def admin_create_task_title(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return CREATING_TASK_TITLE

    title = update.message.text.strip()

    if len(title) < 3:
        await update.message.reply_text("❌ Название должно быть не менее 3 символов!")
        return CREATING_TASK_TITLE

    context.user_data['task_title'] = title

    await update.message.reply_text(
        "📋 **ОПИСАНИЕ ЗАДАНИЯ**\n\n"
        "Введите подробное описание задания:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Отмена", callback_data="tasks_list")]
        ])
    )

    return CREATING_TASK_DESC

async def admin_create_task_desc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return CREATING_TASK_DESC

    description = update.message.text.strip()

    if len(description) < 10:
        await update.message.reply_text("❌ Описание должно быть не менее 10 символов!")
        return CREATING_TASK_DESC

    context.user_data['task_description'] = description

    await update.message.reply_text(
        "💰 **НАГРАДА В АКОЙНАХ**\n\n"
        "Введите количество акойнов за выполнение:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Отмена", callback_data="tasks_list")]
        ])
    )

    return CREATING_TASK_REWARD_COINS

async def admin_create_task_reward_coins(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return CREATING_TASK_REWARD_COINS

    try:
        reward_coins = int(update.message.text.strip())

        if reward_coins < TASK_MIN_REWARD_COINS or reward_coins > TASK_MAX_REWARD_COINS:
            await update.message.reply_text(f"❌ Награда должна быть от {TASK_MIN_REWARD_COINS} до {TASK_MAX_REWARD_COINS} акойнов!")
            return CREATING_TASK_REWARD_COINS

        context.user_data['task_reward_coins'] = reward_coins

        await update.message.reply_text(
            "📈 **НАГРАДА В ОПЫТЕ**\n\n"
            "Введите количество опыта за выполнение:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Отмена", callback_data="tasks_list")]
            ])
        )

        return CREATING_TASK_REWARD_EXP
    except ValueError:
        await update.message.reply_text("❌ Введите число!")
        return CREATING_TASK_REWARD_COINS

async def admin_create_task_reward_exp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return CREATING_TASK_REWARD_EXP

    try:
        reward_exp = int(update.message.text.strip())

        if reward_exp < TASK_MIN_REWARD_EXP or reward_exp > TASK_MAX_REWARD_EXP:
            await update.message.reply_text(f"❌ Опыт должен быть от {TASK_MIN_REWARD_EXP} до {TASK_MAX_REWARD_EXP}!")
            return CREATING_TASK_REWARD_EXP

        context.user_data['task_reward_exp'] = reward_exp

        await update.message.reply_text(
            "📅 **СРОК ВЫПОЛНЕНИЯ**\n\n"
            "Введите количество дней на выполнение задания:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Отмена", callback_data="tasks_list")]
            ])
        )

        return CREATING_TASK_DEADLINE
    except ValueError:
        await update.message.reply_text("❌ Введите число!")
        return CREATING_TASK_REWARD_EXP

async def admin_create_task_deadline(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return CREATING_TASK_DEADLINE

    try:
        deadline_days = int(update.message.text.strip())

        if deadline_days < 1 or deadline_days > 30:
            await update.message.reply_text("❌ Срок должен быть от 1 до 30 дней!")
            return CREATING_TASK_DEADLINE

        task_id = create_task(
            context.user_data['task_title'],
            context.user_data['task_description'],
            context.user_data['task_reward_coins'],
            context.user_data['task_reward_exp'],
            deadline_days
        )

        if task_id:
            await update.message.reply_text(
                f"✅ **ЗАДАНИЕ СОЗДАНО!**\n\n"
                f"🆔 ID задания: #{task_id}\n"
                f"📌 Название: {context.user_data['task_title']}\n"
                f"💰 Награда: {context.user_data['task_reward_coins']} акойнов + {context.user_data['task_reward_exp']} опыта\n"
                f"📅 Срок: {deadline_days} дней\n\n"
                f"Игроки могут увидеть задание после вашего одобрения.",
                reply_markup=get_main_menu(update.effective_user.id)
            )
        else:
            await update.message.reply_text(
                "❌ Ошибка при создании задания!",
                reply_markup=get_main_menu(update.effective_user.id)
            )

        context.user_data.clear()
        return ConversationHandler.END
    except ValueError:
        await update.message.reply_text("❌ Введите число!")
        return CREATING_TASK_DEADLINE

async def complete_task_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data.startswith("complete_task_"):
        task_id = int(query.data.replace("complete_task_", ""))

    task = get_task(task_id)

    if not task or task['status'] != 'active':
        await query.edit_message_text("❌ Задание не найдено или не активно!")
        return VIEWING_TASKS

    user_id = query.from_user.id

    if is_task_completed_by_user(user_id, task_id):
        await query.edit_message_text(
            "✅ **ВЫ УЖЕ ВЫПОЛНИЛИ ЭТО ЗАДАНИЕ!**\n\n"
            "Вы не можете выполнить одно задание дважды.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 К списку заданий", callback_data="tasks_list")]
            ])
        )
        return VIEWING_TASKS

    success, message = complete_task(user_id, task_id)

    if success:
        await query.edit_message_text(
            f"✅ **ЗАДАНИЕ ВЫПОЛНЕНО!**\n\n"
            f"📝 Задание: {task['title']}\n"
            f"⏳ Статус: Отправлено на проверку администратору\n\n"
            f"Ожидайте одобрения и получения награды!",
            reply_markup=get_main_menu(user_id)
        )

        # Уведомляем администратора
        user = get_user(user_id)
        try:
            await context.bot.send_message(
                ADMIN_ID,
                f"✅ **НОВОЕ ВЫПОЛНЕНИЕ ЗАДАНИЯ**\n\n"
                f"📝 Задание: #{task_id} - {task['title']}\n"
                f"👤 Выполнил: {user['nickname']}\n"
                f"📱 @{user.get('username', 'нет')}\n"
                f"🆔 ID: {user_id}\n\n"
                f"💰 Награда: {task['reward_coins']} акойнов + {task['reward_exp']} опыта",
                reply_markup=InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton("✅ Одобрить награду", callback_data=f"approve_completion_{user_id}_{task_id}"),
                        InlineKeyboardButton("❌ Отклонить", callback_data=f"reject_completion_{user_id}_{task_id}")
                    ]
                ])
            )
        except Exception as e:
            logger.error(f"Ошибка уведомления админа: {e}")
    else:
        await query.edit_message_text(
            f"❌ {message}",
            reply_markup=get_main_menu(user_id)
        )

    return ConversationHandler.END

async def admin_check_completions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.from_user.id != ADMIN_ID:
        await query.edit_message_text("⛔ Нет доступа!")
        return

    if query.data.startswith("admin_check_completions_"):
        task_id = int(query.data.replace("admin_check_completions_", ""))

    completions = get_task_completions(task_id)
    task = get_task(task_id)

    if not completions:
        await query.edit_message_text(
            "📭 Нет выполненных заданий на проверку",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Назад", callback_data=f"admin_view_task_{task_id}")]
            ])
        )
        return

    text = f"✅ **ВЫПОЛНЕНИЯ ЗАДАНИЯ #{task_id}**\n\n"
    text += f"📌 {task['title']}\n\n"

    keyboard = []

    for comp in completions[:10]:
        user = get_user(comp['user_id'])
        if user:
            status = comp.get('status', 'pending')
            status_emoji = "✅" if status == 'approved' else "⏳" if status == 'pending' else "❌"

            text += f"{status_emoji} {user['nickname']} - {status}\n"

            if status == 'pending':
                keyboard.append([
                    InlineKeyboardButton(f"✅ Одобрить {user['nickname']}",
                                       callback_data=f"approve_completion_{user['user_id']}_{task_id}")
                ])

    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data=f"admin_view_task_{task_id}")])

    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def admin_approve_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.from_user.id != ADMIN_ID:
        await query.edit_message_text("⛔ Нет доступа!")
        return

    if query.data.startswith("admin_approve_task_"):
        task_id = int(query.data.replace("admin_approve_task_", ""))

    if approve_task(task_id):
        await query.edit_message_text(
            f"✅ **ЗАДАНИЕ #{task_id} ОДОБРЕНО!**\n\n"
            f"Задание теперь видно всем игрокам.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 К заданиям", callback_data="admin_tasks_pending")]
            ])
        )
    else:
        await query.edit_message_text(
            f"❌ Ошибка при одобрении задания!",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 К заданиям", callback_data="admin_tasks_pending")]
            ])
        )

async def admin_reject_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.from_user.id != ADMIN_ID:
        await query.edit_message_text("⛔ Нет доступа!")
        return

    if query.data.startswith("admin_reject_task_"):
        task_id = int(query.data.replace("admin_reject_task_", ""))

    context.user_data['rejecting_task'] = task_id

    await query.edit_message_text(
        f"❌ **ОТКЛОНЕНИЕ ЗАДАНИЯ #{task_id}**\n\n"
        f"Введите причину отклонения:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Отмена", callback_data=f"admin_view_task_{task_id}")]
        ])
    )

async def process_task_rejection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # ИСПРАВЛЕНИЕ: Проверяем, что это администратор
    if update.effective_user.id != ADMIN_ID:
        return ConversationHandler.END

    if not update.message:
        return

    reason = update.message.text.strip()
    task_id = context.user_data.get('rejecting_task')

    if not task_id:
        await update.message.reply_text("❌ Ошибка!")
        return

    if reject_task(task_id, reason):
        await update.message.reply_text(
            f"✅ **ЗАДАНИЕ #{task_id} ОТКЛОНЕНО!**\n"
            f"📝 Причина: {reason}",
            reply_markup=get_main_menu(ADMIN_ID)
        )
    else:
        await update.message.reply_text(
            "❌ Ошибка при отклонении задания!",
            reply_markup=get_main_menu(ADMIN_ID)
        )

    context.user_data.clear()

async def approve_completion_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.from_user.id != ADMIN_ID:
        await query.edit_message_text("⛔ Нет доступа!")
        return

    if query.data.startswith("approve_completion_"):
        parts = query.data.replace("approve_completion_", "").split("_")
        if len(parts) >= 2:
            user_id = int(parts[0])
            task_id = int(parts[1])

    if not user_id or not task_id:
        await query.edit_message_text("❌ Ошибка данных!")
        return

    # Находим completion
    completions = get_task_completions(task_id)
    completion_id = None

    for comp in completions:
        if comp['user_id'] == user_id:
            completion_id = comp.get('id')
            break

    if not completion_id:
        await query.edit_message_text("❌ Выполнение не найдено!")
        return

    task = get_task(task_id)
    user = get_user(user_id)

    if approve_task_completion(completion_id):
        await query.edit_message_text(
            f"✅ **НАГРАДА ВЫДАНА!**\n\n"
            f"👤 Пользователь: {user['nickname']}\n"
            f"📝 Задание: {task['title']}\n"
            f"💰 Награда: {task['reward_coins']} акойнов + {task['reward_exp']} опыта\n\n"
            f"✅ Баланс пользователя обновлен.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 К проверкам", callback_data=f"admin_check_completions_{task_id}")]
            ])
        )

        # Уведомляем пользователя
        try:
            await context.bot.send_message(
                user_id,
                f"✅ **ВАШЕ ЗАДАНИЕ ОДОБРЕНО!**\n\n"
                f"📝 Задание: {task['title']}\n"
                f"💰 Получено: {task['reward_coins']} акойнов\n"
                f"📈 Получено: {task['reward_exp']} опыта\n\n"
                f"Спасибо за участие!",
                reply_markup=get_main_menu(user_id)
            )
        except Exception as e:
            logger.error(f"Ошибка уведомления пользователя: {e}")
    else:
        await query.edit_message_text(
            "❌ Ошибка при выдаче награды!",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 К проверкам", callback_data=f"admin_check_completions_{task_id}")]
            ])
        )

def setup_task_handlers(application):
    """Настройка обработчиков заданий"""
    tasks_conv_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(tasks_list, pattern='^tasks_list$'),
            CallbackQueryHandler(task_view, pattern='^view_task_'),
            CallbackQueryHandler(complete_task_action, pattern='^complete_task_'),
            CallbackQueryHandler(admin_tasks_pending, pattern='^admin_tasks_pending$'),
            CallbackQueryHandler(admin_task_view, pattern='^admin_view_task_'),
            CallbackQueryHandler(admin_approve_task, pattern='^admin_approve_task_'),
            CallbackQueryHandler(admin_reject_task, pattern='^admin_reject_task_'),
            CallbackQueryHandler(admin_check_completions, pattern='^admin_check_completions_'),
            CallbackQueryHandler(approve_completion_action, pattern='^approve_completion_'),
        ],
        states={
            VIEWING_TASKS: [
                CallbackQueryHandler(task_view, pattern='^view_task_'),
                CallbackQueryHandler(tasks_list, pattern='^tasks_list$'),
                CallbackQueryHandler(admin_tasks_pending, pattern='^admin_tasks_pending$'),
                CallbackQueryHandler(admin_task_view, pattern='^admin_view_task_'),
            ],
            COMPLETING_TASK: [
                CallbackQueryHandler(complete_task_action, pattern='^complete_task_'),
                CallbackQueryHandler(task_view, pattern='^view_task_'),
                CallbackQueryHandler(tasks_list, pattern='^tasks_list$'),
            ],
        },
        fallbacks=[CallbackQueryHandler(tasks_list, pattern='^tasks_list$')],
        per_message=False
    )

    create_task_conv_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(admin_create_task_start, pattern='^admin_create_task$'),
        ],
        states={
            CREATING_TASK_TITLE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, admin_create_task_title),
            ],
            CREATING_TASK_DESC: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, admin_create_task_desc),
            ],
            CREATING_TASK_REWARD_COINS: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, admin_create_task_reward_coins),
            ],
            CREATING_TASK_REWARD_EXP: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, admin_create_task_reward_exp),
            ],
            CREATING_TASK_DEADLINE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, admin_create_task_deadline),
            ],
        },
        fallbacks=[CallbackQueryHandler(tasks_list, pattern='^tasks_list$')],
        per_message=False
    )

    application.add_handler(tasks_conv_handler)
    application.add_handler(create_task_conv_handler)
