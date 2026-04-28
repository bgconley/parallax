from pathlib import Path

import yaml
from parallax_api.main import create_app

ROOT = Path(__file__).resolve().parents[1]
OPENAPI_PATH = ROOT / "parallax_v1_3_artifact_pack/contracts/openapi/parallax_api_v1_3.yaml"

IMPLEMENTED_ENDPOINTS = {
    ("GET", "/v1/health"),
    ("GET", "/v1/live"),
    ("GET", "/v1/ready"),
    ("GET", "/v1/version"),
    ("POST", "/v1/activities"),
    ("GET", "/v1/activities"),
    ("POST", "/v1/activities/resolve"),
    ("GET", "/v1/activities/{activity_id}"),
    ("GET", "/v1/activities/{activity_id}/profile"),
    ("POST", "/v1/timing/sessions"),
    ("GET", "/v1/timing/sessions/{session_id}"),
    ("POST", "/v1/timing/sessions/{session_id}/events"),
    ("POST", "/v1/timing/sessions/{session_id}/complete"),
    ("POST", "/v1/timing/sessions/{session_id}/review"),
    ("POST", "/v1/timing/sessions/{session_id}/discard"),
    ("POST", "/v1/timing/sessions/{session_id}/annotations"),
    ("GET", "/v1/timing/annotations/{annotation_id}"),
    ("POST", "/v1/timing/annotations/{annotation_id}/extract"),
    ("POST", "/v1/timing/extracted-events/{event_id}/confirm"),
    ("POST", "/v1/timing/extracted-events/{event_id}/correct"),
    ("GET", "/v1/privacy/context-capture-policy"),
    ("PATCH", "/v1/privacy/context-capture-policy"),
    ("POST", "/v1/timing/sessions/{session_id}/capture-context"),
    ("GET", "/v1/timing/sessions/{session_id}/capture-context"),
    ("GET", "/v1/timing/sessions/{session_id}/review-flags"),
    ("PATCH", "/v1/timing/review-flags/{flag_id}"),
    ("POST", "/v1/places"),
    ("GET", "/v1/places"),
    ("POST", "/v1/places/resolve"),
    ("PATCH", "/v1/places/{place_id}"),
    ("POST", "/v1/sync/push"),
}


def test_runtime_surface_matches_active_phase_canonical_subset() -> None:
    runtime_endpoints = {
        (method, route.path)
        for route in create_app().routes
        for method in getattr(route, "methods", [])
        if route.path.startswith("/v1/")
    }

    assert runtime_endpoints == IMPLEMENTED_ENDPOINTS


def test_implemented_surface_is_declared_as_subset_of_full_canonical_openapi() -> None:
    canonical = yaml.safe_load(OPENAPI_PATH.read_text())
    canonical_endpoints = {
        (method.upper(), path)
        for path, item in canonical["paths"].items()
        for method in item
        if method in {"get", "post", "put", "patch", "delete"}
    }
    phase1_doc = (ROOT / "docs/architecture/phase1_core_loop.md").read_text()
    phase2_doc = (ROOT / "docs/architecture/phase2_review_profile.md").read_text()
    phase_scope_doc = (ROOT / "docs/architecture/api_surface_phase_scope.md").read_text()

    assert IMPLEMENTED_ENDPOINTS <= canonical_endpoints
    assert canonical_endpoints - IMPLEMENTED_ENDPOINTS
    assert (
        "Phase 1 implements a deliberate subset of the canonical v1.3 OpenAPI surface"
        in phase1_doc
    )
    phase3_doc = (ROOT / "docs/architecture/phase3_context_capture.md").read_text()

    assert "Phase 2 extends the implemented canonical subset" in phase2_doc
    assert "Phase 3 extends the implemented canonical subset" in phase3_doc
    assert "not the full v1.3 release contract" in phase_scope_doc
    assert "Phase 5 and later endpoints remain unimplemented" in phase_scope_doc
    for method, path in sorted(canonical_endpoints - IMPLEMENTED_ENDPOINTS):
        assert f"- `{method} {path}`" in phase_scope_doc
