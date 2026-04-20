FROM eecsautograder/ubuntu24:latest

RUN apt-get update \
    && apt-get install -y python3.12 python3.12-venv curl

USER autograder:autograder

RUN curl -fsSL https://install.julialang.org | sh -s -- -y
ENV PATH="/home/autograder/.juliaup/bin:${PATH}"

RUN python3 -m venv env \
    && env/bin/pip install --upgrade pip setuptools wheel \
    && env/bin/pip install ece-test-harness

USER root:root
