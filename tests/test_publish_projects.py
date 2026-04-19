import os
import shutil
from collections.abc import Sequence
from datetime import datetime
from pathlib import Path
from typing import Any

import pytest

import ece_test_harness.scripts.publish_projects as publish_projects

TESTDATA = Path(__file__).parent / "testdata" / "test_course_publish"

# America/Detroit is UTC-5 in January (EST).
# hw1 end_date = 2026-01-20 23:59 local = 2026-01-21T04:59:00Z
HW1_CLOSING_TIME_UTC = "2026-01-21T04:59:00Z"
HW1_CLOSING_TIME_WRONG = "2026-01-22T04:59:00Z"

NOW_BEFORE_HW1_START = datetime(2026, 1, 10, 0, 0)
NOW_AFTER_HW1_START = datetime(2026, 1, 15, 0, 0)
NOW_AFTER_HW1_END = datetime(2026, 1, 25, 0, 0)


class MockHttpClient:
    def __init__(
        self,
        courses: Sequence[dict[str, Any]] = (),
        projects: Sequence[dict[str, Any]] = (),
    ) -> None:
        self._courses = list(courses)
        self._projects = list(projects)
        self.patched: dict[str, dict[str, Any]] = {}

    def get(self, path: str) -> list[dict[str, Any]]:
        if path == "/api/courses/":
            return self._courses
        return self._projects

    def patch(self, path: str, data: dict[str, Any]) -> None:
        self.patched[path] = data


@pytest.fixture()
def course_dir(tmp_path: Path) -> Any:
    dest = tmp_path / "course"
    shutil.copytree(TESTDATA, dest)
    original = Path.cwd()
    os.chdir(dest)
    yield dest
    os.chdir(original)


def make_course() -> dict[str, Any]:
    return {"pk": 1, "name": "EECS 551", "semester": "Fall", "year": 2026}


def make_project(
    name: str,
    pk: int,
    visible: bool = False,
    hide_grades: bool = True,
    closing_time: str = HW1_CLOSING_TIME_UTC,
) -> dict[str, Any]:
    return {
        "pk": pk,
        "name": name,
        "visible_to_students": visible,
        "hide_ultimate_submission_fdbk": hide_grades,
        "closing_time": closing_time,
    }


def run_main(
    course_dir: Path,
    *,
    schedule: str = "schedule.txt",
    http_client: MockHttpClient,
    dry_run: bool = False,
    now: datetime = NOW_AFTER_HW1_END,
) -> None:
    publish_projects.main(
        Path(schedule),
        http_client=http_client,
        dry_run=dry_run,
        now=now,
    )


# ---------------------------------------------------------------------------
# Visibility publishing
# ---------------------------------------------------------------------------


def test_sets_visible_after_start_date(course_dir: Path, capsys: Any) -> None:
    http = MockHttpClient(
        courses=[make_course()],
        projects=[make_project("hw1.py", 101)],
    )
    run_main(course_dir, http_client=http, now=NOW_AFTER_HW1_START)
    assert http.patched.get("/api/projects/101/") == {"visible_to_students": True}


def test_does_not_set_visible_before_start_date(course_dir: Path) -> None:
    http = MockHttpClient(
        courses=[make_course()],
        projects=[make_project("hw1.py", 101)],
    )
    run_main(course_dir, http_client=http, now=NOW_BEFORE_HW1_START)
    assert "/api/projects/101/" not in http.patched


def test_already_visible_no_patch(course_dir: Path, capsys: Any) -> None:
    http = MockHttpClient(
        courses=[make_course()],
        projects=[make_project("hw1.py", 101, visible=True)],
    )
    run_main(course_dir, http_client=http, now=NOW_AFTER_HW1_START)
    assert "/api/projects/101/" not in http.patched
    assert "ok" in capsys.readouterr().out


def test_hides_project_before_start_date(course_dir: Path) -> None:
    http = MockHttpClient(
        courses=[make_course()],
        projects=[make_project("hw1.py", 101, visible=True)],
    )
    run_main(course_dir, http_client=http, now=NOW_BEFORE_HW1_START)
    assert http.patched.get("/api/projects/101/") == {"visible_to_students": False}


def test_already_hidden_before_start_date_no_patch(course_dir: Path) -> None:
    http = MockHttpClient(
        courses=[make_course()],
        projects=[make_project("hw1.py", 101, visible=False)],
    )
    run_main(course_dir, http_client=http, now=NOW_BEFORE_HW1_START)
    assert "/api/projects/101/" not in http.patched


# ---------------------------------------------------------------------------
# Grade publishing
# ---------------------------------------------------------------------------


def test_reveals_grades_after_end_date_when_closing_time_matches(course_dir: Path) -> None:
    http = MockHttpClient(
        courses=[make_course()],
        projects=[make_project("hw1.py", 101, visible=True)],
    )
    run_main(course_dir, http_client=http, now=NOW_AFTER_HW1_END)
    assert http.patched.get("/api/projects/101/") == {"hide_ultimate_submission_fdbk": False}


def test_warns_when_closing_time_mismatch(course_dir: Path, capsys: Any) -> None:
    http = MockHttpClient(
        courses=[make_course()],
        projects=[make_project("hw1.py", 101, visible=True, closing_time=HW1_CLOSING_TIME_WRONG)],
    )
    run_main(course_dir, http_client=http, now=NOW_AFTER_HW1_END)
    assert "/api/projects/101/" not in http.patched
    assert "warning" in capsys.readouterr().out


def test_grades_already_revealed_no_patch(course_dir: Path, capsys: Any) -> None:
    http = MockHttpClient(
        courses=[make_course()],
        projects=[make_project("hw1.py", 101, visible=True, hide_grades=False)],
    )
    run_main(course_dir, http_client=http, now=NOW_AFTER_HW1_END)
    assert "/api/projects/101/" not in http.patched
    assert "ok" in capsys.readouterr().out


def test_hides_grades_before_end_date(course_dir: Path) -> None:
    http = MockHttpClient(
        courses=[make_course()],
        projects=[make_project("hw1.py", 101, visible=True, hide_grades=False)],
    )
    run_main(course_dir, http_client=http, now=NOW_AFTER_HW1_START)
    assert http.patched.get("/api/projects/101/") == {"hide_ultimate_submission_fdbk": True}


def test_already_hiding_grades_before_end_date_no_patch(course_dir: Path) -> None:
    http = MockHttpClient(
        courses=[make_course()],
        projects=[make_project("hw1.py", 101, visible=True, hide_grades=True)],
    )
    run_main(course_dir, http_client=http, now=NOW_AFTER_HW1_START)
    assert "/api/projects/101/" not in http.patched


# ---------------------------------------------------------------------------
# Dry run
# ---------------------------------------------------------------------------


def test_dry_run_does_not_patch(course_dir: Path, capsys: Any) -> None:
    http = MockHttpClient(
        courses=[make_course()],
        projects=[make_project("hw1.py", 101)],
    )
    run_main(course_dir, http_client=http, dry_run=True, now=NOW_AFTER_HW1_END)
    assert not http.patched
    assert "dry-run" in capsys.readouterr().out


# ---------------------------------------------------------------------------
# Project not on server
# ---------------------------------------------------------------------------


def test_skips_project_not_on_server(course_dir: Path, capsys: Any) -> None:
    http = MockHttpClient(courses=[make_course()], projects=[])
    run_main(course_dir, http_client=http)
    assert "skip" in capsys.readouterr().out


# ---------------------------------------------------------------------------
# Error cases
# ---------------------------------------------------------------------------


def test_course_not_found_exits(course_dir: Path) -> None:
    http = MockHttpClient(courses=[], projects=[])
    with pytest.raises(SystemExit) as exc:
        run_main(course_dir, http_client=http)
    assert exc.value.code != 0


def test_missing_schedule_exits(course_dir: Path) -> None:
    http = MockHttpClient()
    with pytest.raises(SystemExit) as exc:
        publish_projects.main(Path("nonexistent.txt"), http_client=http)
    assert exc.value.code != 0
