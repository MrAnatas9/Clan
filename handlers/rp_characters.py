import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, MessageHandler, filters, CallbackQueryHandler
from config import *
from database import *
from states import *
from keyboards.main_menu import get_main_menu

logger = logging.getLogger(__name__)

async def rp_character_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    user = get_user(user_id)

    if not user:
        await query.edit_message_text("❌ Вы не зарегистрированы!", reply_markup=get_main_menu(user_id))
        return

    char = get_rp_character(user_id)
    if char:
        if char.get('status') == 'pending':
            status = "⏳ На рассмотрении"
            status_text = "Ваш персонаж ожидает одобрения администратором."
        elif char.get('status') == 'approved':
            status = "✅ Одобрен"
            status_text = f"Ваш персонаж одобрен. Цена: {char.get('price', 0)} акойнов"
        elif char.get('status') == 'rejected':
            status = "❌ Отклонен"
            status_text = f"Причина: {char.get('rejection_reason', 'не указана')}"
        else:
            status = "❓ Неизвестно"
            status_text = ""

        text = f"🎭 **ВАШ РП ПЕРСОНАЖ**\n\n"
        text += f"📛 **Имя:** {char['name']}\n"
        text += f"💪 **Способности:** {char['abilities'][:100]}...\n"
        text += f"💔 **Слабости:** {char['weaknesses'][:100]}...\n"
        text += f"🎒 **Инвентарь:** {char['items'][:100]}...\n"
        text += f"📖 **Биография:** {char['bio'][:100]}...\n\n"
        text += f"📊 **Статус:** {status}\n"
        text += status_text

        keyboard = []
        if char.get('status') == 'approved':
            keyboard.append([InlineKeyboardButton("💰 Продать персонажа", callback_data="sell_character_start")])
        keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back")])

        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await query.edit_message_text(
            "🎭 **СОЗДАНИЕ РП ПЕРСОНАЖА**\n\n"
            "Создайте своего уникального персонажа для ролевых игр!\n\n"
            "Персонаж будет проверен администратором и получит цену.\n"
            f"💰 Минимальная цена: {RP_CHARACTER_MIN_PRICE} акойнов\n"
            f"💰 Максимальная цена: {RP_CHARACTER_MAX_PRICE} акойнов\n\n"
            "После одобрения вы можете:\n"
            "• Продать персонажа другому игроку\n"
            "• Продать персонажа клану (30% от цены)",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("➕ Создать персонажа", callback_data="create_rp_character")],
                [InlineKeyboardButton("🔙 Назад", callback_data="back")]
            ])
        )

async def create_rp_character_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    user = get_user(user_id)

    if not user:
        await query.edit_message_text("❌ Вы не зарегистрированы!")
        return ConversationHandler.END

    char = get_rp_character(user_id)
    if char:
        status = char.get('status', '')
        if status == 'pending':
            await query.edit_message_text("⏳ У вас уже есть персонаж на рассмотрении!")
            return ConversationHandler.END
        elif status == 'approved':
            await query.edit_message_text("✅ У вас уже есть одобренный персонаж!")
            return ConversationHandler.END

    await query.edit_message_text(
        "🎭 **СОЗДАНИЕ РП ПЕРСОНАЖА**\n\n"
        "📛 **Шаг 1 из 5:** Введите имя персонажа:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Отмена", callback_data="rp_character_menu")]
        ])
    )

    return RP_CHARACTER_NAME

async def process_rp_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return RP_CHARACTER_NAME

    name = update.message.text.strip()
    if len(name) < 2:
        await update.message.reply_text("❌ Имя должно быть не менее 2 символов!")
        return RP_CHARACTER_NAME

    context.user_data['rp_name'] = name
    await update.message.reply_text(
        "💪 **Шаг 2 из 5:** Опишите способности персонажа:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Отмена", callback_data="rp_character_menu")]
        ])
    )

    return RP_CHARACTER_ABILITIES

async def process_rp_abilities(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return RP_CHARACTER_ABILITIES

    abilities = update.message.text.strip()
    if len(abilities) < 10:
        await update.message.reply_text("❌ Описание способностей должно быть не менее 10 символов!")
        return RP_CHARACTER_ABILITIES

    context.user_data['rp_abilities'] = abilities
    await update.message.reply_text(
        "💔 **Шаг 3 из 5:** Опишите слабости персонажа:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Отмена", callback_data="rp_character_menu")]
        ])
    )

    return RP_CHARACTER_WEAKNESSES

async def process_rp_weaknesses(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return RP_CHARACTER_WEAKNESSES

    weaknesses = update.message.text.strip()
    if len(weaknesses) < 10:
        await update.message.reply_text("❌ Описание слабостей должно быть не менее 10 символов!")
        return RP_CHARACTER_WEAKNESSES

    context.user_data['rp_weaknesses'] = weaknesses
    await update.message.reply_text(
        "🎒 **Шаг 4 из 5:** Опишите инвентарь персонажа:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Отмена", callback_data="rp_character_menu")]
        ])
    )

    return RP_CHARACTER_ITEMS

async def process_rp_items(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return RP_CHARACTER_ITEMS

    items = update.message.text.strip()
    if len(items) < 10:
        await update.message.reply_text("❌ Описание инвентаря должно быть не менее 10 символов!")
        return RP_CHARACTER_ITEMS

    context.user_data['rp_items'] = items
    await update.message.reply_text(
        "📖 **Шаг 5 из 5:** Напишите биографию персонажа:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Отмена", callback_data="rp_character_menu")]
        ])
    )

    return RP_CHARACTER_BIO

async def process_rp_bio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return RP_CHARACTER_BIO

    bio = update.message.text.strip()
    if len(bio) < 20:
        await update.message.reply_text("❌ Биография должна быть не менее 20 символов!")
        return RP_CHARACTER_BIO

    user_id = update.effective_user.id
    char_id = create_rp_character(
        user_id,
        context.user_data['rp_name'],
        context.user_data['rp_abilities'],
        context.user_data['rp_weaknesses'],
        context.user_data['rp_items'],
        bio
    )

    if char_id:
        await update.message.reply_text(
            f"✅ **ПЕРСОНАЖ СОЗДАН!**\n\n"
            f"🎭 Имя: {context.user_data['rp_name']}\n"
            f"🆔 ID: #{char_id}\n\n"
            f"⏳ Персонаж отправлен на рассмотрение администратору.\n"
            f"💰 После одобрения будет установлена цена.\n\n"
            f"Спасибо за создание персонажа!",
            reply_markup=get_main_menu(user_id)
        )

        # Уведомляем администратора
        user = get_user(user_id)
        if user:
            try:
                await context.bot.send_message(
                    ADMIN_ID,
                    f"🎭 **НОВЫЙ РП ПЕРСОНАЖ НА РАССМОТРЕНИЕ**\n\n"
                    f"🆔 **ID персонажа:** #{char_id}\n"
                    f"👤 **Автор:** {user['nickname']}\n"
                    f"📱 **TG:** @{user.get('username', 'нет')}\n"
                    f"📛 **Имя персонажа:** {context.user_data['rp_name']}\n\n"
                    f"💪 **Способности:**\n{context.user_data['rp_abilities'][:100]}...\n\n"
                    f"💔 **Слабости:**\n{context.user_data['rp_weaknesses'][:100]}...\n\n"
                    f"🔗 **Ссылка на автора:** tg://user?id={user_id}",
                    reply_markup=InlineKeyboardMarkup([
                        [
                            InlineKeyboardButton("✅ Одобрить", callback_data=f"admin_approve_rp_{char_id}"),
                            InlineKeyboardButton("❌ Отклонить", callback_data=f"admin_reject_rp_{char_id}")
                        ],
                        [InlineKeyboardButton("🎭 Все персонажи", callback_data="admin_rp_pending")]
                    ])
                )
            except Exception as e:
                logger.error(f"Ошибка уведомления админа: {e}")
    else:
        await update.message.reply_text(
            "❌ Ошибка при создании персонажа!",
            reply_markup=get_main_menu(user_id)
        )

    context.user_data.clear()
    return ConversationHandler.END

async def admin_rp_pending(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.from_user.id != ADMIN_ID:
        await query.edit_message_text("⛔ Нет доступа!")
        return

    pending_chars = get_pending_rp_characters()
    if not pending_chars:
        await query.edit_message_text(
            "📭 **Нет персонажей на рассмотрение**",
            reply_markup=get_main_menu(ADMIN_ID)
        )
        return

    text = "🎭 **ПЕРСОНАЖИ НА РАССМОТРЕНИЕ**\n\n"
    keyboard = []
    for char in pending_chars[:5]:
        user = get_user(char['user_id'])
        user_name = user['nickname'] if user else f"ID: {char['user_id']}"

        text += f"🆔 **#{char['id']}**\n"
        text += f"📛 {char['name']}\n"
        text += f"👤 {user_name}\n"
        text += f"💪 {char['abilities'][:30]}...\n\n"
        keyboard.append([
            InlineKeyboardButton(f"👁️ #{char['id']} - {char['name']}", callback_data=f"admin_view_rp_{char['id']}")
        ])

    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="admin_panel")])

    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def admin_view_rp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.from_user.id != ADMIN_ID:
        await query.edit_message_text("⛔ Нет доступа!")
        return

    if not query.data.startswith("admin_view_rp_"):
        return

    char_id = int(query.data.replace("admin_view_rp_", ""))
    chars = db.select('rp_characters', {'id': char_id}, limit=1)

    if not chars:
        await query.edit_message_text("❌ Персонаж не найден!")
        return

    char = chars[0]
    user = get_user(char['user_id'])

    text = f"🎭 **ПЕРСОНАЖ #{char_id}**\n\n"
    if user:
        text += f"👤 **Автор:** {user['nickname']}\n"
        text += f"📱 **TG:** @{user.get('username', 'нет')}\n"
    else:
        text += f"👤 **Автор:** Неизвестно (ID: {char['user_id']})\n"
    text += f"📛 **Имя:** {char['name']}\n"
    text += f"📅 **Создан:** {char.get('created_at', 'N/A')[:10]}\n\n"
    text += f"💪 **Способности:**\n{char['abilities']}\n\n"
    text += f"💔 **Слабости:**\n{char['weaknesses']}\n\n"
    text += f"🎒 **Инвентарь:**\n{char['items']}\n\n"
    text += f"📖 **Биография:**\n{char['bio']}\n"

    keyboard = [
        [
            InlineKeyboardButton("✅ Одобрить", callback_data=f"admin_approve_rp_{char_id}"),
            InlineKeyboardButton("❌ Отклонить", callback_data=f"admin_reject_rp_{char_id}")
        ],
        [InlineKeyboardButton("🔙 Назад", callback_data="admin_rp_pending")]
    ]

    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def admin_approve_rp_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.from_user.id != ADMIN_ID:
        await query.edit_message_text("⛔ Нет доступа!")
        return

    if not query.data.startswith("admin_approve_rp_"):
        return

    char_id = int(query.data.replace("admin_approve_rp_", ""))
    context.user_data['approving_rp'] = char_id

    await query.edit_message_text(
        f"💰 **УСТАНОВКА ЦЕНЫ ПЕРСОНАЖА**\n\n"
        f"Введите цену для персонажа (от {RP_CHARACTER_MIN_PRICE} до {RP_CHARACTER_MAX_PRICE} акойнов):",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Отмена", callback_data=f"admin_view_rp_{char_id}")]
        ])
    )

    return ADMIN_RP_APPROVE_PRICE

async def admin_approve_rp_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # ИСПРАВЛЕНИЕ: Проверяем, что это администратор
    if update.effective_user.id != ADMIN_ID:
        return ConversationHandler.END

    if not update.message:
        return ADMIN_RP_APPROVE_PRICE

    try:
        price = int(update.message.text.strip())
        char_id = context.user_data.get('approving_rp')

        if not char_id:
            await update.message.reply_text("❌ Ошибка!") if update.effective_user.id == ADMIN_ID else None
            return ConversationHandler.END

        if price < RP_CHARACTER_MIN_PRICE or price > RP_CHARACTER_MAX_PRICE:
            await update.message.reply_text(f"❌ Цена должна быть от {RP_CHARACTER_MIN_PRICE} до {RP_CHARACTER_MAX_PRICE}!") if update.effective_user.id == ADMIN_ID else None
            return ADMIN_RP_APPROVE_PRICE

        if approve_rp_character(char_id, price):
            char = db.select('rp_characters', {'id': char_id}, limit=1)
            if char:
                char = char[0]
                user = get_user(char['user_id'])

                await update.message.reply_text(
                    f"✅ **ПЕРСОНАЖ ОДОБРЕН!**\n\n"
                    f"🎭 Имя: {char['name']}\n"
                    f"💰 Цена: {price} акойнов\n"
                    f"👤 Автор: {user['nickname'] if user else 'Неизвестно'}\n"
                    f"✅ Уведомление отправлено автору.",
                    reply_markup=get_main_menu(ADMIN_ID)
                )

                # Уведомляем автора
                if user:
                    try:
                        await context.bot.send_message(
                            char['user_id'],
                            f"✅ **ВАШ ПЕРСОНАЖ ОДОБРЕН!**\n\n"
                            f"🎭 **Имя:** {char['name']}\n"
                            f"💰 **Цена:** {price} акойнов\n\n"
                            f"Теперь вы можете:\n"
                            f"• Продать персонажа другому игроку\n"
                            f"• Продать персонажа клану (30% от цены)\n\n"
                            f"Поздравляем с созданием персонажа!",
                            reply_markup=get_main_menu(char['user_id'])
                        )
                    except Exception as e:
                        logger.error(f"Ошибка уведомления автора: {e}")
        else:
            await update.message.reply_text(
                "❌ Ошибка при одобрении персонажа!",
                reply_markup=get_main_menu(ADMIN_ID)
            )
    except ValueError:
        await update.message.reply_text("❌ Введите число!") if update.effective_user.id == ADMIN_ID else None
        return ADMIN_RP_APPROVE_PRICE

    context.user_data.clear()
    return ConversationHandler.END

async def admin_reject_rp_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.from_user.id != ADMIN_ID:
        await query.edit_message_text("⛔ Нет доступа!")
        return

    if not query.data.startswith("admin_reject_rp_"):
        return

    char_id = int(query.data.replace("admin_reject_rp_", ""))
    context.user_data['rejecting_rp'] = char_id

    await query.edit_message_text(
        f"❌ **ОТКЛОНЕНИЕ ПЕРСОНАЖА**\n\n"
        f"Введите причину отклонения:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Отмена", callback_data=f"admin_view_rp_{char_id}")]
        ])
    )

    return ConversationHandler.END

async def process_rp_rejection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # ИСПРАВЛЕНИЕ: Проверяем, что это администратор
    if update.effective_user.id != ADMIN_ID:
        return ConversationHandler.END

    if not update.message:
        return

    reason = update.message.text.strip()
    char_id = context.user_data.get('rejecting_rp')
    if not char_id:
        await update.message.reply_text("❌ Ошибка!")
        return

    char = db.select('rp_characters', {'id': char_id}, limit=1)
    if not char:
        await update.message.reply_text("❌ Персонаж не найден!")
        return

    char = char[0]

    if reject_rp_character(char_id, reason):
        await update.message.reply_text(
            f"✅ **ПЕРСОНАЖ ОТКЛОНЕН!**\n"
            f"📝 Причина отправлена автору.",
            reply_markup=get_main_menu(ADMIN_ID)
        )

        # Уведомляем автора
        user = get_user(char['user_id'])
        if user:
            try:
                await context.bot.send_message(
                    char['user_id'],
                    f"❌ **ВАШ ПЕРСОНАЖ ОТКЛОНЕН**\n\n"
                    f"🎭 **Имя:** {char['name']}\n"
                    f"📝 **Причина отказа:** {reason}\n\n"
                    f"Вы можете создать нового персонажа с учетом замечаний.",
                    reply_markup=get_main_menu(char['user_id'])
                )
            except Exception as e:
                logger.error(f"Ошибка уведомления автора: {e}")
    else:
        await update.message.reply_text(
            "❌ Ошибка при отклонении персонажа!",
            reply_markup=get_main_menu(ADMIN_ID)
        )

    context.user_data.clear()

def setup_rp_handlers(application):
    """Настройка обработчиков РП персонажей"""
    rp_conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(create_rp_character_start, pattern='^create_rp_character$')],
        states={
            RP_CHARACTER_NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, process_rp_name),
            ],
            RP_CHARACTER_ABILITIES: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, process_rp_abilities),
            ],
            RP_CHARACTER_WEAKNESSES: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, process_rp_weaknesses),
            ],
            RP_CHARACTER_ITEMS: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, process_rp_items),
            ],
            RP_CHARACTER_BIO: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, process_rp_bio),
            ],
            ADMIN_RP_APPROVE_PRICE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, admin_approve_rp_price),
            ],
        },
        fallbacks=[CallbackQueryHandler(rp_character_menu, pattern='^rp_character_menu$')],
        per_message=False
    )

    application.add_handler(CallbackQueryHandler(rp_character_menu, pattern='^rp_character_menu$'))
    application.add_handler(CallbackQueryHandler(admin_rp_pending, pattern='^admin_rp_pending$'))
    application.add_handler(CallbackQueryHandler(admin_view_rp, pattern='^admin_view_rp_'))
    application.add_handler(CallbackQueryHandler(admin_approve_rp_start, pattern='^admin_approve_rp_'))
    application.add_handler(CallbackQueryHandler(admin_reject_rp_start, pattern='^admin_reject_rp_'))
    application.add_handler(rp_conv_handler)
