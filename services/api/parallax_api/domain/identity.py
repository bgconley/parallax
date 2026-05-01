from __future__ import annotations

import hashlib
import hmac
from dataclasses import dataclass
from datetime import UTC, datetime
from functools import lru_cache
from pathlib import Path
from uuid import UUID


@dataclass(frozen=True)
class FirebasePrincipal:
    provider: str
    issuer: str
    subject: str
    firebase_project_id: str
    firebase_tenant_id: str = ""
    sign_in_provider: str | None = None
    email: str | None = None
    email_verified: bool = False
    display_name: str | None = None
    photo_url: str | None = None
    auth_time: datetime | None = None

    @classmethod
    def from_decoded(cls, decoded: dict[str, object]) -> FirebasePrincipal:
        firebase_claim = decoded.get("firebase")
        firebase = firebase_claim if isinstance(firebase_claim, dict) else {}
        auth_time = _auth_time(decoded.get("auth_time"))
        return cls(
            provider="firebase_auth",
            issuer=str(decoded.get("iss") or ""),
            subject=str(decoded.get("uid") or decoded.get("sub") or ""),
            firebase_project_id=str(decoded.get("aud") or ""),
            firebase_tenant_id=str(firebase.get("tenant") or ""),
            sign_in_provider=_optional_str(firebase.get("sign_in_provider")),
            email=_optional_str(decoded.get("email")),
            email_verified=bool(decoded.get("email_verified", False)),
            display_name=_optional_str(decoded.get("name")),
            photo_url=_optional_str(decoded.get("picture")),
            auth_time=auth_time,
        )


@dataclass(frozen=True)
class IdentityProvisioningPolicy:
    auto_provision: bool
    invite_required: bool
    allowed_email_domains: frozenset[str]
    allowed_emails: frozenset[str]
    allowed_firebase_uids: frozenset[str]
    email_conflict_policy: str
    tombstone_secret: str | None

    def permits_first_login(self, principal: FirebasePrincipal) -> bool:
        if self.auto_provision and not self.invite_required:
            return True
        if principal.subject in self.allowed_firebase_uids:
            return True
        if principal.email_verified and principal.email is not None:
            email = _normalize_email(principal.email)
            if email in self.allowed_emails:
                return True
            domain = email.rsplit("@", maxsplit=1)[-1] if "@" in email else ""
            if domain in self.allowed_email_domains:
                return True
        return False


@dataclass(frozen=True)
class ExternalIdentityRecord:
    user_id: UUID
    provider: str
    issuer: str
    subject: str
    firebase_tenant_id: str
    firebase_project_id: str
    sign_in_provider: str | None
    email: str | None
    email_verified: bool
    display_name: str | None
    photo_url: str | None
    auth_time: datetime | None
    created_at: datetime
    updated_at: datetime
    last_seen_at: datetime


class IdentityResolutionError(Exception):
    error_code = "auth_invalid"


class IdentityNotAllowedError(IdentityResolutionError):
    error_code = "auth_not_allowed"


class IdentityConflictError(IdentityResolutionError):
    error_code = "auth_identity_conflict"


class IdentityDeletedError(IdentityResolutionError):
    error_code = "auth_identity_deleted"


def identity_key(principal: FirebasePrincipal) -> tuple[str, str, str, str]:
    return (
        principal.provider,
        principal.issuer,
        principal.subject,
        principal.firebase_tenant_id,
    )


def normalize_identity_email(email: str | None) -> str | None:
    return _normalize_email(email) if email else None


def read_line_set(path: str | None, *, casefold: bool = True) -> frozenset[str]:
    if not path:
        return frozenset()
    file_path = Path(path)
    stat = file_path.stat()
    return _read_line_set_cached(str(file_path), casefold, stat.st_mtime_ns, stat.st_size)


@lru_cache(maxsize=64)
def _read_line_set_cached(
    path: str,
    casefold: bool,
    mtime_ns: int,
    size: int,
) -> frozenset[str]:
    del mtime_ns, size
    values: set[str] = set()
    for line in Path(path).read_text().splitlines():
        value = line.strip()
        if value and not value.startswith("#"):
            values.add(value.casefold() if casefold else value)
    return frozenset(values)


def subject_hmac(principal: FirebasePrincipal, secret: str) -> bytes:
    message = "\x1f".join(identity_key(principal)).encode("utf-8")
    return hmac.new(secret.encode("utf-8"), message, hashlib.sha256).digest()


def _normalize_email(email: str) -> str:
    return email.strip().casefold()


def _optional_str(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _auth_time(value: object) -> datetime | None:
    if value is None:
        return None
    try:
        if isinstance(value, int | float | str | bytes | bytearray):
            return datetime.fromtimestamp(int(value), UTC)
        return None
    except (TypeError, ValueError, OSError):
        return None
