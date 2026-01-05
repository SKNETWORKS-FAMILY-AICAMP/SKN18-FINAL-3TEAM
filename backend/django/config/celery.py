import os
import sys
from pathlib import Path

# ------------------------------------------------------------------------
# [경로 추가] Celery에서 'backend' 모듈을 찾을 수 있도록 프로젝트 루트 추가
# ------------------------------------------------------------------------
current_path = Path(__file__).resolve()
# .parent (config) -> .parent (django) -> .parent (backend) -> .parent (프로젝트 루트)
project_root = current_path.parent.parent.parent.parent

if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
# ------------------------------------------------------------------------

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = Celery("config")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

# Django 앱이 아닌 backend 모듈의 task를 명시적으로 import
# autodiscover_tasks()는 INSTALLED_APPS 내에서만 찾기 때문에
# backend.langgraph_recommendation.tasks는 수동으로 import 필요
try:
    import backend.langgraph_recommendation.tasks  # noqa: F401
except ImportError as e:
    print(f"Warning: Could not import backend.langgraph_recommendation.tasks: {e}")
