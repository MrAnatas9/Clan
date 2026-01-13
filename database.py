import requests
import json
import random
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from config import *

class SupabaseDB:
    def __init__(self):
        self.url = SUPABASE_URL.rstrip('/')
        self.headers = {
            'apikey': SUPABASE_KEY,
            'Authorization': f'Bearer {SUPABASE_KEY}',
            'Content-Type': 'application/json',
            'Prefer': 'return=representation'
        }

    def _request(self, method: str, endpoint: str, data=None, params=None):
        url = f"{self.url}/rest/v1/{endpoint}"
        try:
            response = None
            if method == 'GET':
                response = requests.get(url, headers=self.headers, params=params)
            elif method == 'POST':
                response = requests.post(url, headers=self.headers, json=data)
            elif method == 'PATCH':
                response = requests.patch(url, headers=self.headers, json=data, params=params)
            elif method == 'DELETE':
                response = requests.delete(url, headers=self.headers, params=params)
            else:
                return {'error': f'Unknown method: {method}'}

            if response.status_code in [200, 201, 204]:
                try:
                    return response.json() if response.text else {'success': True}
                except:
                    return {'success': True} if response.status_code in [201, 204] else {}
            else:
                error_text = response.text[:200] if hasattr(response, 'text') else str(response)
                print(f"Supabase error {response.status_code} for {endpoint}: {error_text}")
                return {'error': f'HTTP {response.status_code}'}
        except Exception as e:
            print(f"Supabase request error for {endpoint}: {e}")
            return {'error': str(e)}

    def select(self, table: str, filters: Dict[str, Any] = None, limit: int = 100, order: str = None) -> List[Dict]:
        try:
            params = {}
            if filters:
                for key, value in filters.items():
                    if value is not None:
                        params[key] = f'eq.{value}'
            if limit:
                params['limit'] = str(limit)
            if order:
                params['order'] = order

            result = self._request('GET', table, params=params)
            if isinstance(result, dict) and 'error' in result:
                print(f"Select error from {table}: {result['error']}")
                return []
            return result if isinstance(result, list) else []
        except Exception as e:
            print(f"Select error from {table}: {e}")
            return []

    def insert(self, table: str, data: Dict[str, Any]) -> Dict:
        try:
            result = self._request('POST', table, data=data)
            if isinstance(result, list) and len(result) > 0:
                return result[0]
            elif isinstance(result, dict):
                return result
            else:
                return {}
        except Exception as e:
            print(f"Insert error to {table}: {e}")
            return {'error': str(e)}

    def update(self, table: str, filters: Dict[str, Any], data: Dict[str, Any]) -> Dict:
        try:
            params = {}
            if filters:
                for key, value in filters.items():
                    if value is not None:
                        params[key] = f'eq.{value}'

            result = self._request('PATCH', table, data=data, params=params)
            if isinstance(result, dict):
                return result
            return {'success': True}
        except Exception as e:
            print(f"Update error in {table}: {e}")
            return {'error': str(e)}

    def delete(self, table: str, filters: Dict[str, Any]) -> bool:
        try:
            params = {}
            if filters:
                for key, value in filters.items():
                    if value is not None:
                        params[key] = f'eq.{value}'

            result = self._request('DELETE', table, params=params)
            return not isinstance(result, dict) or 'error' not in result
        except Exception as e:
            print(f"Delete error from {table}: {e}")
            return False

# Инициализация базы данных
db = SupabaseDB()

# ========== РАБОТЫ ==========
JOBS_DETAILS = {
    # 🏛️ Управление & Закон
    "👑 Судья": {"category": "🏛️ Управление & Закон", "max_users": 2, "salary": 100},
    "⚖️ Адвокат": {"category": "🏛️ Управление & Закон", "max_users": 4, "salary": 80},
    "🔍 Следователь": {"category": "🏛️ Управление & Закон", "max_users": 2, "salary": 70},
    "🕊️ Дипломат": {"category": "🏛️ Управление & Закон", "max_users": 2, "salary": 75},
    "📜 Архивариус": {"category": "🏛️ Управление & Закон", "max_users": 2, "salary": 60},
    "🛡️ Офицер Безопасности": {"category": "🏛️ Управление & Закон", "max_users": 2, "salary": 85},

    # 📢 Медиа & Творчество
    "🎥 Ютубер": {"category": "📢 Медиа & Творчество", "max_users": 2, "salary": 90},
    "📰 СМИ (Журналист)": {"category": "📢 Медиа & Творчество", "max_users": 3, "salary": 65},
    "✍️ Писатель": {"category": "📢 Медиа & Творчество", "max_users": 5, "salary": 55},
    "🎨 Художник": {"category": "📢 Медиа & Творчество", "max_users": 4, "salary": 60},
    "📢 Рекламист": {"category": "📢 Медиа & Творчество", "max_users": 3, "salary": 70},
    "🎙️ Ведущий": {"category": "📢 Медиа & Творчество", "max_users": 3, "salary": 75},
    "📱 SMM-менеджер": {"category": "📢 Медиа & Творчество", "max_users": 2, "salary": 80},

    # ⚙️ Профессии & Разработка
    "💻 Программист": {"category": "⚙️ Профессии & Разработка", "max_users": 3, "salary": 95},
    "🔨 Мастер": {"category": "⚙️ Профессии & Разработка", "max_users": 3, "salary": 70},  # ИСПРАВЛЕНО: одинаковая категория
    "🎬 Монтажёр": {"category": "⚙️ Профессии & Разработка", "max_users": 2, "salary": 75},
    "🏗️ Строитель": {"category": "⚙️ Профессии & Разработка", "max_users": 5, "salary": 65},
    "📊 Оператор": {"category": "⚙️ Профессии & Разработка", "max_users": 2, "salary": 70},
    "🎮 Тестировщик": {"category": "⚙️ Профессии & Разработка", "max_users": 2, "salary": 60},
    "📐 Архитектор": {"category": "⚙️ Профессии & Разработка", "max_users": 3, "salary": 85},

    # 📚 Поддержка & Наставничество
    "👁️ Куратор": {"category": "📚 Поддержка & Наставничество", "max_users": 5, "salary": 60},
    "📖 Историк": {"category": "📚 Поддержка & Наставничество", "max_users": 2, "salary": 55},
    "🧭 Гид": {"category": "📚 Поддержка & Наставничество", "max_users": 2, "salary": 65},
    "🤝 Психолог": {"category": "📚 Поддержка & Наставничество", "max_users": 2, "salary": 75},
    
    # 🎭 Оборона & Разведка
    "🏹 Разведчик": {"category": "🎭 Оборона & Разведка", "max_users": 2, "salary": 85},
}

def get_categories() -> List[str]:
    """Возвращает список уникальных категорий работ"""
    categories = set()
    for job_details in JOBS_DETAILS.values():
        categories.add(job_details['category'])
    return sorted(list(categories))

def get_jobs_by_category(category: str) -> Dict[str, Dict]:
    """Возвращает работы определенной категории"""
    return {name: details for name, details in JOBS_DETAILS.items()
            if details['category'] == category}

def get_users_count_by_job(job_name: str) -> int:
    """Считает сколько пользователей выбрало определенную работу"""
    users = get_all_users()
    count = 0
    for user in users:
        if job_name in user.get('selected_jobs', []):
            count += 1
    return count

def is_job_available(job_name: str) -> bool:
    """Проверяет доступна ли работа (не достигнут лимит)"""
    if job_name not in JOBS_DETAILS:
        return False
    current_count = get_users_count_by_job(job_name)
    return current_count < JOBS_DETAILS[job_name]['max_users']

# ========== ПОЛЬЗОВАТЕЛИ ==========
def save_user(user_data: Dict[str, Any]) -> bool:
    try:
        user_id = user_data['user_id']
        result = db.insert('users', user_data)
        return not isinstance(result, dict) or 'error' not in result
    except Exception as e:
        print(f"Error saving user: {e}")
        return False

def get_user(user_id: int) -> Optional[Dict]:
    try:
        users = db.select('users', {'user_id': user_id}, limit=1)
        if users:
            user = users[0]
            # Обрабатываем JSON поля
            for field in ['selected_jobs', 'jobs']:
                if field in user and isinstance(user[field], str):
                    try:
                        user[field] = json.loads(user[field])
                    except:
                        user[field] = []
                elif field not in user:
                    user[field] = []
            
            # Убеждаемся, что есть обязательные поля
            user.setdefault('coins', 0)
            user.setdefault('level', 1)
            user.setdefault('exp', 0)
            user.setdefault('job', 'Безработный')
            user.setdefault('nickname', f'User_{user_id}')
            user.setdefault('is_banned', False)
            
            return user
        return None
    except Exception as e:
        print(f"Error getting user {user_id}: {e}")
        return None

def get_all_users() -> List[Dict]:
    try:
        users = db.select('users', limit=500)
        for user in users:
            # Обрабатываем JSON поля
            for field in ['selected_jobs', 'jobs']:
                if field in user and isinstance(user[field], str):
                    try:
                        user[field] = json.loads(user[field])
                    except:
                        user[field] = []
                elif field not in user:
                    user[field] = []
            
            # Убеждаемся, что есть обязательные поля
            user.setdefault('coins', 0)
            user.setdefault('level', 1)
            user.setdefault('exp', 0)
            user.setdefault('job', 'Безработный')
            user.setdefault('nickname', f'User_{user["user_id"]}')
            user.setdefault('is_banned', False)
                
        return users
    except Exception as e:
        print(f"Error getting all users: {e}")
        return []

def get_users_with_debt() -> List[Dict]:
    users = get_all_users()
    return [u for u in users if u.get('coins', 0) < 0 and u['user_id'] != ADMIN_ID]

def get_top_rich_users(limit: int = 5) -> List[Dict]:
    users = get_all_users()
    sorted_users = sorted(users, key=lambda x: x.get('coins', 0), reverse=True)
    return [u for u in sorted_users if u['user_id'] != ADMIN_ID][:limit]

def get_top_debtors(limit: int = 5) -> List[Dict]:
    users = get_all_users()
    debtors = [u for u in users if u.get('coins', 0) < 0 and u['user_id'] != ADMIN_ID]
    sorted_debtors = sorted(debtors, key=lambda x: abs(x.get('coins', 0)), reverse=True)
    return sorted_debtors[:limit]

def add_user_coins(user_id: int, amount: int) -> bool:
    try:
        user = get_user(user_id)
        if not user:
            return False
            
        new_balance = user.get('coins', 0) + amount
        
        result = db.update('users', {'user_id': user_id}, {'coins': new_balance})
        return not isinstance(result, dict) or 'error' not in result
    except Exception as e:
        print(f"Error adding coins to user {user_id}: {e}")
        return False

def update_user_jobs(user_id: int, jobs: List[str]) -> bool:
    try:
        result = db.update('users', {'user_id': user_id}, {
            'jobs': json.dumps(jobs) if jobs else '[]',
            'job': jobs[0] if jobs else 'Безработный'
        })
        return not isinstance(result, dict) or 'error' not in result
    except Exception as e:
        print(f"Error updating user jobs: {e}")
        return False

def ban_user(user_id: int, reason: str) -> bool:
    try:
        result = db.update('users', {'user_id': user_id}, {
            'is_banned': True,
            'ban_reason': reason
        })
        return not isinstance(result, dict) or 'error' not in result
    except Exception as e:
        print(f"Error banning user: {e}")
        return False

def unban_user(user_id: int) -> bool:
    try:
        result = db.update('users', {'user_id': user_id}, {
            'is_banned': False,
            'ban_reason': ''
        })
        return not isinstance(result, dict) or 'error' not in result
    except Exception as e:
        print(f"Error unbanning user: {e}")
        return False

def search_users_by_nickname(search_term: str) -> List[Dict]:
    try:
        users = get_all_users()
        search_term = search_term.lower()
        result = []
        for user in users:
            if search_term in user.get('nickname', '').lower():
                result.append(user)
        return result
    except Exception as e:
        print(f"Error searching users: {e}")
        return []

# ========== ЗАЯВКИ НА РЕГИСТРАЦИЮ ==========
def create_application(user_id: int, username: str, nickname: str, source: str, jobs: List[str]) -> int:
    try:
        app_data = {
            'user_id': user_id,
            'username': username or '',
            'nickname': nickname,
            'source': source,
            'jobs': json.dumps(jobs) if jobs else '[]',
            'status': 'pending',
            'created_at': datetime.now().isoformat()
        }

        result = db.insert('applications', app_data)
        if isinstance(result, dict) and 'id' in result:
            return result['id']
        return 0
    except Exception as e:
        print(f"Error creating application: {e}")
        return 0

def get_application(app_id: int) -> Optional[Dict]:
    try:
        apps = db.select('applications', {'id': app_id}, limit=1)
        if apps:
            app = apps[0]
            if 'jobs' in app and isinstance(app['jobs'], str):
                try:
                    app['jobs'] = json.loads(app['jobs'])
                except:
                    app['jobs'] = []
            return app
        return None
    except Exception as e:
        print(f"Error getting application: {e}")
        return None

def get_pending_applications() -> List[Dict]:
    try:
        apps = db.select('applications', {'status': 'pending'})
        for app in apps:
            if 'jobs' in app and isinstance(app['jobs'], str):
                try:
                    app['jobs'] = json.loads(app['jobs'])
                except:
                    app['jobs'] = []
        return apps
    except Exception as e:
        print(f"Error getting pending applications: {e}")
        return []

def approve_application(app_id: int) -> bool:
    try:
        app = get_application(app_id)
        if not app:
            return False

        user_data = {
            'user_id': app['user_id'],
            'username': app.get('username', ''),
            'nickname': app['nickname'],
            'coins': START_COINS,
            'level': START_LEVEL,
            'exp': START_EXP,
            'job': app['jobs'][0] if app['jobs'] else 'Безработный',
            'selected_jobs': json.dumps(app['jobs']),
            'registration_date': datetime.now().isoformat()
        }

        result = db.insert('users', user_data)
        if isinstance(result, dict) and 'error' in result:
            return False

        db.update('applications', {'id': app_id}, {'status': 'approved', 'approved_at': datetime.now().isoformat()})
        return True
    except Exception as e:
        print(f"Error approving application: {e}")
        return False

def reject_application(app_id: int, reason: str) -> bool:
    try:
        result = db.update('applications', {'id': app_id}, {
            'status': 'rejected',
            'rejection_reason': reason,
            'rejected_at': datetime.now().isoformat()
        })
        return not isinstance(result, dict) or 'error' not in result
    except Exception as e:
        print(f"Error rejecting application: {e}")
        return False

# ========== КРЕДИТЫ ==========
def create_credit_request(borrower_id: int, amount: int, reason: str) -> Tuple[bool, str, int]:
    try:
        borrower = get_user(borrower_id)
        if not borrower:
            return False, "Пользователь не найден", 0

        if borrower.get('is_banned', False):
            return False, "Вы забанены", 0

        if amount < MIN_CREDIT_AMOUNT or amount > MAX_CREDIT_AMOUNT:
            return False, f"Сумма должна быть от {MIN_CREDIT_AMOUNT} до {MAX_CREDIT_AMOUNT}", 0

        total_to_pay = int(amount * CLAN_CREDIT_RATE)

        credit_data = {
            'borrower_id': borrower_id,
            'lender_id': ADMIN_ID,
            'amount': amount,
            'total_to_pay': total_to_pay,
            'paid_amount': 0,
            'reason': reason,
            'status': 'pending',
            'created_at': datetime.now().isoformat()
        }

        result = db.insert('credits', credit_data)
        if isinstance(result, dict) and 'id' in result:
            return True, f"Заявка на кредит #{result['id']} создана", result['id']
        return False, "Ошибка создания заявки", 0
    except Exception as e:
        return False, f"Ошибка: {str(e)}", 0

def get_credit(credit_id: int) -> Optional[Dict]:
    try:
        credits = db.select('credits', {'id': credit_id}, limit=1)
        if credits:
            credit = credits[0]
            # Убеждаемся, что есть обязательные поля
            credit.setdefault('paid_amount', 0)
            return credit
        return None
    except Exception as e:
        print(f"Error getting credit: {e}")
        return None

def get_pending_credits() -> List[Dict]:
    return db.select('credits', {'status': 'pending'})

def get_active_credits(user_id: int = None) -> List[Dict]:
    if user_id:
        return db.select('credits', {'borrower_id': user_id, 'status': 'active'})
    return db.select('credits', {'status': 'active'})

def approve_credit(credit_id: int) -> Tuple[bool, str]:
    try:
        credit = get_credit(credit_id)
        if not credit:
            return False, "Кредит не найден"

        if not add_user_coins(credit['borrower_id'], credit['amount']):
            return False, "Ошибка выдачи денег"

        result = db.update('credits', {'id': credit_id}, {
            'status': 'active',
            'approved_at': datetime.now().isoformat()
        })
        
        if isinstance(result, dict) and 'error' in result:
            return False, "Ошибка обновления статуса"
            
        return True, "Кредит одобрен"
    except Exception as e:
        return False, f"Ошибка: {str(e)}"

def reject_credit(credit_id: int, reason: str = "") -> bool:
    try:
        result = db.update('credits', {'id': credit_id}, {
            'status': 'rejected',
            'rejection_reason': reason,
            'rejected_at': datetime.now().isoformat()
        })
        return not isinstance(result, dict) or 'error' not in result
    except Exception as e:
        print(f"Error rejecting credit: {e}")
        return False

def pay_credit(credit_id: int, amount: int) -> Tuple[bool, str]:
    try:
        credit = get_credit(credit_id)
        if not credit:
            return False, "Кредит не найден"

        borrower = get_user(credit['borrower_id'])
        if not borrower:
            return False, "Пользователь не найден"

        if amount <= 0:
            return False, "Сумма должна быть больше 0"

        if borrower['coins'] < amount:
            return False, "Недостаточно средств"

        # Забираем деньги у пользователя
        add_user_coins(credit['borrower_id'], -amount)

        # Добавляем администратору
        add_user_coins(ADMIN_ID, amount)

        new_paid = credit.get('paid_amount', 0) + amount

        if new_paid >= credit['total_to_pay']:
            # Кредит полностью погашен
            db.update('credits', {'id': credit_id}, {
                'paid_amount': new_paid,
                'status': 'completed',
                'completed_at': datetime.now().isoformat()
            })
            return True, f"✅ Кредит полностью погашен! Сумма: {amount} акойнов"
        else:
            # Частичное погашение
            db.update('credits', {'id': credit_id}, {
                'paid_amount': new_paid
            })
            return True, f"✅ Внесена сумма: {amount} акойнов. Осталось: {credit['total_to_pay'] - new_paid} акойнов"
            
    except Exception as e:
        return False, f"Ошибка: {str(e)}"

# ========== ПЕРЕВОДЫ ==========
def transfer_coins(from_user_id: int, to_user_id: int, amount: int, reason: str) -> Tuple[bool, str]:
    try:
        from_user = get_user(from_user_id)
        to_user = get_user(to_user_id)

        if not from_user or not to_user:
            return False, "Пользователь не найден"

        if from_user['coins'] < amount:
            return False, "Недостаточно средств"

        # Вычитаем комиссию
        tax = int(amount * P2P_TRANSFER_TAX)
        amount_after_tax = amount - tax

        # Снимаем деньги у отправителя
        if not add_user_coins(from_user_id, -amount):
            return False, "Ошибка списания"

        # Добавляем деньги получателю
        if not add_user_coins(to_user_id, amount_after_tax):
            # Откатываем транзакцию
            add_user_coins(from_user_id, amount)
            return False, "Ошибка зачисления"

        # Добавляем комиссию администратору
        add_user_coins(ADMIN_ID, tax)

        # Логируем транзакцию
        db.insert('transactions', {
            'from_user_id': from_user_id,
            'to_user_id': to_user_id,
            'amount': amount_after_tax,
            'tax': tax,
            'reason': reason,
            'created_at': datetime.now().isoformat()
        })

        return True, f"Перевод {amount_after_tax} акойнов (+{tax} комиссия) выполнен"
    except Exception as e:
        return False, f"Ошибка: {str(e)}"

# ========== ЗАДАНИЯ ==========
def create_task(title: str, description: str, reward_coins: int, reward_exp: int, deadline: str) -> int:
    try:
        task_data = {
            'title': title,
            'description': description,
            'reward_coins': reward_coins,
            'reward_exp': reward_exp,
            'deadline': deadline,
            'status': 'active',
            'created_at': datetime.now().isoformat()
        }

        result = db.insert('tasks', task_data)
        if isinstance(result, dict) and 'id' in result:
            return result['id']
        return 0
    except Exception as e:
        print(f"Error creating task: {e}")
        return 0

def get_task(task_id: int) -> Optional[Dict]:
    tasks = db.select('tasks', {'id': task_id}, limit=1)
    return tasks[0] if tasks else None

def get_active_tasks() -> List[Dict]:
    return db.select('tasks', {'status': 'active'})

def get_pending_tasks() -> List[Dict]:
    return db.select('tasks', {'status': 'pending'})

def approve_task(task_id: int) -> bool:
    try:
        result = db.update('tasks', {'id': task_id}, {
            'status': 'approved',
            'approved_at': datetime.now().isoformat()
        })
        return not isinstance(result, dict) or 'error' not in result
    except Exception as e:
        print(f"Error approving task: {e}")
        return False

def complete_task(user_id: int, task_id: int, proof: str = "") -> Tuple[bool, str]:
    try:
        task = get_task(task_id)
        if not task:
            return False, "Задание не найдено"

        completion_data = {
            'user_id': user_id,
            'task_id': task_id,
            'proof': proof,
            'status': 'pending',
            'completed_at': datetime.now().isoformat()
        }

        result = db.insert('task_completions', completion_data)
        if isinstance(result, dict) and 'error' in result:
            return False, "Ошибка сохранения"

        return True, f"✅ Задание выполнено и отправлено на проверку!"
    except Exception as e:
        return False, f"Ошибка: {str(e)}"

def get_task_completions(task_id: int) -> List[Dict]:
    return db.select('task_completions', {'task_id': task_id})

def approve_task_completion(completion_id: int) -> bool:
    try:
        completions = db.select('task_completions', {'id': completion_id}, limit=1)
        if not completions:
            return False

        completion = completions[0]
        task = get_task(completion['task_id'])
        if not task:
            return False

        # Выдаем награду
        add_user_coins(completion['user_id'], task['reward_coins'])

        # Обновляем статус
        db.update('task_completions', {'id': completion_id}, {
            'status': 'approved',
            'approved_at': datetime.now().isoformat()
        })

        db.update('tasks', {'id': task['id']}, {
            'status': 'completed',
            'completed_at': datetime.now().isoformat()
        })

        return True
    except Exception as e:
        print(f"Error approving task completion: {e}")
        return False

# ========== РП ПЕРСОНАЖИ ==========
def create_rp_character(user_id: int, name: str, abilities: str, weaknesses: str, items: str, bio: str) -> int:
    try:
        char_data = {
            'user_id': user_id,
            'name': name,
            'abilities': abilities,
            'weaknesses': weaknesses,
            'items': items,
            'bio': bio,
            'status': 'pending',
            'price': 0,
            'for_sale': False,
            'created_at': datetime.now().isoformat()
        }

        result = db.insert('rp_characters', char_data)
        if isinstance(result, dict) and 'id' in result:
            return result['id']
        return 0
    except Exception as e:
        print(f"Error creating RP character: {e}")
        return 0

def get_rp_character(user_id: int) -> Optional[Dict]:
    try:
        chars = db.select('rp_characters', {'user_id': user_id}, limit=1)
        return chars[0] if chars else None
    except Exception as e:
        print(f"Error getting RP character: {e}")
        return None

def get_pending_rp_characters() -> List[Dict]:
    try:
        return db.select('rp_characters', {'status': 'pending'})
    except Exception as e:
        print(f"Error getting pending RP characters: {e}")
        return []

def approve_rp_character(character_id: int, price: int = 0) -> bool:
    try:
        if price < RP_CHARACTER_MIN_PRICE or price > RP_CHARACTER_MAX_PRICE:
            return False

        result = db.update('rp_characters', {'id': character_id}, {
            'status': 'approved',
            'price': price,
            'approved_at': datetime.now().isoformat()
        })
        return not isinstance(result, dict) or 'error' not in result
    except Exception as e:
        print(f"Error approving RP character: {e}")
        return False

def reject_rp_character(character_id: int, reason: str = "") -> bool:
    try:
        result = db.update('rp_characters', {'id': character_id}, {
            'status': 'rejected',
            'rejection_reason': reason,
            'rejected_at': datetime.now().isoformat()
        })
        return not isinstance(result, dict) or 'error' not in result
    except Exception as e:
        print(f"Error rejecting RP character: {e}")
        return False

def set_character_for_sale(character_id: int, price: int) -> bool:
    try:
        if price < RP_CHARACTER_MIN_PRICE or price > RP_CHARACTER_MAX_PRICE:
            return False

        result = db.update('rp_characters', {'id': character_id}, {
            'for_sale': True,
            'price': price
        })
        return not isinstance(result, dict) or 'error' not in result
    except Exception as e:
        print(f"Error setting character for sale: {e}")
        return False

def buy_character(buyer_id: int, character_id: int) -> Tuple[bool, str]:
    try:
        chars = db.select('rp_characters', {'id': character_id, 'for_sale': True}, limit=1)
        if not chars:
            return False, "Персонаж не найден или не продается"

        character = chars[0]
        buyer = get_user(buyer_id)

        if not buyer:
            return False, "Покупатель не найден"

        if buyer['coins'] < character['price']:
            return False, "Недостаточно средств"

        # Снимаем деньги у покупателя
        add_user_coins(buyer_id, -character['price'])

        # Даем деньги продавцу
        add_user_coins(character['user_id'], character['price'])

        # Архивируем старого владельца
        archived_char = character.copy()
        archived_char['archived_at'] = datetime.now().isoformat()
        archived_char['archive_reason'] = 'sold_to_player'
        db.insert('archived_characters', archived_char)

        # Меняем владельца
        db.update('rp_characters', {'id': character_id}, {
            'user_id': buyer_id,
            'for_sale': False,
            'sold_at': datetime.now().isoformat()
        })

        # Логируем транзакцию
        db.insert('transactions', {
            'from_user_id': buyer_id,
            'to_user_id': character['user_id'],
            'amount': character['price'],
            'reason': f"Покупка РП персонажа '{character['name']}'",
            'created_at': datetime.now().isoformat()
        })

        return True, "Персонаж успешно куплен!"
    except Exception as e:
        return False, f"Ошибка: {str(e)}"

def sell_character_to_clan(character_id: int) -> Tuple[bool, str]:
    try:
        chars = db.select('rp_characters', {'id': character_id}, limit=1)
        if not chars:
            return False, "Персонаж не найден"

        character = chars[0]

        # Вычисляем 30% от цены
        clan_price = int(character['price'] * RP_SALE_TO_CLAN_RATE)

        # Выдаем деньги продавцу
        if not add_user_coins(character['user_id'], clan_price):
            return False, "Ошибка выдачи денег"

        # Архивируем персонажа
        archived_char = character.copy()
        archived_char['archived_at'] = datetime.now().isoformat()
        archived_char['archive_reason'] = 'sold_to_clan'
        archived_char['sale_price'] = clan_price
        db.insert('archived_characters', archived_char)

        # Удаляем из активных
        db.delete('rp_characters', {'id': character_id})

        # Логируем транзакцию
        db.insert('transactions', {
            'from_user_id': 0,
            'to_user_id': character['user_id'],
            'amount': clan_price,
            'reason': f"Продажа РП персонажа '{character['name']}' клану (30%)",
            'created_at': datetime.now().isoformat()
        })

        return True, f"Персонаж продан клану за {clan_price} акойнов"
    except Exception as e:
        return False, f"Ошибка: {str(e)}"

# ========== ОТПУСКА ==========
def request_vacation(user_id: int, days: int, reason: str) -> int:
    try:
        vacation_data = {
            'user_id': user_id,
            'days': days,
            'reason': reason,
            'status': 'pending',
            'created_at': datetime.now().isoformat()
        }

        result = db.insert('vacations', vacation_data)
        if isinstance(result, dict) and 'id' in result:
            return result['id']
        return 0
    except Exception as e:
        print(f"Error creating vacation request: {e}")
        return 0

def get_vacation(vacation_id: int) -> Optional[Dict]:
    vacations = db.select('vacations', {'id': vacation_id}, limit=1)
    return vacations[0] if vacations else None

def get_pending_vacations() -> List[Dict]:
    return db.select('vacations', {'status': 'pending'})

def approve_vacation(vacation_id: int) -> bool:
    try:
        result = db.update('vacations', {'id': vacation_id}, {
            'status': 'approved',
            'approved_at': datetime.now().isoformat()
        })
        return not isinstance(result, dict) or 'error' not in result
    except Exception as e:
        print(f"Error approving vacation: {e}")
        return False

def reject_vacation(vacation_id: int, reason: str) -> bool:
    try:
        result = db.update('vacations', {'id': vacation_id}, {
            'status': 'rejected',
            'rejection_reason': reason,
            'rejected_at': datetime.now().isoformat()
        })
        return not isinstance(result, dict) or 'error' not in result
    except Exception as e:
        print(f"Error rejecting vacation: {e}")
        return False

# ========== ПРЕДЛОЖЕНИЯ ==========
def create_suggestion(user_id: int, suggestion: str) -> int:
    try:
        suggestion_data = {
            'user_id': user_id,
            'suggestion': suggestion,
            'status': 'pending',
            'created_at': datetime.now().isoformat()
        }

        result = db.insert('suggestions', suggestion_data)
        if isinstance(result, dict) and 'id' in result:
            return result['id']
        return 0
    except Exception as e:
        print(f"Error creating suggestion: {e}")
        return 0

def get_pending_suggestions() -> List[Dict]:
    return db.select('suggestions', {'status': 'pending'})

def approve_suggestion(suggestion_id: int) -> bool:
    try:
        result = db.update('suggestions', {'id': suggestion_id}, {
            'status': 'approved',
            'approved_at': datetime.now().isoformat()
        })
        return not isinstance(result, dict) or 'error' not in result
    except Exception as e:
        print(f"Error approving suggestion: {e}")
        return False

def reject_suggestion(suggestion_id: int, reason: str = "") -> bool:
    try:
        result = db.update('suggestions', {'id': suggestion_id}, {
            'status': 'rejected',
            'rejection_reason': reason,
            'rejected_at': datetime.now().isoformat()
        })
        return not isinstance(result, dict) or 'error' not in result
    except Exception as e:
        print(f"Error rejecting suggestion: {e}")
        return False

# ========== КВОТЫ ==========
def create_quota_report(user_id: int, work_done: str, events: str, rp_played: str, proof: str = "") -> int:
    try:
        quota_data = {
            'user_id': user_id,
            'work_done': work_done,
            'events': events,
            'rp_played': rp_played,
            'proof': proof,
            'status': 'pending',
            'created_at': datetime.now().isoformat()
        }

        result = db.insert('quota_reports', quota_data)
        if isinstance(result, dict) and 'id' in result:
            return result['id']
        return 0
    except Exception as e:
        print(f"Error creating quota report: {e}")
        return 0

# ========== СТАТИСТИКА ==========
def get_statistics() -> Dict[str, Any]:
    stats = {
        'total_users': 0,
        'total_coins': 0,
        'total_debt': 0,
        'pending_applications': 0,
        'pending_credits': 0,
        'pending_tasks': 0,
        'pending_rp_characters': 0,
        'pending_vacations': 0,
        'pending_suggestions': 0,
        'banned_users': 0
    }

    try:
        users = get_all_users()
        stats['total_users'] = len(users)

        for user in users:
            if user['user_id'] != ADMIN_ID:
                coins = user.get('coins', 0)
                stats['total_coins'] += coins
                if coins < 0:
                    stats['total_debt'] += abs(coins)

        pending_applications = get_pending_applications()
        stats['pending_applications'] = len(pending_applications)

        pending_credits = get_pending_credits()
        stats['pending_credits'] = len(pending_credits)

        pending_tasks = get_pending_tasks()
        stats['pending_tasks'] = len(pending_tasks)

        pending_rp = get_pending_rp_characters()
        stats['pending_rp_characters'] = len(pending_rp)

        pending_vacations = get_pending_vacations()
        stats['pending_vacations'] = len(pending_vacations)

        pending_suggestions = get_pending_suggestions()
        stats['pending_suggestions'] = len(pending_suggestions)

        banned_users = [u for u in users if u.get('is_banned', False)]
        stats['banned_users'] = len(banned_users)

        return stats
    except Exception as e:
        print(f"Error getting statistics: {e}")
        return stats

def calculate_weekly_taxes() -> int:
    users = get_all_users()
    total_collected = 0
    
    for user in users:
        if user['user_id'] != ADMIN_ID and not user.get('is_banned', False):
            coins = user.get('coins', 0)
            if coins > 0:
                tax = int(coins * 0.10)  # 10% налог
                if tax > 0:
                    total_collected += tax
    return total_collected

def collect_taxes() -> int:
    users = get_all_users()
    total_collected = 0
    
    for user in users:
        if user['user_id'] != ADMIN_ID and not user.get('is_banned', False):
            coins = user.get('coins', 0)
            if coins > 0:
                tax = int(coins * 0.10)  # 10% налог
                if tax > 0:
                    add_user_coins(user['user_id'], -tax)
                    add_user_coins(ADMIN_ID, tax)
                    total_collected += tax
    return total_collected

# ========== АРХИВ ==========
def archive_character(character_id: int, reason: str = "") -> bool:
    try:
        chars = db.select('rp_characters', {'id': character_id}, limit=1)
        if not chars:
            return False

        character = chars[0]
        archived_char = character.copy()
        archived_char['archived_at'] = datetime.now().isoformat()
        archived_char['archive_reason'] = reason

        db.insert('archived_characters', archived_char)
        db.delete('rp_characters', {'id': character_id})

        return True
    except Exception as e:
        print(f"Error archiving character: {e}")
        return False

def delete_user_completely(user_id: int) -> bool:
    try:
        if user_id == ADMIN_ID:
            return False

        # Архивируем персонажа если есть
        char = get_rp_character(user_id)
        if char and char.get('id'):
            archive_character(char.get('id'), 'user_deleted')

        # Удаляем все записи связанные с пользователем
        db.delete('users', {'user_id': user_id})
        db.delete('credits', {'borrower_id': user_id})
        db.delete('applications', {'user_id': user_id})
        db.delete('rp_characters', {'user_id': user_id})
        db.delete('vacations', {'user_id': user_id})
        db.delete('suggestions', {'user_id': user_id})

        return True
    except Exception as e:
        print(f"Error deleting user: {e}")
        return False

# ========== ИНИЦИАЛИЗАЦИЯ ==========
def initialize_database():
    try:
        print("🔄 Проверка соединения с Supabase...")
        # Проверяем соединение с простым запросом
        result = db.select('users', limit=1)
        print("✅ Соединение с Supabase установлено!")
        
        # Проверяем, есть ли администратор в базе
        admin = get_user(ADMIN_ID)
        if not admin:
            print("🔄 Создание администратора...")
            admin_data = {
                'user_id': ADMIN_ID,
                'username': 'admin',
                'nickname': '👑 Администратор',
                'coins': 10000,
                'level': 100,
                'exp': 10000,
                'job': '👑 Администратор',
                'selected_jobs': '["👑 Администратор"]',
                'registration_date': datetime.now().isoformat(),
                'is_banned': False
            }
            if save_user(admin_data):
                print("✅ Администратор создан!")
            else:
                print("⚠️ Не удалось создать администратора")
        
        return True
    except Exception as e:
        print(f"❌ Ошибка подключения к Supabase: {e}")
        return False