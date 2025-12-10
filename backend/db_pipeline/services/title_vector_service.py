"""
PostgreSQL + pgvector 제목 임베딩 서비스

엔티티 매칭을 위한 제목만 임베딩하여 저장
- OpenAI text-embedding-3-small 모델 사용 (1536 dim)
- 코사인 유사도 기반 검색
- title_embeddings 테이블 사용
"""

import os
from typing import List, Dict
from pathlib import Path
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import execute_values
from openai import OpenAI

# 프로젝트 루트 경로 설정 및 환경변수 로드
project_root = Path(__file__).parent.parent.parent.parent
env_path = project_root / ".env"
load_dotenv(env_path, override=True)

# PostgreSQL 설정 (환경변수에서 로드)
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
POSTGRES_DB = os.getenv("POSTGRES_DB", "sknproject4")
POSTGRES_USER = os.getenv("POSTGRES_USER", "root")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "root1234")

# OpenAI 설정
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
EMBED_MODEL = os.getenv("TITLE_EMBED_MODEL", "text-embedding-3-small")
EMBEDDING_DIM = int(os.getenv("TITLE_EMBED_DIM", "1536"))

# 테이블 설정
TABLE_NAME = os.getenv("TITLE_TABLE_NAME", "title_embeddings")


class TitleVectorService:
    """제목 임베딩 전용 pgvector 검색 서비스"""

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
        """스키마 생성 (pgvector 확장 + title_embeddings 테이블)"""

        if not self.conn:
            self.connect()

        cursor = self.conn.cursor()

        try:
            # ------------------------------------------------------------
            #  1. pgvector 확장 설치
            # ------------------------------------------------------------
            cursor.execute("CREATE EXTENSION IF NOT EXISTS vector;")
            print("  |- pgvector 확장 활성화")

            # ------------------------------------------------------------
            #  2. 기존 테이블 삭제 (옵션)
            # ------------------------------------------------------------
            if drop_existing:
                cursor.execute(f"DROP TABLE IF EXISTS {TABLE_NAME} CASCADE;")
                print(f"  |- 기존 테이블 삭제: {TABLE_NAME}")

            # ------------------------------------------------------------
            #  3. 테이블 생성
            # ------------------------------------------------------------
            cursor.execute(f"""
                CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
                    id SERIAL PRIMARY KEY,
                    title VARCHAR(500) NOT NULL,
                    category VARCHAR(100),
                    embedding vector({EMBEDDING_DIM})
                );
            """)
            print(f"  |- 테이블 생성: {TABLE_NAME}")

            # ------------------------------------------------------------
            #  4. 벡터 인덱스 생성 (HNSW)
            # ------------------------------------------------------------
            cursor.execute(f"""
                CREATE INDEX IF NOT EXISTS {TABLE_NAME}_embedding_idx
                ON {TABLE_NAME}
                USING hnsw (embedding vector_cosine_ops);
            """)
            print(f"  |- 벡터 인덱스 생성 (HNSW)")

            # ------------------------------------------------------------
            #  5. 제목 인덱스 생성
            # ------------------------------------------------------------
            cursor.execute(f"""
                CREATE INDEX IF NOT EXISTS {TABLE_NAME}_title_idx
                ON {TABLE_NAME}(title);
            """)
            print(f"  └─ 제목 인덱스 생성")

            self.conn.commit()
            print(f"  └─ 스키마 생성 완료: {TABLE_NAME}")

        except Exception as e:
            self.conn.rollback()
            print(f"  |- [ERROR] 스키마 생성 실패: {e}")
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

    def insert_entities(self, entities: List[Dict]) -> int:
        """엔티티 배치 삽입 (제목 임베딩)

        Args:
            entities: [{
                "title": "...",
                "category": "..."
            }]

        Returns:
            삽입된 엔티티 수
        """
        if not self.conn:
            self.connect()

        cursor = self.conn.cursor()
        total_inserted = 0

        try:
            # 제목 임베딩 생성 (배치)
            titles = [e["title"] for e in entities]
            embeddings = self.embed_batch(titles)

            # 데이터 삽입
            entity_data = []
            for entity, embedding in zip(entities, embeddings):
                entity_data.append((
                    entity["title"],
                    entity.get("category", ""),
                    embedding
                ))

            execute_values(cursor, f"""
                INSERT INTO {TABLE_NAME} (title, category, embedding)
                VALUES %s
            """, entity_data)

            self.conn.commit()
            total_inserted = len(entities)
            return total_inserted

        except Exception as e:
            self.conn.rollback()
            print(f"  |- [ERROR] 삽입 실패: {e}")
            raise
        finally:
            cursor.close()

    def search(
        self,
        query: str,
        top_k: int = 10,
        threshold: float = 0.5
    ) -> List[Dict]:
        """유사 엔티티 검색 (코사인 유���도)

        Args:
            query: 검색 쿼리 (제목 또는 키워드)
            top_k: 반환할 최대 결과 수
            threshold: 최소 유사도 (0-1)

        Returns:
            [{
                "title": "...",
                "category": "...",
                "similarity": 0.95
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
                    title,
                    category,
                    1 - (embedding <=> %s::vector) AS similarity
                FROM {TABLE_NAME}
                WHERE 1 - (embedding <=> %s::vector) >= %s
                ORDER BY embedding <=> %s::vector
                LIMIT %s;
            """, (query_embedding, query_embedding, threshold, query_embedding, top_k))

            results = []
            for row in cursor.fetchall():
                results.append({
                    "title": row[0],
                    "category": row[1],
                    "similarity": round(row[2], 4)
                })

            return results

        except Exception as e:
            print(f"  |- [ERROR] 검색 실패: {e}")
            return []
        finally:
            cursor.close()

    def search_by_keywords(
        self,
        keywords: List[str],
        top_k_per_keyword: int = 5,
        threshold: float = 0.5
    ) -> List[Dict]:
        """키워드별 유사 엔티티 검색 (중복 제거)

        Args:
            keywords: 검색할 키워드 리스트
            top_k_per_keyword: 키워드당 최대 결과 수
            threshold: 최소 유사도

        Returns:
            중복 제거된 엔티티 리스트
        """
        all_results = {}

        for keyword in keywords:
            results = self.search(keyword, top_k=top_k_per_keyword, threshold=threshold)

            for result in results:
                title = result["title"]
                # 더 높은 점수로 업데이트
                if title not in all_results or result["similarity"] > all_results[title]["similarity"]:
                    result["matched_keyword"] = keyword
                    all_results[title] = result

        # 점수 순 정렬
        sorted_results = sorted(all_results.values(), key=lambda x: x["similarity"], reverse=True)
        return sorted_results

    def get_stats(self) -> Dict:
        """데이터베이스 통계"""
        if not self.conn:
            self.connect()

        cursor = self.conn.cursor()

        try:
            # 총 엔티티 수
            cursor.execute(f"SELECT COUNT(*) FROM {TABLE_NAME};")
            total_entities = cursor.fetchone()[0]

            # 카테고리별 통계
            cursor.execute(f"""
                SELECT category, COUNT(*)
                FROM {TABLE_NAME}
                GROUP BY category
                ORDER BY COUNT(*) DESC;
            """)
            category_stats = dict(cursor.fetchall())

            return {
                "table_name": TABLE_NAME,
                "total_entities": total_entities,
                "category_stats": category_stats
            }

        except Exception as e:
            print(f"  |- [ERROR] 통계 조회 실패: {e}")
            return {}
        finally:
            cursor.close()


# 싱글톤 인스턴스
_title_vector_service = None


def get_title_vector_service() -> TitleVectorService:
    """TitleVectorService 싱글톤 반환"""
    global _title_vector_service
    if _title_vector_service is None:
        _title_vector_service = TitleVectorService()
    return _title_vector_service
