from __future__ import annotations

from pathlib import Path

import yaml
from parallax_api.settings import ApiSettings, validate_runtime_settings

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_optional_profiles_are_copied_outside_baseline_migrations() -> None:
    profile_dir = REPO_ROOT / "database" / "optional_profiles"
    names = {path.name for path in profile_dir.glob("*.sql")}
    assert names == {
        "0009_timescale_optional_analytics_profile.sql",
        "0010_paradedb_optional_search_profile.sql",
        "0012_postgis_optional_geospatial_profile.sql",
        "0013_timescale_capture_context_profile.sql",
    }
    baseline_migrations = (REPO_ROOT / "migrations").glob("*.sql")
    assert not any("optional_profiles" in path.as_posix() for path in baseline_migrations)
    canonical_dir = REPO_ROOT / "parallax_v1_3_artifact_pack" / "database" / "optional_profiles"
    for name in names:
        assert (profile_dir / name).read_text() == (canonical_dir / name).read_text()


def test_phase9_smoke_is_wired_to_makefile() -> None:
    makefile = (REPO_ROOT / "Makefile").read_text()
    assert "phase9-smoke" in makefile
    assert "scripts/phase9_smoke.py" in makefile


def test_phase9_doc_records_reembedding_and_dual_read_plan() -> None:
    doc = (
        REPO_ROOT / "docs" / "architecture" / "phase9_optional_extension_hardening.md"
    ).read_text()
    assert "Re-Embedding and Dual-Read Plan" in doc
    assert "retrieval_embedding_1024" in doc
    assert "retrieval_embedding_1536" in doc
    assert "Compose remains the local development runtime" in doc


def test_k3s_manifests_keep_model_endpoint_internal_and_probe_workloads() -> None:
    docs = _load_k3s_docs()
    services = [doc for doc in docs if doc.get("kind") == "Service"]
    model_services = [
        doc for doc in services if "model" in doc.get("metadata", {}).get("name", "")
    ]
    assert model_services
    assert all(
        doc.get("spec", {}).get("type", "ClusterIP") == "ClusterIP"
        for doc in model_services
    )

    workloads = [doc for doc in docs if doc.get("kind") in {"Deployment", "StatefulSet"}]
    assert workloads
    for workload in workloads:
        containers = workload["spec"]["template"]["spec"]["containers"]
        name = workload["metadata"]["name"]
        assert any("readinessProbe" in container for container in containers), name
        assert any("livenessProbe" in container for container in containers), name


def test_k3s_manifests_include_secret_and_storage_contracts() -> None:
    docs = _load_k3s_docs()
    assert any(doc.get("kind") == "Secret" for doc in docs)
    pvcs = [doc for doc in docs if doc.get("kind") == "PersistentVolumeClaim"]
    assert {pvc["metadata"]["name"] for pvc in pvcs} >= {
        "parallax-postgres-data",
        "parallax-postgres-wal",
        "parallax-objects",
        "parallax-logs",
    }
    assert all(pvc["spec"]["storageClassName"] == "local-path" for pvc in pvcs)


def test_k3s_production_external_bearer_contract_is_startable() -> None:
    config = _doc_by_kind_and_name("ConfigMap", "parallax-config")
    data = config["data"]
    assert data["PARALLAX_ENV"] == "production"
    assert data["PARALLAX_AUTH_MODE"] == "external_bearer"
    assert data["PARALLAX_AUTH_JWT_ALGORITHM"] in {"RS256", "ES256"}
    assert data["PARALLAX_AUTH_JWKS_URL"].startswith("https://")
    assert data["PARALLAX_AUTH_JWT_ISSUER"].startswith("https://")
    assert data["PARALLAX_AUTH_JWT_AUDIENCE"]
    validate_runtime_settings(
        ApiSettings(
            env=data["PARALLAX_ENV"],
            auth_mode=data["PARALLAX_AUTH_MODE"],
            auth_jwt_algorithm=data["PARALLAX_AUTH_JWT_ALGORITHM"],
            auth_jwks_url=data["PARALLAX_AUTH_JWKS_URL"],
            auth_jwt_issuer=data["PARALLAX_AUTH_JWT_ISSUER"],
            auth_jwt_audience=data["PARALLAX_AUTH_JWT_AUDIENCE"],
            metrics_token="phase9-k3s-test-token",
        )
    )


def test_k3s_api_uses_readiness_and_process_liveness_endpoints() -> None:
    api = _doc_by_kind_and_name("Deployment", "parallax-api")
    container = api["spec"]["template"]["spec"]["containers"][0]
    assert container["readinessProbe"]["httpGet"]["path"] == "/v1/ready"
    assert container["livenessProbe"]["httpGet"]["path"] == "/v1/live"


def test_postgis_profile_preserves_baseline_numeric_path() -> None:
    profile = (
        REPO_ROOT
        / "database"
        / "optional_profiles"
        / "0012_postgis_optional_geospatial_profile.sql"
    ).read_text()
    assert "ADD COLUMN geog geography(Point, 4326)" in profile
    assert "idx_user_place_geog_gist" in profile
    query_examples = (
        REPO_ROOT
        / "parallax_v1_3_artifact_pack"
        / "database"
        / "queries"
        / "context_geospatial_queries.sql"
    ).read_text()
    assert "latitude BETWEEN" in query_examples
    assert "ST_DWithin" in query_examples


def _load_k3s_docs() -> list[dict[str, object]]:
    docs: list[dict[str, object]] = []
    for path in sorted((REPO_ROOT / "infra" / "k3s" / "base").glob("*.yaml")):
        for doc in yaml.safe_load_all(path.read_text()):
            if doc:
                docs.append(doc)
    return docs


def _doc_by_kind_and_name(kind: str, name: str) -> dict[str, object]:
    for doc in _load_k3s_docs():
        if doc.get("kind") == kind and doc.get("metadata", {}).get("name") == name:
            return doc
    raise AssertionError(f"missing k3s document: {kind}/{name}")
