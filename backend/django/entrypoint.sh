#!/bin/sh
set -e

cd /app/backend/django

python manage.py shell <<'PY'
import os
from django.contrib.auth import get_user_model

User = get_user_model()
email = os.environ.get("BOT_EMAIL")
pwd = os.environ.get("BOT_PASSWORD")
if email and pwd and not User.objects.filter(email=email).exists():
    User.objects.create_superuser(email=email, password=pwd, nickname="minji jang")
PY

exec "$@"
