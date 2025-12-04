CREATE EXTENSION IF NOT EXISTS vector;

-- 예제 테이블 생성
CREATE TABLE korean_history (
    id SERIAL PRIMARY KEY,
    category VARCHAR(20),
    title VARCHAR(255),
    summary TEXT,
    content TEXT,                 -- 문서 내용
    embedding VECTOR(1536),       -- 임베딩 크기에 맞춤
    metadata JSONB                -- 메타데이터
);
