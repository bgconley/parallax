# Object Storage Plan

Parallax uses S3-compatible object storage for artifacts that should not be stored directly in Postgres.

## Buckets

| Bucket | Purpose | Encryption | Lifecycle |
|---|---|---|---|
| `parallax-raw` | optional audio, raw import artifacts | required outside local dev | governed by privacy settings |
| `parallax-exports` | user export bundles | required | expire staged exports after configured period |
| `parallax-artifacts` | model/eval artifacts, reports | recommended | retain by release/eval policy |
| `parallax-backups` | offsite/object backup target if used | required | backup retention policy |

## Access control

- API can create export jobs and signed export URLs.
- Worker can read/write raw/audio/export/model artifacts.
- Model services should not access object storage directly unless needed and authorized.
- Public anonymous access is disabled.

## Privacy

Raw audio is off by default. Raw exports should be encrypted and short-lived. Delete/redaction workflows must remove or tombstone object references and record backup-retention implications.
