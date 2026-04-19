import os
import shutil
from pathlib import Path
from typing import Any

import pytest
import yaml

import ece_test_harness.scripts.configure_projects as configure_projects

TESTDATA = Path(__file__).parent / "testdata" / "test_course_basic"


@pytest.fixture()
def course_dir(tmp_path: Path) -> Any:
    """Copy the test course into a temp directory and chdir there."""
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
    graders: str = "graders",
    overwrite: bool = False,
    project_settings_defaults: str | None = None,
    test_case_defaults: str | None = None,
) -> None:
    configure_projects.main(
        Path(schedule),
        Path(graders),
        overwrite=overwrite,
        project_settings_defaults=project_settings_defaults,
        test_case_defaults=test_case_defaults,
    )


def load_config(course_dir: Path, filename: str) -> dict[str, Any]:
    return yaml.safe_load((course_dir / "course-configs" / filename / "agproject.yml").read_text())


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


def test_creates_config_for_assignment(course_dir: Path) -> None:
    run_main(course_dir)
    assert (course_dir / "course-configs" / "hw1.py" / "agproject.yml").is_file()


def test_student_and_instructor_files(course_dir: Path) -> None:
    run_main(course_dir)
    config = load_config(course_dir, "hw1.py")
    assert config["project"]["student_files"] == ["hw1.py"]
    names = {e["local_path"] for e in config["project"]["instructor_files"]}
    assert {"hw1_grader.py", "hw1_sol.py"} <= names


def test_instructor_files_copied_to_dir(course_dir: Path) -> None:
    run_main(course_dir)
    project_dir = course_dir / "course-configs" / "hw1.py"
    assert (project_dir / "hw1_grader.py").is_file()
    assert (project_dir / "hw1_sol.py").is_file()


def test_default_project_settings(course_dir: Path) -> None:
    run_main(course_dir)
    settings = load_config(course_dir, "hw1.py")["project"]["settings"]
    assert settings["submission_limit_per_day"] == 1
    assert settings["final_graded_submission_policy"] == "best"
    assert settings["allow_submissions_past_limit"] is False


def test_deadline_and_timezone(course_dir: Path) -> None:
    run_main(course_dir)
    project = load_config(course_dir, "hw1.py")["project"]
    assert project["timezone"] == "America/Detroit"
    deadline = project["settings"]["deadline"]
    assert deadline["cutoff_type"] == "relative"
    assert deadline["deadline"] == "Jan 20, 2026 11:59PM"


def test_test_suite_cmd(course_dir: Path) -> None:
    run_main(course_dir)
    tc = load_config(course_dir, "hw1.py")["project"]["test_suites"][0]["test_cases"][0]
    assert "ece-grade hw1.py" in tc["cmd"]


# ---------------------------------------------------------------------------
# Missing grader — warn and skip
# ---------------------------------------------------------------------------


def test_warns_when_grader_missing(course_dir: Path, capsys: Any) -> None:
    run_main(course_dir)
    assert "hw2.py" in capsys.readouterr().err


def test_no_config_created_when_grader_missing(course_dir: Path) -> None:
    run_main(course_dir)
    assert not (course_dir / "course-configs" / "hw2.py").exists()


# ---------------------------------------------------------------------------
# Blacklist
# ---------------------------------------------------------------------------


def test_blacklist_file_created(course_dir: Path) -> None:
    run_main(course_dir)
    bl = course_dir / "course-configs" / "hw3.py" / "blacklist.txt"
    assert bl.is_file()
    tokens = bl.read_text().split()
    assert "os" in tokens
    assert "numpy" in tokens


def test_blacklist_in_instructor_files(course_dir: Path) -> None:
    run_main(course_dir)
    ifiles = load_config(course_dir, "hw3.py")["project"]["instructor_files"]
    names = {e["local_path"] for e in ifiles}
    assert "blacklist.txt" in names


# ---------------------------------------------------------------------------
# Dependency files
# ---------------------------------------------------------------------------


def test_dependency_file_copied(course_dir: Path) -> None:
    run_main(course_dir)
    assert (course_dir / "course-configs" / "hw4.py" / "hw4lib.py").is_file()


def test_dependency_in_instructor_files(course_dir: Path) -> None:
    run_main(course_dir)
    ifiles = load_config(course_dir, "hw4.py")["project"]["instructor_files"]
    names = {e["local_path"] for e in ifiles}
    assert "hw4lib.py" in names


# ---------------------------------------------------------------------------
# Skip existing / --overwrite
# ---------------------------------------------------------------------------


def test_skips_existing_config(course_dir: Path, capsys: Any) -> None:
    run_main(course_dir)
    config_file = course_dir / "course-configs" / "hw1.py" / "agproject.yml"
    original = config_file.read_text()
    run_main(course_dir)
    assert config_file.read_text() == original
    assert "skip" in capsys.readouterr().out


def test_overwrite_regenerates_config(course_dir: Path) -> None:
    run_main(course_dir)
    config_file = course_dir / "course-configs" / "hw1.py" / "agproject.yml"
    config_file.write_text("# sentinel\n")
    run_main(course_dir, overwrite=True)
    assert "project" in yaml.safe_load(config_file.read_text())


# ---------------------------------------------------------------------------
# --project-settings-defaults
# ---------------------------------------------------------------------------


def test_project_settings_defaults(course_dir: Path, tmp_path: Path) -> None:
    overrides = tmp_path / "ps.yml"
    overrides.write_text("send_email_receipts: true\ntotal_submission_limit: 5\n")
    run_main(course_dir, project_settings_defaults=str(overrides))
    settings = load_config(course_dir, "hw1.py")["project"]["settings"]
    assert settings["send_email_receipts"] is True
    assert settings["total_submission_limit"] == 5


# ---------------------------------------------------------------------------
# --test-case-defaults
# ---------------------------------------------------------------------------


def test_test_case_defaults(course_dir: Path, tmp_path: Path) -> None:
    overrides = tmp_path / "tc.yml"
    overrides.write_text("return_code:\n  expected: zero\n  points: 2\n")
    run_main(course_dir, test_case_defaults=str(overrides))
    tc = load_config(course_dir, "hw1.py")["project"]["test_suites"][0]["test_cases"][0]
    assert tc["return_code"]["points"] == 2


def test_test_case_defaults_reserved_fields_error(course_dir: Path, tmp_path: Path) -> None:
    overrides = tmp_path / "tc.yml"
    overrides.write_text("name: sneaky\ncmd: evil\n")
    with pytest.raises(SystemExit) as exc:
        run_main(course_dir, test_case_defaults=str(overrides))
    assert exc.value.code != 0


def test_test_case_defaults_invalid_field_error(course_dir: Path, tmp_path: Path) -> None:
    overrides = tmp_path / "tc.yml"
    overrides.write_text("not_a_real_field: 999\n")
    with pytest.raises(SystemExit) as exc:
        run_main(course_dir, test_case_defaults=str(overrides))
    assert "not_a_real_field" in str(exc.value.code)


def test_project_settings_defaults_invalid_field_error(course_dir: Path, tmp_path: Path) -> None:
    overrides = tmp_path / "ps.yml"
    overrides.write_text("not_a_real_field: 999\n")
    with pytest.raises(SystemExit) as exc:
        run_main(course_dir, project_settings_defaults=str(overrides))
    assert "not_a_real_field" in str(exc.value.code)


def test_project_settings_defaults_invalid_value_error(course_dir: Path, tmp_path: Path) -> None:
    overrides = tmp_path / "ps.yml"
    overrides.write_text("total_submission_limit: bar\n")
    with pytest.raises(SystemExit) as exc:
        run_main(course_dir, project_settings_defaults=str(overrides))
    msg = str(exc.value.code)
    assert "total_submission_limit" in msg
    assert "integer" in msg.lower()


def test_test_case_defaults_invalid_value_error(course_dir: Path, tmp_path: Path) -> None:
    overrides = tmp_path / "tc.yml"
    overrides.write_text("return_code:\n  expected: zero\n  points: foo\n")
    with pytest.raises(SystemExit) as exc:
        run_main(course_dir, test_case_defaults=str(overrides))
    msg = str(exc.value.code)
    assert "return_code" in msg
    assert "integer" in msg.lower()


# ---------------------------------------------------------------------------
# Error cases
# ---------------------------------------------------------------------------


def test_missing_schedule_exits(course_dir: Path) -> None:
    with pytest.raises(SystemExit) as exc:
        run_main(course_dir, schedule="nonexistent_schedule.txt")
    assert exc.value.code != 0


def test_missing_graders_dir_exits(course_dir: Path) -> None:
    with pytest.raises(SystemExit) as exc:
        run_main(course_dir, graders="nonexistent_graders")
    assert exc.value.code != 0


@pytest.mark.parametrize(
    "bad_schedule",
    [
        "semester = Fall\nyear = 2026\nhw1.py 2026/01/13@00:00 2026/01/20@23:59\n",
        "course = EECS 551\nyear = 2026\nhw1.py 2026/01/13@00:00 2026/01/20@23:59\n",
        "course = EECS 551\nsemester = Fall\nhw1.py 2026/01/13@00:00 2026/01/20@23:59\n",
    ],
)
def test_missing_required_fields_exits(course_dir: Path, tmp_path: Path, bad_schedule: str) -> None:
    sched = tmp_path / "bad.txt"
    sched.write_text(bad_schedule)
    with pytest.raises(SystemExit) as exc:
        run_main(course_dir, schedule=str(sched))
    assert exc.value.code != 0
