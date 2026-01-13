import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, MessageHandler, filters, CallbackQueryHandler
from config import *
from database import *
from states import *
from keyboards.main_menu import get_main_menu
from datetime import datetime

logger = logging.getLogger(__name__)

async def vacations_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.from_user.id != ADMIN_ID:
        # Для обычных пользователей - подача заявления
        user_id = query.from_user.id
        user = get_user(user_id)
        if not user:
            await query.edit_message_text(
                "❌ Вы не зарегистрированы!",
                reply_markup=get_main_menu(user_id)
            )
            return

        pending_vacations = get_pending_vacations()
        user_vacations = [v for v in pending_vacations if v['user_id'] == user_id]

        text = "🏖️ **СИСТЕМА ОТПУСКОВ**\n\n"

        if user_vacations:
            vacation = user_vacations[0]
            text += f"⏳ **У вас есть активное заявление:**\n"
            text += f"📅 Дней: {vacation['days']}\n"
            text += f"📝 Причина: {vacation['reason']}\n"
            text += f"📅 Подано: {vacation['requested_at'][:10]}\n"
            text += f"📊 Статус: На рассмотрении\n\n"
        else:
            text += "📋 **Подача заявления на отпуск:**\n"
            text += "1. Укажите количество дней\n"
            text += "2. Укажите причину отпуска\n"
            text += "3. Ожидайте решения администратора\n\n"
            text += "💡 **Пример:** отпуск заявление 7 семейные обстоятельства"

        keyboard = []
        if not user_vacations:
            keyboard.append([InlineKeyboardButton("📝 Подать заявление", callback_data="vacation_request_start")])
        keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back")])

        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        return

    # Для администратора - список заявлений
    pending_vacations = get_pending_vacations()
    if not pending_vacations:
        await query.edit_message_text(
            "📭 **Нет заявлений на отпуск**",
            reply_markup=get_main_menu(ADMIN_ID)
        )
        return

    text = "🏖️ **ЗАЯВЛЕНИЯ НА ОТПУСК**\n\n"
    keyboard = []

    for vacation in pending_vacations[:5]:
        user = get_user(vacation['user_id'])
        user_name = user['nickname'] if user else f"ID: {vacation['user_id']}"

        text += f"🆔 **#{vacation['id']}**\n"
        text += f"👤 {user_name}\n"
        text += f"📅 {vacation['days']} дней\n"
        text += f"📝 {vacation['reason'][:50]}...\n\n"

        keyboard.append([
            InlineKeyboardButton(f"👁️ #{vacation['id']} - {user_name}", callback_data=f"admin_view_vacation_{vacation['id']}")
        ])

    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="admin_panel")])

    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def vacation_request_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    await query.edit_message_text(
        "📝 **ПОДАЧА ЗАЯВЛЕНИЯ НА ОТПУСК**\n\n"
        "Введите количество дней отпуска (от 1 до 30):",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Отмена", callback_data="vacations_list")]
        ])
    )

    return VACATION_DAYS

async def process_vacation_days(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return VACATION_DAYS

    try:
        days = int(update.message.text.strip())
        if days < 1 or days > 30:
            await update.message.reply_text("❌ Количество дней должно быть от 1 до 30!")
            return VACATION_DAYS

        context.user_data['vacation_days'] = days

        await update.message.reply_text(
            "📝 **ПРИЧИНА ОТПУСКА**\n\n"
            "Опишите причину отпуска:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Назад", callback_data="vacation_request_start")]
            ])
        )

        return VACATION_REASON
    except ValueError:
        await update.message.reply_text("❌ Введите число!")
        return VACATION_DAYS

async def process_vacation_reason(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return VACATION_REASON

    reason = update.message.text.strip()
    if len(reason) < 5:
        await update.message.reply_text("❌ Причина должна быть не менее 5 символов!")
        return VACATION_REASON

    user_id = update.effective_user.id
    days = context.user_data['vacation_days']

    vacation_id = request_vacation(user_id, days, reason)

    if vacation_id:
        await update.message.reply_text(
            f"✅ **ЗАЯВЛЕНИЕ ПОДАНО!**\n\n"
            f"🆔 ID заявления: #{vacation_id}\n"
            f"📅 Дней: {days}\n"
            f"📝 Причина: {reason}\n\n"
            f"⏳ Ожидайте решения администратора.",
            reply_markup=get_main_menu(user_id)
        )
        # Уведомляем администратора
        user = get_user(user_id)
        try:
            await context.bot.send_message(
                ADMIN_ID,
                f"🏖️ **НОВОЕ ЗАЯВЛЕНИЕ НА ОТПУСК**\n\n"
                f"🆔 **ID заявления:** #{vacation_id}\n"
                f"👤 **Сотрудник:** {user['nickname']}\n"
                f"📱 **TG:** @{user.get('username', 'нет')}\n"
                f"🆔 **User ID:** {user_id}\n"
                f"📅 **Дней:** {days}\n"
                f"📝 **Причина:** {reason}\n\n"
                f"🔗 **Ссылка на сотрудника:** tg://user?id={user_id}",
                reply_markup=InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton("✅ Одобрить", callback_data=f"admin_approve_vacation_{vacation_id}"),
                        InlineKeyboardButton("❌ Отклонить", callback_data=f"admin_reject_vacation_{vacation_id}")
                    ],
                    [InlineKeyboardButton("🏖️ Все заявления", callback_data="vacations_list")]
                ])
            )
        except Exception as e:
            logger.error(f"Ошибка уведомления админа: {e}")
    else:
        await update.message.reply_text(
            "❌ Ошибка при подаче заявления!",
            reply_markup=get_main_menu(user_id)
        )

    context.user_data.clear()
    return ConversationHandler.END

async def admin_view_vacation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.from_user.id != ADMIN_ID:
        await query.edit_message_text("⛔ Нет доступа!")
        return

    if not query.data.startswith("admin_view_vacation_"):
        return

    vacation_id = int(query.data.replace("admin_view_vacation_", ""))
    vacation = get_vacation(vacation_id)

    if not vacation:
        await query.edit_message_text("❌ Заявление не найдено!")
        return

    user = get_user(vacation['user_id'])

    text = f"🏖️ **ЗАЯВЛЕНИЕ НА ОТПУСК #{vacation_id}**\n\n"
    text += f"👤 **Сотрудник:** {user['nickname'] if user else 'Неизвестно'}\n"
    text += f"📱 **TG:** @{user.get('username', 'нет') if user else 'нет'}\n"
    text += f"📅 **Дней:** {vacation['days']}\n"
    text += f"📝 **Причина:** {vacation['reason']}\n"
    text += f"📅 **Подано:** {vacation['requested_at'][:10]}\n"
    text += f"📊 **Статус:** {vacation['status']}\n"

    keyboard = [
        [
            InlineKeyboardButton("✅ Одобрить", callback_data=f"admin_approve_vacation_{vacation_id}"),
            InlineKeyboardButton("❌ Отклонить", callback_data=f"admin_reject_vacation_{vacation_id}")
        ],
        [InlineKeyboardButton("🔙 Назад", callback_data="vacations_list")]
    ]

    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def admin_approve_vacation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.from_user.id != ADMIN_ID:
        await query.edit_message_text("⛔ Нет доступа!")
        return

    if not query.data.startswith("admin_approve_vacation_"):
        return

    vacation_id = int(query.data.replace("admin_approve_vacation_", ""))
    if approve_vacation(vacation_id):
        vacation = get_vacation(vacation_id)
        user = get_user(vacation['user_id'])

        await query.edit_message_text(
            f"✅ **ОТПУСК ОДОБРЕН!**\n\n"
            f"👤 Сотрудник: {user['nickname']}\n"
            f"📅 Дней: {vacation['days']}\n"
            f"📝 Причина: {vacation['reason']}\n"
            f"✅ Уведомление отправлено сотруднику.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 К заявлениям", callback_data="vacations_list")]
            ])
        )

        # Уведомляем сотрудника
        try:
            await context.bot.send_message(
                vacation['user_id'],
                f"✅ **ВАШ ОТПУСК ОДОБРЕН!**\n\n"
                f"📅 **Дней:** {vacation['days']}\n"
                f"📝 **Причина:** {vacation['reason']}\n"
                f"📅 **Дата одобрения:** {datetime.now().strftime('%d.%m.%Y')}\n\n"
                f"Хорошего отдыха! 🏖️",
                reply_markup=get_main_menu(vacation['user_id'])
            )
        except Exception as e:
            logger.error(f"Ошибка уведомления сотрудника: {e}")
    else:
        await query.edit_message_text(
            f"❌ Ошибка при одобрении отпуска!",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 К заявлениям", callback_data="vacations_list")]
            ])
        )

async def admin_reject_vacation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.from_user.id != ADMIN_ID:
        await query.edit_message_text("⛔ Нет доступа!")
        return

    if not query.data.startswith("admin_reject_vacation_"):
        return

    vacation_id = int(query.data.replace("admin_reject_vacation_", ""))
    context.user_data['rejecting_vacation'] = vacation_id

    await query.edit_message_text(
        f"❌ **ОТКЛОНЕНИЕ ОТПУСКА**\n\n"
        f"Введите причину отклонения:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Отмена", callback_data=f"admin_view_vacation_{vacation_id}")]
        ])
    )

async def process_vacation_rejection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # ИСПРАВЛЕНИЕ: Проверяем, что это администратор
    if update.effective_user.id != ADMIN_ID:
        return ConversationHandler.END

    if not update.message:
        return

    reason = update.message.text.strip()
    vacation_id = context.user_data.get('rejecting_vacation')

    if not vacation_id:
        await update.message.reply_text("❌ Ошибка!")
        return

    vacation = get_vacation(vacation_id)

    if reject_vacation(vacation_id, reason):
        await update.message.reply_text(
            f"✅ **ОТПУСК ОТКЛОНЕН!**\n"
            f"📝 Причина отправлена сотруднику.",
            reply_markup=get_main_menu(ADMIN_ID)
        )

        # Уведомляем сотрудника
        try:
            await context.bot.send_message(
                vacation['user_id'],
                f"❌ **ВАШ ОТПУСК ОТКЛОНЕН**\n\n"
                f"📅 **Дней:** {vacation['days']}\n"
                f"📝 **Причина запроса:** {vacation['reason']}\n"
                f"📝 **Причина отказа:** {reason}\n\n"
                f"Вы можете подать новое заявление, исправив указанные недочеты.",
                reply_markup=get_main_menu(vacation['user_id'])
            )
        except Exception as e:
            logger.error(f"Ошибка уведомления сотрудника: {e}")
    else:
        await update.message.reply_text(
            "❌ Ошибка при отклонении отпуска!",
            reply_markup=get_main_menu(ADMIN_ID)
        )

    context.user_data.clear()

def setup_vacation_handlers(application):
    """Настройка обработчиков отпусков"""
    vacation_conv_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(vacation_request_start, pattern='^vacation_request_start$'),
            CallbackQueryHandler(vacations_list, pattern='^vacations_list$'),
            CallbackQueryHandler(admin_view_vacation, pattern='^admin_view_vacation_'),
            CallbackQueryHandler(admin_approve_vacation, pattern='^admin_approve_vacation_'),
            CallbackQueryHandler(admin_reject_vacation, pattern='^admin_reject_vacation_'),
        ],
        states={
            VACATION_DAYS: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, process_vacation_days),
            ],
            VACATION_REASON: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, process_vacation_reason),
            ],
        },
        fallbacks=[CallbackQueryHandler(vacations_list, pattern='^vacations_list$')],
        per_message=False
    )

    application.add_handler(vacation_conv_handler)
