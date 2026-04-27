#!/usr/bin/env bash
set -euo pipefail

echo "Bootstrapping Parallax local development environment..."
if [ ! -f infrastructure/.env ]; then
  cp infrastructure/.env.example infrastructure/.env
  echo "Created infrastructure/.env from example."
fi

echo "Start services with:"
echo "  docker compose -f infrastructure/compose/docker-compose.parallax.prototype.yml --env-file infrastructure/.env up --build"
