%
% template4_grader.m
%
% A template file for grading a student function called template4.m with
% optional arguments against the solution file template4_sol.m
%
% Brian Moore
% brimoor@umich.edu
%
% November 10, 2017
%

% Error tolerance when comparing outputs
tol = 1e-12;

% Create test case(s)
testCases(1) = graderutils.generateTestCase({1}, tol);
testCases(2) = graderutils.generateTestCase({1, 2}, tol);
testCases(3) = graderutils.generateTestCase({1, 2, 3}, tol);

% Run test cases
graderutils.runTestCases(testCases, mfilename());
