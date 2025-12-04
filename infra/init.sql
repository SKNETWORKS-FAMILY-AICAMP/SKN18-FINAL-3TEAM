-- PostgreSQL + pgvector 0T §lΩ∏
-- °0 U• \1T
CREATE EXTENSION IF NOT EXISTS vector;

-- 8 ≠l Lt ›1 (ETL t|x– ¨©)
CREATE TABLE IF NOT EXISTS documents (
    doc_id VARCHAR(100) PRIMARY KEY,
    category VARCHAR(200),
    title VARCHAR(500),
    summary TEXT,
    contents_length INT,
    num_chunks INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS document_chunks (
    id SERIAL PRIMARY KEY,
    doc_id VARCHAR(100) REFERENCES documents(doc_id) ON DELETE CASCADE,
    chunk_id INT,
    text TEXT,
    start_pos INT,
    end_pos INT,
    embedding vector(1536),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- °0 Ä…D \ HNSW xq§ ›1
CREATE INDEX IF NOT EXISTS document_chunks_embedding_idx
ON document_chunks
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- | xq§ ›1
CREATE INDEX IF NOT EXISTS document_chunks_doc_id_idx ON document_chunks(doc_id);
CREATE INDEX IF NOT EXISTS documents_category_idx ON documents(category);
CREATE INDEX IF NOT EXISTS documents_title_idx ON documents(title);

-- $T/t|0 Ï	X Lt ( ›)
CREATE TABLE IF NOT EXISTS folktales (
    id SERIAL PRIMARY KEY,
    title VARCHAR(500),
    content TEXT,
    summary TEXT,
    related_entities TEXT[],
    era VARCHAR(100),
    embedding vector(1536),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- $T Ä…D \ HNSW xq§
CREATE INDEX IF NOT EXISTS folktales_embedding_idx
ON folktales
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- å\ $
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO admin;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO admin;
