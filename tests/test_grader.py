import shutil
import subprocess
import sys
from contextlib import contextmanager
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
GRADERS = ROOT / "grader_examples"


TEMPLATES = [
    pytest.param("template1", ".py", marks=pytest.mark.python),
    pytest.param("template2", ".py", marks=pytest.mark.python),
    pytest.param("template3", ".py", marks=pytest.mark.python),
    pytest.param("template4", ".py", marks=pytest.mark.python),
    pytest.param("template1", ".jl", marks=pytest.mark.julia),
    pytest.param("template2", ".jl", marks=pytest.mark.julia),
    pytest.param("template3", ".jl", marks=pytest.mark.julia),
    pytest.param("template4", ".jl", marks=pytest.mark.julia),
]


@pytest.mark.parametrize("name,ext", TEMPLATES)
def test_pass(name, ext):
    status, _, code = run_grader(str(GRADERS / f"{name}{ext}"))
    assert status == "pass"
    assert code == 0


@pytest.mark.parametrize("name,ext", TEMPLATES)
def test_fail(name, ext):
    with buggy_submission(name, ext):
        status, _, code = run_grader(str(GRADERS / f"{name}{ext}"))
    assert status == "fail"
    assert code != 0


@pytest.mark.parametrize(
    "name,ext,tokens",
    [
        pytest.param("template1", ".py", ["os"], marks=pytest.mark.python),
        pytest.param("template1", ".jl", ["run"], marks=pytest.mark.julia),
    ],
)
def test_illegal_keywords(name, ext, tokens):
    with blacklisted_submission(name, ext, tokens):
        status, stdout, code = run_grader(str(GRADERS / f"{name}{ext}"))
    assert status == "illegal"
    assert code != 0
    for token in tokens:
        assert token in stdout


def run_grader(submission_path: str) -> tuple[str, str, int]:
    result = subprocess.run(
        [sys.executable, "-m", "ece_test_harness.main", submission_path],
        capture_output=True,
        text=True,
    )
    first_line = result.stdout.strip().split("\n")[0] if result.stdout.strip() else ""
    return first_line, result.stdout, result.returncode


@contextmanager
def buggy_submission(name: str, ext: str):
    """Swap <name><ext> with <name>_buggy<ext> for the duration of the block."""
    original = GRADERS / f"{name}{ext}"
    buggy = GRADERS / f"{name}_buggy{ext}"

    original_content = original.read_text()
    buggy_content = buggy.read_text()

    shutil.copy(buggy, original)
    try:
        yield
    finally:
        original.write_text(original_content)
        buggy.write_text(buggy_content)


@contextmanager
def blacklisted_submission(name: str, ext: str, tokens: list[str]):
    """Swap <name><ext> with <name>_blacklisted<ext> and write blacklist.txt."""
    original = GRADERS / f"{name}{ext}"
    blacklisted = GRADERS / f"{name}_blacklisted{ext}"
    blacklist_file = GRADERS / "blacklist.txt"

    original_content = original.read_text()
    shutil.copy(blacklisted, original)
    blacklist_file.write_text("\n".join(tokens) + "\n")
    try:
        yield
    finally:
        original.write_text(original_content)
        blacklist_file.unlink(missing_ok=True)
