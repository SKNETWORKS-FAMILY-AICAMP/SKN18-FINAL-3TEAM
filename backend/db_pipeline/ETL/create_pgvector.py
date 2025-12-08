from custom_pgvector import CustomPGVector


def create_pgvector_store(connection_string, collection_name, embeddings):
    """PGVector 스토어 생성"""
    try:
        vectorstore = CustomPGVector(
            conn_str=connection_string,
            embedding_fn=embeddings,
            table=collection_name, # 테이블 이름과 매칭
        )
        print(f"PGVector 스토어 '{collection_name}'이 생성되었습니다.")
        return vectorstore
    except Exception as e:
        print(f"PGVector 스토어 생성 중 오류: {e}")
        return None
    
import psycopg2

def ensure_table(conn_str, table, dim):
    with psycopg2.connect(conn_str) as conn, conn.cursor() as cur:
        cur.execute(f"""
            CREATE TABLE IF NOT EXISTS {table} (
                id bigserial PRIMARY KEY,
                content text,
                embedding vector({dim}),
                metadata jsonb
            );
        """)
        conn.commit()