import json
import logging
import random
from typing import Any
from typing import TYPE_CHECKING

from django.core.cache import cache
from django.db import transaction
from django_redis import get_redis_connection
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.dal.user_dal import UserDAL
from apps.accounts.models.custom_user import CustomUser
from apps.accounts.tasks import send_verification_code_email_task
from apps.shared.exceptions.user_exceptions import UserAuthenticationError
from apps.shared.exceptions.user_exceptions import UserValidationError

if TYPE_CHECKING:
    from redis import Redis

logger = logging.getLogger(__name__)


class PasswordlessService:
    def __init__(self, user_dal=None, redis_client=None):
        self.user_dal = user_dal or UserDAL()
        self._redis: Redis = redis_client or get_redis_connection('default')

    def request_verification_code(self, email: str) -> dict:
        pass

    def _generate_code(self) -> str:
        return str(random.randint(100000, 999999))

    def rate_limited(self, email: str) -> float:
        pass

    def verify_code_and_authenticate(self, email: str, user_code: str) -> dict:
        pass
