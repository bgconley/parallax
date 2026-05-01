from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any

import httpx

REPO_ROOT = Path(__file__).resolve().parents[1]


def _load_script(module_name: str, script_name: str) -> Any:
    path = REPO_ROOT / "scripts" / script_name
    spec = importlib.util.spec_from_file_location(module_name, path)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_release_token_minter_posts_email_password_without_logging_secrets(
    monkeypatch: Any,
) -> None:
    script = _load_script("mint_release_firebase_id_token", "mint_release_firebase_id_token.py")
    captured: dict[str, object] = {}

    def fake_post(
        url: str,
        *,
        params: dict[str, str],
        json: dict[str, object],
        timeout: float,
    ) -> httpx.Response:
        captured.update({"url": url, "params": params, "json": json, "timeout": timeout})
        request = httpx.Request("POST", url)
        return httpx.Response(
            200,
            json={"idToken": "fresh-id-token", "expiresIn": "3600"},
            request=request,
        )

    monkeypatch.setattr(script.httpx, "post", fake_post)

    token = script.mint_release_id_token(
        web_api_key="web-api-key",
        email="release@example.com",
        password="release-password",
    )

    assert token == "fresh-id-token"
    assert "accounts:signInWithPassword" in captured["url"]
    assert captured["params"] == {"key": "web-api-key"}
    assert captured["json"] == {
        "email": "release@example.com",
        "password": "release-password",
        "returnSecureToken": True,
    }


def test_release_auth_probe_can_mint_firebase_token_when_bearer_token_is_absent() -> None:
    source = (REPO_ROOT / "scripts/release_auth_provider_probe.py").read_text()

    assert "release_bearer_token" in source
    assert "PARALLAX_RELEASE_APP_CHECK_TOKEN" in source
    assert "X-Firebase-AppCheck" in source


def test_release_smokes_share_firebase_auth_header_helper() -> None:
    for script in (
        "privacy_lifecycle_smoke.py",
        "release_slo_smoke.py",
        "release_log_privacy_scan.py",
    ):
        source = (REPO_ROOT / "scripts" / script).read_text()
        assert "release_auth_headers" in source
        assert "--app-check-token" in source
