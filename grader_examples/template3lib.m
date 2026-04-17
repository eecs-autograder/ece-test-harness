%
% template3lib.m
%
% Example external module dependency for template3
%
% The graders/ directory is added recursively to the path before running
% user submissions and solutions, so this module can be accessed at runtime
% by calling the methods directory
% 
% NOTE: Here we mimic modules in Python/Julia by wrapping (static) methods
%       in a class, but one can simply include each function in separate
%       files (e.g., add_one.m) if desired
%
% Brian Moore
% brimoor@umich.edu
%
% January 6, 2017
% February 25, 2017
%
classdef template3lib
    methods (Access = public, Static = true)

        % Add one
        function y = add_one(x)
            y = x + 1;
        end

    end
end
