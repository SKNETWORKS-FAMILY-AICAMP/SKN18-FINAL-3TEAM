CREATE EXTENSION IF NOT EXISTS vector;

-- 벡터 스토어 테이블 생성
CREATE TABLE IF NOT EXISTS korean_history (
    id SERIAL PRIMARY KEY,
    category VARCHAR(20),
    title VARCHAR(255),
    summary TEXT,
    content TEXT,                 -- 문서 내용
    embedding VECTOR(1536),       -- 임베딩 크기에 맞춤
    metadata JSONB                -- 메타데이터
);

-- 벡터 검색 최적화를 위한 HNSW 인덱스 생성
CREATE INDEX IF NOT EXISTS korean_history_embedding_idx
ON korean_history
USING hnsw (embedding vector_cosine_ops);
