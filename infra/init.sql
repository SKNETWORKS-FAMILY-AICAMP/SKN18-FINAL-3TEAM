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

-- 회원 정보 관리 테이블 생성
-- "user"는 PostgreSQL 예약어이므로 큰따옴표 필요
CREATE TABLE IF NOT EXISTS "user" (
    id SERIAL PRIMARY KEY,
    nickname VARCHAR(30) UNIQUE,
    profile_image VARCHAR(100) NULL,
    sign_up_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    email TEXT UNIQUE NOT NULL,
    permission VARCHAR(50) NOT NULL DEFAULT 'user',
    gender BOOLEAN NULL,
    age INT NULL,
    -- Django 인증 시스템 필수 필드
    password VARCHAR(128) NOT NULL DEFAULT '',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    is_staff BOOLEAN NOT NULL DEFAULT FALSE,
    is_superuser BOOLEAN NOT NULL DEFAULT FALSE,
    last_login TIMESTAMP NULL
);

-- 영상 관리 테이블 생성
CREATE TABLE IF NOT EXISTS video (
    id SERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    video_url TEXT NOT NULL,
    upload_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    tags TEXT[] NULL,
    likes_count INT NOT NULL DEFAULT 0,
    comments_count INT NOT NULL DEFAULT 0
);

-- 시청 기록 관리 테이블 생성
CREATE TABLE IF NOT EXISTS watching_history (
    id SERIAL PRIMARY KEY,
    video_id INT NOT NULL REFERENCES video(id) ON DELETE CASCADE,
    user_id INT NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
    tags TEXT[] NULL,
    watched_seconds INT NOT NULL DEFAULT 0,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 댓글 관리 테이블 생성
CREATE TABLE IF NOT EXISTS comment (
    id SERIAL PRIMARY KEY,
    user_id INT NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
    video_id INT NOT NULL REFERENCES video(id) ON DELETE CASCADE,
    comment_content TEXT NOT NULL,
    comment_likes_count INT NOT NULL DEFAULT 0,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 답글 관리 테이블 생성
CREATE TABLE IF NOT EXISTS reply (
    id SERIAL PRIMARY KEY,
    comment_id INT NOT NULL REFERENCES comment(id) ON DELETE CASCADE,
    user_id INT NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
    reply_content TEXT NOT NULL,
    parent_reply_id INT NULL REFERENCES reply(id) ON DELETE CASCADE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 좋아요 관리 테이블 생성
CREATE TABLE IF NOT EXISTS likes (
    id SERIAL PRIMARY KEY,
    user_id INT NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
    video_id INT NULL REFERENCES video(id) ON DELETE CASCADE,
    comment_id INT NULL REFERENCES comment(id) ON DELETE CASCADE,
    reply_id INT NULL REFERENCES reply(id) ON DELETE CASCADE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 검색 기록 테이블 생성
CREATE TABLE IF NOT EXISTS search_history (
    id SERIAL PRIMARY KEY,
    user_id INT NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
    search_query TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 벡터 검색 최적화를 위한 HNSW 인덱스 생성
CREATE INDEX IF NOT EXISTS korean_history_embedding_idx
ON korean_history
USING hnsw (embedding vector_cosine_ops);