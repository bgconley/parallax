from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from ..schemas.context import AnnotationStatus, CreateAnnotationRequest, UserPlace


def place_from_row(row: Mapping[str, Any]) -> UserPlace:
    data = dict(row)
    data["latitude"] = float(data["latitude"]) if data.get("latitude") is not None else None
    data["longitude"] = float(data["longitude"]) if data.get("longitude") is not None else None
    return UserPlace.model_validate(data)


def initial_annotation_status(request: CreateAnnotationRequest) -> AnnotationStatus:
    if request.input_mode == "voice" and request.raw_text is None:
        return "transcription_pending"
    if request.raw_text is not None or request.input_mode in {"quick_chip", "review_note"}:
        return "extraction_pending"
    return "captured"
