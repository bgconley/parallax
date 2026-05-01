# Firebase Auth Integration

Firebase Auth is the selected private-alpha identity provider for Parallax.
Firebase is identity-only: Parallax keeps its internal UUID `app_user.id`,
Postgres source of truth, privacy lifecycle, workflow model, sync model, release
gates, and repository-scoped authorization.

## Backend Boundary

iOS clients send Firebase ID tokens to the existing canonical bearer-token API:

```http
Authorization: Bearer <firebase_id_token>
```

Parallax verifies the token with the Firebase Admin SDK and resolves the decoded
Firebase account to an internal user through `external_identity`.

Durable key:

```text
provider = "firebase_auth"
issuer = https://securetoken.google.com/<project_id>
subject = Firebase UID
firebase_tenant_id = token firebase.tenant or ""
```

Firebase sign-in provider values such as `apple.com`, `google.com`, `password`,
and email link are stored only as metadata. They are not durable identity
providers for Parallax user resolution.

## Private Alpha Provisioning

First login does not imply open signup. For private alpha, configure one of:

- `PARALLAX_AUTH_ALLOWED_FIREBASE_UIDS_FILE`
- `PARALLAX_AUTH_ALLOWED_EMAILS_FILE`
- `PARALLAX_AUTH_ALLOWED_EMAIL_DOMAINS`
- `PARALLAX_AUTH_AUTO_PROVISION=true` only when open signup is intended

Verified-email conflicts return `409 auth_identity_conflict`. Parallax does not
auto-merge users by email, and unverified email never updates `app_user.email`.

## App Check

App Check is app attestation, not user authentication. It is controlled by
`PARALLAX_FIREBASE_APP_CHECK_MODE`:

- `off`: ignore the header.
- `monitor`: allow missing/invalid headers and keep sanitized observability.
- `enforce`: require valid `X-Firebase-AppCheck` on protected endpoints and
  reject tokens from unallowed app IDs.

`/v1/health`, `/v1/live`, and `/v1/ready` do not enforce App Check.

## Production Safety

Production/private-alpha runtime refuses:

- `PARALLAX_AUTH_MODE=dev_header`
- `FIREBASE_AUTH_EMULATOR_HOST`
- Firebase auth mode without `PARALLAX_FIREBASE_PROJECT_ID`
- Firebase auth mode without `PARALLAX_AUTH_IDENTITY_TOMBSTONE_SECRET`

The tombstone secret is used to prevent a deleted Parallax account from being
silently recreated by the same Firebase UID. Raw Firebase UIDs, ID tokens,
refresh tokens, App Check tokens, credential JSON, and raw email values must not
be written to release evidence or structured errors.
