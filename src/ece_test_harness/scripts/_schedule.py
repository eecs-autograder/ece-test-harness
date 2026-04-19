import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

COMMENT_CHAR = "#"
_GROUP_RE = re.compile(r"^\[([^\[\]]*)\]=(.*)$")
_GROUP_REF_RE = re.compile(r"^\[[^\[\]]*\]$")
_META_RE = re.compile(r"^(\w+)\s*=\s*(.+)$")
SCHEDULE_DATE_FMT = "%Y/%m/%d@%H:%M:%S"
SCHEDULE_DATE_FMT_NO_SECS = "%Y/%m/%d@%H:%M"


def format_ag_date(dt: datetime) -> str:
    return f"{dt.strftime('%b')} {dt.day}, {dt.strftime('%Y %I:%M%p')}"


def _parse_date(s: str) -> datetime | None:
    for fmt in (SCHEDULE_DATE_FMT, SCHEDULE_DATE_FMT_NO_SECS):
        try:
            return datetime.strptime(s, fmt).replace(second=0)
        except ValueError:
            pass
    return None


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


@dataclass
class Assignment:
    filename: str  # full filename, e.g. "hw1.py"
    start_date: datetime | None = None
    end_date: datetime | None = None
    blacklist: list[str] = field(default_factory=list)

    @property
    def name(self) -> str:
        return Path(self.filename).stem

    @property
    def ext(self) -> str:
        return Path(self.filename).suffix


@dataclass
class Schedule:
    course: str | None = None
    semester: str | None = None
    year: int | None = None
    timezone: str = "America/Detroit"
    assignments: list[Assignment] = field(default_factory=list)


def parse_schedule(schedule_path: Path) -> Schedule:
    groups: dict[str, list[str]] = {}
    schedule = Schedule()

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
            m = _META_RE.match(stripped)
            if m:
                key, value = m.group(1).lower(), m.group(2).strip()
                if key == "course":
                    schedule.course = value
                elif key == "semester":
                    schedule.semester = value
                elif key == "year":
                    try:
                        schedule.year = int(value)
                    except ValueError:
                        pass
                elif key == "timezone":
                    schedule.timezone = value
                continue
            parts = stripped.split()
            filename = parts[0]
            start_date = _parse_date(parts[1]) if len(parts) > 1 else None
            end_date = _parse_date(parts[2]) if len(parts) > 2 else None
            blacklist = _expand_blacklist(parts[3], groups) if len(parts) > 3 else []
            schedule.assignments.append(
                Assignment(
                    filename=filename, start_date=start_date, end_date=end_date, blacklist=blacklist
                )
            )

    return schedule
