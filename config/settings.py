"""
Django settings for RAG project
"""
import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variables
load_dotenv(os.path.join(BASE_DIR, '.env'))

SECRET_KEY = os.getenv('SECRET_KEY', 'your-secret-key-change-this-in-production-123456789')

DEBUG = os.getenv('DEBUG', 'True').lower() in ('true', '1', 'yes')
ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', '*').split(',')

INSTALLED_APPS = [
    'daphne',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'corsheaders',
    'apps.rag',
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
]

ROOT_URLCONF = 'config.urls'

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
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'
ASGI_APPLICATION = 'config.asgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static')]

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

REST_FRAMEWORK = {
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 50,
    'DEFAULT_FILTER_BACKENDS': ['rest_framework.filters.SearchFilter'],
}

CORS_ALLOWED_ORIGINS = os.getenv('CORS_ALLOWED_ORIGINS', 'http://localhost:8000,http://localhost:3000').split(',')
CSRF_TRUSTED_ORIGINS = os.getenv('CSRF_TRUSTED_ORIGINS', 'http://localhost:8000,http://localhost:3000').split(',')

# RAG Configuration
RAG_CONFIG = {
    'OLLAMA_BASE_URL': os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434'),
    'MODEL_NAME': os.getenv('OLLAMA_MODEL', 'deepseek-coder:6.7b'),
    'EMBEDDING_MODEL': os.getenv('OLLAMA_EMBEDDING_MODEL', 'nomic-embed-text'),
    'CHUNK_SIZE': int(os.getenv('RAG_CHUNK_SIZE', '1000')),
    'CHUNK_OVERLAP': int(os.getenv('RAG_CHUNK_OVERLAP', '100')),
    'VECTOR_DB_PATH': os.path.join(BASE_DIR, 'vector_stores'),
    'TEMP_FILES_PATH': os.path.join(BASE_DIR, 'temp_files'),
    'MAX_CONTEXT_LENGTH': 4096,
    'TEMPERATURE': float(os.getenv('RAG_TEMPERATURE', '0.3')),
    'TOP_P': float(os.getenv('RAG_TOP_P', '0.9')),
    'SIMILARITY_THRESHOLD': float(os.getenv('RAG_SIMILARITY_THRESHOLD', '0.5')),
}

# File watching
# Allow all file types EXCEPT images and videos
EXCLUDED_EXTENSIONS = [
    # Images
    '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg', '.webp', '.ico', '.tiff',
    # Videos
    '.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv', '.webm', '.m4v', '.mpg', '.mpeg',
    # Audio (optional - can be excluded if needed)
    '.mp3', '.wav', '.flac', '.aac', '.ogg', '.wma', '.m4a',
    # Archives (optional - to avoid indexing compressed files)
    '.zip', '.rar', '.7z', '.tar', '.gz', '.bz2',
    # Binaries and executables
    '.exe', '.dll', '.so', '.dylib', '.bin', '.o', '.pyc', '.pyo',
    # Dependencies
    '.node_modules', 'node_modules',
]

FILE_WATCH_EXTENSIONS = None  # None means allow all except EXCLUDED_EXTENSIONS
MAX_FILES_PER_PROJECT = 1000
MAX_FILE_SIZE_MB = 10
AUTO_SYNC_ENABLED = os.getenv('AUTO_SYNC_ENABLED', 'True').lower() in ('true', '1', 'yes')
SYNC_INTERVAL_MINUTES = int(os.getenv('SYNC_INTERVAL_MINUTES', '5'))

# Logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
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
}

# WebSocket configuration for Daphne
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels.layers.InMemoryChannelLayer'
    }
}
