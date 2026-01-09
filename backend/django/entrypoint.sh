#!/bin/sh
set -e

cd /app/backend/django

# Set FRONTEND_URL for OAuth redirects
export FRONTEND_URL="${FRONTEND_URL:-https://d2lr1p20b7dwp0.cloudfront.net}"

# PostgreSQL init.sql 실행 (Web 컨테이너에서만)
if ! echo "$@" | grep -qE "celery|worker"; then
    echo "Applying init.sql..."
    export PGPASSWORD="${POSTGRES_PASSWORD}"
    psql -h "${POSTGRES_HOST}" -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" -f /app/init.sql
    echo "✓ init.sql applied"
    unset PGPASSWORD
fi

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

# Django Site 도메인을 HTTPS로 업데이트 (OAuth redirect URI가 HTTPS로 생성되도록)
# ⚠️ Web 컨테이너에서만 실행 (Celery 컨테이너에서는 스킵)
if echo "$@" | grep -qE "celery|worker"; then
    echo "Skipping Site domain setup (running celery worker)"
else
    echo "Updating Django Site domain to HTTPS..."
    python manage.py shell <<'PY'
import os
from django.contrib.sites.models import Site

try:
    site = Site.objects.get(id=1)
    site.domain = "api.histok.info"
    site.name = "HistoK API"
    site.save()
    print(f"Site domain updated to: {site.domain}")
except Exception as exc:
    print(f"Skip site domain update: {exc}")
PY

    # Google Social App 자동 설정
    echo "=========================================="
    echo "Setting up Google Social App..."
    echo "=========================================="
    python manage.py shell <<'PY'
import os
from django.contrib.sites.models import Site
from allauth.socialaccount.models import SocialApp

client_id = os.getenv('GOOGLE_OAUTH_CLIENT_ID')
client_secret = os.getenv('GOOGLE_OAUTH_CLIENT_SECRET')

# 환경 변수 확인 로그
print(f"[DEBUG] GOOGLE_OAUTH_CLIENT_ID present: {bool(client_id)}")
print(f"[DEBUG] GOOGLE_OAUTH_CLIENT_SECRET present: {bool(client_secret)}")
if client_id:
    print(f"[DEBUG] Client ID starts with: {client_id[:20]}...")
if client_secret:
    print(f"[DEBUG] Client Secret starts with: {client_secret[:10]}...")

if not client_id or not client_secret:
    print("⚠ WARNING: GOOGLE_OAUTH_CLIENT_ID or GOOGLE_OAUTH_CLIENT_SECRET not set")
    print("⚠ Social App cannot be created without credentials")
else:
    try:
        # Get or create Google Social App (한 개만 유지)
        social_apps = SocialApp.objects.filter(provider='google')
        print(f"[DEBUG] Current Google Social Apps count: {social_apps.count()}")

        if social_apps.count() > 1:
            deleted_count = social_apps.delete()[0]
            print(f"✓ Deleted {deleted_count} duplicate Google Social Apps")
            social_app = None
        elif social_apps.count() == 1:
            social_app = social_apps.first()
            print(f"✓ Found existing Google Social App (ID: {social_app.id})")
            print(f"[DEBUG] Existing app client_id: {social_app.client_id[:20]}...")
        else:
            print(f"[DEBUG] No existing Google Social App found")
            social_app = None

        if not social_app:
            social_app = SocialApp.objects.create(
                provider='google',
                name='Google',
                client_id=client_id,
                secret=client_secret,
            )
            print(f"✓ Created NEW Google Social App (ID: {social_app.id})")
        else:
            social_app.client_id = client_id
            social_app.secret = client_secret
            social_app.save()
            print(f"✓ Updated existing Google Social App (ID: {social_app.id})")

        # Site 연결 확인
        site = Site.objects.get(id=1)
        print(f"[DEBUG] Site domain: {site.domain}")
        connected_sites = list(social_app.sites.all())
        print(f"[DEBUG] Social App connected to sites: {[s.domain for s in connected_sites]}")

        if site not in connected_sites:
            social_app.sites.add(site)
            print(f"✓ Connected Social App to Site: {site.domain}")
        else:
            print(f"✓ Already connected to Site: {site.domain}")

        final_count = SocialApp.objects.filter(provider='google').count()
        print(f"✓✓✓ FINAL: Total Google Social Apps in DB: {final_count}")

        # 최종 검증
        if final_count != 1:
            print(f"⚠⚠⚠ WARNING: Expected 1 Social App but found {final_count}")
    except Exception as exc:
        print(f"✗✗✗ ERROR setting up Social App: {exc}")
        import traceback
        traceback.print_exc()
PY

    # ==========================================
    # 데이터 적재 파이프라인 (PostgreSQL, Neo4j, Fuseki)
    # ==========================================
    echo "=========================================="
    echo "Checking and loading data pipelines..."
    echo "=========================================="

    # FORCE_DATA_RELOAD 환경 변수가 설정되면 모든 데이터 삭제 후 재적재
    FORCE_RELOAD="${FORCE_DATA_RELOAD:-false}"
    if [ "$FORCE_RELOAD" = "true" ]; then
        echo "⚠️  FORCE_DATA_RELOAD=true 설정됨 - 모든 데이터를 삭제하고 재적재합니다"
    fi

    # 1. PostgreSQL title_embeddings 데이터 적재 (엔티티 매칭용)
    echo "[1/4] PostgreSQL title_embeddings 데이터 확인..."
    python - <<PY
import os
import sys
sys.path.insert(0, '/app')

# Django 설정
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
import django
django.setup()

from django.db import connection

force_reload = os.getenv("FORCE_DATA_RELOAD", "false").lower() == "true"

with connection.cursor() as cursor:
    # title_embeddings 테이블 존재 여부 확인
    cursor.execute("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables
            WHERE table_name = 'title_embeddings'
        )
    """)
    table_exists = cursor.fetchone()[0]

    if table_exists:
        cursor.execute("SELECT COUNT(*) FROM title_embeddings")
        count = cursor.fetchone()[0]
    else:
        count = 0

    print(f"  └─ title_embeddings 데이터 수: {count}")

    # 강제 재적재 또는 데이터 없을 때
    if force_reload and count > 0:
        print("  └─ FORCE_DATA_RELOAD: 기존 데이터 삭제 중...")
        cursor.execute("TRUNCATE TABLE title_embeddings CASCADE")
        connection.commit()
        print("  └─ ✓ 기존 데이터 삭제 완료")
        count = 0

    if count == 0:
        print("  └─ 데이터 없음, 적재 시작...")
        try:
            from backend.db_pipeline.postgres.ETL.load_title_embeddings import main as load_title
            load_title()
            print("  └─ ✓ title_embeddings 데이터 적재 완료")
        except Exception as e:
            print(f"  └─ ✗ title_embeddings 데이터 적재 실패: {e}")
            import traceback
            traceback.print_exc()
    else:
        print("  └─ ✓ 데이터 이미 존재, 스킵")
PY

    # 2. PostgreSQL korean_history 데이터 적재
    echo "[2/4] PostgreSQL korean_history 데이터 확인..."
    python - <<PY
import os
import sys
sys.path.insert(0, '/app')

# Django 설정
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
import django
django.setup()

from django.db import connection

force_reload = os.getenv("FORCE_DATA_RELOAD", "false").lower() == "true"

with connection.cursor() as cursor:
    cursor.execute("SELECT COUNT(*) FROM korean_history")
    count = cursor.fetchone()[0]
    print(f"  └─ korean_history 데이터 수: {count}")

    # 강제 재적재 또는 데이터 없을 때
    if force_reload and count > 0:
        print("  └─ FORCE_DATA_RELOAD: 기존 데이터 삭제 중...")
        cursor.execute("TRUNCATE TABLE korean_history CASCADE")
        connection.commit()
        print("  └─ ✓ 기존 데이터 삭제 완료")
        count = 0

    if count == 0:
        print("  └─ 데이터 없음, 적재 시작...")
        try:
            from backend.db_pipeline.postgres.ETL.load_to_pgvector import run
            run()
            print("  └─ ✓ PostgreSQL 데이터 적재 완료")
        except Exception as e:
            print(f"  └─ ✗ PostgreSQL 데이터 적재 실패: {e}")
    else:
        print("  └─ ✓ 데이터 이미 존재, 스킵")
PY

    # 3. Neo4j 데이터 적재
    echo "[3/4] Neo4j 데이터 확인..."
    python - <<PY
import os
import sys
sys.path.insert(0, '/app')

neo4j_uri = os.getenv("NEO4J_URI", "bolt://neo4j:7687")
neo4j_user = os.getenv("NEO4J_USER", "neo4j")
neo4j_password = os.getenv("NEO4J_PASSWORD", "password")
force_reload = os.getenv("FORCE_DATA_RELOAD", "false").lower() == "true"

try:
    from neo4j import GraphDatabase
    driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))

    with driver.session() as session:
        result = session.run("MATCH (n) RETURN count(n) as count")
        count = result.single()["count"]
        print(f"  └─ Neo4j 노드 수: {count}")

        # 강제 재적재 또는 데이터 없을 때
        if force_reload and count > 0:
            print("  └─ FORCE_DATA_RELOAD: 기존 노드/엣지 삭제 중...")
            session.run("MATCH (n) DETACH DELETE n")
            print("  └─ ✓ 기존 Neo4j 데이터 삭제 완료")
            count = 0

        if count == 0:
            print("  └─ 데이터 없음, 적재 시작...")
            try:
                from backend.db_pipeline.neo4j.ETL.load_to_neo4j import run_all
                run_all()
                print("  └─ ✓ Neo4j 데이터 적재 완료")
            except Exception as e:
                print(f"  └─ ✗ Neo4j 데이터 적재 실패: {e}")
        else:
            print("  └─ ✓ 데이터 이미 존재, 스킵")

    driver.close()
except Exception as e:
    print(f"  └─ Neo4j 연결 실패 (스킵): {e}")
PY

    # 4. Fuseki 데이터 적재
    echo "[4/4] Fuseki 데이터 확인..."
    python - <<PY
import os
import sys
sys.path.insert(0, '/app')

import requests
from pathlib import Path

# Fuseki 설정 (환경 변수에서 읽기)
fuseki_base_url = os.getenv("FUSEKI_URL", "http://fuseki:3030")
# FUSEKI_URL에서 dataset 부분 분리
if "/korean-history" in fuseki_base_url:
    fuseki_base_url = fuseki_base_url.replace("/korean-history", "")
dataset = "korean-history"
fuseki_user = os.getenv("FUSEKI_USER", "admin")
fuseki_password = os.getenv("FUSEKI_PASSWORD") or os.getenv("FUSEKI_ADMIN_PASSWORD", "fuseki1234")
auth = (fuseki_user, fuseki_password)
force_reload = os.getenv("FORCE_DATA_RELOAD", "false").lower() == "true"

ttl_path = Path("/app/backend/langgraph_fuseki/ontology/instances/korean_history_normalized.ttl")

def upload_ttl_direct(fuseki_url, dataset, ttl_file, auth):
    """TTL 파일을 Fuseki에 직접 업로드"""
    try:
        with open(ttl_file, 'rb') as f:
            response = requests.post(
                f"{fuseki_url}/{dataset}/data",
                auth=auth,
                headers={'Content-Type': 'text/turtle'},
                data=f,
                timeout=300
            )
        return response.status_code, response.text
    except Exception as e:
        return 0, str(e)

try:
    # SPARQL 쿼리로 트리플 수 확인
    query = "SELECT (COUNT(*) as ?count) WHERE { ?s ?p ?o }"
    response = requests.post(
        f"{fuseki_base_url}/{dataset}/sparql",
        auth=auth,
        data={'query': query},
        headers={'Accept': 'application/sparql-results+json'},
        timeout=10
    )

    if response.status_code == 200:
        result = response.json()
        count = int(result['results']['bindings'][0]['count']['value'])
        print(f"  └─ Fuseki 트리플 수: {count}")

        # 강제 재적재 또는 데이터 없을 때
        if force_reload and count > 0:
            print("  └─ FORCE_DATA_RELOAD: 기존 트리플 삭제 중...")
            delete_response = requests.post(
                f"{fuseki_base_url}/{dataset}/update",
                auth=auth,
                headers={'Content-Type': 'application/sparql-update'},
                data='DROP ALL',
                timeout=30
            )
            if delete_response.status_code in [200, 204]:
                print("  └─ ✓ 기존 Fuseki 데이터 삭제 완료")
                count = 0
            else:
                print(f"  └─ ⚠ Fuseki 데이터 삭제 실패 (HTTP {delete_response.status_code})")

        if count == 0:
            print("  └─ 데이터 없음, 적재 시작...")
            if not ttl_path.exists():
                print(f"  └─ ✗ TTL 파일 없음: {ttl_path}")
            else:
                status_code, error_text = upload_ttl_direct(fuseki_base_url, dataset, ttl_path, auth)
                if status_code in [200, 204]:
                    print("  └─ ✓ Fuseki 데이터 적재 완료")
                else:
                    print(f"  └─ ✗ Fuseki 데이터 적재 실패 (HTTP {status_code}): {error_text[:200]}")
        else:
            print("  └─ ✓ 데이터 이미 존재, 스킵")
    else:
        print(f"  └─ Fuseki 쿼리 실패 (HTTP {response.status_code}), 데이터 적재 시도...")
        if ttl_path.exists():
            status_code, error_text = upload_ttl_direct(fuseki_base_url, dataset, ttl_path, auth)
            if status_code in [200, 204]:
                print("  └─ ✓ Fuseki 데이터 적재 완료")
            else:
                print(f"  └─ ✗ Fuseki 데이터 적재 실패 (HTTP {status_code}): {error_text[:200]}")
        else:
            print(f"  └─ ✗ TTL 파일 없음: {ttl_path}")
except Exception as e:
    print(f"  └─ Fuseki 연결 실패 (스킵): {e}")
PY

    echo "=========================================="
    echo "데이터 적재 파이프라인 완료"
    echo "=========================================="
fi

# If no command was passed, default to runserver
if [ $# -eq 0 ]; then
    exec python manage.py runserver 0.0.0.0:8000
else
    exec "$@"
fi
