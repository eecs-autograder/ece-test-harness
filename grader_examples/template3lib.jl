#!/usr/bin/env julia
# template3lib.jl
#
# Example external module dependency for template3
#
# The graders/ directory is added recursively to the path before running user
# submissions and solutions, so this module can be accessed at runtime by any
# standard "import" or "using" command. For example:
#
# using template3lib: add_one
# 
# NOTE: The filename (template3lib.jl) must match the module name (template3lib)
#       exactly because the user does not know the absolute path to this file at
#       runtime and hence can't run include("/path/to/template3lib.jl") 
#
# Brian Moore
# brimoor@umich.edu
#
# January 6, 2017
# February 25, 2017
#
module template3lib

# Add one
function add_one(x)
    return x + 1
end

end
