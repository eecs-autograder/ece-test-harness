%
% template1_grader.m
%
% A template file for grading student FUNCTION called template1.m against
% the solution file template1_sol.m
%
% NOTE: See template2_grader.m to learn how to grade SCRIPTS
%
% Brian Moore
% brimoor@umich.edu
%
%   January 19, 2016
% September 15, 2016
%   January  3, 2017
%

% RMSE tolerance when comparing outputs
tol = 1e-12;

% Create test case(s)
testCases(1) = graderutils.generateTestCase({1, 2}, tol);

% Add test case(s) with custom output argument checks
isReal = @(y) isreal(y);
noNans = @(x) ~any(isnan(x));
checks(1) = graderutils.generateCheck(isReal, 1, 'y must be real');
checks(2) = graderutils.generateCheck(noNans, 2, 'x must not be NaN');
testCases(2) = graderutils.generateTestCase({3, 4}, tol, checks);

% Run test cases
graderutils.runTestCases(testCases, mfilename());
