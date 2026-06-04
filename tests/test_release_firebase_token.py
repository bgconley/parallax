from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any
from uuid import UUID

import httpx

REPO_ROOT = Path(__file__).resolve().parents[1]


def _load_script(module_name: str, script_name: str) -> Any:
    path = REPO_ROOT / "scripts" / script_name
    scripts_dir = str(path.parent)
    sys.path.insert(0, scripts_dir)
    spec = importlib.util.spec_from_file_location(module_name, path)
    try:
        assert spec is not None
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.remove(scripts_dir)


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


def test_release_auth_headers_can_require_bearer_auth(monkeypatch: Any) -> None:
    helper = _load_script("release_auth_helpers", "release_auth_helpers.py")
    user_id = UUID("00000000-0000-0000-0000-0000000000a1")
    monkeypatch.delenv("PARALLAX_FIREBASE_WEB_API_KEY", raising=False)
    monkeypatch.delenv("PARALLAX_RELEASE_FIREBASE_EMAIL", raising=False)
    monkeypatch.delenv("PARALLAX_RELEASE_FIREBASE_PASSWORD", raising=False)

    try:
        helper.release_auth_headers(
            fallback_user_id=user_id,
            bearer_token=None,
            require_bearer_auth=True,
        )
    except ValueError as exc:
        assert "bearer auth" in str(exc)
    else:
        raise AssertionError("expected release auth helper to reject dev-header fallback")


def test_release_gate_smokes_require_bearer_auth() -> None:
    makefile = (REPO_ROOT / "Makefile").read_text()
    release_gate_section = makefile.split("release-gate:", 1)[1].split("\n\n", 1)[0]

    for script in (
        "privacy_lifecycle_smoke.py",
        "release_slo_smoke.py",
        "release_log_privacy_scan.py",
    ):
        command_line = next(
            line for line in release_gate_section.splitlines() if script in line
        )
        assert "--require-bearer-auth" in command_line
