import asyncio
import os
import shutil
from pathlib import Path
from typing import Any

import pytest

import ece_test_harness.scripts.test_solutions as test_solutions

TESTDATA = Path(__file__).parent / "testdata" / "test_course_solutions"


async def _no_sleep(_: float) -> None:
    pass


class MockSolutionsClient:
    def __init__(
        self,
        username: str = "testuser",
        course: dict[str, Any] | None = None,
        projects: list[dict[str, Any]] | None = None,
        groups: dict[int, list[dict[str, Any]]] | None = None,
        submission_results: dict[int, dict[str, Any]] | None = None,
    ) -> None:
        self.submitted: list[str] = []
        self.groups_created: list[int] = []
        self._username = username
        self._course: dict[str, Any] | None = (
            course if course is not None else {"pk": 1, "name": "EECS 551"}
        )
        self._projects: list[dict[str, Any]] = projects if projects is not None else []
        self._groups: dict[int, list[dict[str, Any]]] = groups or {}
        self._next_sub_pk = 100
        self._submission_results: dict[int, dict[str, Any]] = submission_results or {}

    async def get_current_user(self) -> dict[str, Any]:
        return {"username": self._username}

    async def find_course(self, name: str, semester: str, year: int) -> dict[str, Any] | None:
        return self._course

    async def get_projects(self, course_pk: int) -> list[dict[str, Any]]:
        return self._projects

    async def get_groups(self, project_pk: int) -> list[dict[str, Any]]:
        return self._groups.get(project_pk, [])

    async def create_group(self, project_pk: int, member_names: list[str]) -> dict[str, Any]:
        self.groups_created.append(project_pk)
        pk = 200 + project_pk
        self._groups[project_pk] = [{"pk": pk}]
        return {"pk": pk}

    async def submit(self, group_pk: int, filename: str, file_path: Path) -> dict[str, Any]:
        pk = self._next_sub_pk
        self._next_sub_pk += 1
        self.submitted.append(filename)
        return {"pk": pk}

    async def get_submission(self, sub_pk: int) -> dict[str, Any]:
        return {"pk": sub_pk, "status": "finished_grading"}

    async def get_submission_results(self, sub_pk: int) -> dict[str, Any]:
        return self._submission_results.get(sub_pk, {"total_points": 1, "total_points_possible": 1})


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
    client: MockSolutionsClient,
) -> None:
    asyncio.run(
        test_solutions.main(
            course_dir / "schedule.txt",
            course_dir / "graders",
            client=client,
            sleep=_no_sleep,
        )
    )


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


def test_submits_solution_file(course_dir: Path) -> None:
    client = MockSolutionsClient(
        projects=[{"name": "hw1.py", "pk": 101}],
    )
    run_main(course_dir, client=client)
    assert "hw1.py" in client.submitted


def test_creates_group_when_none_exists(course_dir: Path) -> None:
    client = MockSolutionsClient(
        projects=[{"name": "hw1.py", "pk": 101}],
    )
    run_main(course_dir, client=client)
    assert 101 in client.groups_created


def test_uses_existing_group(course_dir: Path) -> None:
    client = MockSolutionsClient(
        projects=[{"name": "hw1.py", "pk": 101}],
        groups={101: [{"pk": 999}]},
    )
    run_main(course_dir, client=client)
    assert 101 not in client.groups_created


def test_prints_results_table(course_dir: Path, capsys: Any) -> None:
    client = MockSolutionsClient(
        projects=[{"name": "hw1.py", "pk": 101}],
        submission_results={100: {"total_points": 1, "total_points_possible": 1}},
    )
    run_main(course_dir, client=client)
    out = capsys.readouterr().out
    assert "hw1.py" in out
    assert "1/1" in out
    assert "✓" in out


# ---------------------------------------------------------------------------
# Skips
# ---------------------------------------------------------------------------


def test_skips_project_not_on_server(course_dir: Path, capsys: Any) -> None:
    client = MockSolutionsClient(projects=[])
    with pytest.raises(SystemExit):
        run_main(course_dir, client=client)
    assert "hw1.py" in capsys.readouterr().err


def test_skips_missing_solution_file(course_dir: Path, capsys: Any) -> None:
    client = MockSolutionsClient(
        projects=[{"name": "hw2.py", "pk": 102}],
    )
    with pytest.raises(SystemExit):
        run_main(course_dir, client=client)
    assert "hw2.py" in capsys.readouterr().err


# ---------------------------------------------------------------------------
# No submissions
# ---------------------------------------------------------------------------


def test_exits_when_no_submissions(course_dir: Path) -> None:
    client = MockSolutionsClient(projects=[])
    with pytest.raises(SystemExit) as exc:
        run_main(course_dir, client=client)
    assert exc.value.code != 0


# ---------------------------------------------------------------------------
# Error cases
# ---------------------------------------------------------------------------


def test_course_not_found_exits(course_dir: Path) -> None:
    client = MockSolutionsClient(course=None)
    client._course = None
    with pytest.raises(SystemExit) as exc:
        run_main(course_dir, client=client)
    assert exc.value.code != 0


def test_missing_schedule_exits(course_dir: Path) -> None:
    client = MockSolutionsClient()
    with pytest.raises(SystemExit) as exc:
        asyncio.run(
            test_solutions.main(
                Path("nonexistent.txt"),
                course_dir / "graders",
                client=client,
                sleep=_no_sleep,
            )
        )
    assert exc.value.code != 0


def test_missing_graders_dir_exits(course_dir: Path) -> None:
    client = MockSolutionsClient()
    with pytest.raises(SystemExit) as exc:
        asyncio.run(
            test_solutions.main(
                course_dir / "schedule.txt",
                Path("nonexistent"),
                client=client,
                sleep=_no_sleep,
            )
        )
    assert exc.value.code != 0
