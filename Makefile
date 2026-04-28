.PHONY: validate test lint typecheck security release-status release-gate migrate schema-smoke phase1-smoke phase2-smoke phase3-smoke phase4-smoke dev-up dev-down dev-logs

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
	uv run semgrep --error --no-git-ignore --config=auto services/api/parallax_api services/worker packages scripts

release-status:
	uv run python scripts/release_gate_status.py --summary

release-gate:
	uv run python scripts/release_gate_status.py

migrate:
	uv run python scripts/apply_migrations.py --database-url "$(PARALLAX_HOST_DATABASE_URL)" --migrations-dir migrations

schema-smoke:
	uv run python scripts/apply_migrations.py --database-url "$(PARALLAX_HOST_DATABASE_URL)" --migrations-dir migrations --smoke

phase1-smoke:
	uv run python scripts/phase1_smoke.py --api-url "$(PARALLAX_API_URL)" --database-url "$(PARALLAX_HOST_DATABASE_URL)"

phase2-smoke:
	uv run python scripts/phase2_smoke.py --api-url "$(PARALLAX_API_URL)" --database-url "$(PARALLAX_HOST_DATABASE_URL)"

phase3-smoke:
	uv run python scripts/phase3_smoke.py --api-url "$(PARALLAX_API_URL)" --database-url "$(PARALLAX_HOST_DATABASE_URL)"

phase4-smoke:
	uv run python scripts/phase4_smoke.py --api-url "$(PARALLAX_API_URL)" --database-url "$(PARALLAX_HOST_DATABASE_URL)"

dev-up:
	docker compose -f docker-compose.yml --env-file .env up -d --build

dev-down:
	docker compose -f docker-compose.yml --env-file .env down

dev-logs:
	docker compose -f docker-compose.yml --env-file .env logs -f
