#!/usr/bin/env bash
set -euo pipefail

GPU_HOST="${PARALLAX_GPU_HOST:-bgconley@10.25.0.50}"
GPU_KEY="${PARALLAX_GPU_KEY:-/Users/brennanconley/vibecode/infx/ubuntu24_ed25519}"
GPU_REPO="${PARALLAX_GPU_REPO:-/tank/repos/parallax}"
EXPECTED_SHA="${1:-$(git rev-parse HEAD)}"

remote_sha="$(
  ssh -i "$GPU_KEY" "$GPU_HOST" "git -C '$GPU_REPO' rev-parse HEAD && git -C '$GPU_REPO' status --short"
)"
actual_sha="$(printf '%s\n' "$remote_sha" | sed -n '1p')"
dirty="$(printf '%s\n' "$remote_sha" | sed '1d')"

if [[ "$actual_sha" != "$EXPECTED_SHA" ]]; then
  printf 'GPU checkout mismatch: expected %s, got %s\n' "$EXPECTED_SHA" "$actual_sha" >&2
  exit 1
fi

if [[ -n "$dirty" ]]; then
  printf 'GPU checkout is dirty:\n%s\n' "$dirty" >&2
  exit 1
fi

printf 'GPU checkout clean at %s\n' "$actual_sha"
