%
% template2_grader.m
%
% A template file for grading a student SCRIPT called template2.m
%
% NOTE: See template1_grader.m to learn how to grade FUNCTIONs
%
% Brian Moore
% brimoor@umich.edu
%
% January 19, 2016
% January  3, 2017
%

try
    % Run user script with STDOUT suppressed
    evalc('template2');
catch e
    % Handle error
    graderutils.reportTestResults(graderutils.ERROR);
    rethrow(e);
end

% Check results
xCorrect = exist('x','var') && (x == 1);
yCorrect = exist('y','var') && (y == 2);
if xCorrect && yCorrect
    testStatus = graderutils.PASS;
else
    testStatus = graderutils.FAIL;
end

% Generate log file
log = sprintf('xCorrect = %d\nyCorrect = %d\n', xCorrect, yCorrect);

% Report test results
%   testStatus must be PASS, FAIL, or ERROR
%   log can be an arbitrary string
graderutils.reportTestResults(testStatus, log);
