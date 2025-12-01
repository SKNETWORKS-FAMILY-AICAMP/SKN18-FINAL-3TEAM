"""
CSV 데이터를 Milvus에 적재하는 ETL 스크립트

encykorea_cleaned6.csv → Milvus 벡터 DB
- title 컬럼만 임베딩 (엔티티 매칭용)
- 배치 처리로 효율적 적재
"""

import os
import sys
import csv
import time
from pathlib import Path
from typing import List, Dict

# 상위 경로 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.milvus_service import get_milvus_service, MilvusService


# 경로 설정
DATA_DIR = Path(__file__).parent.parent / "data"
CSV_FILE = DATA_DIR / "encykorea_cleaned6.csv"
BATCH_SIZE = 100


def load_csv_data(csv_path: Path) -> List[Dict]:
    """CSV 파일 로드"""
    entities = []
    
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        
        for row in reader:
            entities.append({
                "title": row.get("title", "").strip(),
                "category": row.get("category", "").strip(),
                "summary": row.get("summary", "").strip()
            })
    
    # 빈 title 필터링
    entities = [e for e in entities if e["title"]]
    
    return entities


def main():
    """메인 ETL 프로세스"""
    
    print("=" * 60)
    print("📦 Milvus 데이터 적재 시작")
    print("=" * 60)
    
    # 1. CSV 로드
    print(f"\n1️⃣ CSV 파일 로드: {CSV_FILE}")
    
    if not CSV_FILE.exists():
        print(f"❌ 파일이 없습니다: {CSV_FILE}")
        return
    
    entities = load_csv_data(CSV_FILE)
    print(f"   ✅ {len(entities)}개 엔티티 로드")
    
    # 샘플 출력
    print(f"\n   📋 샘플 데이터:")
    for i, e in enumerate(entities[:3]):
        print(f"      {i+1}. [{e['category']}] {e['title']}")
    
    # 2. Milvus 연결
    print(f"\n2️⃣ Milvus 연결...")
    service = get_milvus_service()
    
    if not service.connect():
        print("❌ Milvus 연결 실패. Docker 컨테이너를 확인하세요.")
        print("   docker-compose up -d milvus")
        return
    
    # 3. 컬렉션 생성
    print(f"\n3️⃣ 컬렉션 생성...")
    service.create_collection(drop_existing=True)
    
    # 4. 임베딩 모델 로드
    print(f"\n4️⃣ 임베딩 모델 로드...")
    service.load_model()
    
    # 5. 배치 삽입
    print(f"\n5️⃣ 데이터 적재 (배치 크기: {BATCH_SIZE})...")
    
    start_time = time.time()
    total_inserted = 0
    
    for i in range(0, len(entities), BATCH_SIZE):
        batch = entities[i:i + BATCH_SIZE]
        batch_num = i // BATCH_SIZE + 1
        total_batches = (len(entities) + BATCH_SIZE - 1) // BATCH_SIZE
        
        print(f"\n   📦 배치 {batch_num}/{total_batches} ({len(batch)}개)")
        
        try:
            inserted = service.insert_entities(batch)
            total_inserted += inserted
        except Exception as e:
            print(f"   ❌ 배치 삽입 실패: {e}")
            continue
    
    elapsed = time.time() - start_time
    
    # 6. 결과 확인
    print(f"\n6️⃣ 적재 결과")
    print("=" * 60)
    
    stats = service.get_collection_stats()
    print(f"   컬렉션: {stats.get('name')}")
    print(f"   총 엔티티: {stats.get('num_entities')}개")
    print(f"   소요 시간: {elapsed:.1f}초")
    print(f"   처리 속도: {len(entities) / elapsed:.1f}개/초")
    
    # 7. 검색 테스트
    print(f"\n7️⃣ 검색 테스트")
    print("-" * 40)
    
    test_queries = ["환국", "이순신", "임진왜란", "숙종", "조선"]
    
    for query in test_queries:
        results = service.search(query, top_k=3, threshold=0.3)
        print(f"\n   🔍 '{query}' 검색 결과:")
        
        if results:
            for r in results:
                print(f"      - {r['title']} (점수: {r['score']:.3f})")
        else:
            print(f"      - 결과 없음")
    
    # 8. 연결 해제
    service.disconnect()
    
    print("\n" + "=" * 60)
    print("✅ Milvus 데이터 적재 완료!")
    print("=" * 60)


if __name__ == "__main__":
    main()

