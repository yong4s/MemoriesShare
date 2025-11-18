import sys
import os

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
    'apps.reactions',
    
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
}

AUTH_USER_MODEL = 'accounts.CustomUser'

# Google Drive Encryption
GOOGLE_DRIVE_ENCRYPTION_KEY = '8H0rAUyLEhTI2uRJxYaqSHjVK9OtxTI_xQ8DqdmpGEE='

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

    'middleware.s3_exception_middleware.S3ExceptionMiddleware'
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

# Redis Cache Configuration (will be overridden below after Celery config)

# Testing environment optimizations  
if ENVIRONMENT == TESTING_ENVIRONMENT:
    PASSWORD_HASHERS = [
        'django.contrib.auth.hashers.MD5PasswordHasher',
    ]
    # Use in-memory cache for tests
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'test-cache',
        }
    }

# CORS
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000", 
    "http://localhost:8080",
    "http://127.0.0.1:8080",
    env('FRONTEND_URL', default='http://localhost:3000'),
]

# Allow all origins in development (can be restrictive in production)
if DEBUG:
    CORS_ORIGIN_ALLOW_ALL = True
    CORS_ALLOW_ALL_ORIGINS = True

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

# CSRF exemption for API endpoints
CSRF_TRUSTED_ORIGINS = [
    'http://localhost:8000',
    'http://127.0.0.1:8000',
    'http://localhost:3000',
    'http://127.0.0.1:3000',
    env('FRONTEND_URL', default='http://localhost:3000'),
]

# Exempt API endpoints from CSRF protection
CSRF_COOKIE_SECURE = False
CSRF_COOKIE_HTTPONLY = False

# Swagger
SPECTACULAR_SETTINGS = {
    'TITLE': 'Snippets API',
    'DESCRIPTION': 'Test description',
    'VERSION': 'v1',
    'SERVE_INCLUDE_SCHEMA': False,
    'CONTACT': {'email': 'contact@snippets.local'},
    'LICENSE': {'name': 'BSD License'},
    # OTHER SETTINGS
}

# S3 BUCKET
FILE_UPLOAD_STORAGE = f"{env('FILE_UPLOAD_STORAGE', default='local')}"

AWS_ACCESS_KEY_ID = env.str("YOUR_ACCESS_KEY_S3")
AWS_SECRET_ACCESS_KEY = env.str("YOUR_SECRET_KEY_S3")
AWS_S3_REGION_NAME = "eu-north-1"
AWS_STORAGE_BUCKET_NAME = env.str("AWS_STORAGE_BUCKET_NAME_S3")
S3_BUCKET_NAME = "media-flow"

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

LOGIN_REDIRECT_URL = '/api/v1/auth/profile/'
LOGOUT_REDIRECT_URL = '/api/v1/auth/login/'

# Google OAuth Configuration
SOCIALACCOUNT_PROVIDERS = {
    'google': {
        'APP': {
            'client_id': env.str('GOOGLE_OAUTH_CLIENT_ID', default=''),
            'secret': env.str('GOOGLE_OAUTH_CLIENT_SECRET', default=''),
            'key': ''
        },
        'SCOPE': [
            'profile',
            'email',
            'https://www.googleapis.com/auth/drive',
        ],
        'AUTH_PARAMS': {
            'access_type': 'offline',
            'approval_prompt': 'force'
        }
    }
}

# Google Drive API Configuration
GOOGLE_SERVICE_ACCOUNT_KEY_FILE = env.str(
    'GOOGLE_SERVICE_ACCOUNT_KEY_FILE', 
    default=BASE_DIR / 'credentials' / 'google-service-account.json'
)

# Token Encryption Configuration
ENCRYPTION_KEY = env.str('ENCRYPTION_KEY', default='')

# Google OAuth Settings for custom flow
GOOGLE_OAUTH_CLIENT_ID = env.str('GOOGLE_OAUTH_CLIENT_ID', default='')
GOOGLE_OAUTH_CLIENT_SECRET = env.str('GOOGLE_OAUTH_CLIENT_SECRET', default='')

# Clerk Authentication Configuration (DISABLED for development)
# CLERK_SECRET_KEY = env.str('CLERK_SECRET_KEY', default='')
# CLERK_PUBLISHABLE_KEY = env.str('CLERK_PUBLISHABLE_KEY', default='')
# CLERK_WEBHOOK_SECRET = env.str('CLERK_WEBHOOK_SECRET', default='')

# Simple JWT Authentication Configuration
from datetime import timedelta

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60),  # 1 hour
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),     # 1 week
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'UPDATE_LAST_LOGIN': True,

    'ALGORITHM': 'HS256',
    'SIGNING_KEY': env.str('SECRET_KEY', default='ek12k!Kkwk1e2kdkskqkNDNhw278AB@)3nas'),
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

# Legacy JWT service key (for backward compatibility)
SIMPLE_JWT_SECRET_KEY = env.str('SIMPLE_JWT_SECRET_KEY', default='dev-jwt-secret-key-change-in-production')

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

# Celery Configuration
CELERY_BROKER_URL = env.str('CELERY_BROKER_URL', default='redis://localhost:6379/0')
CELERY_RESULT_BACKEND = env.str('CELERY_RESULT_BACKEND', default='redis://localhost:6379/1')

# Celery security and performance settings
CELERY_TASK_SERIALIZER = 'json'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE
CELERY_ENABLE_UTC = True

# Celery task execution settings
CELERY_TASK_ALWAYS_EAGER = False
CELERY_TASK_EAGER_PROPAGATES = True
CELERY_TASK_IGNORE_RESULT = False
CELERY_TASK_STORE_EAGER_RESULT = True

# Celery worker settings
CELERY_WORKER_PREFETCH_MULTIPLIER = 1
CELERY_WORKER_MAX_TASKS_PER_CHILD = 1000
CELERY_WORKER_DISABLE_RATE_LIMITS = True

# Celery task time limits (in seconds)
CELERY_TASK_SOFT_TIME_LIMIT = 300  # 5 minutes

# Celery Email Task Configuration
CELERY_TASK_ROUTES = {
    'apps.events.tasks.send_invite_confirmation_email': {'queue': 'emails'},
    'apps.events.tasks.send_invite_notification_email': {'queue': 'emails'},
    'apps.events.tasks.cleanup_expired_magic_links': {'queue': 'maintenance'},
}

CELERY_TASK_ANNOTATIONS = {
    'apps.events.tasks.send_invite_confirmation_email': {
        'rate_limit': '10/m',  # 10 emails per minute to avoid spam
        'time_limit': 30,      # 30 seconds timeout
        'max_retries': 3,
        'default_retry_delay': 60,
    },
    'apps.events.tasks.send_invite_notification_email': {
        'rate_limit': '5/m',
        'time_limit': 30,
        'max_retries': 3,
    },
    'apps.events.tasks.cleanup_expired_magic_links': {
        'time_limit': 120,  # 2 minutes for cleanup
    },
}
CELERY_TASK_TIME_LIMIT = 600  # 10 minutes
CELERY_TASK_ACKS_LATE = True
CELERY_TASK_REJECT_ON_WORKER_LOST = True

# Celery beat scheduler settings
CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'

# Celery result backend settings
CELERY_RESULT_EXPIRES = 3600  # 1 hour
CELERY_RESULT_PERSISTENT = True

# Redis Cache Configuration (separate from Celery)
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': env.str('REDIS_URL', default='redis://localhost:6379/2'),
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        },
        'TIMEOUT': 3600,  # 1 hour default timeout
        'KEY_PREFIX': 'media_flow',
        'VERSION': 1,
    }
}
