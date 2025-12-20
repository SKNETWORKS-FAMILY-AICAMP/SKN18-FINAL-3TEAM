# 백그라운드 동작을 위한 Celery 앱

from .celery import app as celery_app

__all__ = ("celery_app",)
