-- Last updated: 2026-10-18 10:00 UTC · Codex / Data-RAG · additive LightRAG demo projection.
-- User authorized graph+vector import and removal of Oracle score cutoff on 2026-10-18.
-- No existing scientific tables/columns/views are dropped or overwritten.
-- Extracted descriptions and original embeddings only; raw chunk text stays local.
-- Applied status is recorded by the importer/run report, not inferred from this file.
BEGIN;
CREATE EXTENSION IF NOT EXISTS vector;
CREATE SCHEMA IF NOT EXISTS lightrag_demo;

CREATE TABLE IF NOT EXISTS lightrag_demo.batches (
    batch_id text PRIMARY KEY,
    created_at timestamptz NOT NULL DEFAULT now(),
    embedding_model text NOT NULL,
    embedding_dimension integer NOT NULL CHECK (embedding_dimension = 1024),
    manifest jsonb NOT NULL,
    review_state text NOT NULL DEFAULT 'extracted_demo' CHECK (review_state = 'extracted_demo')
);
CREATE TABLE IF NOT EXISTS lightrag_demo.documents (
    batch_id text NOT NULL REFERENCES lightrag_demo.batches(batch_id),
    document_id text NOT NULL,
    source_id integer NOT NULL REFERENCES public.sources(id),
    doi text NOT NULL,
    PRIMARY KEY (batch_id, document_id)
);
CREATE TABLE IF NOT EXISTS lightrag_demo.chunks (
    batch_id text NOT NULL,
    chunk_id text NOT NULL,
    document_id text NOT NULL,
    chunk_order integer,
    PRIMARY KEY (batch_id, chunk_id),
    FOREIGN KEY (batch_id, document_id) REFERENCES lightrag_demo.documents(batch_id, document_id)
);
CREATE TABLE IF NOT EXISTS lightrag_demo.entities (
    batch_id text NOT NULL REFERENCES lightrag_demo.batches(batch_id),
    entity_id text NOT NULL,
    entity_type text,
    description text NOT NULL,
    PRIMARY KEY (batch_id, entity_id)
);
CREATE TABLE IF NOT EXISTS lightrag_demo.relations (
    batch_id text NOT NULL REFERENCES lightrag_demo.batches(batch_id),
    relation_id text NOT NULL,
    source_entity text NOT NULL,
    target_entity text NOT NULL,
    description text NOT NULL,
    keywords text,
    weight double precision,
    PRIMARY KEY (batch_id, relation_id),
    FOREIGN KEY (batch_id, source_entity) REFERENCES lightrag_demo.entities(batch_id, entity_id),
    FOREIGN KEY (batch_id, target_entity) REFERENCES lightrag_demo.entities(batch_id, entity_id)
);
CREATE TABLE IF NOT EXISTS lightrag_demo.embeddings (
    batch_id text NOT NULL REFERENCES lightrag_demo.batches(batch_id),
    item_id text NOT NULL,
    kind text NOT NULL CHECK (kind IN ('entity', 'relation')),
    entity_id text,
    relation_id text,
    content text NOT NULL,
    content_sha256 text NOT NULL,
    embedding vector(1024) NOT NULL,
    search_vec tsvector GENERATED ALWAYS AS (to_tsvector('english', content)) STORED,
    PRIMARY KEY (batch_id, item_id),
    FOREIGN KEY (batch_id, entity_id) REFERENCES lightrag_demo.entities(batch_id, entity_id),
    FOREIGN KEY (batch_id, relation_id) REFERENCES lightrag_demo.relations(batch_id, relation_id),
    CHECK ((kind = 'entity' AND entity_id IS NOT NULL AND relation_id IS NULL)
        OR (kind = 'relation' AND relation_id IS NOT NULL AND entity_id IS NULL))
);
CREATE TABLE IF NOT EXISTS lightrag_demo.evidence (
    batch_id text NOT NULL,
    item_id text NOT NULL,
    chunk_id text NOT NULL,
    PRIMARY KEY (batch_id, item_id, chunk_id),
    FOREIGN KEY (batch_id, item_id) REFERENCES lightrag_demo.embeddings(batch_id, item_id),
    FOREIGN KEY (batch_id, chunk_id) REFERENCES lightrag_demo.chunks(batch_id, chunk_id)
);
CREATE INDEX IF NOT EXISTS lightrag_embeddings_cosine_idx
    ON lightrag_demo.embeddings USING hnsw (embedding vector_cosine_ops);
CREATE INDEX IF NOT EXISTS lightrag_embeddings_fts_idx
    ON lightrag_demo.embeddings USING gin (search_vec);
CREATE INDEX IF NOT EXISTS lightrag_relation_source_idx ON lightrag_demo.relations(batch_id, source_entity);
CREATE INDEX IF NOT EXISTS lightrag_relation_target_idx ON lightrag_demo.relations(batch_id, target_entity);
CREATE INDEX IF NOT EXISTS lightrag_evidence_chunk_idx ON lightrag_demo.evidence(batch_id, chunk_id);
COMMIT;
