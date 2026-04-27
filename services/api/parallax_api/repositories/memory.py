from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID

from ..schemas.activity import Activity
from ..schemas.timing import TimingEvent, TimingSession

MutationKey = tuple[UUID, str, str]


@dataclass
class MutationRecord:
    mutation_type: str
    entity_type: str
    entity_id: UUID
    result: object


@dataclass
class InMemoryStore:
    activities: dict[UUID, Activity] = field(default_factory=dict)
    activity_keys: dict[tuple[UUID, str], UUID] = field(default_factory=dict)
    sessions: dict[UUID, TimingSession] = field(default_factory=dict)
    session_events: dict[UUID, list[TimingEvent]] = field(default_factory=dict)
    mutation_records: dict[MutationKey, MutationRecord] = field(default_factory=dict)
