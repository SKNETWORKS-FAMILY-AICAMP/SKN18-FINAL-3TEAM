CREATE EXTENSION IF NOT EXISTS vector;

-- 1. 벡터 스토어 테이블
CREATE TABLE IF NOT EXISTS korean_history (
    id SERIAL PRIMARY KEY,
    category VARCHAR(20),
    title VARCHAR(255),
    summary TEXT,
    content TEXT,
    embedding VECTOR(1536),
    metadata JSONB
);

-- 2. 회원 정보 관리 테이블
CREATE TABLE IF NOT EXISTS "user" (
    id SERIAL PRIMARY KEY,
    nickname VARCHAR(30) UNIQUE,
    profile_image TEXT NULL,
    sign_up_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    email TEXT UNIQUE NOT NULL,
    permission VARCHAR(50) NOT NULL DEFAULT 'user',
    gender BOOLEAN NULL,
    age INT NULL,
    password VARCHAR(128) NOT NULL DEFAULT '',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    is_staff BOOLEAN NOT NULL DEFAULT FALSE,
    is_superuser BOOLEAN NOT NULL DEFAULT FALSE,
    last_login TIMESTAMP NULL
);

-- 3. 영상 관리 테이블 (컬럼 추가 및 순서 조정)
CREATE TABLE IF NOT EXISTS video (
    id SERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    video_url TEXT NULL,                -- 추가됨
    thumbnail_url TEXT NULL,            -- 추가됨
    upload_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    tags TEXT[] NULL,
    video_keyword TEXT NULL,
    recommended_keyword TEXT NULL,
    likes_count INT NOT NULL DEFAULT 0,
    comments_count INT NOT NULL DEFAULT 0
);

-- 4. 시청 기록 관리 테이블
CREATE TABLE IF NOT EXISTS watching_history (
    id SERIAL PRIMARY KEY,
    video_id INT NOT NULL REFERENCES video(id) ON DELETE CASCADE,
    user_id INT NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
    tags TEXT NULL,
    video_keyword TEXT NULL,
    recommended_keyword TEXT NULL,
    watched_seconds INT NOT NULL DEFAULT 0,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 5. 댓글 관리 테이블
CREATE TABLE IF NOT EXISTS comment (
    id SERIAL PRIMARY KEY,
    user_id INT NULL REFERENCES "user"(id) ON DELETE SET NULL,
    video_id INT NOT NULL REFERENCES video(id) ON DELETE CASCADE,
    comment_content TEXT NOT NULL,
    comment_likes_count INT NOT NULL DEFAULT 0,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 6. 기타 보조 테이블
CREATE TABLE IF NOT EXISTS reply (
    id SERIAL PRIMARY KEY,
    comment_id INT NOT NULL REFERENCES comment(id) ON DELETE CASCADE,
    user_id INT NULL REFERENCES "user"(id) ON DELETE SET NULL,
    reply_content TEXT NOT NULL,
    parent_reply_id INT NULL DEFAULT NULL REFERENCES reply(id) ON DELETE CASCADE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS likes (
    id SERIAL PRIMARY KEY,
    user_id INT NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
    video_id INT NULL REFERENCES video(id) ON DELETE CASCADE,
    comment_id INT NULL REFERENCES comment(id) ON DELETE CASCADE,
    reply_id INT NULL REFERENCES reply(id) ON DELETE CASCADE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_at_least_one_not_null CHECK (video_id IS NOT NULL OR comment_id IS NOT NULL OR reply_id IS NOT NULL)
);

CREATE TABLE IF NOT EXISTS search_history (
    id SERIAL PRIMARY KEY,
    user_id INT NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
    search_query TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 7. 인덱스 생성
CREATE INDEX IF NOT EXISTS korean_history_embedding_idx ON korean_history USING hnsw (embedding vector_cosine_ops);