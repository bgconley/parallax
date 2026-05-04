.PHONY: validate test lint typecheck security release-status release-gate release-slo privacy-log-scan privacy-lifecycle-smoke backup-restore-drill migrate schema-smoke phase1-smoke phase2-smoke phase3-smoke phase4-smoke phase5-smoke phase6-smoke phase7-smoke phase8-smoke phase9-smoke phase10-smoke dev-up dev-down dev-logs

PARALLAX_HOST_DATABASE_URL ?= postgresql://parallax:parallax_dev_password@127.0.0.1:15432/parallax
PARALLAX_API_URL ?= http://127.0.0.1:18000
RELEASE_PROOF_DIR ?= .release-gate-proofs

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
	uv run python scripts/clear_release_gate_proofs.py --proof-dir "$(RELEASE_PROOF_DIR)"
	uv run python scripts/record_release_gate.py --gate deployed_commit_parity --proof-dir "$(RELEASE_PROOF_DIR)" -- scripts/verify_gpu_commit_parity.sh
	uv run python scripts/record_release_gate.py --gate production_auth_provider --proof-dir "$(RELEASE_PROOF_DIR)" -- uv run python scripts/release_auth_provider_probe.py --api-url "$(PARALLAX_API_URL)" --bearer-token "$$PARALLAX_RELEASE_BEARER_TOKEN" --app-check-token "$$PARALLAX_RELEASE_APP_CHECK_TOKEN"
	uv run python scripts/record_release_gate.py --gate privacy_export_delete_redact --proof-dir "$(RELEASE_PROOF_DIR)" -- uv run python scripts/privacy_lifecycle_smoke.py --api-url "$(PARALLAX_API_URL)" --database-url "$(PARALLAX_HOST_DATABASE_URL)" --bearer-token "$$PARALLAX_RELEASE_BEARER_TOKEN" --app-check-token "$$PARALLAX_RELEASE_APP_CHECK_TOKEN"
	uv run python scripts/record_release_gate.py --gate performance_slo --proof-dir "$(RELEASE_PROOF_DIR)" -- uv run python scripts/release_slo_smoke.py --api-url "$(PARALLAX_API_URL)" --bearer-token "$$PARALLAX_RELEASE_BEARER_TOKEN" --app-check-token "$$PARALLAX_RELEASE_APP_CHECK_TOKEN"
	uv run python scripts/record_release_gate.py --gate production_log_privacy_scan --proof-dir "$(RELEASE_PROOF_DIR)" -- uv run python scripts/release_log_privacy_scan.py --api-url "$(PARALLAX_API_URL)" --bearer-token "$$PARALLAX_RELEASE_BEARER_TOKEN" --app-check-token "$$PARALLAX_RELEASE_APP_CHECK_TOKEN"
	uv run python scripts/record_release_gate.py --gate backup_restore --proof-dir "$(RELEASE_PROOF_DIR)" -- uv run python scripts/release_backup_restore_drill.py --database-url "$(PARALLAX_HOST_DATABASE_URL)" --object-root "$${PARALLAX_OBJECTS_DIR:-/srv/parallax/objects}" --restore-root "$${PARALLAX_RESTORE_DRILL_ROOT:-/srv/parallax/backups/release-restore-drill}"
	uv run python scripts/write_release_gate_evidence.py --proof-dir "$(RELEASE_PROOF_DIR)"

release-slo:
	uv run python scripts/release_slo_smoke.py --api-url "$(PARALLAX_API_URL)"

privacy-log-scan:
	uv run python scripts/release_log_privacy_scan.py --api-url "$(PARALLAX_API_URL)"

privacy-lifecycle-smoke:
	uv run python scripts/privacy_lifecycle_smoke.py --api-url "$(PARALLAX_API_URL)" --database-url "$(PARALLAX_HOST_DATABASE_URL)"

backup-restore-drill:
	uv run python scripts/release_backup_restore_drill.py --database-url "$(PARALLAX_HOST_DATABASE_URL)" --object-root "$${PARALLAX_OBJECTS_DIR:-/srv/parallax/objects}" --restore-root "$${PARALLAX_RESTORE_DRILL_ROOT:-/srv/parallax/exports/release-restore-drill}"

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

phase5-smoke:
	uv run python scripts/phase5_smoke.py --api-url "$(PARALLAX_API_URL)" --database-url "$(PARALLAX_HOST_DATABASE_URL)"

phase6-smoke:
	uv run python scripts/phase6_smoke.py --api-url "$(PARALLAX_API_URL)" --database-url "$(PARALLAX_HOST_DATABASE_URL)"

phase7-smoke:
	uv run python scripts/phase7_smoke.py --api-url "$(PARALLAX_API_URL)" --database-url "$(PARALLAX_HOST_DATABASE_URL)"

phase8-smoke:
	python3 scripts/phase8_ui_contract.py
	swift test --package-path apps/ios
	xcodebuild -project apps/ios/ParallaxNative.xcodeproj -scheme ParallaxNative -destination 'generic/platform=iOS Simulator' -derivedDataPath apps/ios/DerivedData build

phase9-smoke:
	uv run python scripts/phase9_smoke.py

phase10-smoke:
	python3 scripts/phase10_temporal_home_contract.py
	swift test --package-path apps/ios
	xcodebuild -project apps/ios/ParallaxNative.xcodeproj -scheme ParallaxNative -destination 'generic/platform=iOS Simulator' -derivedDataPath apps/ios/DerivedData build

dev-up:
	docker compose -f docker-compose.yml --env-file .env up -d --build

dev-down:
	docker compose -f docker-compose.yml --env-file .env down

dev-logs:
	docker compose -f docker-compose.yml --env-file .env logs -f
