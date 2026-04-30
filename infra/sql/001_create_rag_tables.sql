CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS rag_ingestion_runs (
    id UUID PRIMARY KEY,
    run_label TEXT NOT NULL,
    run_type TEXT NOT NULL DEFAULT 'ingest',
    status TEXT NOT NULL,
    seed_manifest_hash TEXT NOT NULL,
    context_path TEXT,
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    finished_at TIMESTAMPTZ,
    stats_json JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE TABLE IF NOT EXISTS rag_source_documents (
    id UUID PRIMARY KEY,
    source_url TEXT NOT NULL,
    canonical_url TEXT NOT NULL,
    title TEXT,
    content_hash TEXT NOT NULL,
    crawl_version TEXT NOT NULL,
    fetched_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE TABLE IF NOT EXISTS rag_chunks (
    id UUID PRIMARY KEY,
    document_id UUID NOT NULL REFERENCES rag_source_documents(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    chunk_text TEXT NOT NULL,
    token_count INTEGER NOT NULL,
    chunk_hash TEXT NOT NULL,
    embedding_model TEXT NOT NULL,
    embedding_dim INTEGER NOT NULL,
    embedding VECTOR(1536) NOT NULL,
    schema_version TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    is_active BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE UNIQUE INDEX IF NOT EXISTS ux_rag_source_documents_canonical_version
    ON rag_source_documents (canonical_url, crawl_version);

CREATE UNIQUE INDEX IF NOT EXISTS ux_rag_chunks_doc_idx_schema_embedding
    ON rag_chunks (document_id, chunk_index, schema_version, embedding_model);

CREATE INDEX IF NOT EXISTS ix_rag_source_documents_active
    ON rag_source_documents (is_active);

CREATE INDEX IF NOT EXISTS ix_rag_chunks_active
    ON rag_chunks (is_active);

CREATE INDEX IF NOT EXISTS ix_rag_chunks_embedding_model
    ON rag_chunks (embedding_model);

CREATE INDEX IF NOT EXISTS ix_rag_chunks_schema_version
    ON rag_chunks (schema_version);

CREATE INDEX IF NOT EXISTS ix_rag_chunks_embedding_hnsw
    ON rag_chunks USING hnsw (embedding vector_cosine_ops);
