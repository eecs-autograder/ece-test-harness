#!/usr/bin/env julia
# template1_grader.jl
#
# A template file for grading student FUNCTION called template1.jl against
# the solution file template1_sol.jl
#
# NOTE: See template2_grader.jl to learn how to grade SCRIPTS
#
# Brian Moore
# brimoor@umich.edu
#
# January 3, 2017
#
using graderutils: generateCheck, generateTestCase, runTestCases

# Error tolerance when comparing outputs
tol = 1e-12

# Create test case(s)
testCases = []
push!(testCases,generateTestCase((1, 2); tol=tol))

# Add test case(s) with custom output argument checks
isReal(y) = isreal(y)
noNans(x) = !any(isnan(x))
checks = [generateCheck(isReal, 1, "y must be real"),
          generateCheck(noNans, 2, "x must not contain NaNs")]
push!(testCases,generateTestCase((3, 4); tol=tol, checks=checks))

# Run test cases
runTestCases(testCases, @__FILE__)
