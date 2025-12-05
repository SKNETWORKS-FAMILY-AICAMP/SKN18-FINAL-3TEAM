import psycopg2
from pgvector.psycopg2 import register_vector

# 데이터베이스 연결 및 pgvector 확장 활성화
def prepare_vectordb(connection_string):
    """PostgreSQL에 pgvector 확장을 설치하고 활성화"""
    try:
        with psycopg2.connect(connection_string) as conn:
            conn.autocommit = True
            register_vector(conn)
            with conn.cursor() as cursor:
                cursor.execute("CREATE EXTENSION IF NOT EXISTS vector;")
        print("pgvector 확장 설치 완료")
    except Exception as e:
        print(f"pgvector 설정 중 오류 발생: {e}")
        print("PostgreSQL이 실행 중이고 연결 정보가 올바른지 확인하세요.")