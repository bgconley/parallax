#!/usr/bin/env bash
set -euo pipefail

# Permission-only Parallax GPU-node runtime setup.
#
# This script does not create ZFS datasets, clone the repo, or create venvs.
# Run it after the canonical datasets are mounted under /srv/parallax.
#
# Defaults can be overridden with environment variables:
#   PARALLAX_RUNTIME_ROOT=/srv/parallax
#   PARALLAX_OWNER_USER=bgconley
#   PARALLAX_OWNER_GROUP=bgconley
#   PARALLAX_APP_UID=10001
#   PARALLAX_APP_GROUP=bgconley
#   PARALLAX_POSTGRES_UID=999
#   PARALLAX_POSTGRES_GID=999
#   PARALLAX_OBJECT_UID=10001
#   PARALLAX_OBJECT_GROUP=bgconley

BASE_MOUNT="${PARALLAX_RUNTIME_ROOT:-/srv/parallax}"
OWNER_USER="${PARALLAX_OWNER_USER:-${SUDO_USER:-bgconley}}"
OWNER_GROUP="${PARALLAX_OWNER_GROUP:-$(id -gn "${OWNER_USER}")}"
APP_UID="${PARALLAX_APP_UID:-10001}"
APP_GROUP="${PARALLAX_APP_GROUP:-${OWNER_GROUP}}"
POSTGRES_UID="${PARALLAX_POSTGRES_UID:-999}"
POSTGRES_GID="${PARALLAX_POSTGRES_GID:-999}"
OBJECT_UID="${PARALLAX_OBJECT_UID:-${APP_UID}}"
OBJECT_GROUP="${PARALLAX_OBJECT_GROUP:-${APP_GROUP}}"

EXPECTED_DIRS=(
  "${BASE_MOUNT}"
  "${BASE_MOUNT}/postgres"
  "${BASE_MOUNT}/postgres_wal"
  "${BASE_MOUNT}/objects"
  "${BASE_MOUNT}/exports"
  "${BASE_MOUNT}/models"
  "${BASE_MOUNT}/hf_cache"
  "${BASE_MOUNT}/logs"
  "${BASE_MOUNT}/backups"
  "${BASE_MOUNT}/observability"
  "${BASE_MOUNT}/config"
)

require_root() {
  if [[ "${EUID}" -ne 0 ]]; then
    echo "error: run this script with sudo or as root" >&2
    exit 1
  fi
}

require_expected_dirs() {
  local missing=0

  for path in "${EXPECTED_DIRS[@]}"; do
    if [[ ! -d "${path}" ]]; then
      echo "missing expected runtime directory: ${path}" >&2
      missing=1
    fi
  done

  if [[ "${missing}" -ne 0 ]]; then
    echo "error: expected Parallax runtime directories are missing; create and mount datasets first" >&2
    exit 1
  fi
}

set_root_dir() {
  local path="$1"
  chown root:root "${path}"
  chmod 0755 "${path}"
}

set_operator_dir() {
  local path="$1"
  chown -R "${OWNER_USER}:${OWNER_GROUP}" "${path}"
  chmod -R u+rwX,go+rX,go-w "${path}"
}

set_service_dir() {
  local path="$1"
  local uid="$2"
  local group="$3"
  chown -R "${uid}:${group}" "${path}"
  chmod -R u+rwX,g+rwX,o-rwx "${path}"
}

set_private_service_dir() {
  local path="$1"
  local uid="$2"
  local gid="$3"
  chown -R "${uid}:${gid}" "${path}"
  chmod -R u+rwX,go-rwx "${path}"
}

set_backup_dir() {
  local path="$1"
  chown -R "root:${OWNER_GROUP}" "${path}"
  chmod -R u+rwX,g+rX,g-w,o-rwx "${path}"
}

print_summary() {
  echo
  echo "Parallax runtime permissions:"
  stat -c '%a %u:%g %U:%G %n' "${EXPECTED_DIRS[@]}"
}

require_root
require_expected_dirs

set_root_dir "${BASE_MOUNT}"

set_private_service_dir "${BASE_MOUNT}/postgres" "${POSTGRES_UID}" "${POSTGRES_GID}"
set_private_service_dir "${BASE_MOUNT}/postgres_wal" "${POSTGRES_UID}" "${POSTGRES_GID}"

set_service_dir "${BASE_MOUNT}/objects" "${OBJECT_UID}" "${OBJECT_GROUP}"
set_service_dir "${BASE_MOUNT}/exports" "${APP_UID}" "${APP_GROUP}"
set_service_dir "${BASE_MOUNT}/models" "${APP_UID}" "${APP_GROUP}"
set_service_dir "${BASE_MOUNT}/hf_cache" "${APP_UID}" "${APP_GROUP}"
set_service_dir "${BASE_MOUNT}/logs" "${APP_UID}" "${APP_GROUP}"

set_operator_dir "${BASE_MOUNT}/config"
set_operator_dir "${BASE_MOUNT}/observability"
set_backup_dir "${BASE_MOUNT}/backups"

print_summary
