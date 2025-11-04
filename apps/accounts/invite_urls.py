"""
URL маршрути для API запрошень
"""

from django.urls import path

from apps.accounts.invite_views import create_invite
from apps.accounts.invite_views import current_user_info
from apps.accounts.invite_views import deactivate_invite
from apps.accounts.invite_views import generate_qr_for_invite
from apps.accounts.invite_views import list_event_invites
from apps.accounts.invite_views import use_invite
from apps.accounts.invite_views import validate_invite

app_name = 'invites'

urlpatterns = [
    # Створення та управління запрошеннями
    path('create/', create_invite, name='create_invite'),
    path('event/<uuid:event_uuid>/', list_event_invites, name='list_event_invites'),
    path('<int:invite_id>/deactivate/', deactivate_invite, name='deactivate_invite'),
    path('<int:invite_id>/qr/', generate_qr_for_invite, name='generate_qr'),
    # Використання запрошень (для гостей)
    path('validate/<str:token>/', validate_invite, name='validate_invite_with_token'),
    path('validate/', validate_invite, name='validate_invite'),
    path('use/<str:token>/', use_invite, name='use_invite_with_token'),
    path('use/', use_invite, name='use_invite'),
    # Поточний користувач
    path('me/', current_user_info, name='current_user_info'),
]
