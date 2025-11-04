# apps/shared/urls.py
from django.urls import path

from .views.auth_views import LoginView
from .views.auth_views import LogoutAllSessionsView
from .views.auth_views import LogoutView
from .views.auth_views import ProfileView
from .views.auth_views import RefreshTokenView

# Auth views
from .views.auth_views import RegisterView
from .views.auth_views import ValidateTokenView

app_name = 'shared'

urlpatterns = [
    # Authentication endpoints
    path('auth/register/', RegisterView.as_view(), name='register'),
    path('auth/login/', LoginView.as_view(), name='login'),
    path('auth/refresh/', RefreshTokenView.as_view(), name='refresh'),
    path('auth/logout/', LogoutView.as_view(), name='logout'),
    path('auth/logout-all/', LogoutAllSessionsView.as_view(), name='logout-all'),
    path('auth/profile/', ProfileView.as_view(), name='profile'),
    path('auth/validate/', ValidateTokenView.as_view(), name='validate'),
]
