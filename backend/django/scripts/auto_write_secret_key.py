# 
# .env 파일에 DJANGO_SECRET_KEY를 자동 생성/기록하는 스크립트.

import os
from django.core.management.utils import get_random_secret_key

ENV_PATH = ".env"
KEY_NAME = "DJANGO_SECRET_KEY"

def read_env():
    if not os.path.exists(ENV_PATH):
        return []
    with open(ENV_PATH, "r", encoding="utf-8") as f:
        return f.readlines()

def write_env(lines):
    with open(ENV_PATH, "w", encoding="utf-8") as f:
        f.writelines(lines)

def main():
    lines = read_env()

    # 이미 SECRET_KEY가 있는지 확인
    for line in lines:
        if line.startswith(f"{KEY_NAME}="):
            print("이미 .env 에 SECRET_KEY가 존재합니다. 생성하지 않습니다.")
            return

    # 새 SECRET_KEY 생성
    secret_key = get_random_secret_key()
    new_line = f"{KEY_NAME}={secret_key}\n"

    # 기존 내용 + 새 줄 추가
    lines.append(new_line)
    write_env(lines)

    print(f".env 파일에 {KEY_NAME} 추가 완료!")

if __name__ == "__main__":
    main()