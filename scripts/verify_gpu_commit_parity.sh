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

problems=()
if [[ "$actual_sha" != "$EXPECTED_SHA" ]]; then
  problems+=("GPU checkout mismatch: expected $EXPECTED_SHA, got $actual_sha")
fi

if [[ -n "$dirty" ]]; then
  problems+=("GPU checkout is dirty")
fi

if (( ${#problems[@]} )); then
  printf '%s' "${problems[0]}" >&2
  for problem in "${problems[@]:1}"; do
    printf '; %s' "$problem" >&2
  done
  printf '\n' >&2
  exit 1
fi

printf 'GPU checkout clean at %s\n' "$actual_sha"
