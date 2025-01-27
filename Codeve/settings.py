from pathlib import Path
import os
from django.contrib.messages import constants as messages
from dotenv import load_dotenv

# ------------------------------------------------------------------------------
# 기본 설정 (Base Settings)
# ------------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(dotenv_path=os.path.join(BASE_DIR, '.env'))

# 보안 설정 (Security Settings)
SECRET_KEY = os.getenv('DJANGO_SECRET_KEY')
DEBUG = True
ALLOWED_HOSTS = ['3.35.11.71', 'codeve.p-e.kr']

# ------------------------------------------------------------------------------
# 애플리케이션 설정 (Application Settings)
# ------------------------------------------------------------------------------
# Django 기본 앱
DJANGO_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',
]

# 서드파티 앱
THIRD_PARTY_APPS = [
    'rest_framework',
    'rest_framework.authtoken',
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.google',
    'social_django',
]

# 로컬 앱
LOCAL_APPS = [
    'accounts',
    'courses',
    'roadmaps',
    'communities',
    'chatbots',
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

# ------------------------------------------------------------------------------
# 미들웨어 및 URL 설정 (Middleware & URL Settings)
# ------------------------------------------------------------------------------
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'allauth.account.middleware.AccountMiddleware',
]

ROOT_URLCONF = 'Codeve.urls'
WSGI_APPLICATION = 'Codeve.wsgi.application'

# ------------------------------------------------------------------------------
# 템플릿 설정 (Template Settings)
# ------------------------------------------------------------------------------
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
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

WSGI_APPLICATION = 'Codeve.wsgi.application'
# ------------------------------------------------------------------------------
# 데이터베이스 설정 (Database Settings)
# ------------------------------------------------------------------------------
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    },
    'production': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'codeve_db',
        'USER': 'codeve_user',
        'PASSWORD': 'your_password_here',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}

# DEBUG가 True일 때는 SQLite를 사용하고, False일 때는 PostgreSQL을 사용하도록 설정
DATABASES["default"] = DATABASES["default" if DEBUG else "production"]

# ------------------------------------------------------------------------------
# 인증 및 보안 설정 (Authentication & Security Settings)
# ------------------------------------------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

AUTH_USER_MODEL = 'accounts.User'

AUTHENTICATION_BACKENDS = [
    'social_core.backends.google.GoogleOAuth2',
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
]

# 로그인/로그아웃 설정
LOGIN_URL = 'accounts:login'
LOGIN_REDIRECT_URL = 'main'
LOGOUT_REDIRECT_URL = 'main'

# ------------------------------------------------------------------------------
# 구글 OAuth2 설정 (Google OAuth2 Settings)
# ------------------------------------------------------------------------------
SOCIAL_AUTH_GOOGLE_OAUTH2_KEY = os.getenv('SOCIAL_AUTH_GOOGLE_OAUTH2_KEY')
SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET = os.getenv('SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET')
SOCIAL_AUTH_GOOGLE_OAUTH2_SCOPE = [
    'https://www.googleapis.com/auth/userinfo.email',
    'https://www.googleapis.com/auth/userinfo.profile',
]

# ------------------------------------------------------------------------------
# REST Framework 설정
# ------------------------------------------------------------------------------
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.TokenAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
}

# ------------------------------------------------------------------------------
# 이메일 설정 (Email Settings)
# ------------------------------------------------------------------------------
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = str(os.environ.get('EMAIL_HOST'))
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', 587))
EMAIL_HOST_USER = str(os.environ.get('EMAIL_HOST_USER'))
EMAIL_HOST_PASSWORD = str(os.environ.get('EMAIL_HOST_USER_PASSWORD'))
EMAIL_USE_TLS = str(os.environ.get('EMAIL_USE_TLS')).lower() == 'true'
DEFAULT_FROM_EMAIL = str(os.environ.get('DEFAULT_FROM_EMAIL'))

# ------------------------------------------------------------------------------
# 메시지 설정 (Message Settings)
# ------------------------------------------------------------------------------
MESSAGE_TAGS = {
    messages.DEBUG: 'debug',
    messages.INFO: 'info',
    messages.SUCCESS: 'success',
    messages.WARNING: 'warning',
    messages.ERROR: 'error',
}

# ------------------------------------------------------------------------------
# 정적 파일 및 미디어 설정 (Static & Media Settings)
# ------------------------------------------------------------------------------
STATIC_URL = 'static/'
STATICFILES_DIRS = [
    BASE_DIR / 'static',
]
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')


# ------------------------------------------------------------------------------
# 국제화 설정 (Internationalization Settings)
# ------------------------------------------------------------------------------
LANGUAGE_CODE = 'ko-kr'
TIME_ZONE = 'Asia/Seoul'
USE_I18N = True
USE_TZ = True

# ------------------------------------------------------------------------------
# 기타 설정 (Miscellaneous Settings)
# ------------------------------------------------------------------------------
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
SITE_ID = 1
PASSWORD_RESET_TIMEOUT = 259200  # 3일

# OpenAI API 설정
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', None)
