from __future__ import annotations

import hashlib
import hmac
from typing import Any
from uuid import UUID

import psycopg
from psycopg.types.json import Jsonb

from ..domain.identity import (
    FirebasePrincipal,
    IdentityConflictError,
    IdentityDeletedError,
    IdentityNotAllowedError,
    IdentityProvisioningPolicy,
    identity_key,
    normalize_identity_email,
)


class PostgresExternalIdentityRepository:
    def __init__(self, connection: psycopg.Connection[Any]) -> None:
        self._connection = connection

    def resolve_or_create_external_identity(
        self,
        principal: FirebasePrincipal,
        policy: IdentityProvisioningPolicy,
    ) -> UUID:
        if principal.provider != "firebase_auth":
            raise IdentityNotAllowedError("unsupported identity provider")
        self._advisory_lock(principal)
        if self._is_tombstoned(principal, policy.tombstone_secret):
            raise IdentityDeletedError("external identity was deleted")
        existing_user_id = self._existing_identity_user_id(principal)
        if existing_user_id is not None:
            self._update_existing_identity(existing_user_id, principal, policy)
            return existing_user_id
        if not policy.permits_first_login(principal):
            raise IdentityNotAllowedError("external identity is not allowed")
        self._ensure_email_available(None, principal, policy)
        user_id = self._create_app_user(principal)
        self._insert_privacy_settings(user_id)
        self._insert_external_identity(user_id, principal)
        self._record_audit(user_id, principal)
        return user_id

    def tombstone_external_identities_for_user(
        self,
        user_id: UUID,
        tombstone_secret: str | None,
    ) -> int:
        if not tombstone_secret:
            raise ValueError("auth identity tombstone secret is required")
        with self._connection.cursor() as cursor:
            cursor.execute(
                """
                select provider, issuer, subject, firebase_tenant_id
                from external_identity
                where user_id = %s
                for update
                """,
                (user_id,),
            )
            rows = cursor.fetchall()
            for row in rows:
                subject_digest = _subject_hmac(
                    provider=str(row["provider"]),
                    issuer=str(row["issuer"]),
                    subject=str(row["subject"]),
                    firebase_tenant_id=str(row["firebase_tenant_id"]),
                    secret=tombstone_secret,
                )
                cursor.execute(
                    """
                    insert into deleted_external_identity_tombstone (
                      provider, issuer, subject_hmac, firebase_tenant_id, reason
                    )
                    values (%s, %s, %s, %s, %s)
                    on conflict (provider, issuer, subject_hmac, firebase_tenant_id)
                    do nothing
                    """,
                    (
                        row["provider"],
                        row["issuer"],
                        subject_digest,
                        row["firebase_tenant_id"],
                        "parallax_account_deleted",
                    ),
                )
            cursor.execute("delete from external_identity where user_id = %s", (user_id,))
        return len(rows)

    def _advisory_lock(self, principal: FirebasePrincipal) -> None:
        lock_id = _lock_id("\x1f".join(identity_key(principal)))
        with self._connection.cursor() as cursor:
            cursor.execute("select pg_advisory_xact_lock(%s)", (lock_id,))

    def _is_tombstoned(
        self,
        principal: FirebasePrincipal,
        tombstone_secret: str | None,
    ) -> bool:
        if not tombstone_secret:
            return False
        with self._connection.cursor() as cursor:
            cursor.execute(
                """
                select 1
                from deleted_external_identity_tombstone
                where provider = %s
                  and issuer = %s
                  and subject_hmac = %s
                  and firebase_tenant_id = %s
                """,
                (
                    principal.provider,
                    principal.issuer,
                    _subject_hmac(
                        provider=principal.provider,
                        issuer=principal.issuer,
                        subject=principal.subject,
                        firebase_tenant_id=principal.firebase_tenant_id,
                        secret=tombstone_secret,
                    ),
                    principal.firebase_tenant_id,
                ),
            )
            return cursor.fetchone() is not None

    def _existing_identity_user_id(self, principal: FirebasePrincipal) -> UUID | None:
        with self._connection.cursor() as cursor:
            cursor.execute(
                """
                select user_id
                from external_identity
                where provider = %s
                  and issuer = %s
                  and subject = %s
                  and firebase_tenant_id = %s
                for update
                """,
                (
                    principal.provider,
                    principal.issuer,
                    principal.subject,
                    principal.firebase_tenant_id,
                ),
            )
            row = cursor.fetchone()
        return UUID(str(row["user_id"])) if row is not None else None

    def _update_existing_identity(
        self,
        user_id: UUID,
        principal: FirebasePrincipal,
        policy: IdentityProvisioningPolicy,
    ) -> None:
        self._ensure_email_available(user_id, principal, policy)
        self._update_app_user_profile(user_id, principal, policy)
        with self._connection.cursor() as cursor:
            cursor.execute(
                """
                update external_identity
                set firebase_project_id = %s,
                    sign_in_provider = %s,
                    email = %s,
                    email_verified = %s,
                    display_name = %s,
                    photo_url = %s,
                    auth_time = %s,
                    last_seen_at = now(),
                    updated_at = now()
                where provider = %s
                  and issuer = %s
                  and subject = %s
                  and firebase_tenant_id = %s
                """,
                (
                    principal.firebase_project_id,
                    principal.sign_in_provider,
                    normalize_identity_email(principal.email),
                    principal.email_verified,
                    principal.display_name,
                    principal.photo_url,
                    principal.auth_time,
                    principal.provider,
                    principal.issuer,
                    principal.subject,
                    principal.firebase_tenant_id,
                ),
            )

    def _ensure_email_available(
        self,
        current_user_id: UUID | None,
        principal: FirebasePrincipal,
        policy: IdentityProvisioningPolicy,
    ) -> None:
        if not principal.email_verified or not principal.email:
            return
        email = normalize_identity_email(principal.email)
        with self._connection.cursor() as cursor:
            cursor.execute("select id from app_user where email = %s", (email,))
            row = cursor.fetchone()
        if row is None:
            return
        owner = UUID(str(row["id"]))
        if owner != current_user_id:
            raise IdentityConflictError("verified email belongs to another user")

    def _create_app_user(self, principal: FirebasePrincipal) -> UUID:
        email = normalize_identity_email(principal.email) if principal.email_verified else None
        with self._connection.cursor() as cursor:
            try:
                cursor.execute(
                    """
                    insert into app_user (email, display_name)
                    values (%s, %s)
                    returning id
                    """,
                    (email, principal.display_name),
                )
            except psycopg.errors.UniqueViolation as exc:
                raise IdentityConflictError("verified email belongs to another user") from exc
            row = cursor.fetchone()
        if row is None:
            raise RuntimeError("app_user insert returned no row")
        return UUID(str(row["id"]))

    def _insert_privacy_settings(self, user_id: UUID) -> None:
        with self._connection.cursor() as cursor:
            cursor.execute(
                "insert into privacy_settings (user_id) values (%s) on conflict do nothing",
                (user_id,),
            )

    def _insert_external_identity(self, user_id: UUID, principal: FirebasePrincipal) -> None:
        with self._connection.cursor() as cursor:
            cursor.execute(
                """
                insert into external_identity (
                  user_id, provider, issuer, subject, firebase_tenant_id,
                  firebase_project_id, sign_in_provider, email, email_verified,
                  display_name, photo_url, auth_time
                )
                values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    user_id,
                    principal.provider,
                    principal.issuer,
                    principal.subject,
                    principal.firebase_tenant_id,
                    principal.firebase_project_id,
                    principal.sign_in_provider,
                    normalize_identity_email(principal.email),
                    principal.email_verified,
                    principal.display_name,
                    principal.photo_url,
                    principal.auth_time,
                ),
            )

    def _update_app_user_profile(
        self,
        user_id: UUID,
        principal: FirebasePrincipal,
        policy: IdentityProvisioningPolicy,
    ) -> None:
        if not principal.email_verified or not principal.email:
            return
        email = normalize_identity_email(principal.email)
        if email is None:
            return
        with self._connection.cursor() as cursor:
            cursor.execute(
                """
                update app_user
                set email = coalesce(email, %s),
                    display_name = coalesce(display_name, %s),
                    updated_at = now()
                where id = %s
                  and (email is null or email = %s)
                """,
                (email, principal.display_name, user_id, email),
            )

    def _record_audit(self, user_id: UUID, principal: FirebasePrincipal) -> None:
        with self._connection.cursor() as cursor:
            cursor.execute(
                """
                insert into audit_log (user_id, actor_user_id, event_name, metadata)
                values (%s, %s, 'external_identity_created', %s)
                """,
                (
                    user_id,
                    user_id,
                    Jsonb(
                        {
                            "provider": principal.provider,
                            "firebase_project_id": principal.firebase_project_id,
                            "firebase_tenant_present": bool(principal.firebase_tenant_id),
                            "sign_in_provider": principal.sign_in_provider,
                        }
                    ),
                ),
            )


def _lock_id(value: str) -> int:
    digest = hashlib.sha256(value.encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big", signed=True)


def _subject_hmac(
    *,
    provider: str,
    issuer: str,
    subject: str,
    firebase_tenant_id: str,
    secret: str,
) -> bytes:
    message = "\x1f".join((provider, issuer, subject, firebase_tenant_id)).encode("utf-8")
    return hmac.new(secret.encode("utf-8"), message, hashlib.sha256).digest()
