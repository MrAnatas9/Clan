import logging
import random
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, MessageHandler, filters, CallbackQueryHandler
from config import *
from database import *
from states import *
from keyboards.main_menu import get_main_menu
from datetime import datetime

logger = logging.getLogger(__name__)

async def casino_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
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

    text = "🎰 **КАЗИНО АД**\n\n"
    text += f"💰 Ваш баланс: {user['coins']} акойнов\n\n"
    text += "🎲 **Игры:**\n"
    text += "1. 🎰 Слоты (x1.5 за 2 одинаковых, x5 за 3)\n"
    text += "2. 🎲 Кости (x1.5 за победу)\n"
    text += "3. 🔴⚫ Рулетка (x2 за угаданный цвет, x5 за зеленое)\n\n"
    text += f"⚠️ **Внимание:** Шансы уменьшены! Азартные игры могут привести к потере денег!"

    keyboard = [
        [InlineKeyboardButton("🎰 Играть в слоты", callback_data="casino_slots")],
        [InlineKeyboardButton("🎲 Играть в кости", callback_data="casino_dice")],
        [InlineKeyboardButton("🔴⚫ Играть в рулетку", callback_data="casino_roulette")],
        [InlineKeyboardButton("🔙 Назад", callback_data="back")]
    ]

    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def casino_bet_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    user = get_user(user_id)

    if not user:
        await query.edit_message_text("❌ Вы не зарегистрированы!")
        return ConversationHandler.END

    if query.data == "casino_slots":
        game_type = "slots"
        game_name = "🎰 СЛОТЫ"
    elif query.data == "casino_dice":
        game_type = "dice"
        game_name = "🎲 КОСТИ"
    elif query.data == "casino_roulette":
        game_type = "roulette"
        game_name = "🔴⚫ РУЛЕТКА"
    else:
        await query.edit_message_text("❌ Неизвестная игра!")
        return ConversationHandler.END

    context.user_data['casino_game'] = game_type

    await query.edit_message_text(
        f"{game_name}\n\n"
        f"💰 Ваш баланс: {user['coins']} акойнов\n\n"
        f"Введите сумму ставки (минимум {CASINO_MIN_BET} акойнов):",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Отмена", callback_data="casino_menu")]
        ])
    )

    return CASINO_BET_AMOUNT

async def casino_process_bet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return CASINO_BET_AMOUNT

    user_id = update.effective_user.id
    user = get_user(user_id)

    if not user:
        await update.message.reply_text("❌ Вы не зарегистрированы!")
        return ConversationHandler.END

    try:
        bet = int(update.message.text.strip())

        if bet < CASINO_MIN_BET:
            await update.message.reply_text(f"❌ Минимальная ставка - {CASINO_MIN_BET} акойнов!")
            return CASINO_BET_AMOUNT

        if bet > user['coins']:
            await update.message.reply_text("❌ Недостаточно средств!")
            return CASINO_BET_AMOUNT

        game_type = context.user_data.get('casino_game')

        if game_type == 'slots':
            await update.message.reply_text(
                f"🎰 **СТАВКА ПРИНЯТА!**\n\n"
                f"💰 Сумма ставки: {bet} акойнов\n\n"
                f"Начинаем игру...",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🎰 Крутить!", callback_data=f"spin_slots_{bet}")]
                ])
            )
        elif game_type == 'dice':
            await update.message.reply_text(
                f"🎲 **СТАВКА ПРИНЯТА!**\n\n"
                f"💰 Сумма ставки: {bet} акойнов\n\n"
                f"Начинаем игру...",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🎲 Бросить кости!", callback_data=f"roll_dice_{bet}")]
                ])
            )
        elif game_type == 'roulette':
            await update.message.reply_text(
                f"🔴⚫ **СТАВКА ПРИНЯТА!**\n\n"
                f"💰 Сумма ставки: {bet} акойнов\n\n"
                f"Выберите цвет для ставки:",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔴 Красное (x2)", callback_data=f"roulette_red_{bet}")],
                    [InlineKeyboardButton("⚫ Черное (x2)", callback_data=f"roulette_black_{bet}")],
                    [InlineKeyboardButton("🟢 Зеленое (x5)", callback_data=f"roulette_green_{bet}")]
                ])
            )

        return ConversationHandler.END

    except ValueError:
        await update.message.reply_text("❌ Введите число!")
        return CASINO_BET_AMOUNT

async def play_slots(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data.replace("spin_slots_", "")
    bet = int(data)

    user_id = query.from_user.id
    user = get_user(user_id)

    if bet > user['coins']:
        await query.edit_message_text("❌ Недостаточно средств!")
        return

    # Снимаем ставку сразу
    add_user_coins(user_id, -bet)

    symbols = ["🍒", "🍋", "🍊", "🍉", "⭐", "🔔", "7️⃣", "💰"]

    message = query.message

    # Анимация вращения
    for i in range(5):
        reel1 = random.choice(symbols)
        reel2 = random.choice(symbols)
        reel3 = random.choice(symbols)

        await query.edit_message_text(
            f"🎰 **СЛОТЫ КРУТЯТСЯ...** 🎰\n\n"
            f"🎰  {reel1} | {reel2} | {reel3}  🎰\n\n"
            f"💰 Ставка: {bet} акойнов",
            reply_markup=None
        )
        await asyncio.sleep(0.3)

    # Финальный результат
    reel1 = random.choice(symbols)
    reel2 = random.choice(symbols)
    reel3 = random.choice(symbols)

    result = f"{reel1} | {reel2} | {reel3}"

    # Определение выигрыша с уменьшенными шансами
    if reel1 == reel2 == reel3:
        win_amount = bet * CASINO_JACKPOT_MULTIPLIER  # x5
        result_text = f"🎉 **ДЖЕКПОТ! ТРИ ОДИНАКОВЫХ!** 🎉\nВы выиграли {win_amount} акойнов!"
        add_user_coins(user_id, win_amount)
    elif reel1 == reel2 or reel2 == reel3 or reel1 == reel3:
        win_amount = int(bet * CASINO_WIN_MULTIPLIER)  # x1.5
        result_text = f"✅ **ВЫИГРЫШ! ДВА ОДИНАКОВЫХ!**\nВы выиграли {win_amount} акойнов!"
        add_user_coins(user_id, win_amount)
    else:
        win_amount = 0
        result_text = f"❌ **ПРОИГРЫШ**\nВы проиграли {bet} акойнов."

    user = get_user(user_id)

    await query.edit_message_text(
        f"🎰 **РЕЗУЛЬТАТ ИГРЫ В СЛОТЫ**\n\n"
        f"🎰  {result}  🎰\n\n"
        f"{result_text}\n\n"
        f"💰 Новый баланс: {user['coins']} акойнов",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🎰 Играть снова", callback_data="casino_slots")],
            [InlineKeyboardButton("🔙 В меню казино", callback_data="casino_menu")]
        ])
    )

async def play_dice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data.replace("roll_dice_", "")
    bet = int(data)

    user_id = query.from_user.id
    user = get_user(user_id)

    if bet > user['coins']:
        await query.edit_message_text("❌ Недостаточно средств!")
        return

    # Снимаем ставку сразу
    add_user_coins(user_id, -bet)

    message = query.message

    # Анимация броска
    for i in range(3):
        player_dice = random.randint(1, 6)
        bot_dice = random.randint(1, 6)

        await query.edit_message_text(
            f"🎲 **БРОСАЕМ КОСТИ...** 🎲\n\n"
            f"👤 **Вы:** 🎲 {player_dice}\n"
            f"🤖 **Бот:** 🎲 {bot_dice}\n\n"
            f"💰 Ставка: {bet} акойнов",
            reply_markup=None
        )
        await asyncio.sleep(0.5)

    # Финальный бросок
    player_dice = random.randint(1, 6)
    bot_dice = random.randint(1, 6)

    if player_dice > bot_dice:
        win_amount = int(bet * CASINO_WIN_MULTIPLIER)  # x1.5
        result_text = f"✅ **ПОБЕДА!** {player_dice} > {bot_dice}\nВы выиграли {win_amount} акойнов!"
        add_user_coins(user_id, win_amount)
    elif player_dice < bot_dice:
        win_amount = 0
        result_text = f"❌ **ПОРАЖЕНИЕ** {player_dice} < {bot_dice}\nВы проиграли {bet} акойнов."
    else:
        win_amount = bet  # Возвращаем ставку при ничье
        result_text = f"🤝 **НИЧЬЯ!** {player_dice} = {bot_dice}\nСтавка возвращена."
        add_user_coins(user_id, bet)

    user = get_user(user_id)

    await query.edit_message_text(
        f"🎲 **РЕЗУЛЬТАТ ИГРЫ В КОСТИ**\n\n"
        f"👤 **Вы:** 🎲 {player_dice}\n"
        f"🤖 **Бот:** 🎲 {bot_dice}\n\n"
        f"{result_text}\n\n"
        f"💰 Новый баланс: {user['coins']} акойнов",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🎲 Играть снова", callback_data="casino_dice")],
            [InlineKeyboardButton("🔙 В меню казино", callback_data="casino_menu")]
        ])
    )

async def play_roulette(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data
    if data.startswith("roulette_red_"):
        bet_color = "red"
        color_emoji = "🔴"
        multiplier = 2
    elif data.startswith("roulette_black_"):
        bet_color = "black"
        color_emoji = "⚫"
        multiplier = 2
    elif data.startswith("roulette_green_"):
        bet_color = "green"
        color_emoji = "🟢"
        multiplier = 5  # x5 вместо x14
    else:
        await query.edit_message_text("❌ Ошибка выбора цвета!")
        return

    bet = int(data.split("_")[-1])

    user_id = query.from_user.id
    user = get_user(user_id)

    if bet > user['coins']:
        await query.edit_message_text("❌ Недостаточно средств!")
        return

    # Снимаем ставку сразу
    add_user_coins(user_id, -bet)

    # Определяем результат рулетки с уменьшенными шансами
    colors = ["red", "black", "green"]
    probabilities = [49, 49, 2]  # Уменьшены шансы на зеленое
    result_color = random.choices(colors, weights=probabilities, k=1)[0]

    color_emojis = {
        "red": "🔴",
        "black": "⚫",
        "green": "🟢"
    }

    result_emoji = color_emojis[result_color]

    # Анимация вращения рулетки
    for i in range(5):
        temp_color = random.choice(["🔴", "⚫", "🟢"])
        await query.edit_message_text(
            f"🎰 **РУЛЕТКА КРУТИТСЯ...** 🎰\n\n"
            f"🎰 Выпадает: {temp_color} 🎰\n\n"
            f"🎯 Ваша ставка: {color_emoji} (x{multiplier})\n"
            f"💰 Сумма ставки: {bet} акойнов",
            reply_markup=None
        )
        await asyncio.sleep(0.3)

    # Определяем выигрыш
    if bet_color == result_color:
        win_amount = bet * multiplier
        result_text = f"🎉 **ВЫИГРЫШ!** Выпало {result_emoji}\nВы выиграли {win_amount} акойнов (x{multiplier})!"
        add_user_coins(user_id, win_amount)
    else:
        win_amount = 0
        result_text = f"❌ **ПРОИГРЫШ** Выпало {result_emoji}\nВы проиграли {bet} акойнов."

    user = get_user(user_id)

    await query.edit_message_text(
        f"🎰 **РЕЗУЛЬТАТ РУЛЕТКИ**\n\n"
        f"🎰 Выпало: {result_emoji}\n"
        f"🎯 Ваша ставка: {color_emoji}\n\n"
        f"{result_text}\n\n"
        f"💰 Новый баланс: {user['coins']} акойнов",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🎰 Играть снова", callback_data="casino_roulette")],
            [InlineKeyboardButton("🔙 В меню казино", callback_data="casino_menu")]
        ])
    )

# Убрали групповое казино из этого файла, так как оно теперь обрабатывается в group_commands.py

def setup_casino_handlers(application):
    """Настройка обработчиков казино"""
    casino_conv_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(casino_bet_start, pattern='^casino_slots$|^casino_dice$|^casino_roulette$'),
        ],
        states={
            CASINO_BET_AMOUNT: [
                CallbackQueryHandler(casino_menu, pattern='^back$'),
                CallbackQueryHandler(casino_menu, pattern='^casino_menu$'),
                MessageHandler(filters.TEXT & ~filters.COMMAND, casino_process_bet),
            ],
        },
        fallbacks=[CallbackQueryHandler(casino_menu, pattern='^casino_menu$')],
        per_message=False
    )

    application.add_handler(CallbackQueryHandler(casino_menu, pattern='^casino_menu$'))
    application.add_handler(CallbackQueryHandler(play_slots, pattern='^spin_slots_'))
    application.add_handler(CallbackQueryHandler(play_dice, pattern='^roll_dice_'))
    application.add_handler(CallbackQueryHandler(play_roulette, pattern='^roulette_red_|^roulette_black_|^roulette_green_'))
    application.add_handler(casino_conv_handler)
