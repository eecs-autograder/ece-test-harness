import argparse
import os
import re
import sys
from enum import Enum
from subprocess import PIPE, Popen

from .languages import getLanguageByExt
from .utilities import appendPathsToEnvVar

GRADER_POSTFIX = "_grader"
SOLUTION_POSTFIX = "_sol"
BLACKLIST_FILE = "blacklist.txt"
TEST_RESULT_REGEX = "***** RESULTS *****"


class TestStatus(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    ERROR = "error"
    ILLEGAL = "illegal"
    UNKNOWN = "unknown"


def _read_stripped_lines(path, comment_char):
    with open(path) as f:
        lines = [line.strip() for line in f]
    return [line for line in lines if line and not line.startswith(comment_char)]


def _check_blacklist(submission_path, name, lang):
    submission_dir = os.path.dirname(submission_path)
    blacklist_path = os.path.join(submission_dir, BLACKLIST_FILE)

    blacklist = []
    if os.path.isfile(blacklist_path):
        blacklist = _read_stripped_lines(blacklist_path, "#")

    illegal = [name + SOLUTION_POSTFIX] + blacklist
    patt = r"(?<!\w)(%s)(?!\w)" % "|".join(re.escape(tok) for tok in illegal)

    code_lines = _read_stripped_lines(submission_path, lang.COMMENT)
    found = list(set(re.findall(patt, " ".join(code_lines))))
    return found


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Grade a student submission against its corresponding grader and solution files. "
            "The submission directory must contain matching <name>_grader.<ext> and "
            "<name>_sol.<ext> files. Exits with code 0 on pass, 1 otherwise."
        )
    )
    parser.add_argument(
        "submission",
        help="Path to the student submission file (e.g. path/to/hw1/template1.py)",
    )
    args = parser.parse_args()

    submission_path = os.path.abspath(args.submission)
    submission_dir = os.path.dirname(submission_path)
    name, ext = os.path.splitext(os.path.basename(submission_path))
    grader = name + GRADER_POSTFIX

    # Package dir is added to the language path so grader scripts can import graderutils
    pkg_dir = os.path.dirname(os.path.abspath(__file__))
    lang = getLanguageByExt(ext)
    extra = ["@", "@stdlib"] if lang.PATH_ENV == "JULIA_LOAD_PATH" else []
    appendPathsToEnvVar(lang.PATH_ENV, [submission_dir, pkg_dir] + extra)
    os.chdir(submission_dir)

    illegal_keywords = _check_blacklist(submission_path, name, lang)
    if illegal_keywords:
        print(TestStatus.ILLEGAL.value)
        print("Illegal keyword(s) found: %s" % ", ".join(sorted(illegal_keywords)))
        sys.exit(1)

    cmd = lang.RUN_ARGS(grader, submission_dir)
    out, err = Popen(cmd, stdout=PIPE, stderr=PIPE).communicate()

    out = out.decode("utf-8", errors="replace")
    err = err.decode("utf-8", errors="replace")

    stdout = out.rpartition(TEST_RESULT_REGEX)[2]
    vals = stdout.split(None, 1)
    outstr = vals[0] if vals else ""
    log = vals[1].strip() if len(vals) > 1 else ""

    log = re.sub(r"\x1b\[\?1l\x1b>", "", log)

    try:
        status = TestStatus(outstr)
    except ValueError:
        status = TestStatus.UNKNOWN

    print(status.value)
    if log:
        print(log)
    if err:
        print(err.strip(), file=sys.stderr)

    sys.exit(0 if status == TestStatus.PASS else 1)


if __name__ == "__main__":
    main()
