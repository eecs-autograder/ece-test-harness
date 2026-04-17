import os


def appendPathsToEnvVar(envVar, newPaths):
    if envVar in os.environ:
        currPath = [os.environ[envVar].strip(os.pathsep)]
    else:
        currPath = []
    os.environ[envVar] = os.pathsep.join(currPath + newPaths)
