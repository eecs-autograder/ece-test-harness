#!/usr/bin/env julia
# template4_grader.jl
#
# A template file for grading a student function called template4.jl with
# optional positional and keyword arguments against the solution file
# template4_sol.jl
#
# Brian Moore
# brimoor@umich.edu
#
# November 10, 2017
#
using graderutils: generateTestCase, runTestCases

# Error tolerance when comparing outputs
tol = 1e-12

# Create test case(s)
testCases = []
push!(testCases,generateTestCase(1; tol=tol))
push!(testCases,generateTestCase((1, 2); tol=tol))
push!(testCases,generateTestCase((1, 2); kwargs=((:z, 3),), tol=tol))

# Run test cases
runTestCases(testCases, @__FILE__)
