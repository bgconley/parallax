from __future__ import annotations

from typing import Any
from uuid import UUID

import psycopg


class PostgresPrivacyDerivedArtifactRepository:
    """Invalidates privacy-sensitive derived artifacts owned by a user.

    Temporal query provenance is intentionally conservative in the current
    baseline: query answers may combine sessions, spans, context-derived facts,
    evidence bundles, and retrieval documents. Until derivation lineage is more
    granular, privacy delete/redact requests invalidate the user's Ask artifacts
    as a set rather than risking stale derived disclosure.
    """

    def __init__(self, connection: psycopg.Connection[Any]) -> None:
        self._connection = connection

    def invalidate_temporal_query_artifacts(self, user_id: UUID) -> dict[str, int]:
        return {
            "query_retrieval_documents": self._delete_count(
                """
                delete from retrieval_document
                where user_id = %s
                  and entity_type = 'temporal_query_answer'
                returning id
                """,
                (user_id,),
            ),
            "query_outbox_events": self._delete_count(
                """
                delete from outbox_event
                where user_id = %s
                  and aggregate_type = 'temporal_query_answer'
                returning id
                """,
                (user_id,),
            ),
            "query_answers": self._delete_count(
                """
                delete from temporal_query_answer
                where user_id = %s
                returning id
                """,
                (user_id,),
            ),
            "query_evidence_items": self._delete_count(
                """
                delete from evidence_item
                where user_id = %s
                  and bundle_id in (
                    select id
                    from evidence_bundle
                    where user_id = %s
                      and purpose = 'temporal_query_answer'
                  )
                returning id
                """,
                (user_id, user_id),
            ),
            "query_evidence_bundles": self._delete_count(
                """
                delete from evidence_bundle
                where user_id = %s
                  and purpose = 'temporal_query_answer'
                returning id
                """,
                (user_id,),
            ),
        }

    def _delete_count(self, sql: str, params: tuple[object, ...]) -> int:
        with self._connection.cursor() as cursor:
            cursor.execute(sql, params)
            return len(cursor.fetchall())
