#!/bin/sh
set -e

cd /app/backend/django

# 마이그레이션 실행
echo "Applying migrations..."
python - <<'PY'
import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.db import connection

with connection.cursor() as cursor:
    cursor.execute("SELECT to_regclass('public.user')")
    exists = cursor.fetchone()[0] is not None

if not exists:
    # Migrations may be marked applied without the table existing.
    # Reset users app migrations so the table can be created.
    import subprocess
    subprocess.check_call(["python", "manage.py", "migrate", "users", "zero", "--fake"])
PY
python manage.py migrate users --noinput
python manage.py migrate --noinput

# Log current tables to help debug migration state.
python - <<'PY'
import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.db import connection

with connection.cursor() as cursor:
    cursor.execute(
        "SELECT table_name FROM information_schema.tables "
        "WHERE table_schema = 'public' ORDER BY table_name"
    )
    tables = [row[0] for row in cursor.fetchall()]

print("DB tables:", ", ".join(tables))
PY

# 봇 유저 생성 (테이블 이름 체크 제거)
echo "Creating bot user if not exists..."
python manage.py shell <<'PY'
import os
from django.db import connection
from django.contrib.auth import get_user_model
from django.db.utils import ProgrammingError

User = get_user_model()
email = os.environ.get("BOT_EMAIL")
pwd = os.environ.get("BOT_PASSWORD")

if email and pwd:
    try:
        if not User.objects.filter(email=email).exists():
            User.objects.create_superuser(email=email, password=pwd, nickname="minji jang")
            print("Bot user created successfully.")
    except Exception as exc:
        # 테이블이 아직 없거나 다른 에러가 나면 그냥 스킵하게 둠
        print(f"Skip bot user creation: {exc}")
PY

# If no command was passed, default to runserver
if [ $# -eq 0 ]; then
    exec python manage.py runserver 0.0.0.0:8000
else
    exec "$@"
fi
