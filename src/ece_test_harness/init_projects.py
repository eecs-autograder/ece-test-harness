import argparse
import json
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import yaml
from tzlocal import get_localzone_name

COMMENT_CHAR = "#"
_GROUP_RE = re.compile(r"^\[([^\[\]]*)\]=(.*)$")
_GROUP_REF_RE = re.compile(r"^\[[^\[\]]*\]$")

SCHEDULE_DATE_FMT = "%Y/%m/%d@%H:%M:%S"


def _format_ag_date(dt: datetime) -> str:
    return f"{dt.strftime('%b')} {dt.day}, {dt.strftime('%Y %I:%M%p')}"


@dataclass
class Assignment:
    filename: str  # full filename, e.g. "hw1.py"
    end_date: datetime | None = None
    blacklist: list[str] = field(default_factory=list)

    @property
    def name(self) -> str:
        return Path(self.filename).stem

    @property
    def ext(self) -> str:
        return Path(self.filename).suffix


def _expand_blacklist(raw: str, groups: dict[str, list[str]]) -> list[str]:
    tokens: list[str] = []
    for chunk in raw.split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        if _GROUP_REF_RE.match(chunk):
            tokens.extend(groups.get(chunk, []))
        else:
            tokens.append(chunk)
    return tokens


def _parse_schedule(schedule_path: Path) -> list[Assignment]:
    groups: dict[str, list[str]] = {}
    assignments: list[Assignment] = []

    with open(schedule_path) as f:
        for line in f:
            stripped = line.strip()
            if not stripped or stripped.startswith(COMMENT_CHAR):
                continue
            m = _GROUP_RE.match(stripped)
            if m:
                key = f"[{m.group(1)}]"
                groups[key] = _expand_blacklist(m.group(2), groups)
                continue
            parts = stripped.split()
            filename = parts[0]
            end_date = None
            if len(parts) > 2:
                try:
                    end_date = datetime.strptime(parts[2], SCHEDULE_DATE_FMT)
                except ValueError:
                    pass
            blacklist = _expand_blacklist(parts[3], groups) if len(parts) > 3 else []
            assignments.append(
                Assignment(filename=filename, end_date=end_date, blacklist=blacklist)
            )

    return assignments


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Generate Autograder.io project config files from a schedule file. "
            "One project is created per line in the schedule file. "
            "Configs are written to course-configs/<filename>/ in the current directory."
        )
    )
    parser.add_argument("schedule", help="Path to schedule.txt")
    parser.add_argument(
        "--graders",
        default="graders",
        help="Path to the graders directory (default: graders/)",
    )
    parser.add_argument("--course", required=True, help="Course name, e.g. 'EECS 280'")
    parser.add_argument("--semester", required=True, help="Semester term, e.g. 'Fall'")
    parser.add_argument("--year", required=True, help="Year, e.g. '2024'")
    parser.add_argument(
        "--timezone",
        default=None,
        help=(
            "IANA timezone name for deadline interpretation, e.g. 'America/Detroit'. "
            "Defaults to the local machine timezone. "
            "Dates in schedule.txt are assumed to be in this timezone."
        ),
    )
    args = parser.parse_args()

    timezone = args.timezone or get_localzone_name()

    schedule_path = Path(args.schedule)
    graders_dir = Path(args.graders)
    out_dir = Path("course-configs")

    if not schedule_path.is_file():
        sys.exit(f"error: schedule file not found: {schedule_path}")
    if not graders_dir.is_dir():
        sys.exit(f"error: graders directory not found: {graders_dir}")

    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir()

    assignments = _parse_schedule(schedule_path)
    if not assignments:
        sys.exit("error: no assignments found in schedule file")

    for assignment in assignments:
        submission = assignment.filename
        name = assignment.name
        ext = assignment.ext
        project_dir = out_dir / submission
        project_dir.mkdir()
        config_file = project_dir / "agproject.yml"

        # Copy instructor files into the project directory
        instructor_filenames: list[str] = []
        for suffix in ("_grader", "_sol"):
            src = graders_dir / f"{name}{suffix}{ext}"
            if src.is_file():
                shutil.copy(src, project_dir / src.name)
                instructor_filenames.append(src.name)
            else:
                print(
                    f"warning: instructor file not found: {src}",
                    file=sys.stderr,
                )

        # Copy additional dependency files (e.g. template3lib.py for template3.py)
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
                args.course,
                args.semester,
                args.year,
                submission,
                "--config_file",
                str(config_file),
            ],
            check=True,
        )

        with open(config_file) as f:
            config = yaml.safe_load(f)

        config["project"]["timezone"] = timezone

        if assignment.end_date:
            config["project"]["settings"]["deadline"] = {
                "cutoff_type": "relative",
                "deadline": _format_ag_date(assignment.end_date),
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
                    }
                ],
            }
        ]
        config["project"]["mutation_suites"] = []
        config["project"]["handgrading"] = None

        with open(config_file, "w") as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False)

        subprocess.run(
            ["ag", "project", "save", "--config_file", str(config_file)],
            check=True,
        )

        print(f"created and saved {config_file}")

    # Warn about projects on the server not present in the schedule
    expected = {a.filename for a in assignments}
    try:
        courses = json.loads(
            subprocess.run(
                ["ag", "http", "get", "/api/courses/"],
                capture_output=True,
                text=True,
                check=True,
            ).stdout
        )
        course = next(
            (
                c
                for c in courses
                if c["name"] == args.course
                and c.get("semester") == args.semester
                and str(c.get("year")) == str(args.year)
            ),
            None,
        )
        if course:
            server_projects = {
                p["name"]
                for p in json.loads(
                    subprocess.run(
                        ["ag", "http", "get", f"/api/courses/{course['pk']}/projects/"],
                        capture_output=True,
                        text=True,
                        check=True,
                    ).stdout
                )
            }
            for name in sorted(server_projects - expected):
                print(
                    f"warning: project '{name}' exists on server but is not in the schedule file",
                    file=sys.stderr,
                )
    except Exception as e:
        print(f"warning: could not check server for orphaned projects: {e}", file=sys.stderr)


if __name__ == "__main__":
    main()
