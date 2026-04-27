from __future__ import annotations

import json
import sys
from urllib.error import URLError
from urllib.request import urlopen


def main() -> int:
    try:
        with urlopen("http://127.0.0.1:8000/v1/health", timeout=5) as response:
            payload = json.load(response)
    except (OSError, URLError, json.JSONDecodeError):
        return 1
    return 0 if response.status == 200 and payload.get("status") == "healthy" else 1


if __name__ == "__main__":
    sys.exit(main())
