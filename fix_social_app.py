#!/usr/bin/env python
"""
Google Social App을 정리하고 하나만 남기는 스크립트
Django shell에서 실행: python manage.py shell < fix_social_app.py
"""

import os
from django.contrib.sites.models import Site
from allauth.socialaccount.models import SocialApp

# 모든 Google Social App 삭제
deleted_count = SocialApp.objects.filter(provider='google').delete()[0]
print(f"✓ Deleted {deleted_count} existing Google Social Apps")

# 환경 변수에서 credentials 가져오기
client_id = os.getenv('GOOGLE_OAUTH_CLIENT_ID')
client_secret = os.getenv('GOOGLE_OAUTH_CLIENT_SECRET')

if not client_id or not client_secret:
    print("✗ Error: GOOGLE_OAUTH_CLIENT_ID and GOOGLE_OAUTH_CLIENT_SECRET must be set")
    exit(1)

# 새로 하나만 생성
social_app = SocialApp.objects.create(
    provider='google',
    name='Google',
    client_id=client_id,
    secret=client_secret,
)

# Site에 연결
site = Site.objects.get(id=1)
social_app.sites.add(site)

print(f"✓ Created Google Social App (ID: {social_app.id})")
print(f"✓ Connected to Site: {site.domain}")
print(f"\nTotal Google Social Apps: {SocialApp.objects.filter(provider='google').count()}")
