from .base import *

DEBUG = True

ALLOWED_HOSTS = ["localhost", "127.0.0.1", "localhost:8080"]

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

CORS_ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://localhost",
]

print("enter production.py")