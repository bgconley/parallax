from __future__ import annotations

from datetime import datetime
from typing import Protocol
from uuid import UUID

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


class ActivityRepositoryProtocol(Protocol):
    def create(self, user_id: UUID, request: CreateActivityRequest) -> Activity: ...

    def list_activities(
        self,
        user_id: UUID,
        query: str | None = None,
        limit: int = 50,
    ) -> list[Activity]: ...

    def get(self, user_id: UUID, activity_id: UUID) -> Activity | None: ...

    def resolve(self, user_id: UUID, query: str, limit: int) -> list[ResolveActivityCandidate]: ...

    def add_alias(
        self,
        user_id: UUID,
        activity_id: UUID,
        alias_text: str,
        *,
        user_confirmed: bool,
    ) -> ActivityAlias: ...

    def list_aliases(self, user_id: UUID, activity_id: UUID) -> list[ActivityAlias]: ...

    def decide_alias(
        self,
        user_id: UUID,
        activity_id: UUID,
        alias_id: UUID,
        decision: str,
    ) -> ActivityAlias | None: ...

    def create_relationship(
        self,
        user_id: UUID,
        activity_id: UUID,
        request: CreateActivityRelationshipRequest,
    ) -> ActivityRelationship: ...

    def list_relationships(
        self,
        user_id: UUID,
        activity_id: UUID,
    ) -> list[ActivityRelationship]: ...

    def decide_relationship(
        self,
        user_id: UUID,
        activity_id: UUID,
        relationship_id: UUID,
        decision: str,
    ) -> ActivityRelationship | None: ...

    def merge_preview(
        self,
        user_id: UUID,
        source_activity_id: UUID,
        target_activity_id: UUID,
    ) -> ActivityMergePreview: ...

    def merge_activities(
        self,
        user_id: UUID,
        source_activity_id: UUID,
        target_activity_id: UUID,
        reason: str | None,
    ) -> ActivityIdentityChange: ...

    def split_preview(
        self,
        user_id: UUID,
        source_activity_id: UUID,
        proposed_display_name: str,
        session_ids: list[UUID],
    ) -> ActivitySplitPreview: ...

    def list_checkpoints(self, user_id: UUID, activity_id: UUID) -> list[CheckpointTemplate]: ...

    def replace_checkpoints(
        self,
        user_id: UUID,
        activity_id: UUID,
        request: PutCheckpointsRequest,
    ) -> list[CheckpointTemplate]: ...

    def list_preflight_checks(self, user_id: UUID, activity_id: UUID) -> list[PreflightCheck]: ...

    def list_resource_dependencies(
        self,
        user_id: UUID,
        activity_id: UUID,
    ) -> list[ResourceDependency]: ...

    def create_preflight_check(
        self,
        user_id: UUID,
        activity_id: UUID,
        request: CreatePreflightCheckRequest,
    ) -> PreflightCheck: ...

    def decide_preflight_check(
        self,
        user_id: UUID,
        activity_id: UUID,
        check_id: UUID,
        decision: PreflightDecision,
        *,
        snoozed_until: datetime | None,
        reason: str | None,
    ) -> PreflightCheck | None: ...
