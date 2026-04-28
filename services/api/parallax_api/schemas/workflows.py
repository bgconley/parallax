from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from .common import ApiModel

WorkflowStatus = Literal[
    "queued",
    "running",
    "succeeded",
    "failed",
    "cancelled",
    "waiting_for_user",
]
WorkflowType = Literal[
    "ProcessContextAnnotationWorkflow",
    "InferPlaceFromContextWorkflow",
    "PrivacyExportWorkflow",
    "PrivacyRedactWorkflow",
    "PrivacyDeleteWorkflow",
    "FeatureVectorRecomputeWorkflow",
]


class WorkflowRun(ApiModel):
    id: UUID
    user_id: UUID | None
    workflow_type: WorkflowType | str
    temporal_workflow_id: str | None = None
    status: WorkflowStatus
    input_ref: dict[str, object]
    result_ref: dict[str, object]
    error_code: str | None = None
    error_message: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
