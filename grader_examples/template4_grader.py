#!/usr/bin/env python
# template4_grader.py
#
# A template file for grading a student function called template4.py with
# optional keyword arguments against the solution file template4_sol.py
#
# Brian Moore
# brimoor@umich.edu
#
# November 10, 2017
#
from graderutils import generateCheck,generateTestCase,runTestCases

# Error tolerance when comparing outputs
tol = 1e-12

# Create test case(s)
testCases = []
testCases.append(generateTestCase(1, tol=tol))
testCases.append(generateTestCase(1, kwargs={'y': 2}, tol=tol))
testCases.append(generateTestCase(1, kwargs={'y': 2, 'z': 3}, tol=tol))

# Run test cases
runTestCases(testCases, __file__)
