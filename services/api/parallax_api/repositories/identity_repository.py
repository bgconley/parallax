from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from ..domain.identity import (
    ExternalIdentityRecord,
    FirebasePrincipal,
    IdentityConflictError,
    IdentityDeletedError,
    IdentityNotAllowedError,
    IdentityProvisioningPolicy,
    identity_key,
    normalize_identity_email,
)
from .memory import InMemoryStore
from .privacy_repository import default_privacy_settings


class IdentityRepository:
    def __init__(self, store: InMemoryStore) -> None:
        self._store = store

    def resolve_or_create_external_identity(
        self,
        principal: FirebasePrincipal,
        policy: IdentityProvisioningPolicy,
    ) -> UUID:
        key = identity_key(principal)
        if key in self._store.deleted_external_identity_keys:
            raise IdentityDeletedError("external identity was deleted")
        existing = self._store.external_identities.get(key)
        if existing is not None:
            updated = _updated_identity(existing, principal)
            self._store.external_identities[key] = updated
            _update_user_profile(self._store, updated.user_id, principal, policy)
            return updated.user_id
        if not policy.permits_first_login(principal):
            raise IdentityNotAllowedError("external identity is not allowed")
        _ensure_email_available(self._store, principal, policy)
        user_id = uuid4()
        self._store.privacy_settings[user_id] = default_privacy_settings(user_id)
        _update_user_profile(self._store, user_id, principal, policy)
        record = _new_identity(user_id, principal)
        self._store.external_identities[key] = record
        self._store.user_identity_keys.setdefault(user_id, set()).add(key)
        return user_id

    def tombstone_external_identities_for_user(
        self,
        user_id: UUID,
        tombstone_secret: str | None,
    ) -> int:
        keys = set(self._store.user_identity_keys.get(user_id, set()))
        count = 0
        for key in keys:
            if key in self._store.external_identities:
                del self._store.external_identities[key]
                self._store.deleted_external_identity_keys.add(key)
                count += 1
        self._store.user_identity_keys.pop(user_id, None)
        self._store.app_user_emails.pop(user_id, None)
        return count


def _new_identity(user_id: UUID, principal: FirebasePrincipal) -> ExternalIdentityRecord:
    now = datetime.now(UTC)
    return ExternalIdentityRecord(
        user_id=user_id,
        provider=principal.provider,
        issuer=principal.issuer,
        subject=principal.subject,
        firebase_tenant_id=principal.firebase_tenant_id,
        firebase_project_id=principal.firebase_project_id,
        sign_in_provider=principal.sign_in_provider,
        email=normalize_identity_email(principal.email),
        email_verified=principal.email_verified,
        display_name=principal.display_name,
        photo_url=principal.photo_url,
        auth_time=principal.auth_time,
        created_at=now,
        updated_at=now,
        last_seen_at=now,
    )


def _updated_identity(
    existing: ExternalIdentityRecord,
    principal: FirebasePrincipal,
) -> ExternalIdentityRecord:
    now = datetime.now(UTC)
    return ExternalIdentityRecord(
        user_id=existing.user_id,
        provider=existing.provider,
        issuer=existing.issuer,
        subject=existing.subject,
        firebase_tenant_id=existing.firebase_tenant_id,
        firebase_project_id=principal.firebase_project_id,
        sign_in_provider=principal.sign_in_provider,
        email=normalize_identity_email(principal.email),
        email_verified=principal.email_verified,
        display_name=principal.display_name,
        photo_url=principal.photo_url,
        auth_time=principal.auth_time,
        created_at=existing.created_at,
        updated_at=now,
        last_seen_at=now,
    )


def _update_user_profile(
    store: InMemoryStore,
    user_id: UUID,
    principal: FirebasePrincipal,
    policy: IdentityProvisioningPolicy,
) -> None:
    if principal.email_verified and principal.email:
        email = normalize_identity_email(principal.email)
        if email is None:
            return
        owner = _email_owner(store, email)
        if owner is not None and owner != user_id:
            raise IdentityConflictError("verified email belongs to another user")
        store.app_user_emails[user_id] = email


def _ensure_email_available(
    store: InMemoryStore,
    principal: FirebasePrincipal,
    policy: IdentityProvisioningPolicy,
) -> None:
    if not principal.email_verified or not principal.email:
        return
    email = normalize_identity_email(principal.email)
    if email is None:
        return
    if _email_owner(store, email) is not None:
        raise IdentityConflictError("verified email belongs to another user")


def _email_owner(store: InMemoryStore, email: str) -> UUID | None:
    for user_id, stored_email in store.app_user_emails.items():
        if stored_email == email:
            return user_id
    return None
