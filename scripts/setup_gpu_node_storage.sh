#!/usr/bin/env bash
set -euo pipefail

POOL="${1:-tank}"
REMOTE_URL="${2:-https://github.com/bgconley/parallax.git}"
OWNER_USER="${3:-${SUDO_USER:-bgconley}}"
OWNER_GROUP="$(id -gn "${OWNER_USER}")"
APP_UID="${PARALLAX_APP_UID:-10001}"
APP_GROUP="${PARALLAX_APP_GROUP:-${OWNER_GROUP}}"
POSTGRES_UID="${PARALLAX_POSTGRES_UID:-999}"
POSTGRES_GID="${PARALLAX_POSTGRES_GID:-999}"
OBJECT_UID="${PARALLAX_OBJECT_UID:-${APP_UID}}"
OBJECT_GROUP="${PARALLAX_OBJECT_GROUP:-${APP_GROUP}}"

BASE_DATASET="${POOL}/parallax"
BASE_MOUNT="/srv/parallax"
REPO_PARENT="/${POOL}/repos"
VENV_PARENT="/${POOL}/venvs"
REPO_DIR="${REPO_PARENT}/parallax"
VENV_DIR="${VENV_PARENT}/parallax"

if [[ "${EUID}" -ne 0 ]]; then
  echo "Run this script with sudo so it can create ZFS datasets and set ownership." >&2
  exit 1
fi

if ! command -v zfs >/dev/null 2>&1 || ! command -v zpool >/dev/null 2>&1; then
  echo "zfs and zpool commands are required on the GPU node." >&2
  exit 1
fi

if ! zpool list "${POOL}" >/dev/null 2>&1; then
  echo "ZFS pool '${POOL}' was not found." >&2
  exit 1
fi

if [[ ! -d "${REPO_PARENT}" ]]; then
  echo "Expected repo parent '${REPO_PARENT}' does not exist." >&2
  exit 1
fi

if [[ ! -d "${VENV_PARENT}" ]]; then
  echo "Expected venv parent '${VENV_PARENT}' does not exist." >&2
  exit 1
fi

create_dataset() {
  local dataset="$1"
  local mountpoint="$2"
  local recordsize="$3"
  local compression="$4"
  local atime="$5"

  if ! zfs list "${dataset}" >/dev/null 2>&1; then
    zfs create \
      -o mountpoint="${mountpoint}" \
      -o recordsize="${recordsize}" \
      "${dataset}"
  else
    zfs set mountpoint="${mountpoint}" "${dataset}"
    zfs set recordsize="${recordsize}" "${dataset}"
  fi

  if [[ "${compression}" != "inherit" ]]; then
    zfs set compression="${compression}" "${dataset}"
  fi

  if [[ "${atime}" != "inherit" ]]; then
    zfs set atime="${atime}" "${dataset}"
  fi

  zfs mount "${dataset}" >/dev/null 2>&1 || true
}

set_root_dir() {
  local path="$1"
  install -d -m 0755 "${path}"
  chown root:root "${path}"
  chmod 0755 "${path}"
}

set_operator_dir() {
  local path="$1"
  install -d -m 0755 "${path}"
  chown -R "${OWNER_USER}:${OWNER_GROUP}" "${path}"
  chmod -R u+rwX,go+rX,go-w "${path}"
}

set_service_dir() {
  local path="$1"
  local uid="$2"
  local group="$3"
  install -d -m 0770 "${path}"
  chown -R "${uid}:${group}" "${path}"
  chmod -R u+rwX,g+rwX,o-rwx "${path}"
}

set_private_service_dir() {
  local path="$1"
  local uid="$2"
  local gid="$3"
  install -d -m 0700 "${path}"
  chown -R "${uid}:${gid}" "${path}"
  chmod -R u+rwX,go-rwx "${path}"
}

set_backup_dir() {
  local path="$1"
  install -d -m 0750 "${path}"
  chown -R "root:${OWNER_GROUP}" "${path}"
  chmod -R u+rwX,g+rX,g-w,o-rwx "${path}"
}

set_runtime_permissions() {
  set_root_dir "${BASE_MOUNT}"

  # Postgres container ownership must match the pinned database image.
  set_private_service_dir "${BASE_MOUNT}/postgres" "${POSTGRES_UID}" "${POSTGRES_GID}"
  set_private_service_dir "${BASE_MOUNT}/postgres_wal" "${POSTGRES_UID}" "${POSTGRES_GID}"

  # MinIO owns object bytes; API and workers should use S3 credentials.
  set_service_dir "${BASE_MOUNT}/objects" "${OBJECT_UID}" "${OBJECT_GROUP}"

  # Application/model services write these runtime trees.
  set_service_dir "${BASE_MOUNT}/exports" "${APP_UID}" "${APP_GROUP}"
  set_service_dir "${BASE_MOUNT}/models" "${APP_UID}" "${APP_GROUP}"
  set_service_dir "${BASE_MOUNT}/hf_cache" "${APP_UID}" "${APP_GROUP}"
  set_service_dir "${BASE_MOUNT}/logs" "${APP_UID}" "${APP_GROUP}"

  # Operator-managed, non-secret config and service-specific observability state.
  set_operator_dir "${BASE_MOUNT}/config"
  set_operator_dir "${BASE_MOUNT}/observability"

  # Local backup staging is intentionally not service-writable.
  set_backup_dir "${BASE_MOUNT}/backups"
}

# Canonical Parallax datasets from the v1.3 artifact pack, with explicit recordsize.
create_dataset "${BASE_DATASET}" "${BASE_MOUNT}" "128K" "inherit" "inherit"
create_dataset "${BASE_DATASET}/postgres" "${BASE_MOUNT}/postgres" "8K" "zstd" "off"
create_dataset "${BASE_DATASET}/postgres_wal" "${BASE_MOUNT}/postgres_wal" "8K" "inherit" "off"
create_dataset "${BASE_DATASET}/objects" "${BASE_MOUNT}/objects" "1M" "zstd" "off"
create_dataset "${BASE_DATASET}/exports" "${BASE_MOUNT}/exports" "1M" "zstd" "inherit"
create_dataset "${BASE_DATASET}/models" "${BASE_MOUNT}/models" "1M" "inherit" "inherit"
create_dataset "${BASE_DATASET}/hf_cache" "${BASE_MOUNT}/hf_cache" "1M" "inherit" "inherit"
create_dataset "${BASE_DATASET}/logs" "${BASE_MOUNT}/logs" "128K" "zstd" "inherit"
create_dataset "${BASE_DATASET}/backups" "${BASE_MOUNT}/backups" "1M" "zstd" "inherit"
create_dataset "${BASE_DATASET}/observability" "${BASE_MOUNT}/observability" "128K" "zstd" "inherit"
create_dataset "${BASE_DATASET}/config" "${BASE_MOUNT}/config" "128K" "inherit" "inherit"

set_runtime_permissions

install -d -o "${OWNER_USER}" -g "${OWNER_GROUP}" -m 0755 "${REPO_DIR}"
install -d -o "${OWNER_USER}" -g "${OWNER_GROUP}" -m 0755 "${VENV_DIR}"

if [[ -d "${REPO_DIR}/.git" ]]; then
  sudo -u "${OWNER_USER}" git -C "${REPO_DIR}" remote set-url origin "${REMOTE_URL}"
elif [[ -z "$(find "${REPO_DIR}" -mindepth 1 -maxdepth 1 -print -quit)" ]]; then
  sudo -u "${OWNER_USER}" git clone "${REMOTE_URL}" "${REPO_DIR}"
else
  echo "Repo directory exists and is not empty: ${REPO_DIR}" >&2
  echo "Leaving it untouched; initialize or clean it manually before cloning." >&2
fi

cat <<SUMMARY
Parallax GPU-node storage initialized.

ZFS namespace: ${BASE_DATASET}
Runtime mount root: ${BASE_MOUNT}
Repo checkout path: ${REPO_DIR}
Virtualenv root: ${VENV_DIR}

Future code updates after pushing from the Mac:
  cd ${REPO_DIR}
  git pull --ff-only origin master

Dataset recordsize summary:
  ${BASE_DATASET}: 128K
  ${BASE_DATASET}/postgres: 8K
  ${BASE_DATASET}/postgres_wal: 8K
  ${BASE_DATASET}/objects: 1M
  ${BASE_DATASET}/exports: 1M
  ${BASE_DATASET}/models: 1M
  ${BASE_DATASET}/hf_cache: 1M
  ${BASE_DATASET}/logs: 128K
  ${BASE_DATASET}/backups: 1M
  ${BASE_DATASET}/observability: 128K
  ${BASE_DATASET}/config: 128K

Runtime ownership summary:
  ${BASE_MOUNT}: root:root 0755
  ${BASE_MOUNT}/postgres: ${POSTGRES_UID}:${POSTGRES_GID} 0700
  ${BASE_MOUNT}/postgres_wal: ${POSTGRES_UID}:${POSTGRES_GID} 0700
  ${BASE_MOUNT}/objects: ${OBJECT_UID}:${OBJECT_GROUP} 0770
  ${BASE_MOUNT}/exports: ${APP_UID}:${APP_GROUP} 0770
  ${BASE_MOUNT}/models: ${APP_UID}:${APP_GROUP} 0770
  ${BASE_MOUNT}/hf_cache: ${APP_UID}:${APP_GROUP} 0770
  ${BASE_MOUNT}/logs: ${APP_UID}:${APP_GROUP} 0770
  ${BASE_MOUNT}/config: ${OWNER_USER}:${OWNER_GROUP} 0755
  ${BASE_MOUNT}/observability: ${OWNER_USER}:${OWNER_GROUP} 0755
  ${BASE_MOUNT}/backups: root:${OWNER_GROUP} 0750
SUMMARY
