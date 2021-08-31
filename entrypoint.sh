#!/bin/bash

git config --global user.name "$1"
git config --global user.email "$2"

# Create ~/.ssh folder
mkdir -p /root/.ssh
chmod 700 /root/.ssh

# Ease github.com checking
# echo -e "Host github.com\n\tStrictHostKeyChecking no\n" | install -m 600 /dev/stdin /root/.ssh/config

# Create key file, with permissions
echo "${SECRET_KEY}" | install -m 600 /dev/stdin /root/.ssh/id_rsa

# Add github as trusted host
ssh-keyscan -t rsa -H github.com | install -m 600 /dev/stdin /root/.ssh/known_hosts

# Start ssh agent
eval "$(ssh-agent -s)"

# Add key to ssh agent
ssh-add - <<< "${SECRET_KEY}"

datalad install git@github.com:templateflow/templateflow.git
cd templateflow/
datalad install ${GITHUB_REPOSITORY##*/}
datalad update -r --merge any .
datalad save -m "auto(${GITHUB_REPOSITORY##*/}): content update"
datalad push --to origin
