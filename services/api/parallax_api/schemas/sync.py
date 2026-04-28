from __future__ import annotations

from datetime import datetime

from pydantic import Field

from .common import ApiModel, MutationEnvelope


class SyncPushOperation(ApiModel):
    operation: str = Field(min_length=1)
    path: str = Field(min_length=1)
    body: dict[str, object] = Field(default_factory=dict)


class SyncPushRequest(ApiModel):
    mutation: MutationEnvelope
    client_device_id: str = Field(min_length=1)
    mutations: list[SyncPushOperation]


class SyncPushResponse(ApiModel):
    accepted: bool
    operation_count: int = Field(ge=0)
    server_time: datetime


class SyncPullResponse(ApiModel):
    cursor: str
    changes: list[dict[str, object]]
    server_time: datetime
