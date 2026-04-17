using template3lib: add_one

function template3(x)
    return add_one(x) + 1  # bug: off by one
end
