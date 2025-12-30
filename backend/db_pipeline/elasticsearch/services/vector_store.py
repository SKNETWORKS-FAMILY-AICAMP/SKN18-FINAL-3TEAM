from elasticsearch.helpers import bulk
from langchain_core.vectorstores.base import VectorStore
from langchain_core.documents import Document
from typing import List, Sequence, Tuple, Optional
from backend.db_pipeline.common.config import EMBEDDING_DIM


class Singleton(type(VectorStore)):
	_instances = {}

	def __call__(cls, *args, **kwargs):
		if cls not in cls._instances:
			cls._instances[cls] = super(Singleton, cls)\
				.__call__(*args, **kwargs)
		return cls._instances[cls]

class ElasticsearchVectorStore(VectorStore, metaclass=Singleton):
    """Elasticsearch 기반 VectorStore"""

    def __init__(self, es_client, index_name, embeddings, k=2):
        self.es_client = es_client
        self.index_name = index_name
        self._embeddings = embeddings
        self.k = k

    @classmethod
    def from_texts(
        cls,
        texts: Sequence[str],
        embedding,
        es_client,
        index_name: str,
        metadatas: Optional[Sequence[dict]] = None,
        recreate: bool = False,
        vectors: Optional[Sequence[Sequence[float]]] = None,
    ):
        """
        텍스트 리스트를 ES에 임베딩/인덱싱한 뒤 VectorStore 인스턴스를 반환합니다.
        LangChain 호환 시그니처에 맞춰 `embedding` 객체를 그대로 사용합니다.
        vectors가 주어지면 재사용하고, 없으면 embedding.embed_documents로 계산합니다.
        """
        # 안전하게 동일 길이 보장
        metadatas = metadatas or [{} for _ in texts]

        # 필요 시 기존 인덱스 삭제
        if recreate and es_client.indices.exists(index=index_name):
            es_client.indices.delete(index=index_name)

        # 매핑 생성: dense_vector 필드 정의
        if not es_client.indices.exists(index=index_name):
            index_body = {
                "mappings": {
                    "properties": {
                        "text": {"type": "text"},
                        "metadata": {"type": "object", "enabled": True},
                        "embedding": {
                            "type": "dense_vector",
                            "dims": EMBEDDING_DIM,  # 공통 설정 사용
                            "index": True,
                            "similarity": "cosine",
                        },
                    }
                }
            }
            es_client.indices.create(index=index_name, body=index_body)

        # 문서 임베딩 생성 또는 재사용
        if vectors is None:
            vectors = embedding.embed_documents(list(texts))

        # 벌크 인덱싱 페이로드 준비
        actions = []
        for i, (text, meta, vector) in enumerate(zip(texts, metadatas, vectors)):
            actions.append(
                {
                    "_index": index_name,
                    "_id": i,
                    "_source": {
                        "text": text,
                        "metadata": meta or {},
                        "embedding": vector,
                    },
                }
            )

        # 벌크 인덱싱 실행
        bulk(es_client, actions)
        es_client.indices.refresh(index=index_name)

        return cls(es_client=es_client, index_name=index_name, embeddings=embedding, k=2)
 

    def __search_similarity(self, query: str, k: int):
        # 쿼리 텍스트를 임베딩으로 변환
        query_embedding = self._embeddings.embed_query(query)
        
        # KNN 검색 쿼리
        search_query = {
            "knn": {
                "field": "embedding",
                "query_vector": query_embedding,
                "k": k,
                "num_candidates": 100  # 후보 문서 수
            },
            "_source": ["text", "metadata"]  # 반환할 필드
        }
        
        # 검색 실행
        return self.es_client.search(index=self.index_name, body=search_query)


    def similarity_search(self, query: str, k: int = 5) -> List[Document]:
        """벡터 유사도 검색 함수"""
        
        # 검색 실행
        response = self.__search_similarity(query, k)
        
        # 결과 파싱
        documents = []
        for hit in response['hits']['hits']:
            doc = Document(
                page_content=hit['_source']['text'],
                metadata=hit['_source'].get('metadata', {})
            )
            documents.append(doc)

        return documents
    

    def similarity_search_with_score(
        self, query: str, k: int = 4, min_score: Optional[float] = None
    ) -> List[Tuple[Document, float]]:
        """쿼리와 유사도 점수를 함께 반환 (min_score 이상만 유지)"""

        # 검색 실행
        response = self.__search_similarity(query, k)
        
        # 결과 파싱
        documents = []
        for hit in response['hits']['hits']:
            score = hit.get('_score', 0.0)
            if min_score is not None and score < min_score:
                continue
            doc = Document(
                page_content=hit['_source']['text'],
                metadata=hit['_source'].get('metadata', {})
            )
            documents.append((doc, score))

        return documents
    

    def __search_hybrid(self, query: str, k: int):
        # 쿼리 임베딩
        query_embedding = self._embeddings.embed_query(query)
        
        # 하이브리드 검색 쿼리
        search_query = {
            "query": {
                "bool": {
                    "should": [
                        # BM25 키워드 검색
                        {
                            "match": {
                                "text": {
                                    "query": query,
                                    "boost": 1.0  # 키워드 가중치
                                }
                            }
                        }
                    ]
                }
            },
            "knn": {
                "field": "embedding",
                "query_vector": query_embedding,
                "k": k,
                "num_candidates": 100,
                "boost": 2.0  # 벡터 검색 가중치 (벡터에 더 높은 가중치)
            },
            "size": k,
            "_source": ["text", "metadata"]
        }
    
        # 검색 실행
        return self.es_client.search(index=self.index_name, body=search_query)
    

    def hybrid_search_with_score(
        self, query: str, k: int = 4
    ) -> List[Document]:
        """하이브리드 검색: 벡터 검색 + BM25 키워드 검색 반환"""

        # 검색 실행
        response = self.__search_hybrid(query, k)
        
        # 결과 파싱
        documents = []
        for hit in response['hits']['hits']:
            doc = Document(
                page_content=hit['_source']['text'],
                metadata=hit['_source'].get('metadata', {})
            )
            documents.append((doc, hit['_score']))

        return documents    
    


def create_vectorstore(es_client, index_name, embeddings):
    """ElasticsearchVectorStore 생성"""

    vectorstore = ElasticsearchVectorStore(
        es_client=es_client,
        index_name=index_name,
        embeddings=embeddings,
        k=2
    )

    print("Elasticsearch vectorstore 생성 완료")

    return vectorstore


