from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import NotFound

from ..exceptions.exception import UserNotFoundError


def get_user_by_id(user_id: int):
    user_model = get_user_model()

    try:
        return user_model.objects.get(pk=user_id)
    except user_model.DoesNotExist:
        raise UserNotFoundError
