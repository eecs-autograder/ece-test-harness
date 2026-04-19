import argparse
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from ..schedule import parse_schedule
from ._protocols import HttpClient, SubprocessHttpClient


def _parse_closing_time(closing_time: str | None, tz: ZoneInfo) -> datetime | None:
    if not closing_time:
        return None
    try:
        dt = datetime.fromisoformat(closing_time.replace("Z", "+00:00"))
        return dt.astimezone(tz).replace(tzinfo=None, second=0, microsecond=0)
    except (ValueError, AttributeError):
        return None


def main(
    schedule_path: Path,
    *,
    http_client: HttpClient,
    dry_run: bool = False,
    now: datetime | None = None,
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

    tz = ZoneInfo(schedule.timezone)
    if now is None:
        now = datetime.now(tz).replace(tzinfo=None, second=0, microsecond=0)

    courses = http_client.get("/api/courses/")
    course = next(
        (
            c
            for c in courses
            if c["name"] == schedule.course
            and c.get("semester") == schedule.semester
            and c.get("year") == schedule.year
        ),
        None,
    )
    if course is None:
        sys.exit(
            f"error: course '{schedule.course} {schedule.semester} {schedule.year}'"
            " not found on server"
        )

    project_list = http_client.get(f"/api/courses/{course['pk']}/projects/")
    projects = {p["name"]: p for p in project_list}

    for assignment in schedule.assignments:
        filename = assignment.filename
        project = projects.get(filename)
        if project is None:
            print(f"skip     {filename}: no matching project on server")
            continue

        proj_pk = project["pk"]
        changes: dict = {}

        if assignment.start_date is not None and now >= assignment.start_date:
            if not project.get("visible_to_students", False):
                changes["visible_to_students"] = True

        if assignment.end_date is not None and now >= assignment.end_date:
            if project.get("hide_ultimate_submission_fdbk", True):
                closing_time = _parse_closing_time(project.get("closing_time"), tz)
                if closing_time is None:
                    print(
                        f"warning  {filename}: could not parse closing_time from server,"
                        " skipping grade publish"
                    )
                elif closing_time != assignment.end_date:
                    print(
                        f"warning  {filename}: server closing_time {closing_time} does not match "
                        f"schedule due date {assignment.end_date}, skipping grade publish"
                    )
                else:
                    changes["hide_ultimate_submission_fdbk"] = False

        if not changes:
            print(f"ok       {filename}: already up to date")
            continue

        desc = ", ".join(f"{k}={v}" for k, v in changes.items())
        if dry_run:
            print(f"dry-run  {filename}: would set {desc}")
        else:
            http_client.patch(f"/api/projects/{proj_pk}/", changes)
            print(f"updated  {filename}: {desc}")


def cli() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Publish Autograder.io projects based on schedule dates. "
            "Sets visible_to_students=True for projects whose start date has passed, "
            "and hide_ultimate_submission_fdbk=False for projects whose due date has passed."
        )
    )
    parser.add_argument(
        "schedule",
        nargs="?",
        default="schedule.txt",
        help="Path to schedule file (default: schedule.txt)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be changed without making any API calls.",
    )
    args = parser.parse_args()
    main(
        Path(args.schedule),
        http_client=SubprocessHttpClient(),
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    cli()
