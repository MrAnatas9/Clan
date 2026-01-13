import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, MessageHandler, filters, CallbackQueryHandler
from config import *
from database import *
from states import *
from keyboards.main_menu import get_main_menu
from datetime import datetime

logger = logging.getLogger(__name__)

async def suggestions_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.from_user.id != ADMIN_ID:
        # Для обычных пользователей - отправка предложения
        user_id = query.from_user.id
        user = get_user(user_id)

        if not user:
            await query.edit_message_text(
                "❌ Вы не зарегистрированы!",
                reply_markup=get_main_menu(user_id)
            )
            return

        await query.edit_message_text(
            "💡 **СИСТЕМА ПРЕДЛОЖЕНИЙ**\n\n"
            "Отправьте ваше предложение по улучшению клана:\n"
            "• Новые функции\n"
            "• Изменения в правилах\n"
            "• Улучшения бота\n"
            "• Идеи для событий\n\n"
            "📝 **Пример:** Предлагаю добавить систему рангов для активных участников.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📝 Отправить предложение", callback_data="send_suggestion_start")],
                [InlineKeyboardButton("🔙 Назад", callback_data="back")]
            ])
        )
        return

    # Для администратора - список предложений
    pending_suggestions = get_pending_suggestions()
    if not pending_suggestions:
        await query.edit_message_text(
            "📭 **Нет предложений на рассмотрение**",
            reply_markup=get_main_menu(ADMIN_ID)
        )
        return

    text = "💡 **ПРЕДЛОЖЕНИЯ НА РАССМОТРЕНИЕ**\n\n"
    keyboard = []

    for suggestion in pending_suggestions[:5]:
        user = get_user(suggestion['user_id'])
        user_name = user['nickname'] if user else f"ID: {suggestion['user_id']}"

        text += f"🆔 **#{suggestion['id']}**\n"
        text += f"👤 {user_name}\n"
        text += f"💡 {suggestion['suggestion'][:50]}...\n\n"
        keyboard.append([
            InlineKeyboardButton(f"👁️ #{suggestion['id']} - {user_name}", callback_data=f"admin_view_suggestion_{suggestion['id']}")
        ])

    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="admin_panel")])

    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def send_suggestion_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    await query.edit_message_text(
        "💡 **ОТПРАВКА ПРЕДЛОЖЕНИЯ**\n\n"
        "Напишите ваше предложение по улучшению клана:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Отмена", callback_data="suggestions_list")]
        ])
    )

    return SUGGESTION_TEXT

async def process_suggestion(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return SUGGESTION_TEXT

    suggestion_text = update.message.text.strip()
    if len(suggestion_text) < 10:
        await update.message.reply_text("❌ Предложение должно быть не менее 10 символов!")
        return SUGGESTION_TEXT

    user_id = update.effective_user.id
    suggestion_id = create_suggestion(user_id, suggestion_text)

    if suggestion_id:
        await update.message.reply_text(
            f"✅ **ПРЕДЛОЖЕНИЕ ОТПРАВЛЕНО!**\n\n"
            f"🆔 ID предложения: #{suggestion_id}\n"
            f"💡 Ваше предложение отправлено администратору на рассмотрение.\n\n"
            f"Спасибо за участие в развитии клана!",
            reply_markup=get_main_menu(user_id)
        )

        # Уведомляем администратора
        user = get_user(user_id)
        if user:
            try:
                await context.bot.send_message(
                    ADMIN_ID,
                    f"💡 **НОВОЕ ПРЕДЛОЖЕНИЕ**\n\n"
                    f"🆔 **ID предложения:** #{suggestion_id}\n"
                    f"👤 **Автор:** {user['nickname']}\n"
                    f"📱 **TG:** @{user.get('username', 'нет')}\n"
                    f"🆔 **User ID:** {user_id}\n\n"
                    f"💡 **Предложение:**\n{suggestion_text}\n\n"
                    f"🔗 **Ссылка на автора:** tg://user?id={user_id}",
                    reply_markup=InlineKeyboardMarkup([
                        [
                            InlineKeyboardButton("✅ Одобрить", callback_data=f"admin_approve_suggestion_{suggestion_id}"),
                            InlineKeyboardButton("❌ Отклонить", callback_data=f"admin_reject_suggestion_{suggestion_id}")
                        ],
                        [InlineKeyboardButton("💡 Все предложения", callback_data="suggestions_list")]
                    ])
                )
            except Exception as e:
                logger.error(f"Ошибка уведомления админа: {e}")
    else:
        await update.message.reply_text(
            "❌ Ошибка при отправке предложения!",
            reply_markup=get_main_menu(user_id)
        )

    return ConversationHandler.END

async def admin_view_suggestion(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.from_user.id != ADMIN_ID:
        await query.edit_message_text("⛔ Нет доступа!")
        return

    if not query.data.startswith("admin_view_suggestion_"):
        return

    suggestion_id = int(query.data.replace("admin_view_suggestion_", ""))
    suggestions = db.select('suggestions', {'id': suggestion_id}, limit=1)

    if not suggestions:
        await query.edit_message_text("❌ Предложение не найдено!")
        return

    suggestion = suggestions[0]
    user = get_user(suggestion['user_id'])

    text = f"💡 **ПРЕДЛОЖЕНИЕ #{suggestion_id}**\n\n"
    if user:
        text += f"👤 **Автор:** {user['nickname']}\n"
        text += f"📱 **TG:** @{user.get('username', 'нет')}\n"
    else:
        text += f"👤 **Автор:** Неизвестно (ID: {suggestion['user_id']})\n"
    text += f"📅 **Дата:** {suggestion.get('created_at', 'N/A')[:10]}\n"
    text += f"📊 **Статус:** {suggestion.get('status', 'pending')}\n\n"
    text += f"💡 **Предложение:**\n{suggestion['suggestion']}\n"

    keyboard = [
        [
            InlineKeyboardButton("✅ Одобрить", callback_data=f"admin_approve_suggestion_{suggestion_id}"),
            InlineKeyboardButton("❌ Отклонить", callback_data=f"admin_reject_suggestion_{suggestion_id}")
        ],
        [InlineKeyboardButton("🔙 Назад", callback_data="suggestions_list")]
    ]

    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def admin_approve_suggestion(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.from_user.id != ADMIN_ID:
        await query.edit_message_text("⛔ Нет доступа!")
        return

    if not query.data.startswith("admin_approve_suggestion_"):
        return

    suggestion_id = int(query.data.replace("admin_approve_suggestion_", ""))

    if approve_suggestion(suggestion_id):
        suggestion = db.select('suggestions', {'id': suggestion_id}, limit=1)
        if suggestion:
            suggestion = suggestion[0]
            user = get_user(suggestion['user_id'])

            await query.edit_message_text(
                f"✅ **ПРЕДЛОЖЕНИЕ ОДОБРЕНО!**\n\n"
                f"💡 Предложение #{suggestion_id}\n"
                f"👤 Автор: {user['nickname'] if user else 'Неизвестно'}\n"
                f"✅ Уведомление отправлено автору.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 К предложениям", callback_data="suggestions_list")]
                ])
            )

            # Уведомляем автора
            if user:
                try:
                    await context.bot.send_message(
                        suggestion['user_id'],
                        f"✅ **ВАШЕ ПРЕДЛОЖЕНИЕ ОДОБРЕНО!**\n\n"
                        f"💡 **Предложение:**\n{suggestion['suggestion'][:200]}...\n\n"
                        f"Спасибо за ваше предложение! Администрация рассмотрит его реализацию.",
                        reply_markup=get_main_menu(suggestion['user_id'])
                    )
                except Exception as e:
                    logger.error(f"Ошибка уведомления автора: {e}")
    else:
        await query.edit_message_text(
            f"❌ Ошибка при одобрении предложения!",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 К предложениям", callback_data="suggestions_list")]
            ])
        )

async def admin_reject_suggestion_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.from_user.id != ADMIN_ID:
        await query.edit_message_text("⛔ Нет доступа!")
        return

    if not query.data.startswith("admin_reject_suggestion_"):
        return

    suggestion_id = int(query.data.replace("admin_reject_suggestion_", ""))
    context.user_data['rejecting_suggestion'] = suggestion_id

    await query.edit_message_text(
        f"❌ **ОТКЛОНЕНИЕ ПРЕДЛОЖЕНИЯ**\n\n"
        f"Введите причину отклонения:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Отмена", callback_data=f"admin_view_suggestion_{suggestion_id}")]
        ])
    )

    return ConversationHandler.END

async def process_suggestion_rejection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # ИСПРАВЛЕНИЕ: Проверяем, что это администратор
    if update.effective_user.id != ADMIN_ID:
        return ConversationHandler.END

    if not update.message:
        return

    reason = update.message.text.strip()
    suggestion_id = context.user_data.get('rejecting_suggestion')

    if not suggestion_id:
        await update.message.reply_text("❌ Ошибка!")
        return

    suggestion = db.select('suggestions', {'id': suggestion_id}, limit=1)
    if not suggestion:
        await update.message.reply_text("❌ Предложение не найдено!")
        return

    suggestion = suggestion[0]

    if reject_suggestion(suggestion_id, reason):
        await update.message.reply_text(
            f"✅ **ПРЕДЛОЖЕНИЕ ОТКЛОНЕНО!**\n"
            f"📝 Причина отправлена автору.",
            reply_markup=get_main_menu(ADMIN_ID)
        )

        # Уведомляем автора
        user = get_user(suggestion['user_id'])
        if user:
            try:
                await context.bot.send_message(
                    suggestion['user_id'],
                    f"❌ **ВАШЕ ПРЕДЛОЖЕНИЕ ОТКЛОНЕНО**\n\n"
                    f"💡 **Предложение:**\n{suggestion['suggestion'][:200]}...\n"
                    f"📝 **Причина отказа:** {reason}\n\n"
                    f"Вы можете предложить другую идею с учетом замечаний.",
                    reply_markup=get_main_menu(suggestion['user_id'])
                )
            except Exception as e:
                logger.error(f"Ошибка уведомления автора: {e}")
    else:
        await update.message.reply_text(
            "❌ Ошибка при отклонении предложения!",
            reply_markup=get_main_menu(ADMIN_ID)
        )

    context.user_data.clear()

def setup_suggestion_handlers(application):
    """Настройка обработчиков предложений"""
    application.add_handler(CallbackQueryHandler(suggestions_list, pattern='^suggestions_list$'))
    application.add_handler(CallbackQueryHandler(send_suggestion_start, pattern='^send_suggestion_start$'))
    application.add_handler(CallbackQueryHandler(admin_view_suggestion, pattern='^admin_view_suggestion_'))
    application.add_handler(CallbackQueryHandler(admin_approve_suggestion, pattern='^admin_approve_suggestion_'))
    application.add_handler(CallbackQueryHandler(admin_reject_suggestion_start, pattern='^admin_reject_suggestion_'))

    suggestion_conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(send_suggestion_start, pattern='^send_suggestion_start$')],
        states={
            SUGGESTION_TEXT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, process_suggestion),
            ],
        },
        fallbacks=[CallbackQueryHandler(suggestions_list, pattern='^suggestions_list$')],
        per_message=False
    )

    application.add_handler(suggestion_conv_handler)
