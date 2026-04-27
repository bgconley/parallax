from pathlib import Path

import yaml
from parallax_api.main import create_app

ROOT = Path(__file__).resolve().parents[1]
OPENAPI_PATH = ROOT / "parallax_v1_3_artifact_pack/contracts/openapi/parallax_api_v1_3.yaml"

PHASE1_ENDPOINTS = {
    ("GET", "/v1/health"),
    ("GET", "/v1/live"),
    ("GET", "/v1/ready"),
    ("GET", "/v1/version"),
    ("POST", "/v1/activities"),
    ("GET", "/v1/activities"),
    ("POST", "/v1/activities/resolve"),
    ("GET", "/v1/activities/{activity_id}"),
    ("POST", "/v1/timing/sessions"),
    ("GET", "/v1/timing/sessions/{session_id}"),
    ("POST", "/v1/timing/sessions/{session_id}/events"),
    ("POST", "/v1/timing/sessions/{session_id}/complete"),
    ("POST", "/v1/sync/push"),
}


def test_phase1_runtime_surface_matches_phase1_canonical_subset() -> None:
    runtime_endpoints = {
        (method, route.path)
        for route in create_app().routes
        for method in getattr(route, "methods", [])
        if route.path.startswith("/v1/")
    }

    assert runtime_endpoints == PHASE1_ENDPOINTS


def test_phase1_surface_is_declared_as_subset_of_full_canonical_openapi() -> None:
    canonical = yaml.safe_load(OPENAPI_PATH.read_text())
    canonical_endpoints = {
        (method.upper(), path)
        for path, item in canonical["paths"].items()
        for method in item
        if method in {"get", "post", "put", "patch", "delete"}
    }
    phase1_doc = (ROOT / "docs/architecture/phase1_core_loop.md").read_text()

    assert PHASE1_ENDPOINTS <= canonical_endpoints
    assert canonical_endpoints - PHASE1_ENDPOINTS
    assert (
        "Phase 1 implements a deliberate subset of the canonical v1.3 OpenAPI surface"
        in phase1_doc
    )
