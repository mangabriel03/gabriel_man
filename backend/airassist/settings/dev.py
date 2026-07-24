import os

from .base import *  # noqa: F401,F403

DEBUG = True
ALLOWED_HOSTS = ["*"]

EMAIL_BACKEND = os.environ.get(
	"DJANGO_EMAIL_BACKEND",
	"django.core.mail.backends.console.EmailBackend",
)
DEFAULT_FROM_EMAIL = os.environ.get(
	"DJANGO_DEFAULT_FROM_EMAIL",
	"no-reply@airassist.local",
)
