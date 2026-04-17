import argparse
import sys
import time
from pathlib import Path

import requests

from .init_projects import _parse_schedule

DEFAULT_BASE_URL = "https://autograder.io"
DEFAULT_TOKEN_FILE = "~/.agtoken"
POLL_INTERVAL = 5


def _get(session, base, path):
    r = session.get(f"{base}{path}")
    r.raise_for_status()
    return r.json()


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Submit solution files to Autograder.io projects and report results. "
            "Projects must already exist (run ece-init-projects first)."
        )
    )
    parser.add_argument("schedule", help="Path to schedule.txt")
    parser.add_argument(
        "--graders",
        default="graders",
        help="Path to graders directory (default: graders/)",
    )
    parser.add_argument("--course", required=True, help="Course name, e.g. 'EECS 280'")
    parser.add_argument("--semester", required=True, help="Semester term, e.g. 'Fall'")
    parser.add_argument("--year", required=True, type=int, help="Year, e.g. 2024")
    parser.add_argument(
        "--base-url",
        default=DEFAULT_BASE_URL,
        help=f"Autograder.io base URL (default: {DEFAULT_BASE_URL})",
    )
    parser.add_argument(
        "--token-file",
        default=DEFAULT_TOKEN_FILE,
        help=f"AG token filename (default: {DEFAULT_TOKEN_FILE})",
    )
    args = parser.parse_args()

    schedule_path = Path(args.schedule)
    graders_dir = Path(args.graders)

    if not schedule_path.is_file():
        sys.exit(f"error: schedule file not found: {schedule_path}")
    if not graders_dir.is_dir():
        sys.exit(f"error: graders directory not found: {graders_dir}")

    token = Path(args.token_file).expanduser().read_text().strip()
    session = requests.Session()
    session.headers["Authorization"] = f"Token {token}"
    base = args.base_url.rstrip("/")

    username = _get(session, base, "/api/users/current/")["username"]

    # Find course
    courses = _get(session, base, "/api/courses/")
    course = next(
        (
            c
            for c in courses
            if c["name"] == args.course
            and c.get("semester") == args.semester
            and c.get("year") == args.year
        ),
        None,
    )
    if course is None:
        sys.exit(f"error: course '{args.course} {args.semester} {args.year}' not found on server")

    # Build project name -> pk map
    project_list = _get(session, base, f"/api/courses/{course['pk']}/projects/")
    projects = {p["name"]: p["pk"] for p in project_list}

    # Submit each correct student file
    pending: dict[str, int] = {}  # filename -> submission pk

    for assignment in _parse_schedule(schedule_path):
        filename = assignment.filename
        correct_file = graders_dir / f"{assignment.name}{assignment.ext}"

        if filename not in projects:
            print(f"skip  {filename}: no matching project on server", file=sys.stderr)
            continue
        if not correct_file.is_file():
            print(f"skip  {filename}: correct student file not found", file=sys.stderr)
            continue

        proj_pk = projects[filename]

        # Get or create group
        groups = _get(session, base, f"/api/projects/{proj_pk}/groups/")
        if groups:
            group_pk = groups[0]["pk"]
        else:
            r = session.post(
                f"{base}/api/projects/{proj_pk}/groups/",
                json={"member_names": [username]},
            )
            r.raise_for_status()
            group_pk = r.json()["pk"]

        r = session.post(
            f"{base}/api/groups/{group_pk}/submissions/",
            files={"submitted_files": (filename, correct_file.open("rb"))},
        )
        if not r.ok:
            print(f"fail  {filename}: {r.status_code} {r.text[:120]}", file=sys.stderr)
            continue

        sub_pk = r.json()["pk"]
        pending[filename] = sub_pk
        print(f"submitted  {filename} (submission {sub_pk})")

    if not pending:
        sys.exit("no submissions made")

    # Poll until all finished
    print(f"\nwaiting for {len(pending)} submission(s)...", flush=True)
    results: dict[str, dict] = {}

    while pending:
        time.sleep(POLL_INTERVAL)
        done = []
        for filename, sub_pk in pending.items():
            sub = _get(session, base, f"/api/submissions/{sub_pk}/")
            if sub["status"] in ("finished_grading", "removed_from_queue", "error"):
                results[filename] = sub
                done.append(filename)
        for f in done:
            del pending[f]

    # Fetch test suite results for each finished submission
    print("\nResults:")
    print(f"  {'project':<25} {'status':<20} {'points':<12} {'passed'}")
    print(f"  {'-' * 25} {'-' * 20} {'-' * 12} {'-' * 6}")
    for filename, sub in sorted(results.items()):
        status = sub["status"]
        sub_pk = sub["pk"]

        points_str = "n/a"
        passed_str = "-"
        try:
            results_url = f"/api/submissions/{sub_pk}/results/?feedback_category=normal"
            res = _get(session, base, results_url)
            total = res["total_points"]
            possible = res["total_points_possible"]
            points_str = f"{total}/{possible}"
            passed_str = "✓" if possible > 0 and total == possible else "✗"
        except Exception:
            pass

        print(f"  {filename:<25} {status:<20} {points_str:<12} {passed_str}")


if __name__ == "__main__":
    main()
