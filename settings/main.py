import os
import sys

from .base import *

INSTALLED_APPS += [
    'django_extensions',
    'apps.accounts',
    'apps.shared',  # Add shared app for management commands
    'corsheaders',
    'rest_framework',
    'rest_framework_api_key',  # Added for API key authentication
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',
    'drf_spectacular',
    'apps.events',
    'apps.albums',
    'apps.mediafiles',
    # Celery and async tasks
    'django_celery_beat',
    # Django AllAuth
    'django.contrib.sites',
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.google',
]

REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'apps.shared.auth.authentication.CsrfExemptSessionAuthentication',
    ],
    # Enterprise Error Handling - translates business exceptions to HTTP responses
    'EXCEPTION_HANDLER': 'apps.shared.exceptions.api_handler.custom_exception_handler',
}

AUTH_USER_MODEL = 'accounts.CustomUser'

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'allauth.account.middleware.AccountMiddleware',
    'middleware.s3_exception_middleware.S3ExceptionMiddleware',
]

# Environment
TESTING_ENVIRONMENT = 'testing'
PRODUCTION_ENVIRONMENT = 'production'
STAGING_ENVIRONMENT = 'staging'
DEVELOPMENT_ENVIRONMENT = 'development'

if 'test' in sys.argv:  # noqa: SIM108
    ENVIRONMENT = TESTING_ENVIRONMENT
else:
    ENVIRONMENT = env('ENVIRONMENT')

# Testing environment optimizations
if ENVIRONMENT == TESTING_ENVIRONMENT:
    PASSWORD_HASHERS = [
        'django.contrib.auth.hashers.MD5PasswordHasher',
    ]

# CORS
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOWED_ORIGINS = env.list(
    'CORS_ALLOWED_ORIGINS',
    default=[
        'http://localhost:3000',
        'http://127.0.0.1:3000',
        'http://localhost:8080',
        'http://127.0.0.1:8080',
        env('FRONTEND_URL', default='http://localhost:3000'),
    ],
)

CORS_ALLOWED_ORIGIN_REGEXES = []
if DEBUG:
    CORS_ALLOWED_ORIGIN_REGEXES += [
        r'^https://.*\.ngrok-free\.app$',
        r'^https://.*\.ngrok\.io$',
    ]

# CORS Headers for JWT authentication
CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
    'x-api-key',  # For backward compatibility with API keys
]

# CSRF trusted origins
CSRF_TRUSTED_ORIGINS = env.list(
    'CSRF_TRUSTED_ORIGINS',
    default=[
        'http://localhost:8000',
        'http://127.0.0.1:8000',
        'http://localhost:3000',
        'http://127.0.0.1:3000',
        env('FRONTEND_URL', default='http://localhost:3000'),
    ],
)
if DEBUG:
    CSRF_TRUSTED_ORIGINS += ['https://*.ngrok-free.app', 'https://*.ngrok.io']

CSRF_COOKIE_HTTPONLY = False

# Production security headers (active when DEBUG=False).
# See `python manage.py check --deploy` for the full checklist.
if not DEBUG:
    SECURE_SSL_REDIRECT = env.bool('SECURE_SSL_REDIRECT', default=True)
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SECURE_HSTS_SECONDS = env.int('SECURE_HSTS_SECONDS', default=31536000)  # 1 year
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_REFERRER_POLICY = 'same-origin'
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    X_FRAME_OPTIONS = 'DENY'
else:
    CSRF_COOKIE_SECURE = False

# Frontend static bundle integration
STATICFILES_DIRS = [
    BASE_DIR / 'frontend',
]
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Swagger
SPECTACULAR_SETTINGS = {
    'TITLE': 'Media Flow API',
    'DESCRIPTION': 'Django REST API for media management with Google Drive integration, featuring JWT authentication, media file handling, and album/event organization.',
    'VERSION': 'v1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'CONTACT': {'email': 'admin@mediaflow.local'},
    'LICENSE': {'name': 'MIT License'},
    # App-based organization
    'TAGS': [
        {
            'name': 'Authentication',
            'description': 'User authentication, registration, and profile management',
        },
        {
            'name': 'Events',
            'description': 'Event creation, management, and basic CRUD operations',
        },
        {
            'name': 'Event Participants',
            'description': 'Event participant management, RSVP status, and user roles',
        },
        {
            'name': 'Event Invitations',
            'description': 'Guest invitations, bulk invites, and invitation management',
        },
        {
            'name': 'Event Analytics',
            'description': 'Event statistics, analytics, and participation insights',
        },
        {
            'name': 'Albums',
            'description': 'Photo album creation, organization, and management',
        },
        {
            'name': 'Media Files',
            'description': 'Media file upload, processing, and storage management',
        },
        {
            'name': 'System',
            'description': 'Health checks and system utilities',
        },
    ],
    # Customize components
    'COMPONENT_SPLIT_REQUEST': True,
    'COMPONENT_NO_READ_ONLY_REQUIRED': True,
    # UI customization
    'SWAGGER_UI_SETTINGS': {
        'deepLinking': True,
        'persistAuthorization': True,
        'displayOperationId': True,
        'defaultModelsExpandDepth': 2,
        'defaultModelExpandDepth': 2,
        'docExpansion': 'none',  # Start collapsed
        'filter': True,  # Enable search
    },
    # Security scheme
    'APPEND_COMPONENTS': {
        'securitySchemes': {
            'Bearer': {
                'type': 'http',
                'scheme': 'bearer',
                'bearerFormat': 'JWT',
                'description': 'JWT Authorization header using the Bearer scheme. Example: "Authorization: Bearer {token}"',
            }
        }
    },
    'SECURITY': [{'Bearer': []}],
}

# S3 BUCKET
FILE_UPLOAD_STORAGE = f"{env('FILE_UPLOAD_STORAGE', default='local')}"

AWS_ACCESS_KEY_ID = env.str('YOUR_ACCESS_KEY_S3')
AWS_SECRET_ACCESS_KEY = env.str('YOUR_SECRET_KEY_S3')
AWS_S3_REGION_NAME = env.str('AWS_S3_REGION_NAME', default='eu-north-1')
AWS_STORAGE_BUCKET_NAME = env.str('AWS_STORAGE_BUCKET_NAME_S3')
S3_BUCKET_NAME = env.str('AWS_STORAGE_BUCKET_NAME_S3', default='media-flow')

# Django AllAuth Configuration
SITE_ID = 1

AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
]

# Django AllAuth settings (updated for newer version)
ACCOUNT_LOGIN_METHODS = {'email'}
ACCOUNT_SIGNUP_FIELDS = ['email*', 'password1*', 'password2*']
ACCOUNT_EMAIL_VERIFICATION = 'optional'
ACCOUNT_LOGIN_ON_EMAIL_CONFIRMATION = True

LOGIN_REDIRECT_URL = '/api/accounts/profile/'
LOGOUT_REDIRECT_URL = '/api/accounts/auth/login/'

# Google OAuth Configuration
SOCIALACCOUNT_PROVIDERS = {
    'google': {
        'APP': {
            'client_id': env.str('GOOGLE_OAUTH_CLIENT_ID', default=''),
            'secret': env.str('GOOGLE_OAUTH_CLIENT_SECRET', default=''),
            'key': '',
        },
        'SCOPE': [
            'profile',
            'email',
            'https://www.googleapis.com/auth/drive',
        ],
        'AUTH_PARAMS': {'access_type': 'offline', 'approval_prompt': 'force'},
    }
}

# Google Drive API Configuration
GOOGLE_SERVICE_ACCOUNT_KEY_FILE = env.str(
    'GOOGLE_SERVICE_ACCOUNT_KEY_FILE',
    default=BASE_DIR / 'credentials' / 'google-service-account.json',
)

# Token Encryption Configuration
ENCRYPTION_KEY = env.str('ENCRYPTION_KEY', default='')

# Google OAuth Settings for custom flow
GOOGLE_OAUTH_CLIENT_ID = env.str('GOOGLE_OAUTH_CLIENT_ID', default='')
GOOGLE_OAUTH_CLIENT_SECRET = env.str('GOOGLE_OAUTH_CLIENT_SECRET', default='')

# Simple JWT Authentication Configuration
from datetime import timedelta

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60),  # 1 hour
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),  # 1 week
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'UPDATE_LAST_LOGIN': True,
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': env.str('SIMPLE_JWT_SIGNING_KEY', default=SECRET_KEY),
    'VERIFYING_KEY': None,
    'AUDIENCE': None,
    'ISSUER': 'media-flow-api',
    'AUTH_HEADER_TYPES': ('Bearer',),
    'AUTH_HEADER_NAME': 'HTTP_AUTHORIZATION',
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
    'USER_AUTHENTICATION_RULE': 'rest_framework_simplejwt.authentication.default_user_authentication_rule',
    'AUTH_TOKEN_CLASSES': ('rest_framework_simplejwt.tokens.AccessToken',),
    'TOKEN_TYPE_CLAIM': 'token_type',
    'JTI_CLAIM': 'jti',
    'SLIDING_TOKEN_REFRESH_EXP_CLAIM': 'refresh_exp',
    'SLIDING_TOKEN_LIFETIME': timedelta(minutes=60),
    'SLIDING_TOKEN_REFRESH_LIFETIME': timedelta(days=1),
    'TOKEN_OBTAIN_SERIALIZER': 'apps.accounts.serializers.CustomTokenObtainPairSerializer',
    'TOKEN_REFRESH_SERIALIZER': 'rest_framework_simplejwt.serializers.TokenRefreshSerializer',
    'TOKEN_VERIFY_SERIALIZER': 'rest_framework_simplejwt.serializers.TokenVerifySerializer',
    'TOKEN_BLACKLIST_SERIALIZER': 'rest_framework_simplejwt.serializers.TokenBlacklistSerializer',
    'SLIDING_TOKEN_OBTAIN_SERIALIZER': 'rest_framework_simplejwt.serializers.TokenObtainSlidingSerializer',
    'SLIDING_TOKEN_REFRESH_SERIALIZER': 'rest_framework_simplejwt.serializers.TokenRefreshSlidingSerializer',
}

# Email Configuration
EMAIL_BACKEND = env.str('EMAIL_BACKEND', default='django.core.mail.backends.console.EmailBackend')
EMAIL_HOST = env.str('EMAIL_HOST', default='smtp.gmail.com')
EMAIL_PORT = env.int('EMAIL_PORT', default=587)
EMAIL_USE_TLS = env.bool('EMAIL_USE_TLS', default=True)
EMAIL_HOST_USER = env.str('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = env.str('EMAIL_HOST_PASSWORD', default='')
DEFAULT_FROM_EMAIL = env.str('DEFAULT_FROM_EMAIL', default='MediaFlow <noreply@mediaflow.com>')

# Email Templates
EMAIL_SUBJECT_PREFIX = '[MediaFlow] '

# Passwordless Authentication Settings
PASSWORDLESS_CODE_TTL_MINUTES = env.int('PASSWORDLESS_CODE_TTL_MINUTES', default=10)
PASSWORDLESS_MAX_ATTEMPTS = env.int('PASSWORDLESS_MAX_ATTEMPTS', default=5)
PASSWORDLESS_EMAIL_RATE_LIMIT = env.int('PASSWORDLESS_EMAIL_RATE_LIMIT', default=5)
PASSWORDLESS_EMAIL_WINDOW_MINUTES = env.int('PASSWORDLESS_EMAIL_WINDOW_MINUTES', default=15)
PASSWORDLESS_IP_RATE_LIMIT = env.int('PASSWORDLESS_IP_RATE_LIMIT', default=20)
PASSWORDLESS_IP_WINDOW_MINUTES = env.int('PASSWORDLESS_IP_WINDOW_MINUTES', default=15)
PASSWORDLESS_VERIFICATION_ATTEMPTS = env.int('PASSWORDLESS_VERIFICATION_ATTEMPTS', default=5)
PASSWORDLESS_FAILED_LOCKOUT_MINUTES = env.int('PASSWORDLESS_FAILED_LOCKOUT_MINUTES', default=60)

# Number of trusted reverse proxies in front of the app (Render's load balancer = 1).
# Used to resolve the real client IP from X-Forwarded-For without trusting
# attacker-supplied values. Set to 0 for a direct/no-proxy deployment.
TRUSTED_PROXY_COUNT = env.int('TRUSTED_PROXY_COUNT', default=1)

# Site URL for email templates
SITE_URL = env.str('SITE_URL', default='https://mediaflow.com')

# Celery Configuration
CELERY_BROKER_URL = env.str('CELERY_BROKER_URL', default='redis://redis:6379/0')
CELERY_RESULT_BACKEND = env.str('CELERY_RESULT_BACKEND', default='redis://redis:6379/1')

# Basic Celery settings
CELERY_TASK_SERIALIZER = 'json'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE
CELERY_ENABLE_UTC = True

# Redis Cache Configuration (separate from Celery)
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': env.str('REDIS_URL', default='redis://redis:6379/2'),
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        },
        'TIMEOUT': 3600,  # 1 hour default timeout
        'KEY_PREFIX': 'media_flow',
        'VERSION': 1,
    }
}

# Override cache for testing environment
if ENVIRONMENT == TESTING_ENVIRONMENT:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'test-cache',
        }
    }

# Logging — stream to stdout so `docker compose logs` shows everything.
# Root level INFO; `apps.*` loggers stay at DEBUG in dev for verbose tracing.
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '[{asctime}] {levelname} {name}: {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'django.db.backends': {
            'handlers': ['console'],
            'level': 'WARNING',  # set to DEBUG to see every SQL query
            'propagate': False,
        },
        'apps': {
            'handlers': ['console'],
            'level': 'DEBUG' if DEBUG else 'INFO',
            'propagate': False,
        },
        'celery': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}
