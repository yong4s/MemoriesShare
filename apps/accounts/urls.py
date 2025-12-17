from django.urls import path

from apps.accounts import views

app_name = 'accounts'

urlpatterns = [
    # Authentication endpoints
    path('auth/login/', views.CustomTokenObtainPairView.as_view(), name='login'),
    path('auth/refresh/', views.CustomTokenRefreshView.as_view(), name='token_refresh'),
    path('auth/logout/', views.LogoutView.as_view(), name='logout'),
    path('auth/register/', views.UserRegistrationView.as_view(), name='register'),
    path('auth/guest-login/', views.AnonymousGuestLoginView.as_view(), name='guest_login'),
    path('auth/status/', views.auth_status, name='auth_status'),
    # Passwordless authentication
    path(
        'auth/passwordless/request/',
        views.PasswordlessRequestView.as_view(),
        name='passwordless_request',
    ),
    path(
        'auth/passwordless/verify/',
        views.PasswordlessVerifyView.as_view(),
        name='passwordless_verify',
    ),
    path(
        'auth/set-password/',
        views.SetPasswordView.as_view(),
        name='set_password',
    ),
    # Profile management
    path('profile/', views.UserProfileView.as_view(), name='profile'),
    path(
        'profile/change-password/',
        views.PasswordChangeView.as_view(),
        name='change_password',
    ),
    # Health check
    path('health/', views.health_check, name='health_check'),
]
