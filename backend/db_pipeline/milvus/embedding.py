from langchain_openai import OpenAIEmbeddings

# 싱글톤 패턴을 위한 전역 변수
_embedding = None

def get_embedding_model() -> OpenAIEmbeddings:
    global _embedding
    if _embedding is None:
        _embedding = OpenAIEmbeddings(
            model="text-embedding-3-small",
        )
    return _embedding
