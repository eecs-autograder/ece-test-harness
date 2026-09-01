from pathlib import Path
from typing import Any, cast

import requests

from ._ag_cli_http_client import course_path

DEFAULT_BASE_URL = "https://autograder.io"
DEFAULT_TOKEN_FILE = "~/.agtoken"


def make_session(token_file: str, base_url: str) -> tuple[requests.Session, str]:
    token = Path(token_file).expanduser().read_text().strip()
    session = requests.Session()
    session.headers["Authorization"] = f"Token {token}"
    return session, base_url.rstrip("/")


def get(session: requests.Session, base: str, path: str) -> Any:
    r = session.get(f"{base}{path}")
    r.raise_for_status()
    return r.json()


def find_course(
    session: requests.Session, base: str, name: str, semester: str, year: int
) -> dict[str, Any] | None:
    # GET /api/courses/ (the list endpoint) is restricted to Autograder.io
    # superusers, so look the course up by name/semester/year instead --
    # that endpoint is open to any authenticated user.
    r = session.get(f"{base}{course_path(name, semester, year)}")
    if r.status_code == 404:
        return None
    r.raise_for_status()
    return cast(dict[str, Any], r.json())


def get_list(session: requests.Session, base: str, path: str) -> list[dict[str, Any]]:
    return cast(list[dict[str, Any]], get(session, base, path))


def get_dict(session: requests.Session, base: str, path: str) -> dict[str, Any]:
    return cast(dict[str, Any], get(session, base, path))
