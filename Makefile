.PHONY: validate test lint dev-up dev-down

validate:
	python3 parallax_v1_3_artifact_pack/scripts/validate_pack.py --skip-zip-check
	PYTHONPATH=packages/contracts:packages/db:services/api uv run python -m parallax_contracts.validation parallax_v1_3_artifact_pack

test:
	uv run pytest

lint:
	uv run ruff check .

dev-up:
	docker compose -f docker-compose.yml --env-file .env up --build

dev-down:
	docker compose -f docker-compose.yml --env-file .env down
