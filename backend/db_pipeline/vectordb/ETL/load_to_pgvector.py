# backend/db_pipeline/ETL/load_to_pgvector.py

from backend.db_pipeline.common.transform import preprocess_data, chunk_dataframe
from backend.db_pipeline.vectordb.services.db_connection import prepare_vectordb
from backend.db_pipeline.vectordb.services.vector_store import create_pgvector_store
from backend.db_pipeline.common.config import POSTGRES_CONN_STR, HISTORY_TABLE_NAME
from backend.db_pipeline.common.load_raw_data import load_raw_data
from backend.db_pipeline.common.embedding_model import get_embedding

from tqdm import tqdm
import psycopg2


def clear_existing_data(table_name: str = HISTORY_TABLE_NAME):
    """기존 데이터가 있으면 삭제"""
    try:
        with psycopg2.connect(POSTGRES_CONN_STR) as conn:
            with conn.cursor() as cur:
                # 테이블 존재 여부 확인
                cur.execute("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_name = %s
                    );
                """, (table_name,))
                
                table_exists = cur.fetchone()[0]
                
                if table_exists:
                    # 데이터 개수 확인
                    cur.execute(f"SELECT COUNT(*) FROM {table_name};")
                    count = cur.fetchone()[0]
                    
                    if count > 0:
                        print(f"  └─ 기존 데이터 발견: {count:,}개")
                        print(f"  └─ 기존 데이터 삭제 중...")
                        cur.execute(f"TRUNCATE TABLE {table_name} CASCADE;")
                        conn.commit()
                        print(f"  └─ 기존 데이터 삭제 완료")
                    else:
                        print(f"  └─ 기존 데이터 없음 (테이블은 존재하지만 비어있음)")
                else:
                    print(f"  └─ 테이블이 존재하지 않음 (새로 생성됩니다)")
                    
    except Exception as e:
        print(f"  └─ 기존 데이터 확인 중 오류 발생: {e}")
        print(f"  └─ 계속 진행합니다...")


def run():
    """원본 데이터 로드 → 전처리 → 청킹 → 벡터 DB 저장"""
    print("="*70)
    print("ETL Pipeline: 데이터 로드 → 전처리 → 청킹 → 임베딩 → DB 저장")
    print("="*70)
    
    print("\n[0/6] 기존 데이터 확인 및 삭제")
    clear_existing_data(HISTORY_TABLE_NAME)
    
    print("\n[1/6] PostgreSQL pgvector 확장 설정")
    prepare_vectordb(POSTGRES_CONN_STR)
    
    print("\n[2/6] CSV 파일 로드")
    df = load_raw_data()
    print(f"  └─ 로드된 행 수: {len(df):,}개")
    
    print("\n[3/6] 데이터 전처리")
    df = preprocess_data(df)
    print(f"  └─ 전처리 완료: {len(df):,}개 행")
    
    print("\n[4/6] 텍스트 청킹")
    chunks = chunk_dataframe(df)
    print(f"  └─ 생성된 청크 수: {len(chunks):,}개")

    texts = [c["text"] for c in chunks]
    metas = [c["metadata"] for c in chunks]

    print("\n[5/6] 임베딩 생성 및 벡터 DB 저장")
    store = create_pgvector_store(POSTGRES_CONN_STR, HISTORY_TABLE_NAME, get_embedding())
    store.add_texts(texts, metas)

    print("\n[6/6] 데이터 적재 확인")
    try:
        with psycopg2.connect(POSTGRES_CONN_STR) as conn:
            with conn.cursor() as cur:
                cur.execute(f"SELECT COUNT(*) FROM {HISTORY_TABLE_NAME};")
                final_count = cur.fetchone()[0]
                print(f"  └─ 최종 적재된 데이터: {final_count:,}개")
    except Exception as e:
        print(f"  └─ 확인 중 오류: {e}")

    print("\n" + "="*70)
    print("전체 ETL 프로세스 완료")
    print("="*70)


if __name__ == "__main__":
    run()
