import logging
import traceback
import random
from telegram import Update
from telegram.ext import ContextTypes, MessageHandler, filters
from config import *
from database import *

logger = logging.getLogger(__name__)

# Список разрешенных команд (только маленькими буквами)
ALLOWED_COMMANDS = {
    'статистика', 'богачи', 'должники', 'налоги', 'бюджет',
    'работники', 'пинг', 'мой долг', 'сын мой', 'игра казино',
    'помощь', 'help', 'команды', 'справка', 'собрать налоги',
    'слоты', 'кости', 'рулетка', 'казино',  # Добавили команды казино
    'отпуск заявление', 'отпуск одобрить', 'отпуск отклонить',
    'премия', 'штраф', 'уволить', 'забрать', 'выдать'
}

# Команды, которые требуют ответ на сообщение
REPLY_COMMANDS = {
    'премия', 'штраф', 'уволить', 'отпуск одобрить', 'отпуск отклонить',
    'забрать', 'выдать'
}

def is_command(text: str) -> bool:
    """Проверяет, является ли текст командой"""
    if not text:
        return False

    text_lower = text.strip().lower()

    # Проверяем точное совпадение
    if text_lower in ALLOWED_COMMANDS:
        return True

    # Проверяем команды, начинающиеся с определенных слов
    for cmd_start in ['премия ', 'штраф ', 'уволить', 'отпуск отклонить',
                      'отпуск заявление', 'забрать ', 'выдать ', 'слоты ',
                      'кости ', 'рулетка ']:
        if text_lower.startswith(cmd_start):
            return True

    return False

async def handle_group_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик всех групповых сообщений"""
    try:
        # Игнорируем если нет сообщения или текста
        if not update.message or not update.message.text:
            return

        text = update.message.text.strip()
        text_lower = text.lower()

        # Игнорируем не-команды
        if not is_command(text_lower):
            return

        logger.info(f"Group command from {update.effective_user.id}: {text_lower}")

        # Обрабатываем команду в зависимости от типа
        if text_lower == 'статистика':
            await handle_statistics(update)
        elif text_lower == 'богачи':
            await handle_rich(update)
        elif text_lower == 'должники':
            await handle_debtors(update)
        elif text_lower == 'налоги':
            await handle_taxes(update)
        elif text_lower == 'бюджет':
            await handle_budget(update)
        elif text_lower == 'работники':
            await handle_workers(update)
        elif text_lower == 'пинг':
            await update.message.reply_text("🏓 **ПОНГ!** Бот работает исправно!")
        elif text_lower == 'мой долг':
            await handle_my_debt(update)
        elif text_lower == 'сын мой':
            await handle_son_my(update)
        elif text_lower == 'игра казино':
            await handle_casino(update)
        elif text_lower == 'казино':  # Добавили короткую команду
            await handle_casino(update)
        elif text_lower.startswith('слоты'):
            await handle_slots(update, text)
        elif text_lower.startswith('кости'):
            await handle_dice(update, text)
        elif text_lower.startswith('рулетка'):
            await handle_roulette(update, text)
        elif text_lower.startswith('отпуск заявление'):
            await handle_vacation_request(update, text)
        elif text_lower in ['помощь', 'help', 'команды', 'справка']:
            await handle_help(update)
        elif text_lower == 'собрать налоги':
            await handle_collect_taxes(update)
        elif text_lower.startswith('премия '):
            await handle_bonus(update, text)
        elif text_lower.startswith('штраф '):
            await handle_fine(update, text)
        elif text_lower.startswith('уволить'):
            await handle_fire(update, text)
        elif text_lower == 'отпуск одобрить':
            await handle_vacation_approve(update)
        elif text_lower.startswith('отпуск отклонить'):
            await handle_vacation_reject(update, text)
        elif text_lower.startswith('забрать '):
            await handle_take_money(update, text)
        elif text_lower.startswith('выдать '):
            await handle_give_money(update, text)
        else:
            logger.warning(f"Неизвестная команда: {text_lower}")

    except Exception as e:
        logger.error(f"Ошибка в обработке группового сообщения: {e}")
        logger.error(traceback.format_exc())
        # НИЧЕГО НЕ ОТПРАВЛЯЕМ В ГРУППУ!

async def handle_statistics(update: Update):
    """Обработка команды статистика"""
    try:
        stats = get_statistics()
        top_rich = get_top_rich_users(5)
        top_debtors = get_top_debtors(5)

        response = (
            f"📊 **СТАТИСТИКА КЛАНА**\n\n"
            f"👥 **Всего участников:** {stats['total_users']}\n"
            f"💰 **Всего акойнов:** {stats['total_coins']}\n"
            f"🏦 **Общий долг:** {stats['total_debt']}\n"
            f"📋 **Ожидают одобрения:** {stats['pending_applications']}\n\n"
            f"💰 **ТОП 5 БОГАЧЕЙ:**\n"
        )

        for i, rich in enumerate(top_rich, 1):
            response += f"{i}. {rich['nickname']}: {rich['coins']} акойнов\n"

        response += f"\n🏦 **ТОП 5 ДОЛЖНИКОВ:**\n"

        for i, debtor in enumerate(top_debtors, 1):
            response += f"{i}. {debtor['nickname']}: {abs(debtor['coins'])} акойнов\n"

        await update.message.reply_text(response)
    except Exception as e:
        logger.error(f"Ошибка в статистике: {e}")
        logger.error(traceback.format_exc())

async def handle_rich(update: Update):
    """Обработка команды богачи"""
    try:
        top_rich = get_top_rich_users(10)

        response = "💰 **ТОП 10 БОГАЧЕЙ КЛАНА**\n\n"

        for i, rich in enumerate(top_rich, 1):
            response += f"{i}. {rich['nickname']} - {rich['coins']} акойнов\n"

        await update.message.reply_text(response)
    except Exception as e:
        logger.error(f"Ошибка в богачах: {e}")
        logger.error(traceback.format_exc())

async def handle_debtors(update: Update):
    """Обработка команды должники"""
    try:
        top_debtors = get_top_debtors(10)

        if not top_debtors:
            await update.message.reply_text("✅ В клане нет должников!")
            return

        response = "🏦 **ТОП 10 ДОЛЖНИКОВ КЛАНА**\n\n"

        for i, debtor in enumerate(top_debtors, 1):
            response += f"{i}. {debtor['nickname']} - {abs(debtor['coins'])} акойнов\n"

        await update.message.reply_text(response)
    except Exception as e:
        logger.error(f"Ошибка в должниках: {e}")
        logger.error(traceback.format_exc())

async def handle_taxes(update: Update):
    """Обработка команды налоги"""
    try:
        weekly_taxes = calculate_weekly_taxes()

        response = (
            f"💸 **НАЛОГОВАЯ СИСТЕМА**\n\n"
            f"📊 **Ставка налога:** 10% от баланса\n"
            f"💰 **Налоги за неделю:** {weekly_taxes} акойнов\n"
            f"📅 **Сбор налогов:** Администратором командой 'собрать налоги'\n\n"
            f"💡 Налоги идут в бюджет клана на развитие."
        )

        await update.message.reply_text(response)
    except Exception as e:
        logger.error(f"Ошибка в налогах: {e}")
        logger.error(traceback.format_exc())

async def handle_budget(update: Update):
    """Обработка команды бюджет"""
    try:
        admin = get_user(ADMIN_ID)

        response = (
            f"📈 **БЮДЖЕТ КЛАНА**\n\n"
            f"💰 **Средства:** {admin['coins']} акойнов\n"
            f"💸 **Расходы:** Кредиты, премии, закупки\n"
            f"💰 **Доходы:** Налоги, комиссии, продажи\n\n"
            f"👑 **Управляет:** Администратор"
        )

        await update.message.reply_text(response)
    except Exception as e:
        logger.error(f"Ошибка в бюджете: {e}")
        logger.error(traceback.format_exc())

async def handle_workers(update: Update):
    """Обработка команды работники"""
    try:
        all_users = get_all_users()
        workers = [u for u in all_users if u['user_id'] != ADMIN_ID and not u.get('is_banned', False)]

        response = f"👥 **РАБОТНИКИ КЛАНА** ({len(workers)})\n\n"

        for user in workers[:20]:
            response += f"• {user['nickname']} - {user['job']}\n"

        if len(workers) > 20:
            response += f"\n... и еще {len(workers) - 20} работников"

        await update.message.reply_text(response)
    except Exception as e:
        logger.error(f"Ошибка в работниках: {e}")
        logger.error(traceback.format_exc())

async def handle_my_debt(update: Update):
    """Обработка команды мой долг"""
    try:
        user_data = get_user(update.effective_user.id)
        if not user_data:
            return

        balance = user_data['coins']
        if balance >= 0:
            response = (
                f"💰 **ВАШ БАЛАНС**\n\n"
                f"👤 {user_data['nickname']}\n"
                f"💸 Баланс: {balance} акойнов\n"
                f"✅ Без долгов\n"
                f"💼 Работа: {user_data['job']}"
            )
        else:
            debt = abs(balance)
            response = (
                f"⚠️ **ВЫ В ДОЛГАХ!**\n\n"
                f"👤 {user_data['nickname']}\n"
                f"💸 Долг: {debt} акойнов\n"
                f"🏦 Максимум: {MAX_DEBT} акойнов\n"
                f"📈 Проценты: {int(DEBT_INTEREST_RATE * 100)}% в месяц\n"
                f"💼 Работа: {user_data['job']}\n\n"
                f"💡 Для кредита напишите /start в ЛС с ботом"
            )

        await update.message.reply_text(response)
    except Exception as e:
        logger.error(f"Ошибка в моем долге: {e}")
        logger.error(traceback.format_exc())

async def handle_son_my(update: Update):
    """Обработка команды сын мой"""
    try:
        await update.message.reply_text("👑 Да, отец? Чем могу служить?")
    except Exception as e:
        logger.error(f"Ошибка в сын мой: {e}")
        logger.error(traceback.format_exc())

async def handle_casino(update: Update):
    """Обработка команды игра казино"""
    try:
        user_data = get_user(update.effective_user.id)
        if user_data:
            await update.message.reply_text(
                f"🎰 **КАЗИНО В ГРУППЕ**\n\n"
                f"👤 Игрок: {user_data['nickname']}\n"
                f"💰 Баланс: {user_data['coins']} акойнов\n\n"
                f"Для игры напишите:\n"
                f"• **слоты <ставка>** - игра в слоты\n"
                f"• **кости <ставка>** - игра в кости\n"
                f"• **рулетка <ставка> [тип]** - игра в рулетку\n\n"
                f"💡 **Примеры:**\n"
                f"• слоты 100\n"
                f"• кости 500\n"
                f"• рулетка 200 красное\n"
                f"• рулетка 1000 7 (ставка на число 7)"
            )
    except Exception as e:
        logger.error(f"Ошибка в казино: {e}")
        logger.error(traceback.format_exc())

# Новые функции для казино с исправлениями
async def handle_slots(update: Update, text: str):
    """Обработка команды слоты"""
    try:
        user_data = get_user(update.effective_user.id)
        if not user_data:
            return

        parts = text.split()

        if len(parts) < 2:
            await update.message.reply_text(
                "🎰 **ИГРА В СЛОТЫ**\n\n"
                "💰 Чтобы играть, напишите: **слоты <ставка>**\n"
                f"💸 Ваш баланс: {user_data['coins']} акойнов\n"
                f"💡 **Пример:** слоты 100"
            )
            return

        try:
            bet = int(parts[1])
            
            # ИСПРАВЛЕНИЕ 1: Добавляем минимальную и максимальную ставку
            MIN_BET = 10
            MAX_BET = 1000
            
            if bet < MIN_BET:
                await update.message.reply_text(f"❌ Минимальная ставка: {MIN_BET} акойнов!")
                return
            if bet > MAX_BET:
                await update.message.reply_text(f"❌ Максимальная ставка: {MAX_BET} акойнов!")
                return
                
            if bet <= 0:
                await update.message.reply_text("❌ Ставка должна быть больше 0!")
                return

            if bet > user_data['coins']:
                await update.message.reply_text("❌ Недостаточно средств для такой ставки!")
                return

            # Простая реализация слотов
            symbols = ["🍒", "🍋", "🍊", "🍉", "🍇", "⭐", "7️⃣"]
            result = [random.choice(symbols) for _ in range(3)]

            # ИСПРАВЛЕНИЕ 2: Уменьшаем шансы на выигрыш
            if result[0] == result[1] == result[2]:
                win = bet * 3  # Было 5, стало 3
                message = f"🎉 **ДЖЕКПОТ!** Вы выиграли {win} акойнов!"
                add_user_coins(update.effective_user.id, win - bet)
            elif result[0] == result[1] or result[1] == result[2]:
                win = int(bet * 1.5)  # Было 2, стало 1.5
                message = f"🎊 Вы выиграли {win} акойнов!"
                add_user_coins(update.effective_user.id, win - bet)
            else:
                win = 0
                message = "😔 Вы проиграли!"
                add_user_coins(update.effective_user.id, -bet)

            new_balance = get_user(update.effective_user.id)['coins']

            await update.message.reply_text(
                f"🎰 **СЛОТЫ**\n\n"
                f"🎲 Результат: {' '.join(result)}\n"
                f"💰 Ставка: {bet} акойнов\n"
                f"📊 {message}\n"
                f"💸 Новый баланс: {new_balance} акойнов"
            )

        except ValueError:
            await update.message.reply_text("❌ Неверный формат ставки! Используйте: слоты <ставка>")

    except Exception as e:
        logger.error(f"Ошибка в слотах: {e}")
        logger.error(traceback.format_exc())

async def handle_dice(update: Update, text: str):
    """Обработка команды кости"""
    try:
        user_data = get_user(update.effective_user.id)
        if not user_data:
            return

        parts = text.split()

        if len(parts) < 2:
            await update.message.reply_text(
                "🎲 **ИГРА В КОСТИ**\n\n"
                "💰 Чтобы играть, напишите: **кости <ставка>**\n"
                f"💸 Ваш баланс: {user_data['coins']} акойнов\n"
                f"💡 **Пример:** кости 100"
            )
            return

        try:
            bet = int(parts[1])
            
            # ИСПРАВЛЕНИЕ 3: Добавляем минимальную и максимальную ставку
            MIN_BET = 10
            MAX_BET = 1000
            
            if bet < MIN_BET:
                await update.message.reply_text(f"❌ Минимальная ставка: {MIN_BET} акойнов!")
                return
            if bet > MAX_BET:
                await update.message.reply_text(f"❌ Максимальная ставка: {MAX_BET} акойнов!")
                return
                
            if bet <= 0:
                await update.message.reply_text("❌ Ставка должна быть больше 0!")
                return

            if bet > user_data['coins']:
                await update.message.reply_text("❌ Недостаточно средств для такой ставки!")
                return

            # ИСПРАВЛЕНИЕ 4: Кости должны быть от 1 до 6 для каждого кубика
            player_dice = random.randint(1, 6) + random.randint(1, 6)  # Два кубика, сумма от 2 до 12
            bot_dice = random.randint(1, 6) + random.randint(1, 6)  # Два кубика, сумма от 2 до 12

            # ИСПРАВЛЕНИЕ 5: Уменьшаем выигрыш
            if player_dice > bot_dice:
                win = int(bet * 1.5)  # Было 2, стало 1.5
                message = f"🎉 Вы выиграли {win} акойнов! ({player_dice} > {bot_dice})"
                add_user_coins(update.effective_user.id, win - bet)
            elif player_dice == bot_dice:
                message = f"🤝 Ничья! ({player_dice} = {bot_dice})"
                # Возвращаем ставку при ничье
            else:
                win = 0
                message = f"😔 Вы проиграли! ({player_dice} < {bot_dice})"
                add_user_coins(update.effective_user.id, -bet)

            new_balance = get_user(update.effective_user.id)['coins']

            await update.message.reply_text(
                f"🎲 **КОСТИ**\n\n"
                f"👤 Ваш бросок: {player_dice}\n"
                f"🤖 Бросок бота: {bot_dice}\n"
                f"💰 Ставка: {bet} акойнов\n"
                f"📊 {message}\n"
                f"💸 Новый баланс: {new_balance} акойнов"
            )

        except ValueError:
            await update.message.reply_text("❌ Неверный формат ставки! Используйте: кости <ставка>")

    except Exception as e:
        logger.error(f"Ошибка в костях: {e}")
        logger.error(traceback.format_exc())

async def handle_roulette(update: Update, text: str):
    """Обработка команды рулетка"""
    try:
        user_data = get_user(update.effective_user.id)
        if not user_data:
            return

        parts = text.split()

        if len(parts) < 2:
            await update.message.reply_text(
                "🎡 **РУЛЕТКА**\n\n"
                "💰 Чтобы играть, напишите: **рулетка <ставка> [тип]**\n"
                "📋 **Варианты ставок:**\n"
                "• **красное** - ставка на красное (x1.8)\n"
                "• **черное** - ставка на черное (x1.8)\n"
                "• **четное** - ставка на четное (x1.8)\n"
                "• **нечетное** - ставка на нечетное (x1.8)\n"
                "• **1-12**, **13-24**, **25-36** (x2.5)\n"
                "• **конкретное число 1-36** (x30)\n\n"
                f"💸 Ваш баланс: {user_data['coins']} акойнов\n"
                f"💡 **Примеры:**\n"
                f"• рулетка 100 красное\n"
                f"• рулетка 500 1-12\n"
                f"• рулетка 1000 7"
            )
            return

        try:
            bet = int(parts[1])
            
            # ИСПРАВЛЕНИЕ 5: Добавляем минимальную и максимальную ставку
            MIN_BET = 10
            MAX_BET = 1000
            
            if bet < MIN_BET:
                await update.message.reply_text(f"❌ Минимальная ставка: {MIN_BET} акойнов!")
                return
            if bet > MAX_BET:
                await update.message.reply_text(f"❌ Максимальная ставка: {MAX_BET} акойнов!")
                return
                
            if bet <= 0:
                await update.message.reply_text("❌ Ставка должна быть больше 0!")
                return

            if bet > user_data['coins']:
                await update.message.reply_text("❌ Недостаточно средств для такой ставки!")
                return

            # Определяем тип ставки
            bet_type = "число"  # по умолчанию
            bet_number = None

            if len(parts) > 2:
                bet_type = parts[2].lower()
                if bet_type.isdigit():
                    bet_number = int(bet_type)
                    if bet_number < 1 or bet_number > 36:
                        await update.message.reply_text("❌ Число должно быть от 1 до 36!")
                        return

            result = random.randint(0, 36)  # 0-36 в европейской рулетке

            # Определяем цвет числа
            red_numbers = [1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36]
            is_red = result in red_numbers
            is_black = result != 0 and not is_red
            is_even = result != 0 and result % 2 == 0
            is_odd = result != 0 and result % 2 == 1

            # Проверяем выигрыш с ИСПРАВЛЕННЫМИ множителями
            win = 0
            multiplier = 0

            if result == 0:
                message = "🎯 Выпал 0! Все проиграли!"
                add_user_coins(update.effective_user.id, -bet)
            else:
                if bet_type == "красное" and is_red:
                    win = int(bet * 1.8)  # Было 2, стало 1.8
                    multiplier = 1.8
                elif bet_type == "черное" and is_black:
                    win = int(bet * 1.8)  # Было 2, стало 1.8
                    multiplier = 1.8
                elif bet_type == "четное" and is_even:
                    win = int(bet * 1.8)  # Было 2, стало 1.8
                    multiplier = 1.8
                elif bet_type == "нечетное" and is_odd:
                    win = int(bet * 1.8)  # Было 2, стало 1.8
                    multiplier = 1.8
                elif bet_type == "1-12" and 1 <= result <= 12:
                    win = int(bet * 2.5)  # Было 3, стало 2.5
                    multiplier = 2.5
                elif bet_type == "13-24" and 13 <= result <= 24:
                    win = int(bet * 2.5)  # Было 3, стало 2.5
                    multiplier = 2.5
                elif bet_type == "25-36" and 25 <= result <= 36:
                    win = int(bet * 2.5)  # Было 3, стало 2.5
                    multiplier = 2.5
                elif bet_number is not None and result == bet_number:
                    win = int(bet * 30)  # Было 36, стало 30
                    multiplier = 30
                else:
                    win = 0
                    multiplier = 0

                if win > 0:
                    message = f"🎉 Вы выиграли {win} акойнов! (x{multiplier})"
                    add_user_coins(update.effective_user.id, win - bet)
                else:
                    message = f"😔 Вы проиграли {bet} акойнов!"
                    add_user_coins(update.effective_user.id, -bet)

            new_balance = get_user(update.effective_user.id)['coins']
            color = "🟢 0" if result == 0 else f"🔴 {result}" if is_red else f"⚫ {result}"

            await update.message.reply_text(
                f"🎡 **РУЛЕТКА**\n\n"
                f"🎲 Выпало: {color}\n"
                f"💰 Ставка: {bet} акойнов\n"
                f"📊 Тип ставки: {bet_type if bet_number is None else bet_number}\n"
                f"📈 {message}\n"
                f"💸 Новый баланс: {new_balance} акойнов"
            )

        except ValueError:
            await update.message.reply_text("❌ Неверный формат ставки! Используйте: рулетка <ставка> [тип]")

    except Exception as e:
        logger.error(f"Ошибка в рулетке: {e}")
        logger.error(traceback.format_exc())

async def handle_vacation_request(update: Update, text: str):
    """Обработка команды отпуск заявление"""
    try:
        user_data = get_user(update.effective_user.id)
        if not user_data:
            return

        parts = text.split()
        if len(parts) < 4:
            await update.message.reply_text("❌ Формат: отпуск заявление <дни> <причина>")
            return

        try:
            days = int(parts[2])
            if days < 1 or days > 30:
                await update.message.reply_text("❌ Количество дней должно быть от 1 до 30!")
                return

            reason = ' '.join(parts[3:])
            if len(reason) < 5:
                await update.message.reply_text("❌ Причина должна быть не менее 5 символов!")
                return

            # Проверяем, нет ли уже активной заявки
            pending_vacations = get_pending_vacations()
            for vac in pending_vacations:
                if vac['user_id'] == update.effective_user.id:
                    await update.message.reply_text("❌ У вас уже есть активное заявление на отпуск!")
                    return

            vacation_id = request_vacation(update.effective_user.id, days, reason)

            if vacation_id:
                await update.message.reply_text(
                    f"✅ **ЗАЯВЛЕНИЕ НА ОТПУСК ПОДАНО!**\n\n"
                    f"📅 Дней: {days}\n"
                    f"📝 Причина: {reason}\n"
                    f"🆔 ID: #{vacation_id}\n\n"
                    f"⏳ Ожидайте решения администратора."
                )
            else:
                await update.message.reply_text("❌ Ошибка при подаче заявления!")

        except ValueError:
            await update.message.reply_text("❌ Неверный формат дней! Используйте: отпуск заявление <дни> <причина>")

    except Exception as e:
        logger.error(f"Ошибка в заявлении на отпуск: {e}")
        logger.error(traceback.format_exc())

async def handle_help(update: Update):
    """Обработка команды помощь"""
    try:
        help_text = (
            "📋 **ГРУППОВЫЕ КОМАНДЫ**\n\n"
            "📊 **Информационные (все):**\n"
            "• статистика - Общая статистика\n"
            "• богачи - Топ богачей\n"
            "• должники - Топ должников\n"
            "• налоги - Инфо о налогах\n"
            "• бюджет - Бюджет клана\n"
            "• работники - Список работников\n"
            "• пинг - Проверка бота\n"
            "• мой долг - Ваш баланс\n"
            "• сын мой - Приветствие\n\n"
            "👑 **Админские (ответом):**\n"
            "• премия <сумма> <причина>\n"
            "• штраф <сумма> <причина>\n"
            "• уволить <причина>\n"
            "• отпуск одобрить\n"
            "• отпуск отклонить <причина>\n"
            "• собрать налоги\n"
            "• забрать <сумма> (ответом)\n"
            "• выдать <сумма> (ответом)\n\n"
            "🎰 **Казино (все):**\n"
            "• игра казино / казино - Информация о казино\n"
            "• слоты <ставка> - Игра в слоты\n"
            "• кости <ставка> - Игра в кости\n"
            "• рулетка <ставка> [тип] - Игра в рулетку\n\n"
            "💼 **Общие:**\n"
            "• отпуск заявление <дни> <причина>\n\n"
            "💡 **Для личных функций (/start, кредиты, задания и т.д.):**\n"
            "Напишите /start в личных сообщениях с ботом"
        )

        await update.message.reply_text(help_text)
    except Exception as e:
        logger.error(f"Ошибка в помощи: {e}")
        logger.error(traceback.format_exc())

# Команды с ответом на сообщение
async def handle_bonus(update: Update, text: str):
    """Обработка команды премия"""
    try:
        if update.effective_user.id != ADMIN_ID:
            return

        if not update.message.reply_to_message:
            return

        target_user = update.message.reply_to_message.from_user
        target_data = get_user(target_user.id)

        if not target_data:
            return

        parts = text.split()
        if len(parts) < 3:
            await update.message.reply_text("❌ Формат: премия <сумма> <причина>")
            return

        amount = int(parts[1])
        reason = ' '.join(parts[2:])

        if amount <= 0:
            await update.message.reply_text("❌ Сумма должна быть положительной!")
            return

        if add_user_coins(target_user.id, amount):
            response = (
                f"✅ **ПРЕМИЯ ВЫПИСАНА!**\n\n"
                f"👤 Сотрудник: {target_data['nickname']}\n"
                f"💰 Сумма: {amount} акойнов\n"
                f"📝 Причина: {reason}\n"
                f"💸 Новый баланс: {get_user(target_user.id)['coins']} акойнов"
            )
            await update.message.reply_text(response)
    except ValueError:
        await update.message.reply_text("❌ Неверный формат суммы!")
    except Exception as e:
        logger.error(f"Ошибка в премии: {e}")
        logger.error(traceback.format_exc())

async def handle_fine(update: Update, text: str):
    """Обработка команды штраф"""
    try:
        if update.effective_user.id != ADMIN_ID:
            return

        if not update.message.reply_to_message:
            return

        target_user = update.message.reply_to_message.from_user
        target_data = get_user(target_user.id)

        if not target_data:
            return

        parts = text.split()
        if len(parts) < 3:
            await update.message.reply_text("❌ Формат: штраф <сумма> <причина>")
            return

        amount = int(parts[1])
        reason = ' '.join(parts[2:])

        if amount <= 0:
            await update.message.reply_text("❌ Сумма должна быть положительной!")
            return

        if add_user_coins(target_user.id, -amount):
            response = (
                f"⚖️ **ШТРАФ ВЫПИСАН!**\n\n"
                f"👤 Сотрудник: {target_data['nickname']}\n"
                f"💰 Сумма: {amount} акойнов\n"
                f"📝 Причина: {reason}\n"
                f"💸 Новый баланс: {get_user(target_user.id)['coins']} акойнов"
            )
            await update.message.reply_text(response)
    except ValueError:
        await update.message.reply_text("❌ Неверный формат суммы!")
    except Exception as e:
        logger.error(f"Ошибка в штрафе: {e}")
        logger.error(traceback.format_exc())

async def handle_fire(update: Update, text: str):
    """Обработка команды уволить"""
    try:
        if update.effective_user.id != ADMIN_ID:
            return

        if not update.message.reply_to_message:
            return

        target_user = update.message.reply_to_message.from_user
        target_data = get_user(target_user.id)

        if not target_data:
            return

        reason = text.replace("уволить", "").strip()
        if not reason:
            reason = "Не указана"

        update_user_jobs(target_user.id, [])

        response = (
            f"🔨 **СОТРУДНИК УВОЛЕН!**\n\n"
            f"👤 Сотрудник: {target_data['nickname']}\n"
            f"📝 Причина: {reason}\n"
            f"💼 Новый статус: Безработный\n\n"
            f"ℹ️ Для возврата в штат нужно подать новую заявку."
        )

        await update.message.reply_text(response)
    except Exception as e:
        logger.error(f"Ошибка в увольнении: {e}")
        logger.error(traceback.format_exc())

async def handle_vacation_approve(update: Update):
    """Обработка команды отпуск одобрить"""
    try:
        if update.effective_user.id != ADMIN_ID:
            return

        if not update.message.reply_to_message:
            return

        target_user = update.message.reply_to_message.from_user
        target_data = get_user(target_user.id)

        if not target_data:
            return

        pending_vacations = get_pending_vacations()
        user_vacation = None

        for vac in pending_vacations:
            if vac['user_id'] == target_user.id:
                user_vacation = vac
                break

        if not user_vacation:
            await update.message.reply_text("❌ У этого сотрудника нет активных заявлений на отпуск!")
            return

        if approve_vacation(user_vacation['id']):
            response = (
                f"✅ **ОТПУСК ОДОБРЕН!**\n\n"
                f"👤 Сотрудник: {target_data['nickname']}\n"
                f"📅 Дней: {user_vacation['days']}\n"
                f"📝 Причина: {user_vacation['reason']}\n\n"
                f"🏖️ Хорошего отдыха!"
            )
            await update.message.reply_text(response)
    except Exception as e:
        logger.error(f"Ошибка в одобрении отпуска: {e}")
        logger.error(traceback.format_exc())

async def handle_vacation_reject(update: Update, text: str):
    """Обработка команды отпуск отклонить"""
    try:
        if update.effective_user.id != ADMIN_ID:
            return

        if not update.message.reply_to_message:
            return

        target_user = update.message.reply_to_message.from_user
        target_data = get_user(target_user.id)

        if not target_data:
            return

        reason = text.replace("отпуск отклонить", "").strip()
        if not reason:
            await update.message.reply_text("❌ Укажите причину отклонения: отпуск отклонить <причина>")
            return

        pending_vacations = get_pending_vacations()
        user_vacation = None

        for vac in pending_vacations:
            if vac['user_id'] == target_user.id:
                user_vacation = vac
                break

        if not user_vacation:
            await update.message.reply_text("❌ У этого сотрудника нет активных заявлений на отпуск!")
            return

        if reject_vacation(user_vacation['id'], reason):
            response = (
                f"❌ **ОТПУСК ОТКЛОНЕН!**\n\n"
                f"👤 Сотрудник: {target_data['nickname']}\n"
                f"📝 Причина отказа: {reason}"
            )
            await update.message.reply_text(response)
    except Exception as e:
        logger.error(f"Ошибка в отклонении отпуска: {e}")
        logger.error(traceback.format_exc())

async def handle_take_money(update: Update, text: str):
    """Обработка команды забрать (ТОЛЬКО ДЛЯ АДМИНА)"""
    try:
        # Команда только для администратора
        if update.effective_user.id != ADMIN_ID:
            return

        if not update.message.reply_to_message:
            return

        target_user = update.message.reply_to_message.from_user
        target_data = get_user(target_user.id)
        current_user_data = get_user(update.effective_user.id)

        if not target_data or not current_user_data:
            return

        parts = text.split()
        if len(parts) < 2:
            await update.message.reply_text("❌ Используйте: забрать <сумма>")
            return

        amount = int(parts[1])

        if amount <= 0:
            await update.message.reply_text("❌ Сумма должна быть положительной!")
            return

        success, message = transfer_coins(target_user.id, update.effective_user.id, amount, "Забрать в группе (админ)")

        if success:
            tax = int(amount * P2P_TRANSFER_TAX)
            amount_after_tax = amount - tax

            response = (
                f"⬇️ **ДЕНЬГИ ЗАБРАНЫ!**\n\n"
                f"👤 От кого: {target_data['nickname']}\n"
                f"👤 Кому: {current_user_data['nickname']}\n"
                f"💰 Сумма: {amount} акойнов\n"
                f"💸 Комиссия: {tax} акойнов\n"
                f"💸 Получено: {amount_after_tax} акойнов"
            )
        else:
            response = f"❌ {message}"

        await update.message.reply_text(response)
    except ValueError:
        await update.message.reply_text("❌ Используйте: забрать <сумма>")
    except Exception as e:
        logger.error(f"Ошибка в забрать: {e}")
        logger.error(traceback.format_exc())

async def handle_give_money(update: Update, text: str):
    """Обработка команды выдать (ТОЛЬКО ДЛЯ АДМИНА)"""
    try:
        # Команда только для администратора
        if update.effective_user.id != ADMIN_ID:
            return

        if not update.message.reply_to_message:
            return

        target_user = update.message.reply_to_message.from_user
        target_data = get_user(target_user.id)
        current_user_data = get_user(update.effective_user.id)

        if not target_data or not current_user_data:
            return

        parts = text.split()
        if len(parts) < 2:
            await update.message.reply_text("❌ Используйте: выдать <сумма>")
            return

        amount = int(parts[1])

        if amount <= 0:
            await update.message.reply_text("❌ Сумма должна быть положительной!")
            return

        success, message = transfer_coins(update.effective_user.id, target_user.id, amount, "Выдать в группе (админ)")

        if success:
            tax = int(amount * P2P_TRANSFER_TAX)
            amount_after_tax = amount - tax

            response = (
                f"⬆️ **ДЕНЬГИ ВЫДАНЫ!**\n\n"
                f"👤 От кого: {current_user_data['nickname']}\n"
                f"👤 Кому: {target_data['nickname']}\n"
                f"💰 Сумма: {amount} акойнов\n"
                f"💸 Комиссия: {tax} акойнов\n"
                f"💸 Получено: {amount_after_tax} акойнов"
            )
        else:
            response = f"❌ {message}"

        await update.message.reply_text(response)
    except ValueError:
        await update.message.reply_text("❌ Используйте: выдать <сумма>")
    except Exception as e:
        logger.error(f"Ошибка в выдать: {e}")
        logger.error(traceback.format_exc())

async def handle_collect_taxes(update: Update):
    """Обработка команды собрать налоги"""
    try:
        if update.effective_user.id != ADMIN_ID:
            return

        total_collected = collect_taxes()

        response = (
            f"💰 **НАЛОГИ СОБРАНЫ!**\n\n"
            f"📊 **Собрано:** {total_collected} акойнов\n"
            f"📈 **Ставка:** 10% от баланса\n"
            f"🏦 **Поступило в бюджет клана**\n\n"
            f"💡 Средства будут использованы на развитие клана."
        )

        await update.message.reply_text(response)
    except Exception as e:
        logger.error(f"Ошибка в сборе налогов: {e}")
        logger.error(traceback.format_exc())

def setup_group_handlers(application):
    """Настройка обработчиков групповых команд"""
    application.add_handler(MessageHandler(
        filters.TEXT & (filters.ChatType.GROUP | filters.ChatType.SUPERGROUP),
        handle_group_message
    ))
