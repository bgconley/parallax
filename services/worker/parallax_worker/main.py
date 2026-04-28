from __future__ import annotations

import logging
import signal
import time
from typing import cast

from parallax_api.repositories.postgres_unit_of_work import PostgresUnitOfWorkFactory
from parallax_api.repositories.unit_of_work import UnitOfWorkFactory
from parallax_api.settings import get_settings

from .workflow_worker import WorkflowWorker


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    logging.info("Parallax worker bootstrap started")
    settings = get_settings()
    uow_factory = cast(UnitOfWorkFactory, PostgresUnitOfWorkFactory(settings.database_url))
    worker = WorkflowWorker(uow_factory)

    running = True

    def stop(_signum: int, _frame: object) -> None:
        nonlocal running
        running = False

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)

    while running:
        processed = worker.drain_once()
        time.sleep(0.2 if processed else 1.0)

    logging.info("Parallax worker bootstrap stopped")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
