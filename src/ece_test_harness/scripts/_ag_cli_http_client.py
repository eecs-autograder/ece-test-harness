import json
import subprocess
from typing import Any, Protocol
from urllib.parse import quote

from autograder_cli.http_client import HTTPClient


class HttpClient(Protocol):
    def get(self, path: str) -> list[dict[str, Any]]: ...
    def find_course(self, name: str, semester: str, year: int) -> dict[str, Any] | None: ...


class PatchingHttpClient(HttpClient, Protocol):
    def patch(self, path: str, data: dict[str, Any]) -> None: ...


def course_path(name: str, semester: str, year: int) -> str:
    # Note the singular "course": this is the by-name lookup, not the list endpoint.
    return f"/api/course/{quote(name)}/{quote(semester)}/{year}/"


class AgCliHttpClient:
    def get(self, path: str) -> list[dict[str, Any]]:
        result = subprocess.run(
            ["ag", "http", "get", path],
            capture_output=True,
            text=True,
            check=True,
        )
        return json.loads(result.stdout)

    def find_course(self, name: str, semester: str, year: int) -> dict[str, Any] | None:
        # GET /api/courses/ (the list endpoint) is restricted to Autograder.io
        # superusers, so look the course up by name/semester/year instead --
        # that endpoint is open to any authenticated user. This goes through the
        # autograder_cli HTTP client rather than the `ag` CLI because `ag http`
        # exits 1 for every error status, which would make a missing course
        # indistinguishable from an auth failure.
        r = HTTPClient.make_default().get(course_path(name, semester, year))
        if r.status_code == 404:
            return None
        r.raise_for_status()
        return r.json()

    def patch(self, path: str, data: dict[str, Any]) -> None:
        subprocess.run(
            ["ag", "http", "patch", path, "--json_body", json.dumps(data), "--quiet"],
            check=True,
        )
