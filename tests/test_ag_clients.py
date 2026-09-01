"""Tests for the course lookup shared by the ece-* scripts.

GET /api/courses/ (the list endpoint) is superuser-only on Autograder.io, so
both clients look courses up by name/semester/year instead. These tests pin
that path and the 404-vs-error distinction: a missing course is None, an auth
failure must still raise.
"""

from typing import Any

import pytest
import requests

import ece_test_harness.scripts._ag_cli_http_client as ag_cli_client
import ece_test_harness.scripts._requests_ag_client as requests_client

COURSE = {"pk": 1, "name": "EECS 553", "semester": "Fall", "year": 2026}
EXPECTED_PATH = "/api/course/EECS%20553/Fall/2026/"


class FakeResponse:
    def __init__(self, status_code: int, payload: Any = None) -> None:
        self.status_code = status_code
        self._payload = payload

    def json(self) -> Any:
        return self._payload

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise requests.HTTPError(f"{self.status_code} Client Error")


def test_course_path_url_encodes_name() -> None:
    assert ag_cli_client.course_path("EECS 553", "Fall", 2026) == EXPECTED_PATH


# ---------------------------------------------------------------------------
# requests client (ece-test-solutions)
# ---------------------------------------------------------------------------


class FakeSession:
    def __init__(self, response: FakeResponse) -> None:
        self._response = response
        self.requested: list[str] = []

    def get(self, url: str) -> FakeResponse:
        self.requested.append(url)
        return self._response


def test_requests_find_course_uses_by_name_endpoint() -> None:
    session = FakeSession(FakeResponse(200, COURSE))
    course = requests_client.find_course(
        session,  # type: ignore[arg-type]
        "https://autograder.io",
        "EECS 553",
        "Fall",
        2026,
    )
    assert course == COURSE
    assert session.requested == [f"https://autograder.io{EXPECTED_PATH}"]


def test_requests_find_course_returns_none_on_404() -> None:
    session = FakeSession(FakeResponse(404, {"detail": "Not found."}))
    assert (
        requests_client.find_course(
            session,  # type: ignore[arg-type]
            "https://autograder.io",
            "EECS 553",
            "Fall",
            2026,
        )
        is None
    )


def test_requests_find_course_raises_on_403() -> None:
    session = FakeSession(FakeResponse(403, {"detail": "Forbidden"}))
    with pytest.raises(requests.HTTPError):
        requests_client.find_course(
            session,  # type: ignore[arg-type]
            "https://autograder.io",
            "EECS 553",
            "Fall",
            2026,
        )


# ---------------------------------------------------------------------------
# ag CLI client (ece-save-projects, ece-publish-projects)
# ---------------------------------------------------------------------------


class FakeHTTPClient:
    def __init__(self, response: FakeResponse) -> None:
        self._response = response
        self.requested: list[str] = []

    def get(self, url: str) -> FakeResponse:
        self.requested.append(url)
        return self._response


@pytest.fixture()
def fake_ag_client(monkeypatch: pytest.MonkeyPatch) -> Any:
    def install(response: FakeResponse) -> FakeHTTPClient:
        client = FakeHTTPClient(response)
        monkeypatch.setattr(
            ag_cli_client.HTTPClient, "make_default", staticmethod(lambda *a, **kw: client)
        )
        return client

    return install


def test_ag_cli_find_course_uses_by_name_endpoint(fake_ag_client: Any) -> None:
    client = fake_ag_client(FakeResponse(200, COURSE))
    assert ag_cli_client.AgCliHttpClient().find_course("EECS 553", "Fall", 2026) == COURSE
    assert client.requested == [EXPECTED_PATH]


def test_ag_cli_find_course_returns_none_on_404(fake_ag_client: Any) -> None:
    fake_ag_client(FakeResponse(404, {"detail": "Not found."}))
    assert ag_cli_client.AgCliHttpClient().find_course("EECS 553", "Fall", 2026) is None


def test_ag_cli_find_course_raises_on_403(fake_ag_client: Any) -> None:
    fake_ag_client(FakeResponse(403, {"detail": "Forbidden"}))
    with pytest.raises(requests.HTTPError):
        ag_cli_client.AgCliHttpClient().find_course("EECS 553", "Fall", 2026)
