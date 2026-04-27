from __future__ import annotations

import json
import sys
from http.client import HTTPConnection


def main() -> int:
    connection = HTTPConnection("127.0.0.1", 8000, timeout=5)
    try:
        connection.request("GET", "/v1/ready")
        response = connection.getresponse()
        payload = json.loads(response.read().decode("utf-8"))
    except (OSError, json.JSONDecodeError):
        return 1
    finally:
        connection.close()
    return 0 if response.status == 200 and payload.get("status") == "healthy" else 1


if __name__ == "__main__":
    sys.exit(main())
