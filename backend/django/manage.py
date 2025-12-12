#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys
from pathlib import Path  # [필수] 경로 조작을 위해 추가

def main():
    """Run administrative tasks."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

    # ------------------------------------------------------------------------
    # [경로 추가 수정] 
    # 'ModuleNotFoundError: No module named backend' 에러 해결을 위한 코드
    # ------------------------------------------------------------------------
    # 현재 manage.py의 위치: .../git용 작업 폴더/backend/django/manage.py
    # 우리가 필요한 루트: .../git용 작업 폴더/ (이곳에 backend 폴더가 있음)
    
    current_path = Path(__file__).resolve()
    
    # .parent (django) -> .parent (backend) -> .parent (git용 작업 폴더)
    # 총 3번 올라가야 'backend' 폴더를 감싸고 있는 최상위 루트가 나옵니다.
    project_root = current_path.parent.parent.parent
    
    if str(project_root) not in sys.path:
        sys.path.append(str(project_root))
    # ------------------------------------------------------------------------

    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()