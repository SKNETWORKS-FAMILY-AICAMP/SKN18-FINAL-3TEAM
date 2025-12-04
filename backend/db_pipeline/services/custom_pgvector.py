from langchain_core.vectorstores.base import VectorStore
from typing import List, Dict, Any, Optional, Tuple
import json
from langchain_core.documents import Document
from psycopg2.extras import Json
import psycopg2
from pgvector.psycopg2 import register_vector
import time

class CustomPGVector(VectorStore):
    def __init__(self, conn_str: str, embedding_fn, table: str = "vectordb"):
        self.conn = psycopg2.connect(conn_str)
        register_vector(self.conn)
        self.embedding_fn = embedding_fn
        self.table = table


    @classmethod
    def from_texts(
        cls,
        texts: List[str],
        embedding_fn,
        metadatas: Optional[List[Dict[str, Any]]] = None,
        conn_str: str = None,
        table: str = "vectordb",
        **kwargs,
    ):
        store = cls(conn_str=conn_str, embedding_fn=embedding_fn, table=table)
        store.add_texts(texts, metadatas=metadatas)
        return store

    import time

    def add_texts(self, texts, metadatas=None, batch_size=50, sleep_sec=1.0):
        metadatas = metadatas or [{} for _ in texts]

        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i:i+batch_size]
            batch_metas = metadatas[i:i+batch_size]

            embeddings = self.embedding_fn.embed_documents(batch_texts)

            with self.conn.cursor() as cur:
                for text, emb, meta in zip(batch_texts, embeddings, batch_metas):
                    cur.execute(
                        f"""
                        INSERT INTO {self.table}
                        (category, title, summary, content, embedding, metadata)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        """,
                        (
                            meta.get("category"),
                            meta.get("title"),
                            meta.get("summary"),
                            text,
                            emb,
                            Json(meta),
                        ),
                    )
            self.conn.commit()
            time.sleep(sleep_sec)  # 필요시 백오프

    def similarity_search(self, query: str, k: int = 4,
                          filter: Optional[Dict[str, Any]] = None) -> List[Document]:
        
        query_emb = self.embedding_fn.embed_query(query)
        
        # 쿼리 매개변수 리스트 초기화. 필터 매개변수가 있다면 여기에 먼저 추가됩니다.
        params = []
        
        # SQL 쿼리 기본 구조 설정
        sql_query_template = f"""
            SELECT content, metadata
            FROM {self.table}
        """
        
        # WHERE 절을 위한 리스트
        where_clauses = []
        
        if filter:
            # 1. 필터 딕셔너리를 JSON 문자열로 변환합니다.
            filter_json = json.dumps(filter)
            
            # 2. WHERE 절에 'metadata @> %s::jsonb' 조건을 추가합니다.
            where_clauses.append("metadata @> %s::jsonb")
            
            # 3. 필터 JSON 문자열을 params 리스트에 먼저 추가합니다.
            #    이것이 SQL 쿼리에서 가장 먼저 나오는 %s에 바인딩됩니다.
            params.append(filter_json)

        if where_clauses:
            sql_query_template += " WHERE 1=1 AND " + " AND ".join(where_clauses)
        
        # ORDER BY 및 LIMIT 절 추가
        # ORDER BY에는 임베딩 비교가 들어가며, 이는 필터가 있든 없든 항상 두 번째 (혹은 첫 번째) %s가 됩니다.
        sql_query_template += """
            ORDER BY embedding <-> %s::vector
            LIMIT %s
        """
        
        # 4. 임베딩 벡터를 params에 추가합니다.
        #    이는 ORDER BY의 %s에 바인딩됩니다.
        params.append(query_emb)
        
        # 5. LIMIT 값 (k)을 params에 마지막으로 추가합니다.
        #    이는 LIMIT의 %s에 바인딩됩니다.
        params.append(k)
        
        # 최종 SQL 쿼리: (필터가 있을 경우) WHERE [조건] ORDER BY [임베딩] LIMIT [k]
        
        with self.conn.cursor() as cur:
            # 쿼리와 매개변수를 실행
            # 매개변수의 순서는 SQL 쿼리에 나타나는 %s의 순서와 정확히 일치해야 합니다.
            cur.execute(sql_query_template, tuple(params))
            rows = self.__get_unique_documents(cur.fetchall())

        return [Document(page_content=row[0], metadata=row[1]) for row in rows]


    def similarity_search_with_score(
        self, query: str, k: int = 4
    ) -> List[Tuple[Document, float]]:
        """쿼리와 유사도 점수를 함께 반환"""
        query_emb = self.embedding_fn.embed_query(query)

        with self.conn.cursor() as cur:
            """
            (embedding <-> %s::vector)의 의미 
                - L2 거리(Euclidean distance)
                - 즉, 값이 작을수록 두 벡터가 더 유사함
            """
            cur.execute(
                f"""
                SELECT content, metadata, (embedding <-> %s::vector) AS score
                FROM {self.table}
                ORDER BY score
                LIMIT %s
                """,
                (query_emb, k),
            )
            rows = self.__get_unique_documents(cur.fetchall())
            

        return [
            (Document(page_content=row[0], metadata=row[1]), float(row[2]))
            for row in rows
        ]
    
    def __get_unique_documents(self, rows):
        # 중복 제거를 위한 후처리
        unique_contents = set()
        unique_documents = []
        
        for row in rows:
            content = row[0]
            
            if content not in unique_contents:
                unique_contents.add(content)
                unique_documents.append(row) # 중복이 아닐 때 원본 튜플을 저장

        return unique_documents # 중복 제거된 리스트 반환

