from functools import lru_cache
from typing import Iterable, List, Sequence, Union

from langchain_openai import OpenAIEmbeddings
from openai import OpenAI

from backend.db_pipeline.common.config import (
    EMBED_MODEL,
    EMBEDDING_DIM,
    OPENAI_API_KEY,
)

TextInput = Union[str, Sequence[str], Iterable[str]]


@lru_cache(maxsize=1)
def get_openai_client() -> OpenAI:
    """공용 OpenAI 클라이언트 (싱글톤)"""
    return OpenAI(api_key=OPENAI_API_KEY)


@lru_cache(maxsize=1)
def get_embedding():
    """LangChain/pgvector용 임베딩 객체"""
    return OpenAIEmbeddings(model=EMBED_MODEL, api_key=OPENAI_API_KEY)


def embed(texts: TextInput, batch_size: int = 100) -> Union[List[float], List[List[float]]]:
    """
    단일/배치 임베딩을 하나로 처리.
    - 문자열 입력: 벡터(List[float]) 반환
    - 시퀀스 입력: 벡터 리스트(List[List[float]]) 반환
    빈 문자열은 zero-vector로 처리.
    """
    if isinstance(texts, str):
        return _embed_single(texts)
    return _embed_batch(list(texts), batch_size=batch_size)


# 텍스트 임베딩
def _embed_single(text: str) -> List[float]:
    if not text or not text.strip():
        return [0.0] * EMBEDDING_DIM

    client = get_openai_client()
    response = client.embeddings.create(
        model=EMBED_MODEL,
        input=text,
    )
    return response.data[0].embedding


# 배치 텍스트 임베딩
def _embed_batch(texts: Sequence[str], batch_size: int = 100) -> List[List[float]]:
    client = get_openai_client()

    valid_indices = []
    valid_texts = []
    for idx, text in enumerate(texts):
        if text and str(text).strip():
            valid_indices.append(idx)
            valid_texts.append(str(text))

    embeddings: List[List[float]] = []
    for start in range(0, len(valid_texts), batch_size):
        batch = valid_texts[start : start + batch_size]
        response = client.embeddings.create(
            model=EMBED_MODEL,
            input=batch,
        )
        embeddings.extend([item.embedding for item in response.data])

    # 원래 순서 복원 (빈 텍스트는 zero-vector)
    final_embeddings: List[List[float]] = []
    valid_ptr = 0
    for idx in range(len(texts)):
        if idx in valid_indices:
            final_embeddings.append(embeddings[valid_ptr])
            valid_ptr += 1
        else:
            final_embeddings.append([0.0] * EMBEDDING_DIM)

    return final_embeddings
