from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any


def safe_validation_errors(errors: Iterable[Mapping[str, Any]]) -> list[dict[str, object]]:
    """Return validation details without echoing request payload values."""
    safe_errors: list[dict[str, object]] = []
    for error in errors:
        safe_errors.append(
            {
                "type": str(error.get("type", "validation_error")),
                "loc": list(error.get("loc", [])),
                "msg": str(error.get("msg", "request validation failed")),
            }
        )
    return safe_errors
