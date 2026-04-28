from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from ..schemas.context import ContextCapturePolicy


def default_context_capture_policy(user_id: UUID) -> ContextCapturePolicy:
    now = datetime.now(UTC)
    return ContextCapturePolicy(
        id=uuid4(),
        user_id=user_id,
        location_enabled=False,
        precise_location_enabled=False,
        background_location_enabled=False,
        radio_context_enabled=False,
        motion_context_enabled=False,
        device_context_enabled=True,
        raw_location_retention_days=None,
        raw_radio_retention_days=None,
        default_location_retention_policy="derived_only",
        default_radio_retention_policy="derived_only",
        per_run_context_default=True,
        updated_at=now,
        created_at=now,
    )
