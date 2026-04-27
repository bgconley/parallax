# GPU Node Storage

Parallax GPU-node storage starts from the canonical v1.3 ZFS artifacts:

- `parallax_v1_3_artifact_pack/infrastructure/zfs/zfs_dataset_plan.md`
- `parallax_v1_3_artifact_pack/infrastructure/zfs/create_parallax_datasets.sh`

Use the node's existing `tank` pool. Runtime datasets use the canonical `tank/parallax` namespace and mount under `/srv/parallax`. Repo and virtualenv state live outside `/srv/parallax` in existing shared developer areas:

- repo checkout: `/tank/repos/parallax`
- virtualenv root: `/tank/venvs/parallax`

After pushing changes from the Mac, pull them on the GPU node in `/tank/repos/parallax`.

## Dataset Layout

| Dataset | Mountpoint | Recordsize | Runtime owner | Mode |
|---|---|---:|---|---:|
| `tank/parallax` | `/srv/parallax` | `128K` | `root:root` | `0755` |
| `tank/parallax/postgres` | `/srv/parallax/postgres` | `8K` | `${PARALLAX_POSTGRES_UID:-999}:${PARALLAX_POSTGRES_GID:-999}` | `0700` |
| `tank/parallax/postgres_wal` | `/srv/parallax/postgres_wal` | `8K` | `${PARALLAX_POSTGRES_UID:-999}:${PARALLAX_POSTGRES_GID:-999}` | `0700` |
| `tank/parallax/objects` | `/srv/parallax/objects` | `1M` | `${PARALLAX_OBJECT_UID:-10001}:${PARALLAX_OBJECT_GROUP:-bgconley}` | `0770` |
| `tank/parallax/exports` | `/srv/parallax/exports` | `1M` | `${PARALLAX_APP_UID:-10001}:${PARALLAX_APP_GROUP:-bgconley}` | `0770` |
| `tank/parallax/models` | `/srv/parallax/models` | `1M` | `${PARALLAX_APP_UID:-10001}:${PARALLAX_APP_GROUP:-bgconley}` | `0770` |
| `tank/parallax/hf_cache` | `/srv/parallax/hf_cache` | `1M` | `${PARALLAX_APP_UID:-10001}:${PARALLAX_APP_GROUP:-bgconley}` | `0770` |
| `tank/parallax/logs` | `/srv/parallax/logs` | `128K` | `${PARALLAX_APP_UID:-10001}:${PARALLAX_APP_GROUP:-bgconley}` | `0770` |
| `tank/parallax/backups` | `/srv/parallax/backups` | `1M` | `root:bgconley` | `0750` |
| `tank/parallax/observability` | `/srv/parallax/observability` | `128K` | `bgconley:bgconley` | `0755` |
| `tank/parallax/config` | `/srv/parallax/config` | `128K` | `bgconley:bgconley` | `0755` |

## Ownership Policy

The runtime root stays root-owned. Service-writable trees are owned by the numeric container UID and the `bgconley` operator group so services can write while the operator can inspect and repair files from the host.

The default app UID is `10001`. Override `PARALLAX_APP_UID`, `PARALLAX_APP_GROUP`, `PARALLAX_POSTGRES_UID`, `PARALLAX_POSTGRES_GID`, `PARALLAX_OBJECT_UID`, or `PARALLAX_OBJECT_GROUP` before running the script if pinned container images use different IDs.

`/srv/parallax/objects` is object-store-owned. API and worker processes should access object bytes through S3-compatible credentials, not by writing directly into the MinIO data directory. `/srv/parallax/config` is for non-secret config only; secrets should come from environment files or a dedicated secrets mechanism.

Run `scripts/setup_gpu_node_storage.sh` on the GPU node with sudo to create the datasets and project directories.
