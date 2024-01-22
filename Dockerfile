# Container image that runs your code
FROM ghcr.io/courtois-neuromod/datalad:alpine

ADD . /actions
WORKDIR /actions

# Code file to execute when the docker container starts up (`entrypoint.sh`)
ENTRYPOINT ["pytest", "-s", "-o", "log_cli=true", "/actions/tests"]
