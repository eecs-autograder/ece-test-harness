function template4(x, y=0; z=0)
    return x, 0, 0  # bug: ignores y and z
end
