"""
Fuseki 인증 테스트 command
"""
import requests
from django.core.management.base import BaseCommand
import os


class Command(BaseCommand):
    help = 'Test Fuseki authentication'

    def handle(self, *args, **options):
        fuseki_url = os.getenv("FUSEKI_URL", "http://fuseki.skn18.local:3030/korean-history")
        base_url = fuseki_url.replace("/korean-history", "")

        user = os.getenv("FUSEKI_USER", "admin")
        password = os.getenv("FUSEKI_ADMIN_PASSWORD", "fuseki1234")

        self.stdout.write(f"Testing Fuseki connection:")
        self.stdout.write(f"  URL: {base_url}")
        self.stdout.write(f"  User: {user}")
        self.stdout.write(f"  Password: {'***' if password else 'None'}")

        # 1. Ping 테스트
        self.stdout.write("\n[1] Testing /$/ping (no auth)...")
        try:
            response = requests.get(f"{base_url}/$/ping", timeout=5)
            self.stdout.write(self.style.SUCCESS(f"  ✓ Ping: {response.status_code}"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"  ✗ Ping failed: {e}"))

        # 2. Server status (인증 필요)
        self.stdout.write("\n[2] Testing /$/server (no auth)...")
        try:
            response = requests.get(f"{base_url}/$/server", timeout=5)
            self.stdout.write(f"  Status: {response.status_code}")
            if response.status_code == 200:
                self.stdout.write(self.style.SUCCESS(f"  ✓ No auth required"))
            elif response.status_code == 401:
                self.stdout.write(f"  ! Auth required, retrying with credentials...")
                response = requests.get(f"{base_url}/$/server", auth=(user, password), timeout=5)
                self.stdout.write(f"  With auth: {response.status_code}")
                if response.status_code == 200:
                    self.stdout.write(self.style.SUCCESS(f"  ✓ Auth successful!"))
                else:
                    self.stdout.write(self.style.ERROR(f"  ✗ Auth failed: {response.text[:200]}"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"  ✗ Failed: {e}"))

        # 3. Datasets 목록 (관리자 권한 필요)
        self.stdout.write("\n[3] Testing /$/datasets (no auth)...")
        try:
            response = requests.get(f"{base_url}/$/datasets", timeout=5)
            self.stdout.write(f"  Status: {response.status_code}")
            if response.status_code == 200:
                self.stdout.write(self.style.SUCCESS(f"  ✓ No auth required"))
                self.stdout.write(f"  Datasets: {response.json()}")
            elif response.status_code == 401:
                self.stdout.write(f"  ! Auth required, retrying with credentials...")
                response = requests.get(f"{base_url}/$/datasets", auth=(user, password), timeout=5)
                self.stdout.write(f"  With auth: {response.status_code}")
                if response.status_code == 200:
                    self.stdout.write(self.style.SUCCESS(f"  ✓ Auth successful!"))
                    self.stdout.write(f"  Datasets: {response.json()}")
                else:
                    self.stdout.write(self.style.ERROR(f"  ✗ Auth failed: {response.text[:200]}"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"  ✗ Failed: {e}"))

        # 4. Dataset 생성 시도
        self.stdout.write("\n[4] Testing POST /$/datasets (create korean-history)...")
        try:
            # 먼저 인증 없이
            response = requests.post(
                f"{base_url}/$/datasets",
                data={'dbName': 'korean-history', 'dbType': 'tdb2'},
                timeout=30
            )
            self.stdout.write(f"  No auth: {response.status_code}")

            if response.status_code == 401:
                # 인증 추가
                response = requests.post(
                    f"{base_url}/$/datasets",
                    auth=(user, password),
                    data={'dbName': 'korean-history', 'dbType': 'tdb2'},
                    timeout=30
                )
                self.stdout.write(f"  With auth: {response.status_code}")
                if response.status_code in [200, 201]:
                    self.stdout.write(self.style.SUCCESS(f"  ✓ Dataset created!"))
                elif response.status_code == 409:
                    self.stdout.write(self.style.WARNING(f"  ! Dataset already exists"))
                else:
                    self.stdout.write(self.style.ERROR(f"  ✗ Failed: {response.text[:500]}"))
            elif response.status_code in [200, 201]:
                self.stdout.write(self.style.SUCCESS(f"  ✓ Dataset created (no auth needed)!"))
            elif response.status_code == 409:
                self.stdout.write(self.style.WARNING(f"  ! Dataset already exists"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"  ✗ Failed: {e}"))
