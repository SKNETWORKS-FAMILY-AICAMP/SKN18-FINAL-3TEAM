"""
CSV 데이터를 pgvector에 제목만 임베딩하여 적재하는 ETL 스크립트

encykorea_cleaned6.csv → PostgreSQL title_embeddings 테이블
- title 컬럼만 임베딩 (엔티티 매칭용)
- OpenAI text-embedding-3-small 사용
- 배치 처리로 효율적 적재
"""

import os
import sys
import time
from typing import List, Dict
from dotenv import load_dotenv

# 프로젝트 루트 경로 설정
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
sys.path.insert(0, os.path.join(project_root, "backend"))

# 환경변수 로드
env_path = os.path.join(project_root, ".env")
load_dotenv(env_path, override=True)

from backend.db_pipeline.postgres.services.title_vector_service import get_title_vector_service, TitleVectorService
from backend.db_pipeline.common.load_raw_data import load_raw_data
from backend.db_pipeline.common.config import INPUT_CSV

# 경로 설정 (모듈 방식)
CSV_FILE = INPUT_CSV
BATCH_SIZE = int(os.getenv("BATCH_SIZE", "100"))


def main():
    """메인 ETL 프로세스"""

    print("=" * 60)
    print("PostgreSQL title_embeddings 데이터 적재 시작")
    print("=" * 60)

    # ------------------------------------------------------------
    #  1. CSV 파일 로드
    # ------------------------------------------------------------
    print("\n[1/4] CSV 파일 로드")
    print(f"  |- 파일 경로: {CSV_FILE}")

    if not os.path.exists(CSV_FILE):
        print(f"  |- [ERROR] 파일이 없습니다: {CSV_FILE}")
        return

    df = load_raw_data(CSV_FILE, encoding="utf-8-sig")

    # title/category/summary 추출 후 빈 제목 제거
    entities: List[Dict] = []
    for row in df.itertuples(index=False):
        title = getattr(row, "title", "") or ""
        category = getattr(row, "category", "") or ""
        summary = getattr(row, "summary", "") or ""

        title = str(title).strip()
        category = str(category).strip()
        summary = str(summary).strip()

        if not title:
            continue

        entities.append({
            "title": title,
            "category": category,
            "summary": summary,
        })

    print(f"  |- 로드 완료: {len(entities)}개 엔티티")

    # 샘플 출력
    print(f"  |- 샘플 데이터:")
    for i, e in enumerate(entities[:3]):
        if i == len(entities[:3]) - 1:
            print(f"  |   └─ [{e['category']}] {e['title']}")
        else:
            print(f"  |   |- [{e['category']}] {e['title']}")

    # ------------------------------------------------------------
    #  2. PostgreSQL 연결 및 스키마 생성
    # ------------------------------------------------------------
    print("\n[2/4] PostgreSQL 연결 및 스키마 생성")
    service = get_title_vector_service()

    if not service.connect():
        print("  |- [ERROR] PostgreSQL 연결 실패")
        return

    print("  └─ 연결 성공")
    service.create_schema(drop_existing=True)

    # ------------------------------------------------------------
    #  3. 데이터 적재 (배치 처리)
    # ------------------------------------------------------------
    print(f"\n[3/4] 데이터 적재 (배치 크기: {BATCH_SIZE})")

    start_time = time.time()
    total_inserted = 0

    for i in range(0, len(entities), BATCH_SIZE):
        batch = entities[i:i + BATCH_SIZE]
        batch_num = i // BATCH_SIZE + 1
        total_batches = (len(entities) + BATCH_SIZE - 1) // BATCH_SIZE

        print(f"  |- 배치 {batch_num}/{total_batches} ({len(batch)}개)")

        try:
            inserted = service.insert_entities(batch)
            total_inserted += inserted
            print(f"  |   |- 삽입 완료: {inserted}개")
        except Exception as e:
            print(f"  |   |- [ERROR] 배치 삽입 실패: {e}")
            continue

    elapsed = time.time() - start_time

    # ------------------------------------------------------------
    #  4. 적재 결과 확인
    # ------------------------------------------------------------
    print("\n[4/4] 적재 결과")
    print("-" * 60)

    stats = service.get_stats()
    print(f"  |- 테이블: {stats.get('table_name')}")
    print(f"  |- 총 엔티티: {stats.get('total_entities')}개")
    print(f"  |- 소요 시간: {elapsed:.1f}초")
    print(f"  └─ 처리 속도: {len(entities) / elapsed:.1f}개/초")

    # 카테고리별 통계
    category_stats = stats.get('category_stats', {})
    if category_stats:
        print(f"  |- 카테고리별 통계:")
        category_items = list(category_stats.items())[:5]
        for idx, (category, count) in enumerate(category_items):
            if idx == len(category_items) - 1:
                print(f"  |   └─ {category}: {count}개")
            else:
                print(f"  |   |- {category}: {count}개")

    # 연결 해제
    service.disconnect()

    print("\n" + "=" * 60)
    print("PostgreSQL title_embeddings 데이터 적재 완료")
    print("=" * 60)


if __name__ == "__main__":
    main()
