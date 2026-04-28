from __future__ import annotations

from ..schemas.timing import (
    ModelInclusion,
    ModelUpdateDecisionType,
    ReviewTimingSessionRequest,
    RunQuality,
    TimingSessionStatus,
)

_ALLOWED_MODEL_INCLUSIONS: dict[ModelUpdateDecisionType, set[ModelInclusion]] = {
    "save_useful_run": {"full"},
    "mark_unusual": {
        "full",
        "active_duration_only",
        "wall_envelope_only",
        "friction_patterns_only",
        "query_evidence_only",
    },
    "save_partial": {"active_duration_only", "query_evidence_only"},
    "active_only": {"active_duration_only"},
    "friction_only": {"friction_patterns_only"},
    "query_evidence_only": {"query_evidence_only"},
    "discard_timing_keep_note": {"exclude"},
    "discard_all": {"exclude"},
}


def is_model_inclusion_allowed(request: ReviewTimingSessionRequest) -> bool:
    return request.model_inclusion in _ALLOWED_MODEL_INCLUSIONS[request.decision]


def is_discard_decision(decision: ModelUpdateDecisionType) -> bool:
    return decision in {"discard_timing_keep_note", "discard_all"}


def status_for_decision(decision: ModelUpdateDecisionType) -> TimingSessionStatus:
    return "discarded" if is_discard_decision(decision) else "reviewed"


def run_quality_for_decision(decision: ModelUpdateDecisionType) -> RunQuality:
    if decision == "mark_unusual":
        return "useful_unusual"
    if decision == "save_partial":
        return "partial"
    if decision in {"query_evidence_only", "discard_timing_keep_note"}:
        return "do_not_train"
    if decision == "discard_all":
        return "bad_timer"
    return "typical"
