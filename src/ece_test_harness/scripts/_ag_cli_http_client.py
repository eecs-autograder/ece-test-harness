import json
import subprocess
from typing import Any, Protocol


class HttpClient(Protocol):
    def get(self, path: str) -> list[dict[str, Any]]: ...
    def patch(self, path: str, data: dict[str, Any]) -> None: ...


class AgCliHttpClient:
    def get(self, path: str) -> list[dict[str, Any]]:
        result = subprocess.run(
            ["ag", "http", "get", path],
            capture_output=True,
            text=True,
            check=True,
        )
        return json.loads(result.stdout)

    def patch(self, path: str, data: dict[str, Any]) -> None:
        subprocess.run(
            ["ag", "http", "patch", path, "--json_body", json.dumps(data), "--quiet"],
            check=True,
        )
