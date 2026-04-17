FROM eecsautograder/ubuntu24:latest

RUN apt-get update \
    && apt-get install -y python3.12 python3.12-venv wget

RUN wget https://julialang-s3.julialang.org/bin/linux/x64/1.10/julia-1.10.4-linux-x86_64.tar.gz \
    && tar -xzf julia-1.10.4-linux-x86_64.tar.gz -C /usr/local --strip-components=1 \
    && rm julia-1.10.4-linux-x86_64.tar.gz

USER autograder:autograder

RUN python3 -m venv env \
    && env/bin/pip install --upgrade pip setuptools wheel \
    && env/bin/pip install ece-test-harness

USER root:root
