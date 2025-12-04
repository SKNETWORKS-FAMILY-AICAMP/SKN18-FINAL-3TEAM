"""
PostgreSQL + pgvector 벡터 데이터베이스 서비스

문서 청크 임베딩 저장 및 유사도 검색
- OpenAI text-embedding-3-small 모델 사용 (1536 dim)
- 코사인 유사도 기반 검색
- 청크 단위 검색 + 문서 메타데이터
"""

import os
from typing import List, Dict, Optional
from pathlib import Path
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import execute_values
from openai import OpenAI

# .env 로드
env_path = Path(__file__).parent.parent.parent.parent / ".env"
load_dotenv(env_path, override=True)

# 설정
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
POSTGRES_DB = os.getenv("POSTGRES_DB", "sknproject4")
POSTGRES_USER = os.getenv("POSTGRES_USER", "root")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "root1234")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
EMBED_MODEL = "text-embedding-3-small"  # 1536 dimensions
EMBEDDING_DIM = 1536


class PostgresVectorService:
    """PostgreSQL + pgvector 벡터 검색 서비스"""

    def __init__(self):
        self.conn = None
        self.openai_client = None

    def connect(self) -> bool:
        """PostgreSQL 연결"""
        try:
            self.conn = psycopg2.connect(
                host=POSTGRES_HOST,
                port=POSTGRES_PORT,
                dbname=POSTGRES_DB,
                user=POSTGRES_USER,
                password=POSTGRES_PASSWORD
            )
            return True
        except Exception as e:
            print(f"PostgreSQL 연결 실패: {e}")
            return False

    def disconnect(self):
        """PostgreSQL 연결 해제"""
        if self.conn:
            self.conn.close()
            self.conn = None

    def init_openai_client(self):
        """OpenAI 클라이언트 초기화"""
        if self.openai_client is None:
            self.openai_client = OpenAI(api_key=OPENAI_API_KEY)
        return self.openai_client

    def create_schema(self, drop_existing: bool = False):
        """스키마 생성 (pgvector 확장 + 테이블)"""

        if not self.conn:
            self.connect()

        cursor = self.conn.cursor()

        try:
            # 1. pgvector 확장 설치
            cursor.execute("CREATE EXTENSION IF NOT EXISTS vector;")
            print("✅ pgvector 확장 활성화")

            # 2. 기존 테이블 삭제
            if drop_existing:
                cursor.execute("DROP TABLE IF EXISTS document_chunks CASCADE;")
                cursor.execute("DROP TABLE IF EXISTS documents CASCADE;")
                print("🗑️ 기존 테이블 삭제")

            # 3. documents 테이블 생성 (문서 메타데이터)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS documents (
                    doc_id VARCHAR(50) PRIMARY KEY,
                    category VARCHAR(100),
                    title VARCHAR(500),
                    summary TEXT,
                    contents_length INTEGER,
                    num_chunks INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # 4. document_chunks 테이블 생성 (청크 + 임베딩)
            cursor.execute(f"""
                CREATE TABLE IF NOT EXISTS document_chunks (
                    id SERIAL PRIMARY KEY,
                    doc_id VARCHAR(50) REFERENCES documents(doc_id) ON DELETE CASCADE,
                    chunk_id INTEGER,
                    text TEXT,
                    start_pos INTEGER,
                    end_pos INTEGER,
                    embedding vector({EMBEDDING_DIM}),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # 5. 인덱스 생성 (벡터 검색 최적화)
            # HNSW: Hierarchical Navigable Small World (고속 근사 검색)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS document_chunks_embedding_idx
                ON document_chunks
                USING hnsw (embedding vector_cosine_ops);
            """)

            # 6. doc_id 인덱스 (문서별 청크 조회용)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS document_chunks_doc_id_idx
                ON document_chunks(doc_id);
            """)

            self.conn.commit()
            print("✅ 스키마 생성 완료")

        except Exception as e:
            self.conn.rollback()
            print(f"❌ 스키마 생성 실패: {e}")
            raise
        finally:
            cursor.close()

    def embed_text(self, text: str) -> List[float]:
        """텍스트 임베딩 생성 (OpenAI)"""
        if self.openai_client is None:
            self.init_openai_client()

        # 빈 텍스트 처리
        if not text or not text.strip():
            return [0.0] * EMBEDDING_DIM

        response = self.openai_client.embeddings.create(
            model=EMBED_MODEL,
            input=text
        )

        return response.data[0].embedding

    def embed_batch(self, texts: List[str], batch_size: int = 100) -> List[List[float]]:
        """배치 임베딩 생성 (API 효율성)

        Args:
            texts: 임베딩할 텍스트 리스트
            batch_size: OpenAI API 배치 크기 (최대 2048)

        Returns:
            임베딩 벡터 리스트
        """
        if self.openai_client is None:
            self.init_openai_client()

        all_embeddings = []

        # 빈 텍스트 필터링 및 인덱스 매핑
        valid_indices = []
        valid_texts = []

        for i, text in enumerate(texts):
            if text and text.strip():
                valid_indices.append(i)
                valid_texts.append(text)

        # 배치 처리
        for i in range(0, len(valid_texts), batch_size):
            batch = valid_texts[i:i + batch_size]

            response = self.openai_client.embeddings.create(
                model=EMBED_MODEL,
                input=batch
            )

            batch_embeddings = [item.embedding for item in response.data]
            all_embeddings.extend(batch_embeddings)

        # 원래 순서대로 재구성 (빈 텍스트는 zero vector)
        final_embeddings = []
        valid_idx = 0

        for i in range(len(texts)):
            if i in valid_indices:
                final_embeddings.append(all_embeddings[valid_idx])
                valid_idx += 1
            else:
                final_embeddings.append([0.0] * EMBEDDING_DIM)

        return final_embeddings

    def insert_documents(self, documents: List[Dict]) -> int:
        """문서 배치 삽입 (메타데이터 + 청크 + 임베딩)

        Args:
            documents: [{
                "doc_id": "doc_0",
                "category": "물품",
                "title": "가",
                "summary": "...",
                "contents_length": 1234,
                "num_chunks": 3,
                "chunks": [
                    {"chunk_id": 0, "text": "...", "start": 0, "end": 500},
                    ...
                ]
            }]

        Returns:
            삽입된 총 청크 수
        """
        if not self.conn:
            self.connect()

        cursor = self.conn.cursor()
        total_chunks = 0

        try:
            for doc in documents:
                doc_id = doc["doc_id"]

                # 1. documents 테이블 삽입
                cursor.execute("""
                    INSERT INTO documents (doc_id, category, title, summary, contents_length, num_chunks)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (doc_id) DO NOTHING;
                """, (
                    doc_id,
                    doc.get("category", ""),
                    doc.get("title", ""),
                    doc.get("summary", ""),
                    doc.get("contents_length", 0),
                    doc.get("num_chunks", 0)
                ))

                # 2. 청크 임베딩 생성 (배치)
                chunks = doc.get("chunks", [])
                chunk_texts = [chunk["text"] for chunk in chunks]

                if chunk_texts:
                    embeddings = self.embed_batch(chunk_texts)

                    # 3. document_chunks 테이블 삽입
                    chunk_data = []
                    for chunk, embedding in zip(chunks, embeddings):
                        chunk_data.append((
                            doc_id,
                            chunk["chunk_id"],
                            chunk["text"],
                            chunk["start"],
                            chunk["end"],
                            embedding
                        ))

                    execute_values(cursor, """
                        INSERT INTO document_chunks (doc_id, chunk_id, text, start_pos, end_pos, embedding)
                        VALUES %s
                    """, chunk_data)

                    total_chunks += len(chunks)

            self.conn.commit()
            return total_chunks

        except Exception as e:
            self.conn.rollback()
            print(f"❌ 삽입 실패: {e}")
            raise
        finally:
            cursor.close()

    def search(
        self,
        query: str,
        top_k: int = 10,
        threshold: float = 0.5
    ) -> List[Dict]:
        """유사 청크 검색 (코사인 유사도)

        Args:
            query: 검색 쿼리
            top_k: 반환할 최대 결과 수
            threshold: 최소 유사도 (0-1)

        Returns:
            [{
                "doc_id": "doc_0",
                "title": "가",
                "category": "물품",
                "chunk_id": 0,
                "text": "...",
                "score": 0.95
            }]
        """
        if not self.conn:
            self.connect()

        cursor = self.conn.cursor()

        try:
            # 쿼리 임베딩
            query_embedding = self.embed_text(query)

            # 코사인 유사도 검색 (1 - cosine_distance)
            cursor.execute(f"""
                SELECT
                    dc.doc_id,
                    d.title,
                    d.category,
                    dc.chunk_id,
                    dc.text,
                    1 - (dc.embedding <=> %s::vector) AS score
                FROM document_chunks dc
                JOIN documents d ON dc.doc_id = d.doc_id
                WHERE 1 - (dc.embedding <=> %s::vector) >= %s
                ORDER BY dc.embedding <=> %s::vector
                LIMIT %s;
            """, (query_embedding, query_embedding, threshold, query_embedding, top_k))

            results = []
            for row in cursor.fetchall():
                results.append({
                    "doc_id": row[0],
                    "title": row[1],
                    "category": row[2],
                    "chunk_id": row[3],
                    "text": row[4],
                    "score": round(row[5], 4)
                })

            return results

        except Exception as e:
            print(f"❌ 검색 실패: {e}")
            return []
        finally:
            cursor.close()

    def get_stats(self) -> Dict:
        """데이터베이스 통계"""
        if not self.conn:
            self.connect()

        cursor = self.conn.cursor()

        try:
            # 문서 수
            cursor.execute("SELECT COUNT(*) FROM documents;")
            num_docs = cursor.fetchone()[0]

            # 청크 수
            cursor.execute("SELECT COUNT(*) FROM document_chunks;")
            num_chunks = cursor.fetchone()[0]

            # 평균 청크 수
            cursor.execute("SELECT AVG(num_chunks) FROM documents;")
            avg_chunks = cursor.fetchone()[0] or 0

            return {
                "total_documents": num_docs,
                "total_chunks": num_chunks,
                "avg_chunks_per_doc": round(avg_chunks, 2)
            }

        except Exception as e:
            print(f"❌ 통계 조회 실패: {e}")
            return {}
        finally:
            cursor.close()


# 싱글톤 인스턴스
_postgres_service = None


def get_postgres_service() -> PostgresVectorService:
    """PostgreSQL 서비스 싱글톤 반환"""
    global _postgres_service
    if _postgres_service is None:
        _postgres_service = PostgresVectorService()
    return _postgres_service
