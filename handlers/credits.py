import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, MessageHandler, filters, CallbackQueryHandler
from config import *
from database import *
from states import *
from keyboards.main_menu import get_main_menu

logger = logging.getLogger(__name__)

async def credit_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
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

    active_credits = get_active_credits(user_id)
    pending_credits = db.select('credits', {'borrower_id': user_id, 'status': 'pending'})

    text = "🏦 **КРЕДИТНАЯ СИСТЕМА**\n\n"
    text += f"💰 Ваш баланс: {user['coins']} акойнов\n\n"
    text += "📊 **Информация:**\n"
    text += f"• Ставка кредита у клана: +{int((CLAN_CREDIT_RATE - 1) * 100)}%\n"
    text += f"• Минимальная сумма: {MIN_CREDIT_AMOUNT} акойнов\n"
    text += f"• Максимальная сумма: {MAX_CREDIT_AMOUNT} акойнов\n\n"

    if active_credits:
        text += "📋 **ВАШИ АКТИВНЫЕ КРЕДИТЫ:**\n"
        for credit in active_credits:
            remaining = credit['total_to_pay'] - credit.get('paid_amount', 0)
            text += f"• #{credit['id']}: {remaining} акойнов осталось\n"

    if pending_credits:
        text += f"\n⏳ У вас есть {len(pending_credits)} заявка(ок) на рассмотрении\n"

    keyboard = [
        [InlineKeyboardButton("📝 Запросить кредит", callback_data="request_credit")],
    ]

    if active_credits:
        keyboard.append([InlineKeyboardButton("💰 Погасить кредит", callback_data="pay_credit_start")])

    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back")])

    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def request_credit_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    user = get_user(user_id)
    if not user:
        await query.edit_message_text("❌ Вы не зарегистрированы!")
        return ConversationHandler.END

    await query.edit_message_text(
        f"🏦 **ЗАПРОС КРЕДИТА**\n\n"
        f"💰 Ваш баланс: {user['coins']} акойнов\n"
        f"💸 Ставка: +{int((CLAN_CREDIT_RATE - 1) * 100)}%\n\n"
        f"Введите сумму кредита (от {MIN_CREDIT_AMOUNT} до {MAX_CREDIT_AMOUNT} акойнов):",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Отмена", callback_data="credit_menu")]
        ])
    )

    return REQUESTING_CREDIT_AMOUNT

async def process_credit_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return REQUESTING_CREDIT_AMOUNT

    try:
        amount = int(update.message.text.strip())

        if amount < MIN_CREDIT_AMOUNT or amount > MAX_CREDIT_AMOUNT:
            await update.message.reply_text(f"❌ Сумма должна быть от {MIN_CREDIT_AMOUNT} до {MAX_CREDIT_AMOUNT} акойнов!")
            return REQUESTING_CREDIT_AMOUNT

        context.user_data['credit_amount'] = amount

        await update.message.reply_text(
            f"📝 **Сумма кредита: {amount} акойнов**\n"
            f"💰 К возврату: {int(amount * CLAN_CREDIT_RATE)} акойнов\n\n"
            f"Введите причину для кредита:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Отмена", callback_data="credit_menu")]
            ])
        )

        return REQUESTING_CREDIT_REASON
    except ValueError:
        await update.message.reply_text("❌ Введите число!")
        return REQUESTING_CREDIT_AMOUNT

async def process_credit_reason(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return REQUESTING_CREDIT_REASON

    reason = update.message.text.strip()
    amount = context.user_data.get('credit_amount')
    user_id = update.effective_user.id

    if not amount:
        await update.message.reply_text("❌ Ошибка: сумма не указана!")
        return REQUESTING_CREDIT_AMOUNT

    success, message, credit_id = create_credit_request(user_id, amount, reason)

    if success:
        await update.message.reply_text(
            f"✅ **ЗАЯВКА НА КРЕДИТ ОТПРАВЛЕНА!**\n\n"
            f"🆔 ID заявки: #{credit_id}\n"
            f"💰 Сумма: {amount} акойнов\n"
            f"💸 К возврату: {int(amount * CLAN_CREDIT_RATE)} акойнов\n"
            f"📝 Причина: {reason}\n\n"
            f"⏳ Ожидайте одобрения администратора.",
            reply_markup=get_main_menu(user_id)
        )
        # Уведомляем администратора
        user = get_user(user_id)
        if user:
            try:
                await context.bot.send_message(
                    ADMIN_ID,
                    f"🏦 **НОВЫЙ ЗАПРОС НА КРЕДИТ**\n\n"
                    f"🆔 **ID заявки:** #{credit_id}\n"
                    f"👤 **Заемщик:** {user['nickname']}\n"
                    f"📱 **TG:** @{user.get('username', 'нет')}\n"
                    f"💰 **Сумма:** {amount} акойнов\n"
                    f"💸 **К возврату:** {int(amount * CLAN_CREDIT_RATE)} акойнов\n"
                    f"📝 **Причина:** {reason}\n\n"
                    f"🔗 **Ссылка на заемщика:** tg://user?id={user_id}",
                    reply_markup=InlineKeyboardMarkup([
                        [
                            InlineKeyboardButton("✅ Одобрить", callback_data=f"admin_approve_credit_{credit_id}"),
                            InlineKeyboardButton("❌ Отклонить", callback_data=f"admin_reject_credit_{credit_id}")
                        ],
                        [InlineKeyboardButton("🏦 Все кредиты", callback_data="pending_credits")]
                    ])
                )
            except Exception as e:
                logger.error(f"Ошибка уведомления админа: {e}")
    else:
        await update.message.reply_text(
            f"❌ {message}",
            reply_markup=get_main_menu(user_id)
        )

    context.user_data.clear()
    return ConversationHandler.END

async def pending_credits_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.from_user.id != ADMIN_ID:
        await query.edit_message_text("⛔ Нет доступа!")
        return

    pending_credits = get_pending_credits()

    if not pending_credits:
        await query.edit_message_text(
            "📭 **Нет заявок на кредит**",
            reply_markup=get_main_menu(ADMIN_ID)
        )
        return

    text = "🏦 **ЗАЯВКИ НА КРЕДИТ**\n\n"

    keyboard = []

    for credit in pending_credits[:5]:
        user = get_user(credit['borrower_id'])
        user_name = user['nickname'] if user else f"ID: {credit['borrower_id']}"

        text += f"🆔 **#{credit['id']}**\n"
        text += f"👤 {user_name}\n"
        text += f"💰 {credit['amount']} акойнов (+{int((CLAN_CREDIT_RATE - 1) * 100)}%)\n"
        text += f"📝 {credit['reason'][:30]}...\n\n"

        keyboard.append([
            InlineKeyboardButton(f"👁️ #{credit['id']} - {user_name}", callback_data=f"admin_view_credit_{credit['id']}")
        ])

    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="admin_panel")])
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def admin_view_credit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.from_user.id != ADMIN_ID:
        await query.edit_message_text("⛔ Нет доступа!")
        return

    if not query.data.startswith("admin_view_credit_"):
        return

    credit_id = int(query.data.replace("admin_view_credit_", ""))
    credit = get_credit(credit_id)
    if not credit:
        await query.edit_message_text("❌ Кредит не найден!")
        return

    user = get_user(credit['borrower_id'])

    text = f"🏦 **КРЕДИТ #{credit_id}**\n\n"
    if user:
        text += f"👤 **Заемщик:** {user['nickname']}\n"
        text += f"📱 **TG:** @{user.get('username', 'нет')}\n"
    else:
        text += f"👤 **Заемщик:** Неизвестно (ID: {credit['borrower_id']})\n"
    text += f"💰 **Сумма:** {credit['amount']} акойнов\n"
    text += f"💸 **К возврату:** {credit['total_to_pay']} акойнов\n"
    text += f"📅 **Дата:** {credit.get('created_at', 'N/A')[:10]}\n"
    text += f"📝 **Причина:** {credit['reason']}\n"

    keyboard = [
        [
            InlineKeyboardButton("✅ Одобрить", callback_data=f"admin_approve_credit_{credit_id}"),
            InlineKeyboardButton("❌ Отклонить", callback_data=f"admin_reject_credit_{credit_id}")
        ],
        [InlineKeyboardButton("🔙 Назад", callback_data="pending_credits")]
    ]

    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def admin_approve_credit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.from_user.id != ADMIN_ID:
        await query.edit_message_text("⛔ Нет доступа!")
        return

    if not query.data.startswith("admin_approve_credit_"):
        return

    credit_id = int(query.data.replace("admin_approve_credit_", ""))

    success, message = approve_credit(credit_id)

    if success:
        credit = get_credit(credit_id)
        user = get_user(credit['borrower_id'])

        await query.edit_message_text(
            f"✅ **КРЕДИТ ОДОБРЕН!**\n\n"
            f"🏦 Кредит #{credit_id}\n"
            f"👤 Заемщик: {user['nickname'] if user else 'Неизвестно'}\n"
            f"💰 Выдано: {credit['amount']} акойнов\n"
            f"💸 К возврату: {credit['total_to_pay']} акойнов\n"
            f"✅ Уведомление отправлено заемщику.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 К кредитам", callback_data="pending_credits")]
            ])
        )
        # Уведомляем заемщика
        if user:
            try:
                await context.bot.send_message(
                    credit['borrower_id'],
                    f"✅ **ВАШ КРЕДИТ ОДОБРЕН!**\n\n"
                    f"💰 **Сумма:** {credit['amount']} акойнов\n"
                    f"💸 **К возврату:** {credit['total_to_pay']} акойнов\n"
                    f"📝 **Причина:** {credit['reason']}\n\n"
                    f"💡 Для погашения перейдите в раздел 'Кредит' в боте.",
                    reply_markup=get_main_menu(credit['borrower_id'])
                )
            except Exception as e:
                logger.error(f"Ошибка уведомления заемщика: {e}")
    else:
        await query.edit_message_text(
            f"❌ {message}",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 К кредитам", callback_data="pending_credits")]
            ])
        )

async def admin_reject_credit_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.from_user.id != ADMIN_ID:
        await query.edit_message_text("⛔ Нет доступа!")
        return

    if not query.data.startswith("admin_reject_credit_"):
        return

    credit_id = int(query.data.replace("admin_reject_credit_", ""))
    context.user_data['rejecting_credit'] = credit_id

    await query.edit_message_text(
        f"❌ **ОТКЛОНЕНИЕ КРЕДИТА**\n\n"
        f"Введите причину отклонения:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Отмена", callback_data=f"admin_view_credit_{credit_id}")]
        ])
    )

    return ConversationHandler.END

async def process_credit_rejection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # ИСПРАВЛЕНИЕ: Проверяем, что это администратор
    if update.effective_user.id != ADMIN_ID:
        return ConversationHandler.END

    if not update.message:
        return

    reason = update.message.text.strip()
    credit_id = context.user_data.get('rejecting_credit')

    if not credit_id:
        await update.message.reply_text("❌ Ошибка!")
        return

    credit = get_credit(credit_id)
    if not credit:
        await update.message.reply_text("❌ Кредит не найден!")
        return

    if reject_credit(credit_id, reason):
        await update.message.reply_text(
            f"✅ **КРЕДИТ ОТКЛОНЕН!**\n"
            f"📝 Причина отправлена заемщику.",
            reply_markup=get_main_menu(ADMIN_ID)
        )

        # Уведомляем заемщика
        user = get_user(credit['borrower_id'])
        if user:
            try:
                await context.bot.send_message(
                    credit['borrower_id'],
                    f"❌ **ВАШ КРЕДИТ ОТКЛОНЕН**\n\n"
                    f"💰 **Сумма:** {credit['amount']} акойнов\n"
                    f"📝 **Причина отказа:** {reason}\n\n"
                    f"Вы можете подать новую заявку на кредит.",
                    reply_markup=get_main_menu(credit['borrower_id'])
                )
            except Exception as e:
                logger.error(f"Ошибка уведомления заемщика: {e}")
    else:
        await update.message.reply_text(
            "❌ Ошибка при отклонении кредита!",
            reply_markup=get_main_menu(ADMIN_ID)
        )

    context.user_data.clear()

async def pay_credit_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    active_credits = get_active_credits(user_id)

    if not active_credits:
        await query.edit_message_text("❌ У вас нет активных кредитов!")
        return

    text = "💰 **ПОГАШЕНИЕ КРЕДИТА**\n\n"
    text += "Выберите кредит для погашения:\n\n"

    keyboard = []
    for credit in active_credits:
        remaining = credit['total_to_pay'] - credit.get('paid_amount', 0)
        text += f"🆔 **#{credit['id']}**\n"
        text += f"   💰 Осталось: {remaining} акойнов\n\n"
        keyboard.append([
            InlineKeyboardButton(f"💳 #{credit['id']} - {remaining} акойнов", callback_data=f"pay_credit_{credit['id']}")
        ])

    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="credit_menu")])

    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def pay_credit_select(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if not query.data.startswith("pay_credit_"):
        return

    credit_id = int(query.data.replace("pay_credit_", ""))
    credit = get_credit(credit_id)

    if not credit:
        await query.edit_message_text("❌ Кредит не найден!")
        return

    remaining = credit['total_to_pay'] - credit.get('paid_amount', 0)
    user = get_user(credit['borrower_id'])

    context.user_data['paying_credit'] = credit_id

    await query.edit_message_text(
        f"💳 **ПОГАШЕНИЕ КРЕДИТА #{credit_id}**\n\n"
        f"💰 Остаток долга: {remaining} акойнов\n"
        f"👤 Заемщик: {user['nickname']}\n"
        f"💸 Ваш баланс: {user['coins']} акойнов\n\n"
        f"Введите сумму для погашения:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Отмена", callback_data="credit_menu")]
        ])
    )

    return PAY_CREDIT_AMOUNT

async def process_pay_credit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # ИСПРАВЛЕНИЕ: Проверяем, что это не администратор (этот обработчик только для обычных пользователей)
    # Но на всякий случай проверим, что это тот пользователь, который должен погашать кредит
    user_id = update.effective_user.id
    credit_id = context.user_data.get('paying_credit')
    
    if credit_id:
        credit = get_credit(credit_id)
        if credit and credit['borrower_id'] != user_id:
            # Если это не заемщик, выходим
            return ConversationHandler.END

    if not update.message:
        return PAY_CREDIT_AMOUNT

    try:
        amount = int(update.message.text.strip())
        credit_id = context.user_data.get('paying_credit')

        if not credit_id:
            await update.message.reply_text("❌ Ошибка!")
            return ConversationHandler.END

        if amount <= 0:
            await update.message.reply_text("❌ Сумма должна быть больше 0!")
            return PAY_CREDIT_AMOUNT

        success, message = pay_credit(credit_id, amount)

        if success:
            await update.message.reply_text(
                f"✅ {message}",
                reply_markup=get_main_menu(update.effective_user.id)
            )
        else:
            await update.message.reply_text(
                f"❌ {message}",
                reply_markup=get_main_menu(update.effective_user.id)
            )

    except ValueError:
        await update.message.reply_text("❌ Введите число!")
        return PAY_CREDIT_AMOUNT

    context.user_data.clear()
    return ConversationHandler.END

def setup_credit_handlers(application):
    """Настройка обработчиков кредитов"""
    credit_conv_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(request_credit_start, pattern='^request_credit$'),
            CallbackQueryHandler(pay_credit_start, pattern='^pay_credit_start$'),
            CallbackQueryHandler(pay_credit_select, pattern='^pay_credit_'),
        ],
        states={
            REQUESTING_CREDIT_AMOUNT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, process_credit_amount),
            ],
            REQUESTING_CREDIT_REASON: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, process_credit_reason),
            ],
            PAY_CREDIT_AMOUNT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, process_pay_credit),
            ],
        },
        fallbacks=[CallbackQueryHandler(credit_menu, pattern='^credit_menu$')],
        per_message=False
    )

    application.add_handler(CallbackQueryHandler(credit_menu, pattern='^credit_menu$'))
    application.add_handler(CallbackQueryHandler(pending_credits_list, pattern='^pending_credits$'))
    application.add_handler(CallbackQueryHandler(admin_view_credit, pattern='^admin_view_credit_'))
    application.add_handler(CallbackQueryHandler(admin_approve_credit, pattern='^admin_approve_credit_'))
    application.add_handler(CallbackQueryHandler(admin_reject_credit_start, pattern='^admin_reject_credit_'))
    application.add_handler(credit_conv_handler)
