#!/usr/bin/env julia
# template3.jl
#
# Template user function that uses an external module
#
# Brian Moore
# brimoor@umich.edu
#
# January 6, 2017
# February 25, 2017
#
using template3lib: add_one

# Add one
function template3(x)
    return add_one(x)
end
