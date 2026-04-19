import os
import shutil
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import pytest
import yaml

import ece_test_harness.scripts.save_projects as save_projects

TESTDATA = Path(__file__).parent / "testdata" / "test_course_save"


class MockProjectCli:
    def __init__(self) -> None:
        self.saved: list[Path] = []

    def save(self, config_file: Path) -> None:
        self.saved.append(config_file)


class MockHttpClient:
    def __init__(
        self,
        courses: Sequence[dict[str, Any]] = (),
        projects: Sequence[dict[str, Any]] = (),
    ) -> None:
        self._courses = list(courses)
        self._projects = list(projects)

    def get(self, path: str) -> list[dict[str, Any]]:
        if path == "/api/courses/":
            return self._courses
        return self._projects


@pytest.fixture()
def course_dir(tmp_path: Path) -> Any:
    dest = tmp_path / "course"
    shutil.copytree(TESTDATA, dest)
    original = Path.cwd()
    os.chdir(dest)
    yield dest
    os.chdir(original)


def run_main(
    course_dir: Path,
    *,
    schedule: str = "schedule.txt",
    project_cli: MockProjectCli | None = None,
    http_client: MockHttpClient | None = None,
) -> None:
    save_projects.main(
        Path(schedule),
        project_cli=project_cli or MockProjectCli(),
        http_client=http_client or MockHttpClient(),
    )


def load_config(course_dir: Path, filename: str) -> dict[str, Any]:
    return yaml.safe_load((course_dir / "course-configs" / filename / "agproject.yml").read_text())


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


def test_save_called_for_each_assignment(course_dir: Path) -> None:
    cli = MockProjectCli()
    run_main(course_dir, project_cli=cli)
    saved_names = {p.parent.name for p in cli.saved}
    assert saved_names == {"hw1.py", "hw2.py"}


def test_deadline_stamped_from_schedule(course_dir: Path) -> None:
    run_main(course_dir)
    deadline = load_config(course_dir, "hw1.py")["project"]["settings"]["deadline"]
    assert deadline["deadline"] == "Jan 20, 2026 11:59PM"
    assert deadline["cutoff_type"] == "relative"


def test_timezone_stamped_from_schedule(course_dir: Path) -> None:
    run_main(course_dir)
    assert load_config(course_dir, "hw1.py")["project"]["timezone"] == "America/Detroit"


def test_no_deadline_when_no_end_date(course_dir: Path) -> None:
    run_main(course_dir)
    settings = load_config(course_dir, "hw2.py")["project"]["settings"]
    assert "deadline" not in settings


# ---------------------------------------------------------------------------
# Orphan warning
# ---------------------------------------------------------------------------


def test_orphan_warning(course_dir: Path, capsys: Any) -> None:
    http = MockHttpClient(
        courses=[{"name": "EECS 551", "semester": "Fall", "year": 2026, "pk": 1}],
        projects=[{"name": "hw1.py"}, {"name": "hw2.py"}, {"name": "hw3.py"}],
    )
    run_main(course_dir, http_client=http)
    assert "hw3.py" in capsys.readouterr().err


def test_no_orphan_warning_when_server_matches(course_dir: Path, capsys: Any) -> None:
    http = MockHttpClient(
        courses=[{"name": "EECS 551", "semester": "Fall", "year": 2026, "pk": 1}],
        projects=[{"name": "hw1.py"}, {"name": "hw2.py"}],
    )
    run_main(course_dir, http_client=http)
    assert "warning" not in capsys.readouterr().err


# ---------------------------------------------------------------------------
# Error cases
# ---------------------------------------------------------------------------


def test_missing_config_exits(course_dir: Path) -> None:
    (course_dir / "course-configs" / "hw1.py" / "agproject.yml").unlink()
    with pytest.raises(SystemExit) as exc:
        run_main(course_dir)
    assert exc.value.code != 0


def test_missing_schedule_exits(course_dir: Path) -> None:
    with pytest.raises(SystemExit) as exc:
        run_main(course_dir, schedule="nonexistent_schedule.txt")
    assert exc.value.code != 0
