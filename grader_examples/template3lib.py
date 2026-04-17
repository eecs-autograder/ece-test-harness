#!/usr/bin/env python
# template3lib.py
#
# Example external module dependency for template3
#
# The graders/ directory is added recursively to the path before running user
# submissions and solutions, so this module can be accessed at runtime by any
# standard "import" command. For example:
#
# from template3lib import add_one
# 
# Brian Moore
# brimoor@umich.edu
#
# January 6, 2017
# February 25, 2017
#

# Add one
def add_one(x):
    return x + 1
