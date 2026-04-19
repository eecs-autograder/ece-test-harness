import argparse
import sys
import time
from pathlib import Path
from typing import Any, Callable, Protocol

# The ag CLI doesn't support multipart file uploads, so this script uses requests
# directly to submit solution files. _agclient wraps the shared auth and API helpers.
from ._requests_ag_client import (
    DEFAULT_BASE_URL,
    DEFAULT_TOKEN_FILE,
    find_course,
    get_dict,
    get_list,
    make_session,
)
from ._schedule import parse_schedule

POLL_INTERVAL = 5


class SolutionsClient(Protocol):
    def get_current_user(self) -> dict[str, Any]: ...
    def find_course(self, name: str, semester: str, year: int) -> dict[str, Any] | None: ...
    def get_projects(self, course_pk: int) -> list[dict[str, Any]]: ...
    def get_groups(self, project_pk: int) -> list[dict[str, Any]]: ...
    def create_group(self, project_pk: int, member_names: list[str]) -> dict[str, Any]: ...
    def submit(self, group_pk: int, filename: str, file_path: Path) -> dict[str, Any]: ...
    def get_submission(self, sub_pk: int) -> dict[str, Any]: ...
    def get_submission_results(self, sub_pk: int) -> dict[str, Any]: ...


class RequestsSolutionsClient:
    def __init__(self, token_file: str, base_url: str):
        self._session, self._base = make_session(token_file, base_url)

    def get_current_user(self) -> dict[str, Any]:
        return get_dict(self._session, self._base, "/api/users/current/")

    def find_course(self, name: str, semester: str, year: int) -> dict[str, Any] | None:
        return find_course(self._session, self._base, name, semester, year)

    def get_projects(self, course_pk: int) -> list[dict[str, Any]]:
        return get_list(self._session, self._base, f"/api/courses/{course_pk}/projects/")

    def get_groups(self, project_pk: int) -> list[dict[str, Any]]:
        return get_list(self._session, self._base, f"/api/projects/{project_pk}/groups/")

    def create_group(self, project_pk: int, member_names: list[str]) -> dict[str, Any]:
        r = self._session.post(
            f"{self._base}/api/projects/{project_pk}/groups/",
            json={"member_names": member_names},
        )
        r.raise_for_status()
        return r.json()

    def submit(self, group_pk: int, filename: str, file_path: Path) -> dict[str, Any]:
        r = self._session.post(
            f"{self._base}/api/groups/{group_pk}/submissions/",
            files={"submitted_files": (filename, file_path.open("rb"))},
        )
        if not r.ok:
            raise RuntimeError(f"{r.status_code} {r.text[:120]}")
        return r.json()

    def get_submission(self, sub_pk: int) -> dict[str, Any]:
        return get_dict(self._session, self._base, f"/api/submissions/{sub_pk}/")

    def get_submission_results(self, sub_pk: int) -> dict[str, Any]:
        return get_dict(
            self._session,
            self._base,
            f"/api/submissions/{sub_pk}/results/?feedback_category=normal",
        )


def main(
    schedule_path: Path,
    graders_dir: Path,
    *,
    client: SolutionsClient,
    sleep: Callable[[float], None] = time.sleep,
) -> None:
    if not schedule_path.is_file():
        sys.exit(f"error: schedule file not found: {schedule_path}")
    if not graders_dir.is_dir():
        sys.exit(f"error: graders directory not found: {graders_dir}")

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

    username = client.get_current_user()["username"]

    course = client.find_course(schedule.course, schedule.semester, schedule.year)
    if course is None:
        sys.exit(
            f"error: course '{schedule.course} {schedule.semester} {schedule.year}'"
            " not found on server"
        )

    projects = {p["name"]: p["pk"] for p in client.get_projects(course["pk"])}

    pending: dict[str, int] = {}  # filename -> submission pk

    for assignment in schedule.assignments:
        filename = assignment.filename
        correct_file = graders_dir / f"{assignment.name}{assignment.ext}"

        if filename not in projects:
            print(f"skip  {filename}: no matching project on server", file=sys.stderr)
            continue
        if not correct_file.is_file():
            print(f"skip  {filename}: correct student file not found", file=sys.stderr)
            continue

        proj_pk = projects[filename]

        groups = client.get_groups(proj_pk)
        if groups:
            group_pk = groups[0]["pk"]
        else:
            group_pk = client.create_group(proj_pk, [username])["pk"]

        try:
            result = client.submit(group_pk, filename, correct_file)
        except Exception as e:
            print(f"fail  {filename}: {e}", file=sys.stderr)
            continue

        sub_pk = result["pk"]
        pending[filename] = sub_pk
        print(f"submitted  {filename} (submission {sub_pk})")

    if not pending:
        sys.exit("no submissions made")

    print(f"\nwaiting for {len(pending)} submission(s)...", flush=True)
    results: dict[str, dict] = {}

    while pending:
        sleep(POLL_INTERVAL)
        done = []
        for filename, sub_pk in pending.items():
            sub = client.get_submission(sub_pk)
            if sub["status"] in ("finished_grading", "removed_from_queue", "error"):
                results[filename] = sub
                done.append(filename)
        for f in done:
            del pending[f]

    print("\nResults:")
    print(f"  {'project':<25} {'status':<20} {'points':<12} {'passed'}")
    print(f"  {'-' * 25} {'-' * 20} {'-' * 12} {'-' * 6}")
    for filename, sub in sorted(results.items()):
        status = sub["status"]
        sub_pk = sub["pk"]

        points_str = "n/a"
        passed_str = "-"
        try:
            res = client.get_submission_results(sub_pk)
            total = res["total_points"]
            possible = res["total_points_possible"]
            points_str = f"{total}/{possible}"
            passed_str = "✓" if possible > 0 and total == possible else "✗"
        except Exception:
            pass

        print(f"  {filename:<25} {status:<20} {points_str:<12} {passed_str}")


def cli() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Submit solution files to Autograder.io projects and report results. "
            "Projects must already exist (run ece-save-projects first)."
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
        help="Path to graders directory (default: graders/)",
    )
    parser.add_argument(
        "--base-url",
        default=DEFAULT_BASE_URL,
        help=f"Autograder.io base URL (default: {DEFAULT_BASE_URL})",
    )
    parser.add_argument(
        "--token-file",
        default=DEFAULT_TOKEN_FILE,
        help=f"AG token file path (default: {DEFAULT_TOKEN_FILE})",
    )
    args = parser.parse_args()
    main(
        Path(args.schedule),
        Path(args.graders),
        client=RequestsSolutionsClient(args.token_file, args.base_url),
    )


if __name__ == "__main__":
    cli()
