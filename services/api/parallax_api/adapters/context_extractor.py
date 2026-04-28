from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Protocol

from pydantic import Field

from ..schemas.common import ApiModel
from ..schemas.context import TemporalContextAnnotation
from ..schemas.timing import CountPolicy, FrictionCategory, TemporalSpanType


class ExtractionModelUnavailable(RuntimeError):
    pass


class ExtractorCandidate(ApiModel):
    span_type: TemporalSpanType
    friction_category: FrictionCategory
    friction_subtype: str | None = None
    resource_name: str | None = None
    location_from: str | None = None
    location_to: str | None = None
    duration_seconds: int | None = Field(default=None, ge=0)
    count_policy: CountPolicy
    count_in_wall_time: bool
    count_in_active_time: bool
    model_update_scopes: list[str]
    suggested_preflight_text: str | None = None
    confidence: float = Field(ge=0, le=1)
    sensitive_data_detected: bool = False
    source_json: dict[str, object]


class ExtractorOutput(ApiModel):
    candidates: list[ExtractorCandidate]


class ContextExtractor(Protocol):
    def extract(self, annotation: TemporalContextAnnotation) -> dict[str, Any]: ...


class DeterministicContextExtractor:
    """Local Phase 4 extractor boundary.

    This adapter intentionally returns structured data only. It does not log or
    persist the raw note; the caller records only hashes in model_invocation.
    """

    def extract(self, annotation: TemporalContextAnnotation) -> dict[str, Any]:
        text = annotation.redacted_text or annotation.raw_text or ""
        lowered = text.casefold()
        if "PARALLAX_TEST_MODEL_UNAVAILABLE".casefold() in lowered:
            raise ExtractionModelUnavailable("local extractor unavailable")
        if "PARALLAX_TEST_INVALID_STRUCTURED_EXTRACTION".casefold() in lowered:
            return {"candidates": [{"span_type": "resource_detour"}]}
        if "sponge" in lowered and any(term in lowered for term in ("find", "missing", "stop")):
            duration = _duration_from_text(lowered) or annotation.timer_elapsed_seconds
            return {
                "candidates": [
                    {
                        "span_type": "resource_detour",
                        "friction_category": "resource",
                        "resource_name": "sponge",
                        "duration_seconds": duration,
                        "count_policy": "wall_only",
                        "count_in_wall_time": True,
                        "count_in_active_time": False,
                        "model_update_scopes": ["friction_patterns", "preflight_suggestions"],
                        "suggested_preflight_text": (
                            "Check sponge availability before starting this activity."
                        ),
                        "confidence": 0.91,
                        "sensitive_data_detected": False,
                        "source_json": {
                            "evidence": "resource_detour_keyword",
                            "schema_version": "context-extractor-output-v1.3",
                        },
                    }
                ]
            }
        return {"candidates": []}


def content_hash(payload: object) -> str:
    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def annotation_request_hash(annotation: TemporalContextAnnotation) -> str:
    payload = {
        "annotation_id": str(annotation.id),
        "privacy_class": annotation.privacy_class,
        "redacted_text": annotation.redacted_text,
        "raw_text_hash": hashlib.sha256((annotation.raw_text or "").encode("utf-8")).hexdigest(),
        "timer_elapsed_seconds": annotation.timer_elapsed_seconds,
        "timer_active_seconds": annotation.timer_active_seconds,
    }
    return content_hash(payload)


def _duration_from_text(text: str) -> int | None:
    match = re.search(r"\b(\d+)\s*(minute|minutes|min|mins)\b", text)
    if match:
        return int(match.group(1)) * 60
    match = re.search(r"\b(\d+)\s*(second|seconds|sec|secs)\b", text)
    if match:
        return int(match.group(1))
    return None
