"""Tests for output comparison in the Python grading API.

A submission is compared against the solution by zipping their outputs
together, so the two have to agree on how many outputs there are. These pin
that agreement: fewer outputs than the solution must fail rather than compare
only the ones that happen to line up.
"""

import pytest

from ece_test_harness import graderutils


def run_case(user_fcn, sol_fcn, args=(1, 2), tol=0.0):
    return graderutils._runTestCase(graderutils.generateTestCase(args, tol=tol), user_fcn, sol_fcn)


def flip(x, y):
    return (y, x)


def test_matching_outputs_pass() -> None:
    assert run_case(flip, flip)["success"]


def test_wrong_output_still_fails() -> None:
    assert not run_case(lambda x, y: (x, y), flip)["success"]


def test_single_output_pass() -> None:
    assert run_case(lambda x, y: x + y, lambda x, y: x + y)["success"]


# ---------------------------------------------------------------------------
# Output count mismatches
# ---------------------------------------------------------------------------


def test_returns_nothing_reports_output_count() -> None:
    # Previously raised "'NoneType' object is not iterable" out of zip().
    with pytest.raises(ValueError, match=r"Received 0 output\(s\) but expected 2"):
        run_case(lambda x, y: None, flip)


def test_too_few_outputs_does_not_silently_pass() -> None:
    # zip() stops at the shorter of the two, so returning only the outputs that
    # happen to be correct used to pass the test case.
    with pytest.raises(ValueError, match=r"Received 1 output\(s\) but expected 2"):
        run_case(lambda x, y: y, flip)


def test_too_many_outputs_reports_output_count() -> None:
    with pytest.raises(ValueError, match=r"Received 3 output\(s\) but expected 2"):
        run_case(lambda x, y: (y, x, x), flip)


def test_solution_returning_nothing_reports_grader_error() -> None:
    with pytest.raises(ValueError, match="solution function returned no outputs"):
        run_case(flip, lambda x, y: None)
