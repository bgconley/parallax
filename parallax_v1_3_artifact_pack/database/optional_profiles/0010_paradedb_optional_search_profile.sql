-- Parallax v1.3 migration 0010
-- OPTIONAL ParadeDB/pg_search profile.
-- Enable only after target image compatibility tests pass.
-- Baseline PostgreSQL FTS remains required even if this profile is disabled.

BEGIN;

CREATE EXTENSION IF NOT EXISTS pg_search;

CREATE INDEX IF NOT EXISTS retrieval_document_bm25_idx
ON retrieval_document
USING bm25 (id, text_content, entity_type, document_kind)
WITH (key_field='id');

COMMIT;
