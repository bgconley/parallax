from __future__ import annotations

import logging
import signal
import time


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    logging.info("Parallax worker bootstrap started")

    running = True

    def stop(_signum: int, _frame: object) -> None:
        nonlocal running
        running = False

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)

    while running:
        time.sleep(1)

    logging.info("Parallax worker bootstrap stopped")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
