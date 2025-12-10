# backend/db_pipeline/ETL/load_to_pgvector.py

from .transform import preprocess_data, chunk_dataframe
from ..services.db_connection import prepare_vectordb
from ..services.vector_store import create_pgvector_store
from ..config import POSTGRES_CONN_STR, INPUT_CSV, EMBED_MODEL
import pandas as pd
from langchain_openai import OpenAIEmbeddings
from tqdm import tqdm
import psycopg2


def load_raw_data():
    """CSV 파일에서 원본 데이터 로드"""
    print(f"CSV 파일 읽기: {INPUT_CSV}")
    # CSV 필드 크기 제한 증가 및 파싱 오류 처리
    import sys
    import csv
    max_int = sys.maxsize
    while True:
        try:
            csv.field_size_limit(max_int)
            break
        except OverflowError:
            max_int = int(max_int / 10)
    
    # 따옴표 처리 및 오류 행 건너뛰기
    df = pd.read_csv(
        INPUT_CSV, 
        encoding='utf-8',
        quoting=csv.QUOTE_MINIMAL,
        on_bad_lines='skip',  # 잘못된 행 건너뛰기
        engine='python'  # Python 엔진 사용 (더 유연한 파싱)
    )
    return df


def get_embedding():
    """임베딩 모델 반환"""
    return OpenAIEmbeddings(model=EMBED_MODEL)


def clear_existing_data(table_name: str = "korean_history"):
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
    clear_existing_data("korean_history")
    
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
    store = create_pgvector_store(POSTGRES_CONN_STR, "korean_history", get_embedding())
    store.add_texts(texts, metas)

    print("\n[6/6] 데이터 적재 확인")
    try:
        with psycopg2.connect(POSTGRES_CONN_STR) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM korean_history;")
                final_count = cur.fetchone()[0]
                print(f"  └─ 최종 적재된 데이터: {final_count:,}개")
    except Exception as e:
        print(f"  └─ 확인 중 오류: {e}")

    print("\n" + "="*70)
    print("전체 ETL 프로세스 완료")
    print("="*70)


if __name__ == "__main__":
    run()