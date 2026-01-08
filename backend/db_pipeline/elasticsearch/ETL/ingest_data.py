from db.db_connetion import create_connection
from db.load_data import load_and_split_data
from backend.db_pipeline.common.embedding_model import get_embedding
from db.vector_store import ElasticsearchVectorStore

INDEX_NAME = "rag_embeddings"


def ingest_data(recreate: bool = True):
    """데이터 로드 → 임베딩 → ES 인덱싱까지 한 번에 진행"""
    es_client = create_connection()

    # CSV -> Document 리스트 분할
    docs_by_splitter = load_and_split_data()
    texts = [doc.page_content for doc in docs_by_splitter]
    metadatas = [doc.metadata for doc in docs_by_splitter]

    # 임베딩 객체 (embed_documents/ embed_query 모두 사용)
    embeddings = get_embedding()

    # 인덱스 생성 + 벌크 인덱싱 (이미 계산된 vectors 재사용)
    vectorstore = ElasticsearchVectorStore.from_texts(
        texts=texts,
        embedding=embeddings,
        es_client=es_client,
        index_name=INDEX_NAME,
        metadatas=metadatas,
        recreate=recreate,  # True면 기존 인덱스 삭제 후 재생성
    )
    print(f"인덱싱 완료: {len(texts)}개 문서")
    return vectorstore  # 필요 시 즉시 검색을 테스트할 수 있도록 반환


if __name__ == "__main__":
    # 필요 시 인덱스를 초기화하려면 recreate=True로 실행
    ingest_data(recreate=True)
