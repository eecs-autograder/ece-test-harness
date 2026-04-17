#!/usr/bin/env julia
# template2_grader.jl
#
# A template file for grading a student SCRIPT called template2.jl
#
# NOTE: See template1_grader.jl to learn how to grade FUNCTIONs
#
# Brian Moore
# brimoor@umich.edu
#
# January  3, 2017
#
using graderutils: with_NoStdout, include_from_LOAD_PATH, reportTestResults, PASS, FAIL, ERROR
using Printf

try
    # Run user script with STDOUT suppressed
    with_NoStdout() do
        include_from_LOAD_PATH("template2.jl")
    end
catch
    # Handle error
    reportTestResults(ERROR)
    rethrow()
end

# Check results
xCorrect = isdefined(Main, :x) && (x == 1)
yCorrect = isdefined(Main, :y) && (y == 2)
testStatus = xCorrect && yCorrect ? PASS : FAIL

# Generate log file
log = @sprintf("xCorrect = %d\nyCorrect = %d\n", xCorrect, yCorrect)

# Report test results
#   testStatus must be PASS, FAIL, or ERROR
#   log can be an arbitrary string
reportTestResults(testStatus; log=log)
