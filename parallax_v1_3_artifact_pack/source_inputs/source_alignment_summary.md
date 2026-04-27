# Source Artifact Alignment Summary

This v1.3 pack was generated after reviewing the uploaded v0.9, v1.0, and v1.1 artifact packs plus the prior handoff audit.

## Issues corrected

- Project is now named Parallax throughout generated source-facing artifacts.
- Retired placeholders are removed from v1.3.
- Backend/domain contracts are canonical.
- UI contracts are explicitly treated as projections.
- `user_id` replaces the prior identity split.
- Event/status/review-decision enums are normalized.
- OpenAPI includes the full P0 surface.
- Offline mutation/idempotency envelope is required for every mutating endpoint.
- Read-only resolver POSTs are explicitly exempt from mutation semantics and cannot write domain data.
- Context capture policy and timing review flags are explicit API/DB/schema contracts.
- Capture snapshot creation can explicitly link checkpoint and known place context.
- Context-specific privacy export/redaction/delete scopes cover location, radio,
  place, and context-derived features.
- Radio observation display text is restricted to redacted/user-safe labels.
- TimescaleDB, ParadeDB, and PostGIS are optional profiles rather than baseline dependencies.
- Design language is articulated for a Figma-capable agent without requiring direct Figma modification.

## Historical packs

Do not hand the earlier packs to an implementation agent as equal source truth. Use this v1.3 pack as canonical. Earlier packs may be referenced only for historical design intent or source audit.

## v1.3 added alignment

The user specifically asked whether timing analytics, capture workflows, geospatial context, Wi-Fi/BLE/GPS data, and user stories were complete enough. v1.3 answers that by adding capture context snapshots, sensor/permission data contracts, context capture policy, timing review flags, context-specific privacy deletion guidance, context-aware analytics, optional geospatial/time-series profiles, and new user stories/acceptance gates.
