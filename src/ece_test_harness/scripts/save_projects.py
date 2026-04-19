import argparse
import subprocess
import sys
from pathlib import Path
from typing import Any, Protocol

import yaml

from ..schedule import Assignment, format_ag_date, parse_schedule
from ._protocols import SubprocessHttpClient


class HttpClient(Protocol):
    def get(self, path: str) -> list[dict[str, Any]]: ...


CONFIGS_DIR = Path("course-configs")


class ProjectCli(Protocol):
    def save(self, config_file: Path) -> None: ...


class SubprocessProjectCli:
    def save(self, config_file: Path) -> None:
        subprocess.run(
            ["ag", "project", "save", "--config_file", str(config_file)],
            check=True,
        )


def _apply_schedule_fields(config: dict[str, Any], assignment: Assignment, timezone: str) -> None:
    config["project"]["timezone"] = timezone
    if assignment.end_date:
        config["project"]["settings"]["deadline"] = {
            "cutoff_type": "relative",
            "deadline": format_ag_date(assignment.end_date),
            "cutoff": "0h0m",
        }
    else:
        config["project"]["settings"].pop("deadline", None)


def main(
    schedule_path: Path,
    *,
    project_cli: ProjectCli,
    http_client: HttpClient,
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

    if not CONFIGS_DIR.is_dir():
        sys.exit(f"error: {CONFIGS_DIR}/ not found — run ece-configure-projects first")

    for assignment in schedule.assignments:
        config_file = CONFIGS_DIR / assignment.filename / "agproject.yml"
        if not config_file.is_file():
            sys.exit(
                f"error: config file not found for {assignment.filename}"
                " — run ece-configure-projects to generate it"
            )

        with open(config_file) as f:
            config = yaml.safe_load(f)

        _apply_schedule_fields(config, assignment, schedule.timezone)

        with open(config_file, "w") as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False)

        project_cli.save(config_file)
        print(f"saved {config_file}")

    # Warn about projects on the server not in the schedule
    expected = {a.filename for a in schedule.assignments}
    try:
        courses = http_client.get("/api/courses/")
        course = next(
            (
                c
                for c in courses
                if c["name"] == schedule.course
                and c.get("semester") == schedule.semester
                and str(c.get("year")) == str(schedule.year)
            ),
            None,
        )
        if course:
            server_projects = {
                p["name"] for p in http_client.get(f"/api/courses/{course['pk']}/projects/")
            }
            for name in sorted(server_projects - expected):
                print(
                    f"warning: project '{name}' exists on server but is not in the schedule file",
                    file=sys.stderr,
                )
    except Exception as e:
        print(f"warning: could not check server for orphaned projects: {e}", file=sys.stderr)


def cli() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Push project configs from course-configs/ to Autograder.io, using "
            "schedule.txt as the source of truth for deadlines. "
            "Creates projects that don't exist yet and updates those that do. "
            "Run ece-configure-projects first to generate the config files."
        )
    )
    parser.add_argument(
        "schedule",
        nargs="?",
        default="schedule.txt",
        help="Path to schedule file (default: schedule.txt)",
    )
    args = parser.parse_args()
    main(
        Path(args.schedule),
        project_cli=SubprocessProjectCli(),
        http_client=SubprocessHttpClient(),
    )


if __name__ == "__main__":
    cli()
