from pathlib import Path

import yaml
from parallax_api.main import create_app

ROOT = Path(__file__).resolve().parents[1]
OPENAPI_PATH = ROOT / "parallax_v1_3_artifact_pack/contracts/openapi/parallax_api_v1_3.yaml"


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
