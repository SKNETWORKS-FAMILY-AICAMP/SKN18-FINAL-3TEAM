"""
PostgreSQL + pgvector 데이터 적재 스크립트

transformed_chunks.json → PostgreSQL + pgvector
- OpenAI text-embedding-3-small 임베딩 (1536 dim)
- 배치 처리로 효율적 적재
- 청크 단위 벡터 검색 지원
"""

import json
import time
from pathlib import Path
import sys

# 상위 경로 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.postgres_service import get_postgres_service


# 경로 설정
DATA_DIR = Path(__file__).parent.parent / "data"
INPUT_JSON = DATA_DIR / "transformed_chunks.json"
BATCH_SIZE = 50  # 문서 배치 크기 (청크는 내부에서 배치 처리)


def load_transformed_data(json_path: Path) -> dict:
    """변환된 JSON 데이터 로드"""
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data


def main():
    """메인 ETL 프로세스"""

    print("=" * 70)
    print("📦 PostgreSQL + pgvector 데이터 적재 시작")
    print("=" * 70)

    # 1. JSON 로드
    print(f"\n1️⃣ JSON 파일 로드: {INPUT_JSON}")

    if not INPUT_JSON.exists():
        print(f"❌ 파일이 없습니다: {INPUT_JSON}")
        print(f"   먼저 transform.py를 실행하세요:")
        print(f"   python backend/db_pipeline/ETL/transform.py")
        return

    data = load_transformed_data(INPUT_JSON)
    documents = data.get("documents", [])
    total_chunks = sum(doc["num_chunks"] for doc in documents)

    print(f"   ✅ {len(documents):,}개 문서, {total_chunks:,}개 청크")

    # 2. PostgreSQL 연결
    print(f"\n2️⃣ PostgreSQL 연결...")
    service = get_postgres_service()

    if not service.connect():
        print("❌ PostgreSQL 연결 실패. Docker 컨테이너를 확인하세요.")
        print("   docker-compose up -d postgres")
        return

    print("   ✅ PostgreSQL 연결 성공")

    # 3. 스키마 생성
    print(f"\n3️⃣ 스키마 생성 (pgvector 확장 + 테이블)...")
    try:
        service.create_schema(drop_existing=True)
    except Exception as e:
        print(f"❌ 스키마 생성 실패: {e}")
        service.disconnect()
        return

    # 4. OpenAI 클라이언트 초기화
    print(f"\n4️⃣ OpenAI 임베딩 모델 초기화...")
    try:
        service.init_openai_client()
        print("   ✅ OpenAI 클라이언트 초기화 완료")
    except Exception as e:
        print(f"❌ OpenAI 초기화 실패: {e}")
        print("   .env 파일에 OPENAI_API_KEY가 설정되었는지 확인하세요.")
        service.disconnect()
        return

    # 5. 배치 삽입
    print(f"\n5️⃣ 데이터 적재 중... (OpenAI 임베딩 생성)")

    start_time = time.time()
    total_chunks_inserted = 0

    for i in range(0, len(documents), BATCH_SIZE):
        batch = documents[i:i + BATCH_SIZE]
        batch_num = i // BATCH_SIZE + 1
        total_batches = (len(documents) + BATCH_SIZE - 1) // BATCH_SIZE

        print(f"   배치 {batch_num}/{total_batches} 처리 중...")

        try:
            chunks_inserted = service.insert_documents(batch)
            total_chunks_inserted += chunks_inserted
        except Exception as e:
            print(f"   ❌ 배치 {batch_num} 실패: {e}")
            continue

    elapsed = time.time() - start_time

    # 6. 결과
    stats = service.get_stats()
    print(f"\n✅ 적재 완료!")
    print(f"   ├─ 문서: {stats.get('total_documents', 0):,}개")
    print(f"   ├─ 청크: {stats.get('total_chunks', 0):,}개")
    print(f"   └─ 소요시간: {elapsed:.1f}초")

    # 7. 검색 테스트
    print(f"\n🔍 벡터 검색 테스트:")
    results = service.search("이순신 임진왜란", top_k=3, threshold=0.3)
    for r in results:
        print(f"   - [{r['category']}] {r['title']} (점수: {r['score']:.3f})")

    service.disconnect()
    print(f"\n{'='*70}")
    print("✅ PostgreSQL + pgvector ETL 완료")
    print(f"{'='*70}")


if __name__ == "__main__":
    main()
