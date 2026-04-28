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


def test_runtime_surface_matches_canonical_openapi() -> None:
    runtime_endpoints = {
        (method, route.path)
        for route in create_app().routes
        for method in getattr(route, "methods", [])
        if route.path.startswith("/v1/")
    }
    canonical = yaml.safe_load(OPENAPI_PATH.read_text())
    canonical_endpoints = {
        (method.upper(), path)
        for path, item in canonical["paths"].items()
        for method in item
        if method in {"get", "post", "put", "patch", "delete"}
    }

    assert runtime_endpoints == canonical_endpoints
