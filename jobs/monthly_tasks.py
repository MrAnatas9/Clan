import logging
from datetime import datetime
from telegram.ext import ContextTypes
from database import charge_debt_interest
from config import ADMIN_ID

logger = logging.getLogger(__name__)

async def charge_debt_interest_job(context: ContextTypes.DEFAULT_TYPE):
    """Ежемесячное начисление процентов по долгам (50%)"""
    users_with_debt = get_users_with_debt()
    
    if not users_with_debt:
        return
    
    for user in users_with_debt:
        try:
            old_debt = abs(user['coins'])
            charge_debt_interest()
            user_updated = get_user(user['user_id'])
            new_debt = abs(user_updated['coins'])
            
            await context.bot.send_message(
                user['user_id'],
                f"⚠️ **НАЧИСЛЕНИЕ ПРОЦЕНТОВ ПО ДОЛГУ**\n\n"
                f"Ваш предыдущий долг: {old_debt} акойнов\n"
                f"Процентная ставка: {int(DEBT_INTEREST_RATE * 100)}%\n"
                f"Начислено процентов: {new_debt - old_debt} акойнов\n"
                f"📈 **Общий долг теперь: {new_debt} акойнов**\n\n"
                f"Погасите долг, чтобы избежать дальнейших начислений!"
            )
        except Exception as e:
            logger.error(f"Ошибка при начислении процентов для {user['user_id']}: {e}")
    
    # Уведомляем администратора
    try:
        total_debt = sum(abs(user['coins']) for user in users_with_debt)
        await context.bot.send_message(
            ADMIN_ID,
            f"📊 **ЕЖЕМЕСЯЧНОЕ НАЧИСЛЕНИЕ ПРОЦЕНТОВ ПО ДОЛГАМ**\n\n"
            f"👤 **Затронуто пользователей:** {len(users_with_debt)}\n"
            f"💰 **Общий долг до начисления:** {sum(abs(user['coins']) for user in users_with_debt)} акойнов\n"
            f"📈 **Ставка:** {int(DEBT_INTEREST_RATE * 100)}%\n\n"
            f"✅ Начисление процентов завершено!"
        )
    except Exception as e:
        logger.error(f"Ошибка уведомления администратора: {e}")

def setup_monthly_jobs(job_queue):
    """Настройка ежемесячных задач"""
    if job_queue:
        # Ежемесячное начисление процентов по долгам (1-го числа каждого месяца в 00:00)
        job_queue.run_monthly(
            charge_debt_interest_job,
            datetime.time(hour=0, minute=0),
            day=1,
            name="monthly_debt_interest"
        )
        
        logger.info("✅ Ежемесячные задачи настроены")
    else:
        logger.warning("⚠️ Job queue не доступен, ежемесячные задачи не настроены")
