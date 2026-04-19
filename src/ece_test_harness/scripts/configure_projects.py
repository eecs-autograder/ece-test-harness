import argparse
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import yaml
from autograder_cli.config.models import ProjectSettings, SingleCmdTestCaseConfig
from pydantic import BaseModel, ValidationError

from ..schedule import format_ag_date, parse_schedule

CONFIGS_DIR = Path("course-configs")

_PROJECT_SETTINGS_VALID_KEYS: frozenset[str] = frozenset(
    name
    for field_name, field in ProjectSettings.model_fields.items()
    for name in ([field_name] + ([field.alias] if field.alias else []))
)

_TEST_CASE_VALID_KEYS: frozenset[str] = frozenset(
    name
    for field_name, field in SingleCmdTestCaseConfig.model_fields.items()
    for name in ([field_name] + ([field.alias] if field.alias else []))
)


def _validate_override_values(
    overrides: dict[str, Any],
    model: type[BaseModel],
    label: str,
    extra: dict[str, Any] | None = None,
) -> None:
    try:
        model.model_validate({**(extra or {}), **overrides}, context={"read_yaml": True})
    except ValidationError as e:
        errors = [err for err in e.errors() if err["loc"] and err["loc"][0] in overrides]
        if errors:
            detail = "; ".join(
                f"{'.'.join(str(x) for x in err['loc'])}: {err['msg']}" for err in errors
            )
            sys.exit(f"error: {label} contains invalid value(s): {detail}")


def _load_yaml_arg(path: str, label: str) -> dict[str, Any]:
    try:
        with open(path) as f:
            data = yaml.safe_load(f)
    except OSError as e:
        sys.exit(f"error: could not read {label} file: {e}")
    if not isinstance(data, dict):
        sys.exit(f"error: {label} file must be a YAML mapping")
    return data


def main(
    schedule_path: Path,
    graders_dir: Path,
    *,
    overwrite: bool = False,
    project_settings_defaults: str | None = None,
    test_case_defaults: str | None = None,
) -> None:
    if not schedule_path.is_file():
        sys.exit(f"error: schedule file not found: {schedule_path}")

    schedule = parse_schedule(schedule_path)

    missing = [
        f
        for f, v in [
            ("course", schedule.course),
            ("semester", schedule.semester),
            ("year", schedule.year),
        ]
        if v is None
    ]
    if missing:
        sys.exit(f"error: schedule.txt is missing required field(s): {', '.join(missing)}")

    assert schedule.course is not None
    assert schedule.semester is not None
    assert schedule.year is not None

    if not graders_dir.is_dir():
        sys.exit(f"error: graders directory not found: {graders_dir}")
    if not schedule.assignments:
        sys.exit("error: no assignments found in schedule file")

    project_settings_overrides = {}
    if project_settings_defaults:
        project_settings_overrides = _load_yaml_arg(
            project_settings_defaults, "--project-settings-defaults"
        )
        invalid = sorted(
            k for k in project_settings_overrides if k not in _PROJECT_SETTINGS_VALID_KEYS
        )
        if invalid:
            sys.exit(
                "error: --project-settings-defaults contains unknown field(s): "
                + ", ".join(invalid)
            )
        _validate_override_values(
            project_settings_overrides, ProjectSettings, "--project-settings-defaults"
        )

    test_case_overrides = {}
    if test_case_defaults:
        test_case_overrides = _load_yaml_arg(test_case_defaults, "--test-case-defaults")
        reserved = {k for k in ("name", "cmd") if k in test_case_overrides}
        if reserved:
            sys.exit(
                "error: --test-case-defaults must not contain reserved field(s): "
                + ", ".join(sorted(reserved))
            )
        invalid = sorted(k for k in test_case_overrides if k not in _TEST_CASE_VALID_KEYS)
        if invalid:
            sys.exit(f"error: --test-case-defaults contains unknown field(s): {', '.join(invalid)}")
        _validate_override_values(
            test_case_overrides,
            SingleCmdTestCaseConfig,
            "--test-case-defaults",
            extra={"name": "_", "cmd": "_"},
        )

    CONFIGS_DIR.mkdir(exist_ok=True)

    for assignment in schedule.assignments:
        submission = assignment.filename
        name = assignment.name
        ext = assignment.ext
        project_dir = CONFIGS_DIR / submission
        config_file = project_dir / "agproject.yml"

        if config_file.is_file():
            if not overwrite:
                print(f"skip  {submission}: config already exists")
                continue
            shutil.rmtree(project_dir)

        grader_file = graders_dir / f"{name}_grader{ext}"
        if not grader_file.is_file():
            print(f"warning: no grader file found for {submission}, skipping", file=sys.stderr)
            continue

        project_dir.mkdir(exist_ok=True)

        # Copy instructor files
        instructor_filenames: list[str] = []
        for suffix in ("_grader", "_sol"):
            src = graders_dir / f"{name}{suffix}{ext}"
            if src.is_file():
                shutil.copy(src, project_dir / src.name)
                instructor_filenames.append(src.name)
            else:
                print(f"warning: instructor file not found: {src}", file=sys.stderr)

        # Copy additional dependency files (e.g. hw1lib.py for hw1.py)
        reserved = {submission, f"{name}_sol{ext}", f"{name}_grader{ext}"}
        for dep in sorted(graders_dir.glob(f"{name}*{ext}")):
            if dep.name not in reserved:
                shutil.copy(dep, project_dir / dep.name)
                instructor_filenames.append(dep.name)

        if assignment.blacklist:
            (project_dir / "blacklist.txt").write_text("\n".join(assignment.blacklist) + "\n")
            instructor_filenames.append("blacklist.txt")

        subprocess.run(
            [
                "ag",
                "project",
                "init",
                schedule.course,
                schedule.semester,
                str(schedule.year),
                submission,
                "--config_file",
                str(config_file),
            ],
            check=True,
        )

        with open(config_file) as f:
            config = yaml.safe_load(f)

        config["project"]["timezone"] = schedule.timezone
        config["project"]["settings"].update(
            {
                "submission_limit_per_day": 1,
                "final_graded_submission_policy": "best",
                "allow_submissions_past_limit": False,
                **project_settings_overrides,
            }
        )

        if assignment.end_date:
            config["project"]["settings"]["deadline"] = {
                "cutoff_type": "relative",
                "deadline": format_ag_date(assignment.end_date),
                "cutoff": "0h0m",
            }

        config["project"]["student_files"] = [submission]
        config["project"]["instructor_files"] = [
            {"local_path": fname} for fname in instructor_filenames
        ]
        config["project"]["test_suites"] = [
            {
                "name": "Grading",
                "sandbox_docker_image": "ece-autograder",
                "student_files_needed": [submission],
                "instructor_files_needed": instructor_filenames,
                "test_cases": [
                    {
                        "name": f"Grade {submission}",
                        "cmd": f"source env/bin/activate && ece-grade {submission}",
                        "return_code": {"expected": "zero", "points": 1},
                        "feedback": {
                            "normal": "pass/fail+timeout",
                            "final_graded_submission": "pass/fail+timeout",
                        },
                        **test_case_overrides,
                    }
                ],
            }
        ]
        config["project"]["mutation_suites"] = []
        config["project"]["handgrading"] = None

        with open(config_file, "w") as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False)

        print(f"created {config_file}")


def cli() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Generate Autograder.io project config files with sane defaults for any "
            "assignments in schedule.txt that don't already have a config. "
            "Existing configs are never modified unless --overwrite is given. "
            "Configs are written to course-configs/<filename>/agproject.yml."
        )
    )
    parser.add_argument(
        "schedule",
        nargs="?",
        default="schedule.txt",
        help="Path to schedule file (default: schedule.txt)",
    )
    parser.add_argument(
        "--graders",
        default="graders",
        help="Path to the graders directory (default: graders/)",
    )
    parser.add_argument(
        "--project-settings-defaults",
        metavar="FILE",
        help="YAML file of project settings fields to merge into the defaults.",
    )
    parser.add_argument(
        "--test-case-defaults",
        metavar="FILE",
        help=(
            "YAML file of test case fields to merge into the defaults."
            " 'name' and 'cmd' are not allowed."
        ),
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Regenerate configs that already exist, discarding any manual edits.",
    )
    args = parser.parse_args()
    main(
        Path(args.schedule),
        Path(args.graders),
        overwrite=args.overwrite,
        project_settings_defaults=args.project_settings_defaults,
        test_case_defaults=args.test_case_defaults,
    )


if __name__ == "__main__":
    cli()
