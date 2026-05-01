# Firebase Auth Integration Plan

## Decision

Use Firebase Auth as the Parallax private-alpha identity provider, behind the
existing canonical bearer-token API contract. Firebase Auth is identity only.
Parallax keeps its internal UUID user model, Postgres source of truth, privacy
lifecycle, workflow model, offline sync model, authorization rules, and release
gates.

The integration target is:

1. The iOS app signs in to Firebase Auth using Apple, Google, email link, or
   email/password if explicitly enabled.
2. The iOS app sends only a Firebase ID token to Parallax:
   `Authorization: Bearer <firebase_id_token>`.
3. Parallax verifies the Firebase ID token server-side.
4. Parallax resolves the durable Firebase account identity to internal
   `app_user.id`.
5. All repositories and services continue to authorize and query by internal
   UUID `user_id`.
6. Firebase App Check is added as an API abuse-control layer, first in monitor
   mode, then enforce mode once iOS token delivery is proven.

The durable Parallax external identity key for Firebase Auth is:

```text
provider = "firebase_auth"
issuer = decoded_token["iss"]
subject = decoded_token["uid"] or decoded_token["sub"]
firebase_tenant_id = decoded_token.get("firebase", {}).get("tenant") or ""
```

Apple, Google, password, and email link are Firebase sign-in methods. They are
metadata only and must never become the durable Parallax external identity
provider key. This prevents a linked Firebase account from becoming multiple
Parallax users when the same Firebase UID signs in through different providers.

## Source Findings

Canonical Parallax artifacts require bearer JWT auth and authenticated user
scope, but intentionally leave the exact alpha auth provider open.

- `contracts/openapi/parallax_api_v1_3.yaml` declares global bearer JWT auth.
- `docs/10_security_privacy_nfr.md` requires `user_id` to be inferred from auth
  context, every query to be user-scoped, cross-user tests, and no secrets in
  repo.
- `docs/23_agentic_implementation_guardrails.md` allows a private-alpha auth
  stub only for early implementation, not as the release posture.
- `docs/00_pack_summary.md` and `docs/15_risk_register_open_questions.md`
  explicitly leave exact alpha auth provider selection open.

Firebase official-doc findings from Firecrawl research:

- Firebase clients can send the signed-in user's Firebase ID token to a custom
  backend over HTTPS; the backend verifies the token and uses the decoded
  `uid`.
- Firebase Admin SDK verification validates token format, expiry, and
  signature, and returns decoded claims. Revocation is not checked unless
  explicitly requested.
- Firebase ID-token manual verification requires RS256, Firebase project ID as
  `aud`, issuer `https://securetoken.google.com/<projectId>`, and non-empty
  `sub` equal to the Firebase UID.
- Firebase ID tokens are short-lived, roughly one hour. Refresh tokens continue
  until user deletion, disablement, or major account changes.
- Revocation checking requires a Firebase Auth backend network round trip, so
  it must be configurable and explicitly tested when enabled.
- Firebase supports linking multiple auth providers to one Firebase user
  account. The same Firebase user remains identifiable by one Firebase user ID
  regardless of sign-in provider.
- Firebase user records track linked sign-in providers. Those provider IDs are
  useful for audit/debug metadata, not Parallax account identity resolution.
- Firebase iOS supports Apple, Google, email link, and email/password auth.
- Sign in with Apple requires a cryptographically secure nonce flow, Apple
  Developer setup, Firebase Apple provider setup, return URL registration, and
  private email relay configuration if Firebase sends emails to Apple private
  relay addresses.
- Firebase email-link auth should use Firebase Hosting based links and
  associated domains. The old Dynamic Links based email-link flow is deprecated,
  and Firebase Dynamic Links shut down on August 25, 2025.
- Firebase App Check can protect custom backends by sending
  `X-Firebase-AppCheck`; backends verify the token. App Attest is the preferred
  iOS provider, with DeviceCheck fallback if older iOS support is needed.
- App Check custom-backend verification checks token validity, project
  audience, issuer, expiry, and app ID. Replay protection is documented around
  Node SDK consume semantics, so Python replay-consume behavior is not a
  release requirement now.
- The Firebase Auth emulator accepts unsigned emulator ID tokens when
  `FIREBASE_AUTH_EMULATOR_HOST` is set. That environment variable must be
  forbidden in production/private-alpha runtime.

Firecrawl artifacts saved under:

- `.firecrawl/firebase-auth-research/`
- `.firecrawl/firebase.google.com-docs-auth-admin-verify-id-tokens.md`
- `.firecrawl/firebase.google.com-docs-auth-admin-manage-sessions.md`
- `.firecrawl/firebase.google.com-docs-auth-ios-account-linking.md`
- `.firecrawl/firebase.google.com-docs-auth-users.md`
- `.firecrawl/firebase.google.com-docs-auth-ios-apple.md`
- `.firecrawl/firebase.google.com-docs-auth-ios-google-signin.md`
- `.firecrawl/firebase.google.com-docs-auth-ios-email-link-auth.md`
- `.firecrawl/firebase.google.com-docs-auth-ios-password-auth.md`
- `.firecrawl/firebase.google.com-docs-app-check-*.md`
- `.firecrawl/firebase.google.com-docs-emulator-suite-connect_auth.md`
- `.firecrawl/firebase.google.com-docs-reference-rest-auth.md`

## Current Parallax Seams

### API Auth Dependency

Current file:

- `services/api/parallax_api/auth.py`

Current behavior:

- `dev_header` accepts `X-Parallax-User-Id` in development/test only.
- `external_bearer` validates HS256 or JWKS-backed JWTs.
- `_user_id_from_claims()` currently requires the configured claim to already
  be an internal UUID.

Required change:

- Split token verification from identity resolution.
- Add a Firebase ID-token verifier.
- Resolve Firebase UID to internal `app_user.id` through the repository/UoW
  layer.
- Preserve `AuthContext.user_id: UUID` so route/service boundaries do not
  churn.
- Ignore or reject `X-Parallax-User-Id` when `PARALLAX_AUTH_MODE=firebase`.
- Keep Firebase claims as authentication input only. Application authorization
  uses Parallax `app_user`, roles, entitlements, privacy state, release gates,
  and repository user scoping.

Recommended shape:

- `services/api/parallax_api/auth.py`: FastAPI dependency, auth error mapping,
  request-state attachment, and no Firebase SDK details.
- `services/api/parallax_api/auth_verifiers.py`: small protocol and concrete
  verifiers for dev, generic JWT, and Firebase.
- `services/api/parallax_api/firebase_auth.py`: Firebase Admin SDK integration,
  lazy named app initialization, and no import-time I/O.
- `services/api/parallax_api/app_check.py`: optional App Check verification
  dependency/helper.

### Settings

Current file:

- `services/api/parallax_api/settings.py`

Required additions:

```python
auth_mode: Literal["dev_header", "external_bearer", "firebase"]

firebase_project_id: str | None
firebase_project_number: str | None
firebase_credentials_file: str | None
firebase_credentials_json: str | None
firebase_check_revoked: bool = False

firebase_app_check_mode: Literal["off", "monitor", "enforce"] = "off"
firebase_app_check_project_number: str | None = None
firebase_app_check_allowed_app_ids: list[str] = []

auth_auto_provision: bool = False
auth_invite_required: bool = True
auth_allowed_email_domains: list[str] = []
auth_allowed_emails_file: str | None = None
auth_allowed_firebase_uids_file: str | None = None
auth_email_conflict_policy: Literal["reject"] = "reject"
```

Startup guards:

- `PARALLAX_AUTH_MODE=firebase` requires `PARALLAX_FIREBASE_PROJECT_ID`.
- Production/private-alpha refuses `PARALLAX_AUTH_MODE=dev_header`.
- Production/private-alpha refuses `FIREBASE_AUTH_EMULATOR_HOST`.
- Production/private-alpha refuses Firebase mode when credentials or
  application default credentials are unavailable.
- Production/private-alpha must not log service-account JSON, credential file
  contents, raw bearer tokens, raw App Check tokens, or Firebase UID values.

Deployment defaults:

- local `.env.example`: `PARALLAX_AUTH_MODE=dev_header`
- production/private-alpha: `PARALLAX_AUTH_MODE=firebase`
- production/private-alpha: credentials via secret manager, mounted read-only
  file, or application default credentials, not committed env values.

### External Identity and Provisioning

Current files:

- `migrations/0002_identity_privacy_audit.sql`
- `services/api/parallax_api/repositories/postgres_identity.py`
- `services/api/parallax_api/repositories/unit_of_work.py`
- `services/api/parallax_api/repositories/postgres_unit_of_work.py`
- `services/api/parallax_api/repositories/in_memory_unit_of_work.py`
- `services/api/parallax_api/repositories/memory.py`

Current behavior:

- `app_user.id` is the canonical internal UUID.
- `ensure_app_user(cursor, user_id)` auto-creates an internal user by UUID.
- No external identity table exists.

Required migration:

```sql
CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS citext;

CREATE TABLE external_identity (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),

  user_id uuid NOT NULL
    REFERENCES app_user(id)
    ON DELETE CASCADE,

  -- For Firebase Auth this is always "firebase_auth".
  provider text NOT NULL,

  -- For Firebase ID tokens:
  -- https://securetoken.google.com/<projectId>
  issuer text NOT NULL,

  -- Firebase UID. Do not store Apple or Google provider subject here.
  subject text NOT NULL,

  -- Empty string when Firebase multi-tenancy is not in use.
  firebase_tenant_id text NOT NULL DEFAULT '',

  firebase_project_id text NOT NULL,

  -- Latest Firebase sign-in method, for audit/debug only.
  -- Examples: apple.com, google.com, password.
  sign_in_provider text,

  email citext,
  email_verified boolean,
  display_name text,
  photo_url text,

  auth_time timestamptz,
  last_seen_at timestamptz NOT NULL DEFAULT now(),

  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),

  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,

  CHECK (provider <> ''),
  CHECK (issuer <> ''),
  CHECK (subject <> ''),
  CHECK (firebase_project_id <> ''),

  UNIQUE(provider, issuer, subject, firebase_tenant_id)
);

CREATE INDEX idx_external_identity_user_id
  ON external_identity(user_id);
```

Add an `updated_at` trigger or require every update path to set
`updated_at = now()`. Do not add a redundant non-unique index on the same
`(provider, issuer, subject, firebase_tenant_id)` shape unless query evidence
shows a different index shape is needed.

If Parallax does not support Firebase multi-tenancy at implementation time,
explicitly reject tokens containing a tenant claim instead of silently ignoring
it. If tenancy is supported, keep `firebase_tenant_id` in the durable key.

Optional private-alpha invite table:

```sql
CREATE TABLE alpha_invite (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  email citext UNIQUE,
  firebase_uid text UNIQUE,
  status text NOT NULL DEFAULT 'active',
  invited_by uuid REFERENCES app_user(id),
  expires_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  accepted_at timestamptz
);
```

Required repository protocol:

- Add `IdentityRepositoryProtocol` to `unit_of_work.py`.
- Add `resolve_or_create_external_identity(principal) -> UUID`.
- Implement Postgres and in-memory versions.
- Use repository from auth dependency via `request.app.state.uow_factory`.

Race-safe resolve-or-create algorithm:

```text
resolve_or_create_external_identity(principal):

1. Assert principal.provider == "firebase_auth".
2. Begin transaction.
3. Acquire a transaction-scoped advisory lock keyed by
   provider + issuer + subject + firebase_tenant_id, or use equivalent
   SERIALIZABLE/upsert conflict handling.
4. SELECT external_identity FOR UPDATE by durable key.
5. If found:
   - update last_seen_at, sign_in_provider, safe profile fields, auth_time,
     and updated_at;
   - return user_id.
6. If not found:
   - apply private-alpha provisioning gate;
   - apply verified-email conflict policy;
   - create app_user;
   - create privacy_settings;
   - insert external_identity;
   - write sanitized privacy/audit evidence;
   - return new app_user.id.
7. Commit.
```

Private-alpha provisioning policy:

```text
Existing external_identity:
  allow.

No existing external_identity and auth_auto_provision=false:
  require active invite by verified email or explicit Firebase UID.

No verified email:
  require explicit Firebase UID invite.

Verified email belongs to another app_user:
  return 409 auth_identity_conflict.

Unverified email:
  never update app_user.email.
```

Do not auto-merge accounts by email. Apple private relay email is a
contact/profile attribute, not a durable identity key.

### Firebase Principal

Use a narrow application principal object:

```python
FirebasePrincipal(
    provider="firebase_auth",
    issuer=decoded["iss"],
    subject=decoded["uid"],  # Firebase UID; must equal token sub.
    firebase_project_id=decoded["aud"],
    firebase_tenant_id=decoded.get("firebase", {}).get("tenant") or "",
    sign_in_provider=decoded.get("firebase", {}).get("sign_in_provider"),
    email=decoded.get("email"),
    email_verified=bool(decoded.get("email_verified")),
    display_name=decoded.get("name"),
    picture=decoded.get("picture"),
    auth_time=decoded.get("auth_time"),
)
```

The verifier must defensively post-check:

- `iss == f"https://securetoken.google.com/{firebase_project_id}"`
- `aud == firebase_project_id`
- `sub` is present and equals `uid`
- `uid` is present
- tenant claim is either supported and included in the durable key, or rejected

### FastAPI and Firebase Admin SDK

The Firebase Admin Python SDK verification calls are synchronous. In async
FastAPI dependencies, do not block the event loop while verifying tokens,
especially when `firebase_check_revoked=true` can add a network round trip.
Either:

- call sync verification through `anyio.to_thread.run_sync(...)`; or
- keep the auth dependency synchronous so FastAPI executes it in the threadpool.

Conceptual verifier shape:

```python
class FirebaseAuthVerifier:
    def __init__(self, settings: Settings):
        self.settings = settings
        self._init_lock = threading.Lock()
        self._app: firebase_admin.App | None = None

    def _get_app(self) -> firebase_admin.App:
        # Lazy, named app initialization.
        # No import-time I/O.
        # No credential JSON logging.
        ...

    def verify_sync(self, token: str) -> FirebasePrincipal:
        decoded = firebase_admin.auth.verify_id_token(
            token,
            app=self._get_app(),
            check_revoked=self.settings.firebase_check_revoked,
        )

        expected_issuer = (
            f"https://securetoken.google.com/"
            f"{self.settings.firebase_project_id}"
        )
        if decoded.get("iss") != expected_issuer:
            raise AuthInvalid("wrong_issuer")
        if decoded.get("aud") != self.settings.firebase_project_id:
            raise AuthInvalid("wrong_audience")
        if not decoded.get("sub") or decoded.get("sub") != decoded.get("uid"):
            raise AuthInvalid("bad_subject")

        return FirebasePrincipal.from_decoded(decoded)
```

### Auth Error Surface

Return structured Parallax API errors with sanitized messages. Never include
raw ID tokens, App Check tokens, service-account paths, credential JSON, email,
or Firebase UID in response bodies or logs.

Recommended mapping:

```text
Missing Authorization header:
  401 auth_missing
  WWW-Authenticate: Bearer

Wrong auth scheme:
  401 auth_invalid_scheme
  WWW-Authenticate: Bearer

Malformed bearer token:
  401 auth_invalid

Expired Firebase ID token:
  401 auth_token_expired

Revoked Firebase ID token:
  401 auth_token_revoked

Disabled Firebase user:
  403 auth_user_disabled

Wrong project, audience, issuer, subject, or tenant:
  401 auth_invalid

Valid Firebase identity but not invited or allowed:
  403 auth_not_allowed

Verified-email conflict:
  409 auth_identity_conflict

Missing App Check token in enforce mode:
  403 app_check_missing

Invalid App Check token in enforce mode:
  403 app_check_invalid

Valid App Check token from unallowed app ID:
  403 app_check_app_not_allowed
```

Use a keyed hash or fingerprint of Firebase UID only if correlation is needed
in logs or release evidence.

### App Check

App Check is app attestation, not user authentication. It must not replace
Firebase Auth or Parallax authorization.

Settings:

```python
firebase_project_number: str | None
firebase_app_check_project_number: str | None = None
firebase_app_check_allowed_app_ids: list[str] = []
firebase_app_check_mode: Literal["off", "monitor", "enforce"] = "off"
```

Expected header:

```http
X-Firebase-AppCheck: <app_check_token>
```

Protected endpoint behavior:

```text
off:
  ignore header and continue.

monitor:
  missing token -> allow request, emit sanitized metric/audit signal.
  invalid token -> allow request, emit sanitized metric/audit signal.
  valid token -> allow request, attach app_id to request state.

enforce:
  missing token -> 403 app_check_missing.
  invalid token -> 403 app_check_invalid.
  valid wrong app_id -> 403 app_check_app_not_allowed.
  valid allowed app_id -> continue.
```

Do not enforce App Check on `/v1/health`, `/v1/live`, or `/v1/ready`. Document
whether `/docs`, `/openapi.json`, and metrics endpoints are exposed or protected
in private alpha before enabling enforce mode.

If relying on `firebase_admin.app_check.verify_token()`, still keep project
number and allowed app IDs in settings for auditability and future manual
verification. Do not make replay-consume App Check semantics a Python release
requirement until the supported SDK path is clear.

### Account Deletion and Privacy Lifecycle

Firebase must not replace the Parallax privacy lifecycle. Parallax delete,
redact, export, workflow evidence, sync invalidation, and derived artifact
handling remain the source of truth.

Account deletion must not allow immediate silent recreation of a deleted
Parallax user through the same still-valid Firebase account.

Preferred private-alpha policy:

```text
On Parallax account deletion:
  1. delete/anonymize Parallax user data according to privacy lifecycle;
  2. delete or disable the corresponding Firebase Auth user through Admin SDK;
  3. revoke Firebase refresh tokens;
  4. remove external_identity through cascade;
  5. write privacy audit evidence without raw token values.
```

If Parallax cannot delete/disable Firebase users because Firebase is managed
outside the backend, add an HMAC tombstone:

```sql
CREATE TABLE deleted_external_identity_tombstone (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  provider text NOT NULL,
  issuer text NOT NULL,
  subject_hmac bytea NOT NULL,
  firebase_tenant_id text NOT NULL DEFAULT '',
  deleted_at timestamptz NOT NULL DEFAULT now(),
  reason text,
  UNIQUE(provider, issuer, subject_hmac, firebase_tenant_id)
);
```

Reject auto-provisioning if a deleted identity tombstone matches. Do not store
raw deleted Firebase UIDs in tombstones.

For iOS/App Store compliance, the app must let users initiate account deletion.
Apple-token revocation may require the user to sign in again before revocation
or deletion can complete.

### API Contract

The canonical OpenAPI already declares bearer JWT auth. Firebase ID tokens fit
that contract as bearer JWTs.

Required OpenAPI/docs changes:

- No endpoint path changes.
- Add implementation docs stating Firebase Auth is the selected private-alpha
  provider.
- If App Check becomes mandatory, update OpenAPI with a documented
  `X-Firebase-AppCheck` header/security extension before enforcing it broadly.
  Until then, keep App Check in monitor mode or implementation docs only to
  avoid hidden contract requirements.

### Release Gate

Current files:

- `scripts/release_auth_provider_probe.py`
- `docs/release/release_gate_status.md`
- `docs/release/release_gate_evidence.json`
- `Makefile`

Required changes:

- Extend probe semantics to Firebase:
  - require a fresh Firebase ID token;
  - confirm `/v1/activities` succeeds using only `Authorization: Bearer`;
  - confirm `X-Parallax-User-Id` is rejected/ignored in Firebase mode;
  - confirm dev-header mode is not accepted in production/private-alpha config;
  - optionally require `PARALLAX_RELEASE_APP_CHECK_TOKEN` when App Check is in
    enforce mode.
- Generate release auth tokens deterministically immediately before running the
  gate. Do not rely on a manually pasted long-lived value.
- Keep `release-gate` evidence writing only after probe success.
- Store only sanitized facts in evidence:
  - project ID;
  - issuer;
  - hashed Firebase UID;
  - internal `app_user.id`;
  - auth mode;
  - App Check mode;
  - commit SHA;
  - timestamp;
  - probe result.
- Never store ID tokens, refresh tokens, App Check tokens, service-account JSON,
  raw Firebase UID, or raw email in evidence.

Token acquisition options:

```text
Option A - dedicated email/password release user:
  1. Create dedicated Firebase test user:
     parallax-release-probe@<domain>
  2. Store password in CI secret manager.
  3. Release script calls:
     accounts:signInWithPassword?key=<Firebase Web API key>
  4. Extract idToken.
  5. Run release gate with the fresh idToken.

Option B - custom-token exchange:
  1. Release script uses service account to mint Firebase custom token for a
     dedicated release UID.
  2. Script exchanges custom token through:
     accounts:signInWithCustomToken?key=<Firebase Web API key>
  3. Extract idToken.
  4. Run release gate with the fresh idToken.
```

For App Check enforce mode, a headless backend job cannot generally mint a real
production iOS App Check token. Use one of these policies:

```text
Private-alpha production proof:
  run App Check enforce proof from a physical device or simulator flow and pass
  a fresh App Check token to the release probe.

Non-production CI proof:
  use Firebase App Check debug provider only in a test Firebase project, never
  in production.
```

### iOS Client Boundary

There is not yet an iOS app implementation in this repo, but the backend plan
must leave a clean seam for it.

iOS responsibilities:

- Configure Firebase project and `GoogleService-Info.plist`.
- Add Firebase Auth SDK through Swift Package Manager.
- Implement Apple sign-in first for iOS-first distribution.
- Generate a cryptographically secure nonce for Apple sign-in, send the SHA-256
  hash in the Apple request, and use the raw nonce when creating the Firebase
  credential.
- Preserve Apple display/profile fields on first sign-in because Apple only
  shares some fields once.
- Treat Apple private relay email as contact metadata only. Configure Apple
  private email relay if Firebase sends email to anonymized relay addresses.
- Implement Google sign-in if enabled.
- Prefer email-link auth over email/password for lower-friction private alpha.
- Use Firebase Hosting based email-link auth and associated domains; do not use
  Dynamic Links based email-link flows.
- If email/password is enabled, require Firebase password policy and email
  enumeration protection.
- After Firebase sign-in, call `getIDToken()` and attach:
  - `Authorization: Bearer <firebase_id_token>`
- Do not send Apple identity tokens, Google ID tokens, OAuth access tokens, or
  Firebase refresh tokens to Parallax.
- Initialize App Check before using other Firebase SDKs.
- Use App Attest on iOS 14+ with DeviceCheck fallback only if supporting older
  OS versions.
- When App Check is enabled, call `AppCheck.appCheck().token(...)` and attach:
  - `X-Firebase-AppCheck: <app_check_token>`

Client retry behavior:

```text
Normal request:
  use current Firebase ID token.

401 auth_token_expired:
  call getIDTokenForcingRefresh(true);
  retry once.

401 auth_token_revoked or 403 auth_user_disabled:
  sign out or require reauthentication.

403 auth_not_allowed:
  show private-alpha access message; do not retry token refresh.

409 auth_identity_conflict:
  show account-link/support flow.
```

### Dependencies

Current file:

- `pyproject.toml`

Required addition:

- `firebase-admin`

Keep existing `PyJWT` because the generic bearer path and tests still use it.
Do not add Firebase client SDKs to backend Python; those belong to iOS later.

### Docker / Deployment

Current files:

- `services/api/Dockerfile`
- `docker-compose.yml`
- `.env.example`
- `infra/compose/*`

Required changes:

- Ensure service account file can be mounted read-only or injected by secret
  manager.
- Document:
  - `PARALLAX_AUTH_MODE=firebase`
  - `PARALLAX_FIREBASE_PROJECT_ID`
  - `PARALLAX_FIREBASE_PROJECT_NUMBER`
  - `PARALLAX_FIREBASE_CREDENTIALS_FILE`
  - `PARALLAX_FIREBASE_CHECK_REVOKED`
  - `PARALLAX_FIREBASE_APP_CHECK_MODE`
  - `PARALLAX_FIREBASE_APP_CHECK_PROJECT_NUMBER`
  - `PARALLAX_FIREBASE_APP_CHECK_ALLOWED_APP_IDS`
  - private-alpha invite/allowlist settings
- Do not bake credentials into images.
- Do not expose Firebase emulator env vars in production Compose or systemd
  environments.

## Implementation Phases

### Phase A - Auth Provider Decision Record

Deliverables:

- Add ADR or architecture doc selecting Firebase Auth for private alpha.
- Clarify Firebase is identity only; Parallax remains data/workflow source of
  truth.
- Document supported sign-in methods:
  - Apple: required for iOS-first.
  - Email link: preferred email auth.
  - Google: optional but supported.
  - Email/password: optional fallback only with password policy and enumeration
    protection.
- Document that Firebase sign-in providers are metadata, not Parallax durable
  identity providers.

Acceptance:

- Docs cite canonical Parallax auth requirements and Firebase provider choice.
- No code behavior changes.

### Phase B - External Identity Mapping and Private-Alpha Provisioning

Deliverables:

- Migration for `external_identity`.
- Optional `alpha_invite` migration or file-backed allowlist support.
- Optional deleted-identity tombstone migration if Firebase delete/disable is
  not guaranteed.
- Repository protocol and Postgres/in-memory implementations.
- Race-safe `resolve_or_create_external_identity` with advisory lock or
  equivalent conflict-safe transaction behavior.
- Verified-email conflict behavior, returning `409 auth_identity_conflict` in
  private alpha.
- Provisioning gate for invites/allowlists.
- Unit tests for:
  - first login with valid invite creates one app user and identity;
  - first login without invite returns 403 in private-alpha mode;
  - existing identity works even if invite expired;
  - repeated login returns same internal user;
  - Firebase UID with Apple then linked Google still maps to same Parallax user;
  - same Firebase UID with different `sign_in_provider` does not create a new
    Parallax user;
  - same Firebase UID in a different Firebase project maps to a different
    identity;
  - verified email conflict returns 409;
  - unverified email never updates `app_user.email`;
  - two simultaneous first logins for the same Firebase UID create one
    `app_user`;
  - no orphan `app_user` remains after conflict paths.

Acceptance:

- Existing route/service code still sees internal UUID `user_id`.
- Existing dev-header tests still pass.
- Migration smoke passes.
- No account is auto-created in private-alpha mode without invite/allowlist
  authorization.

### Phase C - Firebase ID Token Verification

Deliverables:

- Add `firebase-admin` dependency.
- Add Firebase verifier module with lazy initialization.
- Add `firebase` auth mode.
- Resolve Firebase principal through identity repository.
- Use threadpool handling for synchronous Firebase Admin SDK calls when invoked
  from async FastAPI dependencies.
- Preserve generic `external_bearer` tests.
- Add Firebase tests with mocked Admin SDK:
  - valid ID token maps to internal UUID;
  - missing token;
  - wrong auth scheme;
  - invalid token;
  - expired token;
  - revoked token when `firebase_check_revoked=true`;
  - disabled user;
  - malformed claims;
  - wrong project/audience/issuer;
  - empty or mismatched `sub`/`uid`;
  - tenant claim handled or explicitly rejected;
  - production refuses `auth_mode=dev_header`;
  - production refuses `FIREBASE_AUTH_EMULATOR_HOST`;
  - Firebase mode ignores/rejects `X-Parallax-User-Id`;
  - no raw token, email, UID, service-account path, or credential JSON appears
    in errors/logs/evidence.

Acceptance:

- `PARALLAX_AUTH_MODE=firebase` works without client-supplied user UUID.
- Normal Parallax endpoints remain user-scoped.
- `make validate lint typecheck test security` passes.

### Phase D - App Check Monitor and Enforce Modes

Deliverables:

- Add App Check verifier.
- Add App Check settings for project number and allowed app IDs.
- In monitor mode:
  - missing/invalid App Check is recorded as sanitized metric/audit signal, but
    request is allowed.
- In enforce mode:
  - protected endpoints reject missing/invalid App Check token;
  - protected endpoints reject valid tokens from unallowed app IDs.
- Do not enforce on `/v1/health`, `/v1/ready`, or `/v1/live`.
- Document `/docs`, `/openapi.json`, and metrics exposure/protection behavior.

Acceptance:

- Tests cover off/monitor/enforce modes.
- Tests cover allowed and unallowed app IDs.
- No raw App Check token appears in logs/errors.
- OpenAPI/docs explicitly describe any enforced header before release.

### Phase E - Deterministic Release Probe and GPU Proof

Deliverables:

- Update `release_auth_provider_probe.py` for Firebase auth mode.
- Add deterministic release-token acquisition:
  - dedicated email/password test user; or
  - service-account custom-token exchange.
- Add optional App Check probe input.
- Update release docs with exact private-alpha token proof procedure.
- Run on GPU node with actual Firebase project config and real ID token.

Acceptance:

- `make release-gate` succeeds only when:
  - GPU checkout parity passes;
  - Firebase ID-token auth succeeds;
  - dev-header is not accepted in production/private-alpha mode;
  - Firebase emulator env is absent;
  - App Check proof is satisfied when enforce mode is configured;
  - privacy lifecycle, SLO, log privacy scan, and backup/restore pass;
  - evidence JSON is commit-matched, non-empty, and sanitized.

### Phase F - iOS Client Integration

Deliverables:

- Firebase project setup for iOS bundle ID.
- Apple sign-in configured with nonce handling.
- Email link configured with Firebase Hosting, universal links, and associated
  domains.
- Google sign-in configured if enabled.
- API client attaches Firebase ID token, not Apple/Google provider tokens.
- API client attaches App Check token when enabled.
- Client token refresh and error-handling policy implemented.

Acceptance:

- Physical device or simulator auth smoke:
  - Apple sign-in creates/loads Parallax user;
  - email link sign-in creates/loads Parallax user;
  - linked Apple/Google sign-in resolves the same Parallax user;
  - token refresh path works;
  - sign-out clears local credentials;
  - backend rejects stale/missing bearer token;
  - private-alpha rejection and identity-conflict responses produce the expected
    user-facing flows.

### Phase G - Privacy and Account Lifecycle Closure

Deliverables:

- Account deletion policy implemented:
  - delete/disable Firebase user and revoke refresh tokens; or
  - create HMAC tombstone if Firebase account deletion is not owned by backend.
- `external_identity` cascade or tombstone behavior proven.
- Re-login after Parallax account deletion tested.
- Privacy audit evidence remains sanitized.

Acceptance:

- Deleted/disabled Firebase user cannot access Parallax.
- Deleted Parallax user cannot silently recreate an account through the same
  Firebase UID unless an explicit re-enrollment policy allows it.
- Privacy export/delete/redact gates still pass after Firebase identity mapping
  is added.

## Test Matrix

Identity mapping:

- Firebase UID signs in with Apple, then linked Google; same Parallax user.
- Same Firebase UID with different `sign_in_provider` does not create a new
  user.
- Same Firebase UID in different Firebase project maps to different identity.
- Token with wrong `aud` or `iss` is rejected.
- Token with tenant claim is handled or explicitly rejected.
- Empty or mismatched `sub`/`uid` is rejected.

Provisioning:

- First login with valid invite creates user.
- First login without invite is 403 in private-alpha mode.
- Existing identity works even if invite expired.
- Verified email conflict returns 409.
- Unverified email never updates `app_user.email`.

Concurrency:

- Two simultaneous first logins for same Firebase UID produce one app user.
- No orphan app user remains after conflict path.

Privacy:

- Deleted/disabled Firebase user cannot access.
- Deleted Parallax user cannot silently recreate account through same Firebase
  UID unless policy explicitly allows re-enrollment.
- `external_identity` cascades or tombstones correctly.

App Check:

- off mode ignores header.
- monitor mode allows missing/invalid token and emits sanitized metric/audit.
- enforce mode rejects missing token.
- enforce mode rejects invalid token.
- enforce mode rejects valid token from unallowed app ID.
- health/live/ready bypass App Check.

Environment safety:

- production refuses `auth_mode=dev_header`.
- production refuses `FIREBASE_AUTH_EMULATOR_HOST`.
- firebase mode ignores/rejects `X-Parallax-User-Id`.
- no raw bearer token or App Check token appears in logs/errors/evidence.

iOS/API behavior:

- expired ID token refresh retry works once.
- revoked token signs user out or forces reauth.
- Apple private relay email is not used as durable identity.
- email-link flow uses Firebase Hosting associated domain, not Dynamic Links.

## Risks and Controls

- Risk: Firebase `uid` is treated as Parallax `user_id`.
  - Control: use `external_identity` mapping; Parallax `user_id` remains UUID.

- Risk: sign-in provider creates duplicate Parallax users.
  - Control: durable provider is always `firebase_auth`; Apple/Google/password
    are metadata only.

- Risk: accidental open signup during private alpha.
  - Control: invite/allowlist gate defaults to required; no first-login
    provisioning without explicit authorization.

- Risk: email identity merge bug.
  - Control: never key identity by email; return 409 on verified-email conflict
    in private alpha.

- Risk: first-login race creates duplicate or orphan users.
  - Control: advisory lock or equivalent conflict-safe transaction around
    `resolve_or_create_external_identity`.

- Risk: App Check is mistaken for user auth.
  - Control: App Check is app attestation only; Firebase Auth ID token remains
    user identity.

- Risk: revocation checks add latency.
  - Control: make `firebase_check_revoked` configurable; require it only when
    private-alpha policy demands immediate revocation detection.

- Risk: service account secrets leak.
  - Control: secret manager/mounted file only; no env dumps; no raw credential
    logging; security scan should reject credential patterns.

- Risk: emulator tokens are accepted in production.
  - Control: startup guard rejects `FIREBASE_AUTH_EMULATOR_HOST` in
    production/private-alpha.

- Risk: Firebase becomes source of truth for user data.
  - Control: store product/user/privacy state in Parallax Postgres only.

- Risk: deleted user silently re-provisions.
  - Control: delete/disable Firebase user and revoke tokens, or use HMAC
    deleted-identity tombstone.

## Verification Commands

Local:

```bash
make validate
make lint
make typecheck
make test
make security
python3 -m compileall -q services packages scripts
docker compose -f docker-compose.yml --env-file .env.example config
```

GPU node after implementation:

```bash
scripts/verify_gpu_commit_parity.sh
ssh -i /Users/brennanconley/vibecode/infx/ubuntu24_ed25519 bgconley@10.25.0.50 \
  'cd /tank/repos/parallax && PATH=/home/bgconley/.local/bin:$PATH UV_PROJECT_ENVIRONMENT=/tank/venvs/parallax make validate lint typecheck test security'
ssh -i /Users/brennanconley/vibecode/infx/ubuntu24_ed25519 bgconley@10.25.0.50 \
  'cd /tank/repos/parallax && PATH=/home/bgconley/.local/bin:$PATH UV_PROJECT_ENVIRONMENT=/tank/venvs/parallax make schema-smoke phase1-smoke phase2-smoke phase3-smoke phase4-smoke phase5-smoke'
```

Release proof with real Firebase project/token:

```bash
PARALLAX_RELEASE_BEARER_TOKEN="$(scripts/mint_release_firebase_id_token.sh)" \
make release-gate
make release-status
```

If App Check is enforced:

```bash
PARALLAX_RELEASE_BEARER_TOKEN="$(scripts/mint_release_firebase_id_token.sh)" \
PARALLAX_RELEASE_APP_CHECK_TOKEN='<fresh-firebase-app-check-token>' \
make release-gate
```

The App Check token for production/private-alpha enforce mode must come from a
real iOS App Check flow. The debug provider is allowed only in non-production
Firebase projects.
