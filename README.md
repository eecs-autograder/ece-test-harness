# ECE Test Harness

A test harness made for ECE classes at UM that want to migrate from Brian Moore's autograder software to [Autograder.io](autograder.io) while making minimal changes to their course materials.

**Note:** MATLAB support is not available on Autograder.io due to licensing constraints. The MATLAB code path is retained in the codebase for potential future use (e.g. via Octave), but is untested.

## Installation

```bash
pip install ece-test-harness
```

## Grading a submission locally

```bash
ece-grade path/to/submission.py
```

The submission's directory must also contain `<name>_grader.<ext>` and `<name>_sol.<ext>` files. Exits with code 0 on pass, 1 otherwise.

The first line of output is one of the following status values:

| Status | Meaning |
|--------|---------|
| `pass` | All test cases passed |
| `fail` | One or more test cases failed |
| `error` | The grader or submission raised an unhandled exception |
| `illegal` | A blacklisted keyword was found in the submission; grader was not run |
| `unknown` | The grader produced output that could not be parsed |

A log with per-test details follows the status line when available.

### External dependencies

If a submission depends on a shared library, place the library file in the same directory as the submission, solution, and grader. The harness adds the submission directory to the language path at runtime, so any file there is importable. Students should be given a copy of any required library files for local testing.

### Writing a grader

See `grader_examples/` for complete examples of how to grade functions and scripts.

---

## Course setup on Autograder.io

> **Prerequisites:**
> - An Autograder.io course must already exist for your semester. Course creation can be handled by you cloning a previous semester's course, or by a sysadmin if it's a new course.
> - You must be enrolled as an admin on the course.
> - The `ag` CLI must be authenticated: run `ag` once and follow the login prompts. Your token will be saved to `~/.agtoken`.

### Local course directory layout

It is suggested to organize your course directory as follows:

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
course   = EECS 551
semester = Fall
year     = 2026
timezone = America/Detroit   # optional, defaults to America/Detroit

#
# Column 1: Submission filename (with extension)
# Column 2: Start date  YYYY/MM/DD@HH:MM  (seconds optional, ignored if present)
# Column 3: Due date    YYYY/MM/DD@HH:MM  (seconds optional, ignored if present)
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

- `course`, `semester`, and `year` are required; all `ece-*` scripts read them from this file.
- `timezone` is an IANA timezone name used for interpreting dates; defaults to `America/Detroit`.
- Each assignment line defines one Autograder.io project.
- The blacklist column is optional and can be omitted for assignments with no restrictions.
- Keyword groups (e.g. `[PY]`) are defined once at the top and reused across entries.
- Individual tokens can be mixed with groups (e.g. `[PY],numpy`).

### Building the sandbox image for your course on Autograder.io

Navigate to "Course settings" > "Sandbox Images". If your course was cloned from a previous semester, you should see "ece-autograder" under "Images" and you don't have to do anything. If this is the first semester using Autograder.io for this course, you'll have to build the image. Click "Choose files to upload" and select the Dockerfile in this repo, and then click "Build". This will take some time. Once it's built, you'll see a new image under "Images". Click the new image and change the name to "ece-autograder".

#### Using custom sandbox images

The "ece-autograder" image is an Ubuntu 24.04 image that comes with Python 3.12 (with numpy) and Julia 1.10 installed, along with this package. If you need additional dependencies for your assignments, you can modify the Dockerfile in this repo accordingly and use the modified file to build the image on Autograder.io. If you do alter the Dockerfile, it's recommended to still name the image "ece-autograder" to be compatible with the `ece-configure-projects` script below.

### Setting up projects on Autograder.io

Project setup is a two-step process, which allows you to review and customize the generated config files before pushing them to the server.

**Step 1 — generate config files locally:**

```bash
ece-configure-projects schedule.txt
```

For each assignment in `schedule.txt` that does not already have a config, this creates `course-configs/<filename>/agproject.yml` with sane defaults:
- The correct student file and due date
- The grader and solution as instructor files
- A `blacklist.txt` instructor file if blacklisted keywords are defined
- A single test suite that runs `ece-grade <submission>`

Assignments with no matching grader files in `graders/` produce a warning and are skipped. Assignments that already have a config are skipped silently, so it is safe to re-run after adding new assignments without affecting existing configs.

If your grader files are not in a directory named `graders/`, use `--graders <path>`.

You can edit any `agproject.yml` to customize per-project settings before pushing. To regenerate a config from scratch (discarding manual edits), use `--overwrite`.

#### Overriding defaults

Two flags let you adjust the defaults applied to every new config without editing each file manually.

**`--project-settings-defaults <file>`** — merges the given YAML into the project settings block. Example:

```yaml
# project-settings-overrides.yml
send_email_receipts: true   # send students an email confirmation on each submission
total_submission_limit: 1   # cap total submissions across the entire deadline period
```

**`--test-case-defaults <file>`** — merges the given YAML into the test case. `name` and `cmd` are not allowed. Example:

```yaml
# test-case-defaults.yml
return_code:
  expected: zero
  points: 2
feedback:
  normal: private                    # hide results from students during the grading period
  final_graded_submission: public    # show full results on the final graded submission
```

Invalid field names in either file are caught at config generation time. See the [Autograder.io API docs](https://autograder.io/api/docs/) for a full reference of available fields and values.

Example invocation with both overrides:

```bash
ece-configure-projects --project-settings-defaults project-settings-overrides.yml \
                       --test-case-defaults test-case-defaults.yml
```

**Step 2 — push configs to Autograder.io:**

```bash
ece-save-projects schedule.txt
```

This calls `ag project save` for each config in `course-configs/`, creating projects that don't exist yet and updating those that do. If any projects exist on the server that are not in the schedule file, a warning is printed.

Before pushing each config, `ece-save-projects` stamps in the current `deadline` and `timezone`, as well as the `course`, `year`, and `semester` fields from the schedule file so those fields are always authoritative from the schedule file regardless of what's in the YAML. All other fields in the YAML are left as-is, so per-project customizations are preserved across runs.

For a new semester, update `semester`, `year`, and the dates in `schedule.txt` and re-run `ece-save-projects` — no need to regenerate configs unless the graders or test setup changed. To add a new assignment mid-semester, add it to `schedule.txt` and run `ece-configure-projects` to generate only its config, then `ece-save-projects` to push everything.

### Testing solution files

Once projects are pushed, verify the graders work end-to-end by submitting the reference solution for each assignment:

**Note:** Staff and admins can always submit, even if the project isn't published to students

```bash
ece-test-solutions schedule.txt
```

Optional flags:
- `--graders <path>` — path to grader files if not `graders/`
- `--base-url <url>` — Autograder.io base URL (default: `https://autograder.io`)
- `--token-file <path>` — path to AG token file (default: `~/.agtoken`)

This submits each `<name>.<ext>` file from the graders directory (the instructor's correct student file) to its corresponding project, polls until grading finishes, and prints a results table:

```
  project     status             points       passed
  ----------- ------------------ ------------ ------
  hw1.py      finished_grading   1/1          ✓
  hw1.jl      finished_grading   1/1          ✓
  hw2.py      finished_grading   1/1          ✓
```

### Publishing projects throughout the semester

Autograder.io projects are not visible to students until published. Run the following command to publish any projects whose start date has passed and reveal final grades for any projects whose due date has passed:

```bash
ece-publish-projects schedule.txt
```

For each project:
- If the current time is past the **start date**, `visible_to_students` is set to `True`.
- If the current time is past the **due date**, `hide_ultimate_submission_fdbk` is set to `False` (revealing final grades). Before doing this, the script verifies that the project's `closing_time` on the server matches the due date in `schedule.txt` — if they differ, the grade publish is skipped with a warning so you can investigate before proceeding.

Use `--dry-run` to preview what would change without making any API calls.

This command takes no additional flags beyond `--dry-run` and the optional `schedule` positional argument.

This command is safe to re-run; projects already in the correct state are left unchanged.

### Updating due dates (new semester)

1. Have a sysadmin clone the previous semester's course on Autograder.io.
2. Update `schedule.txt` with the new `semester`, `year`, and dates.
3. Run `ece-save-projects schedule.txt` to push the updated dates — existing configs are preserved and the deadline is always taken from `schedule.txt`.

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

**Run linting and type checks:**
```bash
bash lint.sh
```

**Run tests:**
```bash
pytest tests/
pytest -m python    # Python only
pytest -m julia     # Julia only
```
