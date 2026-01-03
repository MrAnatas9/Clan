import os
import json
from datetime import datetime, timedelta
from supabase import create_client, Client
from config import *

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

JOBS_DETAILS = {
    "👑 Судья": {"category": "🏛️ Управление & Закон", "min_level": 1, "max_users": 2},
    "⚖️ Адвокат": {"category": "🏛️ Управление & Закон", "min_level": 1, "max_users": 4},
    "🔍 Следователь": {"category": "🏛️ Управление & Закон", "min_level": 1, "max_users": 2},
    "🕊️ Дипломат": {"category": "🏛️ Управление & Закон", "min_level": 1, "max_users": 2},
    "📜 Архивариус": {"category": "🏛️ Управление & Закон", "min_level": 1, "max_users": 2},
    "🛡️ Офицер Безопасности": {"category": "🏛️ Управление & Закон", "min_level": 1, "max_users": 2},
    "🎥 Ютубер": {"category": "📢 Медиа & Творчество", "min_level": 1, "max_users": 2},
    "📰 Журналист": {"category": "📢 Медиа & Творчество", "min_level": 1, "max_users": 3},
    "✍️ Писатель": {"category": "📢 Медиа & Творчество", "min_level": 1, "max_users": 5},
    "🎨 Художник": {"category": "📢 Медиа & Творчество", "min_level": 1, "max_users": 4},
    "📢 Рекламист": {"category": "📢 Медиа & Творчество", "min_level": 1, "max_users": 3},
    "🎙️ Ведущий": {"category": "📢 Медиа & Творчество", "min_level": 1, "max_users": 3},
    "📱 SMM-менеджер": {"category": "📢 Медиа & Творчество", "min_level": 1, "max_users": 2},
    "💻 Программист": {"category": "⚙️ Профессии & Разработка", "min_level": 1, "max_users": 3},
    "🔨 Мастер": {"category": "⚙️ Профессии & Разработка", "min_level": 1, "max_users": 3},
    "🎬 Монтажёр": {"category": "⚙️ Профессии & Разработка", "min_level": 1, "max_users": 2},
    "🏗️ Строитель": {"category": "⚙️ Профессии & Разработка", "min_level": 1, "max_users": 5},
    "📊 Оператор": {"category": "⚙️ Профессии & Разработка", "min_level": 1, "max_users": 2},
    "🎮 Тестировщик": {"category": "⚙️ Профессии & Разработка", "min_level": 1, "max_users": 2},
    "📐 Архитектор": {"category": "⚙️ Профессии & Разработка", "min_level": 1, "max_users": 3},
    "👁️ Куратор": {"category": "📚 Поддержка & Наставничество", "min_level": 1, "max_users": 5},
    "📖 Историк": {"category": "📚 Поддержка & Наставничество", "min_level": 1, "max_users": 2},
    "🧭 Гид": {"category": "📚 Поддержка & Наставничество", "min_level": 1, "max_users": 2},
    "🤝 Психолог": {"category": "📚 Поддержка & Наставничество", "min_level": 1, "max_users": 2},
    "🏹 Разведчик": {"category": "🎭 Оборона & Разведка", "min_level": 1, "max_users": 2}
}

def initialize_admin():
    admin_id = ADMIN_ID
    response = supabase.table('users').select('*').eq('user_id', admin_id).execute()
    if not response.data:
        admin_data = {
            'user_id': admin_id,
            'username': 'admin',
            'nickname': '👑 Глава Клана',
            'job': '👑 Глава Клана',
            'selected_jobs': ['👑 Глава Клана'],
            'coins': 999999,
            'level': 10,
            'exp': 0,
            'messages_sent': 0,
            'is_admin': True,
            'debt': 0
        }
        supabase.table('users').insert(admin_data).execute()

def save_user(user_id, username, nickname, selected_jobs):
    user_data = {
        'user_id': user_id,
        'username': username,
        'nickname': nickname,
        'job': selected_jobs[0] if selected_jobs else 'Безработный',
        'selected_jobs': selected_jobs,
        'coins': START_COINS,
        'level': 1,
        'exp': 0,
        'messages_sent': 0,
        'is_admin': False,
        'debt': 0
    }
    response = supabase.table('users').upsert(user_data).execute()
    return bool(response.data)

def get_user(user_id):
    response = supabase.table('users').select('*').eq('user_id', user_id).execute()
    return response.data[0] if response.data else None

def transfer_coins(from_user_id, to_user_id, amount, reason=""):
    from_user = get_user(from_user_id)
    to_user = get_user(to_user_id)
    
    if not from_user or not to_user:
        return False, "Пользователь не найден"
    
    if from_user['coins'] - amount < -MAX_DEBT:
        return False, f"Превышен лимит долга ({-MAX_DEBT} акойнов)"
    
    # Списание
    supabase.table('users').update({'coins': from_user['coins'] - amount}).eq('user_id', from_user_id).execute()
    
    # Зачисление
    supabase.table('users').update({'coins': to_user['coins'] + amount}).eq('user_id', to_user_id).execute()
    
    # Запись транзакции
    supabase.table('transactions').insert({
        'from_user_id': from_user_id,
        'to_user_id': to_user_id,
        'amount': amount,
        'reason': reason,
        'created_at': datetime.now().isoformat()
    }).execute()
    
    return True, f"Перевод {amount} акойнов успешен"

def take_coins_from_message(message_text, from_user_id, to_user_id=None):
    # Парсим команду "забрать 100" или "выдать @username 100"
    parts = message_text.split()
    
    if len(parts) < 2:
        return False, "Некорректная команда"
    
    # Если есть упоминание пользователя
    if parts[0] == "выдать" and len(parts) >= 3:
        try:
            amount = int(parts[-1])
            return transfer_coins(from_user_id, to_user_id, amount, "Перевод в группе")
        except:
            return False, "Некорректная сумма"
    
    # Если просто "забрать"
    elif parts[0] == "забрать":
        try:
            amount = int(parts[1])
            # Забрать у себя (добавить)
            user = get_user(from_user_id)
            new_balance = user['coins'] + amount
            supabase.table('users').update({'coins': new_balance}).eq('user_id', from_user_id).execute()
            return True, f"Добавлено {amount} акойнов"
        except:
            return False, "Некорректная сумма"
    
    return False, "Неизвестная команда"

def create_task(title, description, reward_coins, reward_exp, deadline_hours=72):
    deadline = datetime.now() + timedelta(hours=deadline_hours)
    task_data = {
        'title': title,
        'description': description,
        'reward_coins': reward_coins,
        'reward_exp': reward_exp,
        'status': 'active',
        'deadline': deadline.isoformat(),
        'assigned_to': None,
        'proof_photos': []
    }
    response = supabase.table('tasks').insert(task_data).execute()
    return response.data[0]['id'] if response.data else 0

def assign_task(task_id, user_id):
    task = get_task(task_id)
    if not task or task['status'] != 'active':
        return False, "Задание недоступно"
    
    if task['assigned_to']:
        return False, "Задание уже взято"
    
    deadline = datetime.fromisoformat(task['deadline'])
    if datetime.now() > deadline:
        return False, "Срок задания истек"
    
    supabase.table('tasks').update({
        'status': 'assigned',
        'assigned_to': user_id,
        'assigned_at': datetime.now().isoformat()
    }).eq('id', task_id).execute()
    
    # Уведомление админу
    user = get_user(user_id)
    supabase.table('notifications').insert({
        'user_id': ADMIN_ID,
        'type': 'task_assigned',
        'text': f"Пользователь {user['nickname']} взял задание '{task['title']}'",
        'data': {'task_id': task_id, 'user_id': user_id}
    }).execute()
    
    return True, "Задание успешно взято"

def submit_task_proof(task_id, user_id, photo_urls):
    task = get_task(task_id)
    if not task or task['assigned_to'] != user_id:
        return False, "Задание не найдено или не ваше"
    
    if task['status'] != 'assigned':
        return False, "Задание не в процессе выполнения"
    
    # Сохраняем фото
    supabase.table('tasks').update({
        'proof_photos': photo_urls,
        'status': 'proof_submitted',
        'proof_submitted_at': datetime.now().isoformat()
    }).eq('id', task_id).execute()
    
    # Уведомление админу
    user = get_user(user_id)
    supabase.table('notifications').insert({
        'user_id': ADMIN_ID,
        'type': 'task_proof',
        'text': f"Пользователь {user['nickname']} отправил proof задания '{task['title']}'",
        'data': {'task_id': task_id, 'user_id': user_id, 'photos': photo_urls}
    }).execute()
    
    return True, "Proof отправлен на проверку"

def approve_task(task_id):
    task = get_task(task_id)
    if not task or task['status'] != 'proof_submitted':
        return False, "Задание не на проверке"
    
    # Выдача награды
    user_id = task['assigned_to']
    user = get_user(user_id)
    
    # Добавляем акойны
    new_coins = user['coins'] + task['reward_coins']
    supabase.table('users').update({'coins': new_coins}).eq('user_id', user_id).execute()
    
    # Добавляем опыт
    add_exp(user_id, task['reward_exp'])
    
    # Обновляем статус
    supabase.table('tasks').update({
        'status': 'completed',
        'completed_at': datetime.now().isoformat()
    }).eq('id', task_id).execute()
    
    return True, f"Задание одобрено! Награда: {task['reward_coins']} акойнов + {task['reward_exp']} опыта"

def reject_task(task_id, reason):
    task = get_task(task_id)
    if not task or task['status'] != 'proof_submitted':
        return False, "Задание не на проверке"
    
    # Штраф за невыполнение
    user_id = task['assigned_to']
    penalty_coins = int(task['reward_coins'] * TASK_PENALTY_PERCENT)
    penalty_exp = TASK_FAIL_PENALTY_EXP
    
    user = get_user(user_id)
    new_coins = user['coins'] - penalty_coins
    supabase.table('users').update({
        'coins': new_coins,
        'exp': max(0, user['exp'] - penalty_exp)
    }).eq('user_id', user_id).execute()
    
    supabase.table('tasks').update({
        'status': 'rejected',
        'rejection_reason': reason,
        'rejected_at': datetime.now().isoformat()
    }).eq('id', task_id).execute()
    
    return True, f"Задание отклонено. Штраф: {penalty_coins} акойнов + {penalty_exp} опыта"

def check_task_deadlines():
    """Проверяет просроченные задания"""
    now = datetime.now()
    response = supabase.table('tasks').select('*').eq('status', 'assigned').execute()
    
    for task in response.data:
        deadline = datetime.fromisoformat(task['deadline'])
        if now > deadline:
            # Штраф за просрочку
            user_id = task['assigned_to']
            penalty_coins = int(task['reward_coins'] * TASK_PENALTY_PERCENT)
            
            user = get_user(user_id)
            new_coins = user['coins'] - penalty_coins
            supabase.table('users').update({'coins': new_coins}).eq('user_id', user_id).execute()
            
            supabase.table('tasks').update({
                'status': 'expired',
                'expired_at': now.isoformat()
            }).eq('id', task['id']).execute()
    
    return True

def get_task(task_id):
    response = supabase.table('tasks').select('*').eq('id', task_id).execute()
    return response.data[0] if response.data else None

def get_active_tasks():
    response = supabase.table('tasks').select('*').in_('status', ['active', 'assigned']).execute()
    return response.data if response.data else []

def add_exp(user_id, amount):
    user = get_user(user_id)
    if not user:
        return None, None
    
    new_exp = user['exp'] + amount
    exp_needed = user['level'] * EXP_PER_LEVEL
    new_level = user['level']
    leveled_up = False
    
    while new_exp >= exp_needed:
        new_level += 1
        new_exp -= exp_needed
        exp_needed = new_level * EXP_PER_LEVEL
        leveled_up = True
    
    supabase.table('users').update({
        'exp': new_exp,
        'level': new_level
    }).eq('user_id', user_id).execute()
    
    return leveled_up, new_level

def get_all_users():
    response = supabase.table('users').select('*').eq('is_admin', False).execute()
    return response.data if response.data else []

def get_jobs_by_category(category):
    return {k: v for k, v in JOBS_DETAILS.items() if v['category'] == category}

def get_categories():
    return list(set([v['category'] for v in JOBS_DETAILS.values()]))

def get_users_count_by_job(job_name):
    response = supabase.table('users').select('*').execute()
    count = 0
    for user in response.data:
        if job_name in user.get('selected_jobs', []):
            count += 1
    return count

def is_job_available(job_name):
    if job_name not in JOBS_DETAILS:
        return False
    max_users = JOBS_DETAILS[job_name]['max_users']
    current_users = get_users_count_by_job(job_name)
    return current_users < max_users

# Создаем необходимые таблицы при первом запуске
def create_tables_if_not_exists():
    tables = ['users', 'tasks', 'transactions', 'notifications']
    for table in tables:
        try:
            supabase.table(table).select('*').limit(1).execute()
        except:
            print(f"Таблица {table} не существует, создайте в Supabase")

create_tables_if_not_exists()
initialize_admin()
