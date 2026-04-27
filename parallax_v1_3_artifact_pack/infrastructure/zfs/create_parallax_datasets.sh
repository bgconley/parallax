#!/usr/bin/env bash
set -euo pipefail

POOL="${1:-pool}"
BASE="${POOL}/parallax"

create_dataset() {
  local name="$1"
  local mountpoint="$2"
  if ! zfs list "${name}" >/dev/null 2>&1; then
    zfs create -o mountpoint="${mountpoint}" "${name}"
  fi
}

create_dataset "${BASE}" "/srv/parallax"
create_dataset "${BASE}/postgres" "/srv/parallax/postgres"
create_dataset "${BASE}/postgres_wal" "/srv/parallax/postgres_wal"
create_dataset "${BASE}/objects" "/srv/parallax/objects"
create_dataset "${BASE}/exports" "/srv/parallax/exports"
create_dataset "${BASE}/models" "/srv/parallax/models"
create_dataset "${BASE}/hf_cache" "/srv/parallax/hf_cache"
create_dataset "${BASE}/logs" "/srv/parallax/logs"
create_dataset "${BASE}/backups" "/srv/parallax/backups"
create_dataset "${BASE}/observability" "/srv/parallax/observability"
create_dataset "${BASE}/config" "/srv/parallax/config"

zfs set compression=zstd "${BASE}/postgres" "${BASE}/objects" "${BASE}/exports" "${BASE}/logs" "${BASE}/backups" "${BASE}/observability" || true
zfs set atime=off "${BASE}/postgres" "${BASE}/postgres_wal" "${BASE}/objects" || true

echo "Parallax ZFS datasets created under ${BASE}."
