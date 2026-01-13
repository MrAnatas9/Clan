# Пакет обработчиков
from .common import setup_common_handlers
from .registration import setup_registration_handlers
from .profile import setup_profile_handlers
from .credits import setup_credit_handlers
from .transfers import setup_transfer_handlers
from .admin import setup_admin_handlers
from .tasks import setup_task_handlers
from .casino import setup_casino_handlers
from .rp_characters import setup_rp_handlers
from .vacations import setup_vacation_handlers
from .suggestions import setup_suggestion_handlers
from .group_commands import setup_group_handlers

__all__ = [
    'setup_common_handlers',
    'setup_registration_handlers',
    'setup_profile_handlers',
    'setup_credit_handlers',
    'setup_transfer_handlers',
    'setup_admin_handlers',
    'setup_task_handlers',
    'setup_casino_handlers',
    'setup_rp_handlers',
    'setup_vacation_handlers',
    'setup_suggestion_handlers',
    'setup_group_handlers'
]
