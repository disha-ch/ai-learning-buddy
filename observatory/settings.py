import os,secrets
from pathlib import Path
from dotenv import load_dotenv
BASE_DIR=Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR/'.env')
DEBUG=os.getenv('DJANGO_DEBUG','0')=='1'
# Single-process classroom deployment. Set a stable key in production.
SECRET_KEY=os.getenv('DJANGO_SECRET_KEY') or secrets.token_hex(32)
ALLOWED_HOSTS=[x.strip() for x in os.getenv('DJANGO_ALLOWED_HOSTS','localhost,127.0.0.1,[::1],.onrender.com').split(',')]
CSRF_TRUSTED_ORIGINS=[x for x in os.getenv('DJANGO_CSRF_TRUSTED_ORIGINS','').split(',') if x]
ROOT_URLCONF='observatory.urls'
WSGI_APPLICATION='observatory.wsgi.application'
INSTALLED_APPS=['django.contrib.staticfiles','django.contrib.sessions']
MIDDLEWARE=['django.middleware.security.SecurityMiddleware','whitenoise.middleware.WhiteNoiseMiddleware','django.contrib.sessions.middleware.SessionMiddleware','django.middleware.common.CommonMiddleware','django.middleware.csrf.CsrfViewMiddleware','django.middleware.clickjacking.XFrameOptionsMiddleware']
TEMPLATES=[{'BACKEND':'django.template.backends.django.DjangoTemplates','DIRS':[BASE_DIR/'templates'],'APP_DIRS':True,'OPTIONS':{'context_processors':['django.template.context_processors.request']}}]
SESSION_ENGINE='django.contrib.sessions.backends.signed_cookies'
SESSION_COOKIE_HTTPONLY=True
SESSION_COOKIE_SAMESITE='Lax'
SESSION_COOKIE_SECURE=os.getenv('DJANGO_SECURE_COOKIES','0')=='1'
CSRF_COOKIE_SECURE=SESSION_COOKIE_SECURE
SECURE_CONTENT_TYPE_NOSNIFF=True
X_FRAME_OPTIONS='DENY'
STATIC_URL='/static/'
STATICFILES_DIRS=[BASE_DIR/'static']
STATIC_ROOT=BASE_DIR/'staticfiles'
STORAGES={'default':{'BACKEND':'django.core.files.storage.FileSystemStorage'},'staticfiles':{'BACKEND':'whitenoise.storage.CompressedManifestStaticFilesStorage'}}
DATA_UPLOAD_MAX_MEMORY_SIZE=20000
DEFAULT_AUTO_FIELD='django.db.models.BigAutoField'
USE_TZ=True
