"""
Milvus 벡터 데이터베이스 서비스

엔티티 임베딩 저장 및 유사도 검색
- intfloat/multilingual-e5-large 모델 사용
- 코사인 유사도 기반 검색
"""

import os
from typing import List, Dict, Optional
from pathlib import Path
from dotenv import load_dotenv

# .env 로드
env_path = Path(__file__).parent.parent.parent.parent / ".env"
load_dotenv(env_path, override=True)

from pymilvus import (
    connections,
    Collection,
    CollectionSchema,
    FieldSchema,
    DataType,
    utility
)
from sentence_transformers import SentenceTransformer

# 설정
MILVUS_HOST = os.getenv("MILVUS_HOST", "localhost")
MILVUS_PORT = os.getenv("MILVUS_PORT", "19530")
EMBED_MODEL_NAME = os.getenv("EMBED_MODEL_NAME", "intfloat/multilingual-e5-large")
COLLECTION_NAME = "korean_history_entities"

# 임베딩 차원 (multilingual-e5-large: 1024)
EMBEDDING_DIM = 1024


class MilvusService:
    """Milvus 벡터 검색 서비스"""
    
    def __init__(self):
        self.model = None
        self.collection = None
        self._connected = False
    
    def connect(self) -> bool:
        """Milvus 연결"""
        try:
            connections.connect(
                alias="default",
                host=MILVUS_HOST,
                port=MILVUS_PORT
            )
            self._connected = True
            # Milvus 연결 성공 (로그 간소화)
            return True
        except Exception as e:
            print(f"Milvus 연결 실패: {e}")
            self._connected = False
            return False

    def disconnect(self):
        """Milvus 연결 해제"""
        if self._connected:
            connections.disconnect("default")
            self._connected = False
            # Milvus 연결 해제 (로그 간소화)

    def load_model(self):
        """임베딩 모델 로드"""
        if self.model is None:
            # 임베딩 모델 로딩 중... (로그 간소화)
            self.model = SentenceTransformer(EMBED_MODEL_NAME)
            # 모델 로드 완료 (로그 간소화)
        return self.model
    
    def create_collection(self, drop_existing: bool = False) -> Collection:
        """컬렉션 생성"""
        
        if not self._connected:
            self.connect()
        
        # 기존 컬렉션 삭제
        if drop_existing and utility.has_collection(COLLECTION_NAME):
            utility.drop_collection(COLLECTION_NAME)
            print(f"🗑️ 기존 컬렉션 삭제: {COLLECTION_NAME}")
        
        # 컬렉션이 이미 존재하면 반환
        if utility.has_collection(COLLECTION_NAME):
            self.collection = Collection(COLLECTION_NAME)
            self.collection.load()
            print(f"📂 기존 컬렉션 로드: {COLLECTION_NAME}")
            return self.collection
        
        # 스키마 정의
        fields = [
            FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
            FieldSchema(name="title", dtype=DataType.VARCHAR, max_length=500),
            FieldSchema(name="category", dtype=DataType.VARCHAR, max_length=100),
            FieldSchema(name="summary", dtype=DataType.VARCHAR, max_length=2000),
            FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=EMBEDDING_DIM)
        ]
        
        schema = CollectionSchema(
            fields=fields,
            description="한국사 엔티티 벡터 컬렉션"
        )
        
        # 컬렉션 생성
        self.collection = Collection(
            name=COLLECTION_NAME,
            schema=schema
        )
        
        # 인덱스 생성 (코사인 유사도)
        index_params = {
            "metric_type": "COSINE",
            "index_type": "IVF_FLAT",
            "params": {"nlist": 128}
        }
        
        self.collection.create_index(
            field_name="embedding",
            index_params=index_params
        )
        
        print(f"✅ 컬렉션 생성 완료: {COLLECTION_NAME}")
        return self.collection
    
    def embed_text(self, text: str) -> List[float]:
        """텍스트 임베딩 생성 (E5 모델용 prefix 추가)"""
        if self.model is None:
            self.load_model()
        
        # E5 모델은 "query: " 또는 "passage: " prefix 필요
        prefixed_text = f"passage: {text}"
        embedding = self.model.encode(prefixed_text, normalize_embeddings=True)
        return embedding.tolist()
    
    def embed_query(self, query: str) -> List[float]:
        """쿼리 임베딩 생성 (검색용)"""
        if self.model is None:
            self.load_model()
        
        # E5 모델 검색용 prefix
        prefixed_query = f"query: {query}"
        embedding = self.model.encode(prefixed_query, normalize_embeddings=True)
        return embedding.tolist()
    
    def insert_entities(self, entities: List[Dict]) -> int:
        """엔티티 배치 삽입
        
        Args:
            entities: [{"title": "...", "category": "...", "summary": "..."}]
        
        Returns:
            삽입된 엔티티 수
        """
        if not self._connected:
            self.connect()
        
        if self.collection is None:
            self.create_collection()
        
        # 임베딩 생성 (title만)
        titles = [e["title"] for e in entities]
        embeddings = []
        
        print(f"🔄 임베딩 생성 중... ({len(titles)}개)")
        for i, title in enumerate(titles):
            embedding = self.embed_text(title)
            embeddings.append(embedding)
            
            if (i + 1) % 100 == 0:
                print(f"   {i + 1}/{len(titles)} 완료")
        
        # 데이터 준비
        data = [
            titles,
            [e.get("category", "") for e in entities],
            [e.get("summary", "")[:1990] for e in entities],  # max_length 제한
            embeddings
        ]
        
        # 삽입
        self.collection.insert(data)
        self.collection.flush()
        
        print(f"✅ {len(entities)}개 엔티티 삽입 완료")
        return len(entities)
    
    def search(
        self,
        query: str,
        top_k: int = 10,
        threshold: float = 0.5
    ) -> List[Dict]:
        """유사 엔티티 검색
        
        Args:
            query: 검색 쿼리 (키워드 또는 문장)
            top_k: 반환할 최대 결과 수
            threshold: 최소 유사도 (0-1, 코사인)
        
        Returns:
            [{"title": "...", "category": "...", "score": 0.95, ...}]
        """
        if not self._connected:
            self.connect()
        
        if self.collection is None:
            self.collection = Collection(COLLECTION_NAME)
        
        # 컬렉션 로드
        self.collection.load()
        
        # 쿼리 임베딩
        query_embedding = self.embed_query(query)
        
        # 검색
        search_params = {
            "metric_type": "COSINE",
            "params": {"nprobe": 10}
        }
        
        results = self.collection.search(
            data=[query_embedding],
            anns_field="embedding",
            param=search_params,
            limit=top_k,
            output_fields=["title", "category", "summary"]
        )
        
        # 결과 포맷팅
        entities = []
        for hits in results:
            for hit in hits:
                score = hit.score  # 코사인 유사도 (0-1)
                
                if score >= threshold:
                    entities.append({
                        "title": hit.entity.get("title"),
                        "category": hit.entity.get("category"),
                        "summary": hit.entity.get("summary"),
                        "score": round(score, 4)
                    })
        
        return entities
    
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
                if title not in all_results or result["score"] > all_results[title]["score"]:
                    result["matched_keyword"] = keyword
                    all_results[title] = result
        
        # 점수 순 정렬
        sorted_results = sorted(all_results.values(), key=lambda x: x["score"], reverse=True)
        return sorted_results
    
    def get_collection_stats(self) -> Dict:
        """컬렉션 통계"""
        if not self._connected:
            self.connect()
        
        if not utility.has_collection(COLLECTION_NAME):
            return {"exists": False}
        
        collection = Collection(COLLECTION_NAME)
        
        return {
            "exists": True,
            "name": COLLECTION_NAME,
            "num_entities": collection.num_entities,
            "schema": str(collection.schema)
        }


# 싱글톤 인스턴스
_milvus_service = None


def get_milvus_service() -> MilvusService:
    """Milvus 서비스 싱글톤 반환"""
    global _milvus_service
    if _milvus_service is None:
        _milvus_service = MilvusService()
    return _milvus_service

