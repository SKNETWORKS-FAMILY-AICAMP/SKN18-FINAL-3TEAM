#!/usr/bin/env python
"""
Standalone script to add video_url column to PostgreSQL
"""
import os
import sys
import django

# Django 설정
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.append('/app/backend/django')
django.setup()

from django.db import connection

def add_video_url_column():
    """video 테이블에 video_url 컬럼 추가"""
    with connection.cursor() as cursor:
        try:
            cursor.execute("""
                ALTER TABLE video
                ADD COLUMN IF NOT EXISTS video_url TEXT;
            """)
            print("✅ Successfully added video_url column to video table")
        except Exception as e:
            print(f"❌ Error: {e}")
            raise

if __name__ == "__main__":
    add_video_url_column()
