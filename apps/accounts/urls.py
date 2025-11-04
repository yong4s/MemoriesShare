from django.urls import include
from django.urls import path

from . import views

app_name = 'accounts'

urlpatterns = [
    # JWT Authentication endpoints
    path('auth/login/', views.CustomTokenObtainPairView.as_view(), name='login'),
    path('auth/refresh/', views.CustomTokenRefreshView.as_view(), name='token_refresh'),
    path('auth/logout/', views.LogoutView.as_view(), name='logout'),
    # User management endpoints
    path('auth/register/', views.UserRegistrationView.as_view(), name='register'),
    path('auth/profile/', views.UserProfileView.as_view(), name='profile'),
    path('auth/change-password/', views.PasswordChangeView.as_view(), name='change_password'),
    path('auth/status/', views.auth_status, name='auth_status'),
    # Anonymous guest authentication
    path('auth/guest-login/', views.AnonymousGuestLoginView.as_view(), name='guest_login'),
    # Health check
    path('health/', views.health_check, name='health_check'),
    # Legacy session-based authentication (for backward compatibility)
    path('session/login/', views.SessionLoginView.as_view(), name='session_login'),
    path('session/logout/', views.SessionLogoutView.as_view(), name='session_logout'),
    # Guest management URLs (moved from events app)
    path('<uuid:event_uuid>/guests/', views.GuestListAPIView.as_view(), name='guest-list'),  # GET/POST guests
    path('guests/<int:guest_id>/', views.GuestDetailAPIView.as_view(), name='guest-detail'),  # GET guest detail
    path('guests/<int:guest_id>/update/', views.GuestDetailAPIView.as_view(), name='guest-update'),  # PUT guest update
    path('guests/<int:guest_id>/delete/', views.GuestDetailAPIView.as_view(), name='guest-delete'),  # DELETE guest
    path(
        'guests/<int:guest_id>/status/', views.GuestUpdateStatusAPIView.as_view(), name='guest-update-status'
    ),  # PATCH guest status
]
