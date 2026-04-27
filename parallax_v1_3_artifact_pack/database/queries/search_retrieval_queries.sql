-- Retrieval examples.

-- Baseline PostgreSQL FTS.
SELECT id, entity_type, entity_id, document_kind, text_content,
       ts_rank(search_tsv, plainto_tsquery('english', :query_text)) AS rank
FROM retrieval_document
WHERE user_id = :user_id
  AND search_tsv @@ plainto_tsquery('english', :query_text)
  AND privacy_class <> 'private'
ORDER BY rank DESC
LIMIT 20;

-- pgvector 1024-dim cosine search.
SELECT rd.id, rd.entity_type, rd.entity_id, rd.document_kind, rd.text_content,
       (re.embedding <=> :query_embedding) AS cosine_distance
FROM retrieval_embedding_1024 re
JOIN retrieval_document rd ON rd.id = re.document_id
WHERE rd.user_id = :user_id
  AND rd.privacy_class <> 'private'
ORDER BY re.embedding <=> :query_embedding
LIMIT 20;
