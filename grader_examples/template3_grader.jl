#!/usr/bin/env julia
# template3_grader.jl
#
# A template file for grading student function called template3.jl against
# the solution file template3_sol.jl
#
# Brian Moore
# brimoor@umich.edu
#
# January 6, 2017
#
using graderutils: generateTestCase, runTestCases

# Create test case(s)
testCases = [generateTestCase(0)]

# Run test cases
runTestCases(testCases, @__FILE__)
