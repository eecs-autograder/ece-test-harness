from pathlib import Path
from typing import Any, cast

import requests

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
    courses: list[dict[str, Any]] = get(session, base, "/api/courses/")
    return next(
        (
            c
            for c in courses
            if c["name"] == name and c.get("semester") == semester and c.get("year") == year
        ),
        None,
    )


def get_list(session: requests.Session, base: str, path: str) -> list[dict[str, Any]]:
    return cast(list[dict[str, Any]], get(session, base, path))


def get_dict(session: requests.Session, base: str, path: str) -> dict[str, Any]:
    return cast(dict[str, Any], get(session, base, path))
