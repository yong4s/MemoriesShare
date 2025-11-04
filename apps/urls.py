"""URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include
from django.urls import path
from drf_spectacular.views import SpectacularAPIView
from drf_spectacular.views import SpectacularRedocView
from drf_spectacular.views import SpectacularSwaggerView

from settings import base

urlpatterns = [
    # Admin and Documentation
    path('admin/', admin.site.urls),
    path('api-auth/', include('rest_framework.urls', namespace='rest_framework')),
    # API Documentation
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('swagger/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
    # Core API Routes - CLEAN SEPARATION
    path('api/events/', include('apps.events.urls')),  # Events CRUD
    path('api/albums/', include('apps.albums.urls')),  # Albums CRUD
    path('api/mediafiles/', include('apps.mediafiles.urls')),  # MediaFiles CRUD
    path('api/accounts/', include('apps.accounts.urls')),  # User management + Guests
    # Specialized Routes
    # path('invites/', include('apps.accounts.invite_urls')),     # QR-код запрошення (TODO: Fix EventInvite)
    path('api/v1/', include('apps.shared.urls')),  # Shared utilities
    # Authentication
    path('accounts/', include('allauth.urls')),  # Django AllAuth URLs
]

if base.DEBUG:
    urlpatterns += static(base.MEDIA_URL, document_root=base.MEDIA_ROOT)
