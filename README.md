# ECE Test Harness

Autograding package for Python and Julia submissions. Grades a student submission by running test cases against a reference solution and comparing outputs.

**Note:** MATLAB may be supported but is not currently tested.

## Installation

```bash
pip install ece-test-harness
```

## Grading a submission locally

```bash
ece-grade path/to/submission.py
```

The submission's directory must also contain `<name>_grader.<ext>` and `<name>_sol.<ext>` files. Exits with code 0 on pass, 1 otherwise.

### External dependencies

If a submission depends on a shared library, place the library file in the same directory as the submission, solution, and grader. The harness adds the submission directory to the language path at runtime, so any file there is importable. Students should be given a copy of any required library files for local testing.

### Writing a grader

See `grader_examples/` for complete examples of how to grade functions and scripts.

---

## Course setup on Autograder.io

> **Prerequisites:**
> - An Autograder.io course must already exist for your semester. Course creation is handled by a sysadmin.
> - You must be enrolled as an instructor on the course.
> - The `ag` CLI must be authenticated: run `ag` once and follow the login prompts. Your token will be saved to `~/.agtoken`.

### Local course directory layout

Organize your course directory as follows:

```
my-course/
  schedule.txt          # assignment schedule (see format below)
  graders/
    hw1.py              # student submission stub (or representative file)
    hw1_sol.py          # reference solution
    hw1_grader.py       # grader script
    hw1.jl              # Julia variants (if applicable)
    hw1_sol.jl
    hw1_grader.jl
    hw2.py
    ...
```

All files for a given assignment must share the same base name (e.g. `hw1`). The grader, solution, and any shared library files all live in `graders/`.

### schedule.txt format

```
#
# Column 1: Submission filename (with extension)
# Column 2: Start date  YYYY/MM/DD@HH:MM:SS
# Column 3: Due date    YYYY/MM/DD@HH:MM:SS
# Column 4: Comma-separated keyword blacklist (optional)
#
# Blacklist groups (expand to a list of tokens)
[]=
[PY]=os,sys,subprocess,open
[JL]=run,spawn,eval

hw1.py   2026/01/13@00:00:01   2026/01/20@23:59:59   [PY]
hw1.jl   2026/01/13@00:00:01   2026/01/20@23:59:59   [JL]
hw2.py   2026/01/20@00:00:01   2026/01/27@23:59:59   [PY]
hw2.jl   2026/01/20@00:00:01   2026/01/27@23:59:59   [JL]
```

- Each line defines one Autograder.io project. Python and Julia variants of the same assignment are listed as separate entries.
- The blacklist column is optional and can be omitted for assignments with no restrictions.
- Keyword groups (e.g. `[PY]`) are defined once at the top and reused across entries.
- Individual tokens can be mixed with groups (e.g. `[PY],numpy`).

### Pushing projects to Autograder.io

From your course directory, run:

```bash
ece-init-projects schedule.txt --course "EECS 280" --semester Fall --year 2026
```

Dates in `schedule.txt` are interpreted in your local machine's timezone by default. If your machine is already set to the correct timezone (e.g. `America/Detroit` for an Eastern-time course), no extra flags are needed. If you are running the script from a machine in a different timezone, use `--timezone` to specify the intended IANA timezone explicitly:

```bash
ece-init-projects schedule.txt --course "EECS 280" --semester Fall --year 2026 --timezone America/Detroit
```

This creates one Autograder.io project per submission file found in `graders/` (one per assignment per language). Each project is configured with:
- The correct student file and due date
- The grader and solution uploaded as instructor files
- A `blacklist.txt` instructor file if blacklisted keywords are defined
- A single test suite that runs `ece-grade <submission>`

Re-running the command on an existing course (e.g. after cloning for a new semester) will update deadlines and configuration without recreating projects from scratch. If any projects exist on the server that are not in the schedule file, a warning is printed.

Generated config files are written to `course-configs/` for reference.

### Testing solution files

Once projects are pushed, verify the graders work end-to-end by submitting the reference solution for each assignment:

```bash
ece-test-solutions schedule.txt \
  --course "EECS 280" --semester Fall --year 2026 \
  --username you@umich.edu
```

This submits each `<name>.<ext>` file from the graders directory (the instructor's correct student file) to its corresponding project, polls until grading finishes, and prints a results table:

```
  project     status             points       passed
  ----------- ------------------ ------------ ------
  hw1.py      finished_grading   1/1          ✓
  hw1.jl      finished_grading   1/1          ✓
  hw2.py      finished_grading   1/1          ✓
```

> **Note:** Grading requires a Docker image configured for the course sandbox. Until one is set up, submissions will finish with 0 points. Contact your sysadmin to configure the sandbox image.

### Updating due dates (new semester)

1. Have a sysadmin clone the previous semester's course on Autograder.io.
2. Update `schedule.txt` with the new dates.
3. Re-run `ece-init-projects` with the new `--semester` and `--year`.

---

## Development

```bash
git clone <repo-url>
cd ece-test-harness
python -m venv env
source env/bin/activate
pip install -e ".[dev]"
```

**Versioning:** `YYYY.MM.N` (e.g. `2026.4.0`). Increment `N` for bug fixes and minor changes. Bump the year/month for breaking changes or significant new features — this signals to courses depending on the package that they should review the release before upgrading.

**Run tests:**
```bash
pytest tests/
pytest -m python    # Python only
pytest -m julia     # Julia only
```
