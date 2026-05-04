# Phase 9 Optional Extension Hardening

Canonical scope: `parallax_v1_3_artifact_pack/docs/03_phased_implementation_plan.md`
Phase 9 only. Phase 9 enables optional search, analytics, geospatial, and k3s
readiness profiles after the baseline temporal loop and grounded Ask behavior are
already proven.

## Scope

Phase 9 implements validation and readiness artifacts for:

- pgvector HNSW retrieval tables from baseline migration `0007`;
- optional ParadeDB/`pg_search` BM25 profile `0010`;
- optional Timescale analytics profile `0009`;
- optional PostGIS geospatial profile `0012`;
- optional Timescale capture-context profile `0013`;
- k3s manifests that preserve Compose as local development source while adding
  internal-only cluster services, secrets, volumes, and health checks.

Phase 9 does not move source-of-truth timing data into extension-only tables.
Postgres relational tables remain canonical. Optional Timescale tables are
analytics projections, PostGIS adds geography/index helpers, and ParadeDB/pgvector
augment retrieval quality without replacing Phase 7 deterministic facts.

## Research Notes

Firecrawl was used for the external-source pass. The implementation tracks these
source-backed constraints:

- pgvector HNSW indexes use distance-specific operator classes such as
  `vector_cosine_ops`; `vector` indexes support up to 2,000 dimensions, which
  covers Parallax's selected 1024 and 1536 embedding tables.
- pgvector production guidance recommends concurrent index creation for live
  tables; Phase 9 records this in the re-embedding plan but validates the existing
  migration indexes in isolated smoke databases.
- ParadeDB current and legacy docs both support BM25 index creation with
  `USING bm25 (...) WITH (key_field='id')`; the key field must be unique and first
  in the indexed column list.
- PostGIS `ST_DWithin` on `geography` accepts distances in meters and includes a
  bounding-box comparison that can use available GiST indexes.
- K3s ships a `local-path` storage class suitable for single-node PVC readiness;
  production storage selection can be changed without changing Parallax source
  table semantics.
- Timescale logical restore uses a custom-format `pg_dump`, an initialized target
  database with TimescaleDB enabled, `timescaledb_pre_restore()`, non-parallel
  `pg_restore`, and `timescaledb_post_restore()`.

Timescale has version-sensitive continuous-aggregate behavior around ordered-set
percentiles. The canonical optional profiles keep the documented exact percentile
path, and `phase9-smoke` live-tests the selected Timescale image instead of
assuming compatibility.

## Re-Embedding and Dual-Read Plan

Embedding model changes must not swap retrieval behavior in place.

1. Register the new embedding profile in `embedding_model`.
2. Populate the dimension-appropriate table, for example
   `retrieval_embedding_1024` or `retrieval_embedding_1536`.
3. Run dual-read comparison for a stable query set: native FTS, old vector table,
   new vector table, and hybrid result merge.
4. Compare top-k overlap, expected evidence hit rate, and privacy filtering.
5. Switch the active read profile only after the new table matches or improves
   the measured evidence quality.
6. Retain the old embedding rows until rollback risk is low, then delete by model
   profile through a privacy-aware maintenance job.

`scripts/phase9_smoke.py` proves the mechanics by inserting 1024- and
1536-dimensional embeddings for the same retrieval documents and verifying both
tables return the same expected evidence card.

## k3s Readiness Boundary

Compose remains the local development runtime. The k3s manifests under
`infra/k3s/base/` are deployment-readiness artifacts, not a replacement for
`make dev-up`.

The manifests define:

- a `parallax` namespace with pod-security labels;
- a secret/config contract with no real production secret values;
- PVCs for Postgres data, Postgres WAL, objects, and logs;
- ClusterIP services only for data-plane, app-plane, and model endpoint wiring;
- readiness and liveness probes on every workload.

The model endpoint service is intentionally internal-only. No Phase 9 manifest
uses `NodePort` or `LoadBalancer` for model-serving paths.

The API manifest keeps the production external-bearer auth contract startable by
setting an asymmetric JWT algorithm plus JWKS URL, issuer, and audience
placeholders in the config map. Deployments must replace those placeholder
values with the real private-alpha/production identity provider before serving
traffic.

API probes are split by lifecycle responsibility: readiness uses `/v1/ready`
because it includes migration-state checks, while liveness uses `/v1/live` so
dependency outages remove the pod from service without forcing process restarts.

## Verification

`make phase9-smoke` runs isolated Docker-backed smoke databases for each optional
extension image and static-validates k3s manifests:

- pgvector: HNSW indexes exist and 1024/1536 dual-read comparison agrees.
- ParadeDB: BM25 profile applies and ranks the expected evidence document first.
- Timescale analytics: shadow metric table, hypertable, continuous aggregate,
  closed-bucket backfill, and Timescale-supported logical backup/restore work.
- PostGIS: baseline numeric lookup works before the profile; `ST_DWithin` works
  after the profile with GiST indexes.
- Timescale capture context: high-volume context metric projection and aggregate
  backfill work.
- k3s: manifests include secrets, PVCs, ClusterIP services, and probes.
- k3s API: production external-bearer settings are present, readiness points at
  `/v1/ready`, and liveness points at `/v1/live`.
