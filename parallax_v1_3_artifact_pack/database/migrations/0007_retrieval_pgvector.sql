-- Parallax v1.3 migration 0007
-- Retrieval documents, PostgreSQL FTS, and optional pgvector embedding tables.
-- Baseline lexical retrieval must work without pgvector. Embedding tables are
-- created only when the vector extension is available and can be enabled.

BEGIN;

CREATE TABLE embedding_model (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  provider text NOT NULL,
  model_name text NOT NULL,
  model_version text,
  dimension integer NOT NULL CHECK (dimension > 0),
  normalized boolean NOT NULL DEFAULT true,
  purpose text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE(provider, model_name, model_version, purpose)
);

CREATE TABLE retrieval_document (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES app_user(id) ON DELETE CASCADE,
  entity_type text NOT NULL,
  entity_id uuid NOT NULL,
  document_kind text NOT NULL,
  text_content text NOT NULL,
  search_tsv tsvector GENERATED ALWAYS AS (to_tsvector('english', coalesce(text_content,''))) STORED,
  privacy_class privacy_class NOT NULL DEFAULT 'normal',
  source_hash text,
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE(user_id, entity_type, entity_id, document_kind)
);

CREATE INDEX idx_retrieval_document_tsv ON retrieval_document USING gin(search_tsv);
CREATE INDEX idx_retrieval_document_entity ON retrieval_document(user_id, entity_type, entity_id);
CREATE INDEX idx_retrieval_document_privacy ON retrieval_document(user_id, privacy_class, document_kind);

DO $$
DECLARE
  vector_ready boolean := false;
BEGIN
  IF EXISTS (SELECT 1 FROM pg_available_extensions WHERE name = 'vector') THEN
    BEGIN
      CREATE EXTENSION IF NOT EXISTS vector;
      vector_ready := true;
    EXCEPTION
      WHEN insufficient_privilege THEN
        RAISE NOTICE 'pgvector extension is available but cannot be enabled by this role; skipping embedding tables.';
      WHEN undefined_file THEN
        RAISE NOTICE 'pgvector extension files are unavailable; skipping embedding tables.';
    END;
  ELSE
    RAISE NOTICE 'pgvector extension is not available; skipping embedding tables.';
  END IF;

  IF vector_ready THEN
    EXECUTE $sql$
      CREATE TABLE IF NOT EXISTS retrieval_embedding_1024 (
        document_id uuid PRIMARY KEY REFERENCES retrieval_document(id) ON DELETE CASCADE,
        embedding_model_id uuid NOT NULL REFERENCES embedding_model(id),
        embedding vector(1024) NOT NULL,
        embedded_at timestamptz NOT NULL DEFAULT now()
      )
    $sql$;

    EXECUTE $sql$
      CREATE INDEX IF NOT EXISTS idx_retrieval_embedding_1024_hnsw
        ON retrieval_embedding_1024
        USING hnsw (embedding vector_cosine_ops)
    $sql$;

    EXECUTE $sql$
      CREATE TABLE IF NOT EXISTS retrieval_embedding_1536 (
        document_id uuid PRIMARY KEY REFERENCES retrieval_document(id) ON DELETE CASCADE,
        embedding_model_id uuid NOT NULL REFERENCES embedding_model(id),
        embedding vector(1536) NOT NULL,
        embedded_at timestamptz NOT NULL DEFAULT now()
      )
    $sql$;

    EXECUTE $sql$
      CREATE INDEX IF NOT EXISTS idx_retrieval_embedding_1536_hnsw
        ON retrieval_embedding_1536
        USING hnsw (embedding vector_cosine_ops)
    $sql$;
  END IF;
END $$;

COMMIT;
