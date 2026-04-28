from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ExtractionSchemaVersion:
    role: str
    provider: str
    model_name: str
    model_version: str
    prompt_version: str
    schema_version: str


CONTEXT_EXTRACTOR_V1 = ExtractionSchemaVersion(
    role="context_extractor",
    provider="parallax-local",
    model_name="deterministic-context-extractor",
    model_version="v1",
    prompt_version="context-extractor-v1.3-phase4",
    schema_version="context-extractor-output-v1.3",
)
