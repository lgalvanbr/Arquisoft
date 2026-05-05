"""
Django settings for finops_platform project - FinOps Platform for BITE.CO
Implementación de Auth0 según laboratorio ISIS2503
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Quick-start development settings
SECRET_KEY = os.getenv('SECRET_KEY', 'django-insecure-finops-bite-co-secret-key-2024')

DEBUG = os.getenv('DEBUG', 'True') == 'True'

ALLOWED_HOSTS = ['*']

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'corsheaders',
    'social_django',  # Auth0 via social_auth
    'finops_platform',
    'autenticacion',
    'reportes',
    'usuario',
    'empresa',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'autenticacion.middleware.AuditLoggingMiddleware',  # Auditoría de intentos
]

ROOT_URLCONF = 'finops_platform.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            os.path.join(BASE_DIR, 'finops_platform', 'templates'),
            os.path.join(BASE_DIR, 'autenticacion', 'templates'),
            os.path.join(BASE_DIR, 'reportes', 'templates'),
            os.path.join(BASE_DIR, 'usuario', 'templates'),
            os.path.join(BASE_DIR, 'empresa', 'templates'),
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'social_django.context_processors.backends',
                'social_django.context_processors.login_redirect',
            ],
        },
    },
]

WSGI_APPLICATION = 'finops_platform.wsgi.application'

# Database
# Configure PostgreSQL connection for AWS deployment
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('DB_NAME', 'monitoring_db'),
        'USER': os.getenv('DB_USER', 'report_user'),
        'PASSWORD': os.getenv('DB_PASSWORD', 'isis2503'),
        'HOST': os.getenv('DATABASE_HOST', 'localhost'),
        'PORT': os.getenv('DB_PORT', '5432'),
    }
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
LANGUAGE_CODE = 'es-es'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True

# Static files
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ======================== SESSION CONFIGURATION ========================
# Asegurar que las sesiones se limpien correctamente al logout
SESSION_ENGINE = 'django.contrib.sessions.backends.db'  # Usar BD para sesiones
SESSION_COOKIE_AGE = 3600  # 1 hora de inactividad
SESSION_COOKIE_HTTPONLY = True  # No accessible via JavaScript
SESSION_COOKIE_SECURE = False  # True en producción (HTTPS)
SESSION_COOKIE_SAMESITE = 'Lax'  # Protege CSRF
SESSION_EXPIRE_AT_BROWSER_CLOSE = True  # Expira al cerrar navegador
SESSION_SAVE_EVERY_REQUEST = True  # Actualizar sesión en cada request
# Limpiar datos de sesión cuando el usuario logout
CSRF_COOKIE_SECURE = False  # True en producción (HTTPS)
CSRF_COOKIE_HTTPONLY = False  # Necesario para lectura en JavaScript

# ======================== AUTH0 CONFIGURATION (Laboratorio ISIS2503) ========================

LOGIN_URL = "/login/auth0"
LOGIN_REDIRECT_URL = "/"

# LOGOUT_REDIRECT_URL: Opción A - Hardcodear manualmente después de terraform apply
# Pasos:
# 1. terraform apply -auto-approve
# 2. Obtener IP pública de app-a desde terraform output
# 3. Editar esta línea: LOGOUT_REDIRECT_URL = "https://dev-vy27mzsmkwosyqhr.us.auth0.com/v2/logout?returnTo=http://<IP_PUBLICA>:8080"
# 4. Git commit y push (o SSH a instancia y editar manualmente)
#
# Placeholder para desarrollo local:
LOGOUT_REDIRECT_URL = 'https://dev-vy27mzsmkwosyqhr.us.auth0.com/v2/logout?returnTo=http%3A%2F%2Fip_publica_instancia:8080'

SOCIAL_AUTH_TRAILING_SLASH = False

SOCIAL_AUTH_AUTH0_DOMAIN = 'dev-vy27mzsmkwosyqhr.us.auth0.com'
SOCIAL_AUTH_AUTH0_KEY = 'hLSCIWW4Wof9DJeDv58kPXBLX07YLZCA'
SOCIAL_AUTH_AUTH0_SECRET = 'Jn1VRUtos80bWySfxL5HFHk-aMu30fZM0CyKsRyaREIsGwVAq6y2rXmN4GmCbRAZ'

SOCIAL_AUTH_AUTH0_SCOPE = [
    'openid',
    'profile',
    'email',
    'role',
]

SOCIAL_AUTH_AUTH0_AUTH_EXTRA_ARGUMENTS = {
    'audience': 'https://finops-api',
    'prompt': 'login',
    'max_age': 0,
}

# Pipeline personalizado para generar JWT después de Auth0 login
SOCIAL_AUTH_PIPELINE = (
    # Pipeline por defecto de social_django
    'social_core.pipeline.social_auth.social_details',
    'social_core.pipeline.social_auth.social_uid',
    'social_core.pipeline.social_auth.auth_allowed',
    'social_core.pipeline.social_auth.social_user',
    'social_core.pipeline.user.get_username',
    'social_core.pipeline.user.create_user',
    'social_core.pipeline.social_auth.associate_user',
    'social_core.pipeline.social_auth.load_extra_data',
    'social_core.pipeline.user.user_details',
    # Pipeline personalizado: genera JWT y guarda en sesión
    'autenticacion.pipeline.save_jwt_to_session',
)

# LOGIN_REDIRECT_URL: después de Auth0, redirige a la vista que captura tokens
LOGIN_REDIRECT_URL = '/auth0/callback/'

AUTHENTICATION_BACKENDS = (
    'autenticacion.auth0backend.Auth0',
    'django.contrib.auth.backends.ModelBackend',
)

# ======================== REST FRAMEWORK ========================
REST_FRAMEWORK = {
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 100,
    'DEFAULT_FILTER_BACKENDS': [
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
}

# CORS
CORS_ALLOW_ALL_ORIGINS = True

# ======================== SECURITY SETTINGS ========================
SECURITY_SETTINGS = {
    'MAX_INTENTOS_LOGIN': 5,
    'VENTANA_TIEMPO_INTENTOS_SEGUNDOS': 3600,
    'DURACION_BLOQUEO_SEGUNDOS': 300,
}
