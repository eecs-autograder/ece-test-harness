#!/usr/bin/env python
# template2_grader.py
#
# A template file for grading a student SCRIPT called template2.py
#
# NOTE: See template1_grader.py to learn how to grade FUNCTIONs
#
# Brian Moore
# brimoor@umich.edu
#
# January 19, 2016
# January  3, 2017
#
from graderutils import NoStdout, reportTestResults, PASS, FAIL, ERROR

try:
    # Run user script with STDOUT suppressed
    with NoStdout():
        exec(open("template2.py").read())
except:
    # Handle error
    reportTestResults(ERROR)
    raise

# Check results
xCorrect = ('x' in vars()) and (x == 1)
yCorrect = ('y' in vars()) and (y == 2)
testStatus = PASS if (xCorrect and yCorrect) else FAIL

# Generate log file
log = "xCorrect = %d\nyCorrect = %d\n" % (xCorrect, yCorrect)

# Report test results
#   testStatus must be PASS, FAIL, or ERROR
#   log can be an arbitrary string
reportTestResults(testStatus, log=log)
