.PHONY: validate test lint typecheck security migrate schema-smoke phase1-smoke dev-up dev-down dev-logs

PARALLAX_HOST_DATABASE_URL ?= postgresql://parallax:parallax_dev_password@127.0.0.1:15432/parallax
PARALLAX_API_URL ?= http://127.0.0.1:18000

validate:
	python3 parallax_v1_3_artifact_pack/scripts/validate_pack.py --skip-zip-check
	PYTHONPATH=packages/contracts:packages/db:services/api uv run python -m parallax_contracts.validation parallax_v1_3_artifact_pack

test:
	uv run pytest

lint:
	uv run ruff check .

typecheck:
	uv run mypy services packages scripts

security:
	uv run bandit -q -r services/api/parallax_api services/worker packages scripts
	uv run semgrep --error --config=auto services/api/parallax_api services/worker packages scripts

migrate:
	uv run python scripts/apply_migrations.py --database-url "$(PARALLAX_HOST_DATABASE_URL)" --migrations-dir migrations

schema-smoke:
	uv run python scripts/apply_migrations.py --database-url "$(PARALLAX_HOST_DATABASE_URL)" --migrations-dir migrations --smoke

phase1-smoke:
	uv run python scripts/phase1_smoke.py --api-url "$(PARALLAX_API_URL)" --database-url "$(PARALLAX_HOST_DATABASE_URL)"

dev-up:
	docker compose -f docker-compose.yml --env-file .env up -d --build

dev-down:
	docker compose -f docker-compose.yml --env-file .env down

dev-logs:
	docker compose -f docker-compose.yml --env-file .env logs -f
