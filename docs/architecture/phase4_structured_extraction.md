# Phase 4 Structured Extraction

Phase 4 extends the implemented canonical subset with validated context
extraction and correction endpoints:

- `POST /v1/timing/annotations/{annotation_id}/extract`
- `POST /v1/timing/extracted-events/{event_id}/confirm`
- `POST /v1/timing/extracted-events/{event_id}/correct`

The scope is limited to `docs/03_phased_implementation_plan.md` Phase 4. Ask
About Time, prediction APIs, privacy export/delete/redact, production auth,
optional geospatial profiles, and later Temporal workflows remain out of scope
until their owning phases are explicitly started.

## Architecture

Routes stay thin and delegate to `ExtractionService`. API DTOs live in
`schemas/extraction.py`. The local model boundary lives in
`adapters/context_extractor.py` behind a `ContextExtractor` protocol, with prompt
and schema version metadata centralized in `domain/extraction_registry.py`.
Context persistence remains behind the `contexts` unit-of-work repository, with
Postgres extraction and place-inference SQL split into dedicated modules.

## Semantics

Extraction produces `temporal_extracted_context_event` candidates only. It does
not mutate source timing events, session wall/active totals, or source notes.
Model invocation records store hashes and schema metadata, not raw prompts or
raw annotation text. Private or sensitive annotations are blocked before model
invocation unless a later redaction workflow supplies safe text.

The Phase 4 golden path recognizes a sponge resource detour as a candidate with
`count_policy=wall_only`, a suggested preflight check, and
`confirmation_state=needs_confirmation`. Confirmation or correction applies a
derived `timing_event_span`, persists correction audit state when applicable,
and triggers activity-profile recomputation. Resolver POST endpoints remain
read-only; inferred place observations are created during capture-context
processing and only read by `POST /v1/places/resolve`.

## Verification

Phase 4 is complete only when local unit/static/security/contract checks pass
and the GPU node passes `make schema-smoke`, `make phase1-smoke`,
`make phase2-smoke`, `make phase3-smoke`, and `make phase4-smoke` against the
current working tree.
