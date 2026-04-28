from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _use_development_header_auth_in_tests(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PARALLAX_ENV", "test")
    monkeypatch.setenv("PARALLAX_AUTH_MODE", "dev_header")
