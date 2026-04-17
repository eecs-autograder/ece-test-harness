import os
import sys


class Matlab:
    NAME = "MATLAB"
    EXT = ".m"
    COMMENT = "%"
    PATH_ENV = "MATLABPATH"

    @staticmethod
    def RUN_ARGS(grader, _):
        matlabcmd = '"%s; exit"' % grader
        return ["matlab", "-nodesktop", "-nojvm", "-nosplash", "-r", matlabcmd]


class Python:
    NAME = "Python"
    EXT = ".py"
    COMMENT = "#"
    PATH_ENV = "PYTHONPATH"

    @staticmethod
    def RUN_ARGS(grader, _):
        return [sys.executable, "-B", "-c", "import %s" % grader]


class Julia:
    NAME = "Julia"
    EXT = ".jl"
    COMMENT = "#"
    PATH_ENV = "JULIA_LOAD_PATH"

    @staticmethod
    def RUN_ARGS(grader, grader_dir):
        graderjl = os.path.join(grader_dir, grader + ".jl")
        return ["julia", "-e", 'include("%s")' % graderjl]


SUPPORTED_LANGUAGES = [
    Matlab,
    Python,
    Julia,
]


def getLanguageByExt(ext):
    try:
        return next(L for L in SUPPORTED_LANGUAGES if L.EXT == ext)
    except StopIteration:
        raise ValueError("Unsupported language extension: %s" % ext)
