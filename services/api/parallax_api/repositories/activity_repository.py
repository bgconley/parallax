from __future__ import annotations

import re
from datetime import UTC, datetime
from uuid import UUID, uuid4

from ..schemas.activity import Activity, CreateActivityRequest, ResolveActivityCandidate
from ..schemas.activity_metadata import (
    ActivityAlias,
    ActivityIdentityChange,
    ActivityMergePreview,
    ActivityRelationship,
    ActivitySplitPreview,
    CheckpointTemplate,
    CreateActivityRelationshipRequest,
    CreatePreflightCheckRequest,
    PreflightCheck,
    PreflightDecision,
    PutCheckpointsRequest,
    ResourceDependency,
)
from .memory import InMemoryStore


class DuplicateActivityError(ValueError):
    pass


class ActivityRepository:
    def __init__(self, store: InMemoryStore) -> None:
        self._store = store

    def create(self, user_id: UUID, request: CreateActivityRequest) -> Activity:
        canonical_key = normalize_activity_key(request.display_name)
        if (user_id, canonical_key) in self._store.activity_keys:
            raise DuplicateActivityError(f"activity already exists: {canonical_key}")

        now = datetime.now(UTC)
        activity = Activity(
            id=uuid4(),
            user_id=user_id,
            display_name=request.display_name,
            canonical_key=canonical_key,
            description=request.description,
            status="active",
            merged_into_activity_id=None,
            default_timing_mode=request.default_timing_mode,
            privacy_class=request.privacy_class,
            created_at=now,
            updated_at=now,
        )
        self._store.activities[activity.id] = activity
        self._store.activity_keys[(user_id, canonical_key)] = activity.id
        return activity

    def list_activities(
        self,
        user_id: UUID,
        query: str | None = None,
        limit: int = 50,
    ) -> list[Activity]:
        activities = [
            activity
            for activity in self._store.activities.values()
            if activity.user_id == user_id
        ]
        if query:
            normalized_query = query.casefold()
            activities = [a for a in activities if normalized_query in a.display_name.casefold()]
        return sorted(activities, key=lambda activity: activity.created_at)[:limit]

    def get(self, user_id: UUID, activity_id: UUID) -> Activity | None:
        activity = self._store.activities.get(activity_id)
        if activity is None or activity.user_id != user_id:
            return None
        return activity

    def resolve(self, user_id: UUID, query: str, limit: int) -> list[ResolveActivityCandidate]:
        canonical_key = normalize_activity_key(query)
        activity_id = self._store.activity_keys.get((user_id, canonical_key))
        if activity_id:
            activity = self._store.activities[activity_id]
            return [
                ResolveActivityCandidate(
                    activity=activity,
                    display_name=activity.display_name,
                    confidence=1.0,
                    match_type="canonical",
                    evidence={"canonical_key": canonical_key},
                )
            ][:limit]

        alias_matches = [
            alias
            for alias in self._store.activity_aliases.values()
            if alias.user_id == user_id
            and alias.normalized_alias == canonical_key
            and alias.user_confirmed
            and not alias.rejected
        ]
        alias_matches.sort(key=lambda alias: (-alias.confidence, alias.created_at))
        if alias_matches:
            return [
                ResolveActivityCandidate(
                    activity=self._store.activities.get(alias.activity_id),
                    display_name=self._store.activities[alias.activity_id].display_name,
                    confidence=alias.confidence,
                    match_type="alias",
                    evidence={"normalized_alias": canonical_key, "alias_id": str(alias.id)},
                )
                for alias in alias_matches[:limit]
                if alias.activity_id in self._store.activities
            ]

        return [
            ResolveActivityCandidate(
                activity=None,
                display_name=query,
                confidence=0.0,
                match_type="no_match",
                evidence={"reason": "no matching activity"},
            )
        ]

    def add_alias(
        self,
        user_id: UUID,
        activity_id: UUID,
        alias_text: str,
        *,
        user_confirmed: bool,
    ) -> ActivityAlias:
        normalized_alias = normalize_activity_key(alias_text)
        now = datetime.now(UTC)
        alias = ActivityAlias(
            id=uuid4(),
            user_id=user_id,
            activity_id=activity_id,
            alias_text=alias_text,
            normalized_alias=normalized_alias,
            source="user" if user_confirmed else "system_suggested",
            confidence=1.0 if user_confirmed else 0.75,
            user_confirmed=user_confirmed,
            rejected=False,
            created_at=now,
        )
        self._store.activity_aliases[alias.id] = alias
        return alias

    def list_aliases(self, user_id: UUID, activity_id: UUID) -> list[ActivityAlias]:
        aliases = [
            alias
            for alias in self._store.activity_aliases.values()
            if alias.user_id == user_id and alias.activity_id == activity_id
        ]
        return sorted(aliases, key=lambda alias: alias.created_at)

    def decide_alias(
        self,
        user_id: UUID,
        activity_id: UUID,
        alias_id: UUID,
        decision: str,
    ) -> ActivityAlias | None:
        alias = self._store.activity_aliases.get(alias_id)
        if alias is None or alias.user_id != user_id or alias.activity_id != activity_id:
            return None
        accepted = decision == "accept"
        updated = alias.model_copy(
            update={
                "user_confirmed": accepted,
                "rejected": not accepted,
                "confidence": 1.0 if accepted else alias.confidence,
            }
        )
        self._store.activity_aliases[alias_id] = updated
        return updated

    def create_relationship(
        self,
        user_id: UUID,
        activity_id: UUID,
        request: CreateActivityRelationshipRequest,
    ) -> ActivityRelationship:
        relationship = ActivityRelationship(
            id=uuid4(),
            user_id=user_id,
            from_activity_id=activity_id,
            to_activity_id=request.to_activity_id,
            kind=request.kind,
            metadata=request.metadata,
            user_confirmed=request.user_confirmed,
            state="confirmed" if request.user_confirmed else "suggested",
            created_at=datetime.now(UTC),
        )
        self._store.activity_relationships[relationship.id] = relationship
        return relationship

    def list_relationships(self, user_id: UUID, activity_id: UUID) -> list[ActivityRelationship]:
        relationships = [
            relationship
            for relationship in self._store.activity_relationships.values()
            if relationship.user_id == user_id and relationship.from_activity_id == activity_id
        ]
        return sorted(relationships, key=lambda relationship: relationship.created_at)

    def decide_relationship(
        self,
        user_id: UUID,
        activity_id: UUID,
        relationship_id: UUID,
        decision: str,
    ) -> ActivityRelationship | None:
        relationship = self._store.activity_relationships.get(relationship_id)
        if (
            relationship is None
            or relationship.user_id != user_id
            or relationship.from_activity_id != activity_id
        ):
            return None
        accepted = decision == "accept"
        updated = relationship.model_copy(
            update={
                "user_confirmed": accepted,
                "state": "confirmed" if accepted else "rejected",
            }
        )
        self._store.activity_relationships[relationship_id] = updated
        return updated

    def merge_preview(
        self,
        user_id: UUID,
        source_activity_id: UUID,
        target_activity_id: UUID,
    ) -> ActivityMergePreview:
        return ActivityMergePreview(
            source_activity_id=source_activity_id,
            target_activity_id=target_activity_id,
            affected_session_count=self._count_sessions(user_id, source_activity_id),
        )

    def merge_activities(
        self,
        user_id: UUID,
        source_activity_id: UUID,
        target_activity_id: UUID,
        reason: str | None,
    ) -> ActivityIdentityChange:
        now = datetime.now(UTC)
        source = self._store.activities[source_activity_id]
        self._store.activities[source_activity_id] = source.model_copy(
            update={
                "status": "merged",
                "merged_into_activity_id": target_activity_id,
                "updated_at": now,
            }
        )
        relationship = ActivityRelationship(
            id=uuid4(),
            user_id=user_id,
            from_activity_id=source_activity_id,
            to_activity_id=target_activity_id,
            kind="same_as",
            metadata={"reason": reason} if reason else {},
            user_confirmed=True,
            state="confirmed",
            created_at=now,
        )
        self._store.activity_relationships[relationship.id] = relationship
        change = ActivityIdentityChange(
            id=uuid4(),
            user_id=user_id,
            change_type="merge",
            source_activity_id=source_activity_id,
            target_activity_id=target_activity_id,
            affected_session_count=self._count_sessions(user_id, source_activity_id),
            audit_id=uuid4(),
            created_at=now,
        )
        self._store.activity_identity_changes[change.id] = change
        return change

    def split_preview(
        self,
        user_id: UUID,
        source_activity_id: UUID,
        proposed_display_name: str,
        session_ids: list[UUID],
    ) -> ActivitySplitPreview:
        session_id_set = set(session_ids)
        movable = [
            session
            for session in self._store.sessions.values()
            if session.user_id == user_id
            and session.activity_id == source_activity_id
            and (not session_id_set or session.id in session_id_set)
        ]
        return ActivitySplitPreview(
            source_activity_id=source_activity_id,
            proposed_display_name=proposed_display_name,
            movable_session_count=len(movable),
        )

    def list_checkpoints(self, user_id: UUID, activity_id: UUID) -> list[CheckpointTemplate]:
        checkpoints = [
            checkpoint
            for checkpoint in self._store.checkpoint_templates.values()
            if checkpoint.user_id == user_id and checkpoint.activity_id == activity_id
        ]
        return sorted(checkpoints, key=lambda checkpoint: checkpoint.sequence_order)

    def replace_checkpoints(
        self,
        user_id: UUID,
        activity_id: UUID,
        request: PutCheckpointsRequest,
    ) -> list[CheckpointTemplate]:
        now = datetime.now(UTC)
        self._store.checkpoint_templates = {
            checkpoint_id: checkpoint
            for checkpoint_id, checkpoint in self._store.checkpoint_templates.items()
            if not (checkpoint.user_id == user_id and checkpoint.activity_id == activity_id)
        }
        checkpoints = [
            CheckpointTemplate(
                id=uuid4(),
                user_id=user_id,
                activity_id=activity_id,
                sequence_order=item.sequence_order,
                label=item.label,
                phase_type=item.phase_type,
                optional=item.optional,
                created_at=now,
                updated_at=now,
            )
            for item in sorted(request.checkpoints, key=lambda item: item.sequence_order)
        ]
        for checkpoint in checkpoints:
            self._store.checkpoint_templates[checkpoint.id] = checkpoint
        return checkpoints

    def list_preflight_checks(self, user_id: UUID, activity_id: UUID) -> list[PreflightCheck]:
        checks = [
            check
            for check in self._store.preflight_checks.values()
            if check.user_id == user_id and check.activity_id == activity_id
        ]
        return sorted(checks, key=lambda check: check.check_text.casefold())

    def list_resource_dependencies(
        self,
        user_id: UUID,
        activity_id: UUID,
    ) -> list[ResourceDependency]:
        dependencies = [
            dependency
            for dependency in self._store.resource_dependencies.values()
            if dependency.user_id == user_id and dependency.activity_id == activity_id
        ]
        return sorted(
            dependencies,
            key=lambda dependency: (-dependency.failure_count, dependency.resource_name.casefold()),
        )

    def create_preflight_check(
        self,
        user_id: UUID,
        activity_id: UUID,
        request: CreatePreflightCheckRequest,
    ) -> PreflightCheck:
        check = PreflightCheck(
            id=uuid4(),
            user_id=user_id,
            activity_id=activity_id,
            check_text=request.check_text,
            state="active" if request.source == "user_created" else "suggested",
            source=request.source,
            confidence=1.0 if request.source == "user_created" else None,
            failure_count=0,
            evidence_count=0,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        self._store.preflight_checks[check.id] = check
        return check

    def decide_preflight_check(
        self,
        user_id: UUID,
        activity_id: UUID,
        check_id: UUID,
        decision: PreflightDecision,
        *,
        snoozed_until: datetime | None,
        reason: str | None,
    ) -> PreflightCheck | None:
        check = self._store.preflight_checks.get(check_id)
        if check is None or check.user_id != user_id or check.activity_id != activity_id:
            return None
        state = _preflight_state_for_decision(decision)
        now = datetime.now(UTC)
        updated = check.model_copy(
            update={
                "state": state,
                "snoozed_until": snoozed_until if state == "snoozed" else None,
                "last_decided_at": now,
                "decision_reason": reason,
                "updated_at": now,
            }
        )
        self._store.preflight_checks[check_id] = updated
        return updated

    def _count_sessions(self, user_id: UUID, activity_id: UUID) -> int:
        return sum(
            1
            for session in self._store.sessions.values()
            if session.user_id == user_id and session.activity_id == activity_id
        )


def normalize_activity_key(display_name: str) -> str:
    lowered = display_name.strip().casefold()
    collapsed = re.sub(r"[^a-z0-9]+", "-", lowered).strip("-")
    return collapsed or "activity"


def _preflight_state_for_decision(decision: PreflightDecision) -> str:
    return {
        "accept": "active",
        "hide": "hidden",
        "snooze": "snoozed",
        "retire": "retired",
    }[decision]
