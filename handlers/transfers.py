import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, MessageHandler, filters, CallbackQueryHandler
from config import *
from database import *
from states import *
from keyboards.main_menu import get_main_menu
from utils.helpers import get_user_by_username

logger = logging.getLogger(__name__)

async def transfer_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
    
    await query.edit_message_text(
        "💸 **ПЕРЕВОД АКОЙНОВ**\n\n"
        f"💰 Ваш баланс: {user['coins']} акойнов\n"
        "📊 Комиссия за перевод: 5%\n\n"
        "Выберите способ перевода:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔍 Поиск по username", callback_data="transfer_by_username")],
            [InlineKeyboardButton("📋 Список пользователей", callback_data="transfer_user_list")],
            [InlineKeyboardButton("🔙 Назад", callback_data="back")]
        ])
    )

async def transfer_by_username_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        "🔍 **ПЕРЕВОД ПО USERNAME**\n\n"
        "Введите username получателя (например, @username или просто username):\n"
        "Или введите часть ника для поиска:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Назад", callback_data="transfer_menu")]
        ])
    )
    
    return TRANSFER_USERNAME

async def transfer_process_username(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return TRANSFER_USERNAME
    
    search_term = update.message.text.strip().lstrip('@')
    
    if len(search_term) < 2:
        await update.message.reply_text("❌ Введите минимум 2 символа для поиска!")
        return TRANSFER_USERNAME
    
    # Ищем пользователей
    all_users = get_all_users()
    sender_id = update.effective_user.id
    
    results = []
    for user in all_users:
        if user['user_id'] == sender_id:
            continue
        
        if (search_term.lower() in user.get('username', '').lower() or 
            search_term.lower() in user.get('nickname', '').lower()):
            results.append(user)
    
    if not results:
        await update.message.reply_text(
            "❌ Пользователи не найдены!\nПопробуйте другой username или ник.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 Попробовать снова", callback_data="transfer_by_username")],
                [InlineKeyboardButton("🔙 Назад", callback_data="transfer_menu")]
            ])
        )
        return TRANSFER_USERNAME
    
    text = "🔍 **НАЙДЕННЫЕ ПОЛЬЗОВАТЕЛИ:**\n\n"
    keyboard = []
    
    for user in results[:10]:
        text += f"👤 **{user['nickname']}**\n"
        text += f"📱 @{user.get('username', 'нет')}\n"
        text += f"💼 {user['job']}\n\n"
        
        keyboard.append([
            InlineKeyboardButton(f"➡️ Перевести {user['nickname']}", 
                               callback_data=f"transfer_to_{user['user_id']}")
        ])
    
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="transfer_menu")])
    
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    return TRANSFER_AMOUNT

async def transfer_to_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data.startswith("transfer_to_"):
        target_id = int(query.data.replace("transfer_to_", ""))
    
    context.user_data['transfer_target_id'] = target_id
    target_user = get_user(target_id)
    sender_id = query.from_user.id
    sender = get_user(sender_id)
    
    if not target_user:
        await query.edit_message_text(
            "❌ Пользователь не найден!",
            reply_markup=get_main_menu(sender_id)
        )
        return ConversationHandler.END
    
    await query.edit_message_text(
        f"💸 **ПЕРЕВОД ПОЛЬЗОВАТЕЛЮ**\n\n"
        f"👤 **Получатель:** {target_user['nickname']}\n"
        f"📱 @{target_user.get('username', 'нет')}\n"
        f"💼 {target_user['job']}\n\n"
        f"💰 **Ваш баланс:** {sender['coins']} акойнов\n"
        f"💸 **Комиссия:** 5%\n\n"
        f"Введите сумму для перевода:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Назад", callback_data="transfer_by_username")]
        ])
    )
    
    return TRANSFER_AMOUNT

async def process_transfer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return TRANSFER_AMOUNT
    
    user_id = update.effective_user.id
    text = update.message.text.strip()
    
    try:
        amount = int(text)
        
        if amount <= 0:
            await update.message.reply_text("❌ Сумма должна быть положительной!")
            return TRANSFER_AMOUNT
        
        target_id = context.user_data.get('transfer_target_id')
        
        if not target_id:
            await update.message.reply_text("❌ Получатель не выбран!")
            return TRANSFER_AMOUNT
        
        success, message = transfer_coins(user_id, target_id, amount, "Перевод через бота")
        
        if success:
            await update.message.reply_text(
                f"{message}",
                reply_markup=get_main_menu(user_id)
            )
        else:
            await update.message.reply_text(
                f"❌ {message}",
                reply_markup=get_main_menu(user_id)
            )
        
        context.user_data.clear()
        return ConversationHandler.END
        
    except ValueError:
        await update.message.reply_text("❌ Введите корректную сумму (число)!")
        return TRANSFER_AMOUNT

def setup_transfer_handlers(application):
    """Настройка обработчиков переводов"""
    transfer_conv_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(transfer_by_username_start, pattern='^transfer_by_username$'),
            CallbackQueryHandler(transfer_to_user, pattern='^transfer_to_'),
        ],
        states={
            TRANSFER_USERNAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, transfer_process_username),
            ],
            TRANSFER_AMOUNT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, process_transfer),
                CallbackQueryHandler(transfer_by_username_start, pattern='^transfer_by_username$')
            ],
        },
        fallbacks=[CallbackQueryHandler(transfer_menu, pattern='^transfer_menu$')],
        per_message=False
    )
    
    application.add_handler(CallbackQueryHandler(transfer_menu, pattern='^transfer_menu$'))
    application.add_handler(transfer_conv_handler)
