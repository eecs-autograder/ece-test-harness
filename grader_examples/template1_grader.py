#!/usr/bin/env python
# template1_grader.py
#
# A template file for grading student FUNCTION called template1.py against
# the solution file template1_sol.py
#
# NOTE: See template2_grader.py to learn how to grade SCRIPTS
#
# Brian Moore
# brimoor@umich.edu
#
#   January 19, 2016
# September 15, 2016
#   January  3, 2017
#
from graderutils import generateCheck,generateTestCase,runTestCases
import numpy as np

# Error tolerance when comparing outputs
tol = 1e-12

# Create test case(s)
testCases = []
testCases.append(generateTestCase((1, 2), tol=tol))

# Add test case(s) with custom output argument checks
isReal = lambda y: np.isrealobj(y)
noNans = lambda x: not any(np.isnan(x if not np.isscalar(x) else [x]))
checks = [generateCheck(isReal, 1, "y must be real"),
          generateCheck(noNans, 2, "x must not contain NaNs")]
testCases.append(generateTestCase((3, 4), tol=tol, checks=checks))

# Run test cases
runTestCases(testCases, __file__)
