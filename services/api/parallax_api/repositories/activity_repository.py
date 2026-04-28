from __future__ import annotations

import re
from datetime import UTC, datetime
from uuid import UUID, uuid4

from ..schemas.activity import Activity, CreateActivityRequest, ResolveActivityCandidate
from ..schemas.activity_metadata import (
    ActivityAlias,
    ActivityRelationship,
    CheckpointTemplate,
    CreateActivityRelationshipRequest,
    CreatePreflightCheckRequest,
    PreflightCheck,
    PutCheckpointsRequest,
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
            source="user",
            confidence=1.0 if user_confirmed else 0.75,
            user_confirmed=user_confirmed,
            rejected=False,
            created_at=now,
        )
        self._store.activity_aliases[alias.id] = alias
        return alias

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
            user_confirmed=True,
            created_at=datetime.now(UTC),
        )
        self._store.activity_relationships[relationship.id] = relationship
        return relationship

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
            state="active",
            source=request.source,
            confidence=1.0 if request.source == "user_created" else None,
            failure_count=0,
        )
        self._store.preflight_checks[check.id] = check
        return check


def normalize_activity_key(display_name: str) -> str:
    lowered = display_name.strip().casefold()
    collapsed = re.sub(r"[^a-z0-9]+", "-", lowered).strip("-")
    return collapsed or "activity"
