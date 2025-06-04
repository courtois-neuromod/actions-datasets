import os
import tempfile
import subprocess
import platform
import pytest
import ssh_agent_setup
from datalad.api import install
from datalad.config import ConfigManager
from datalad.log import no_progress

GIT_ANNEX_TEST_BRANCH='dev'

import logging
logger = logging.getLogger(__name__)

@pytest.fixture(scope="session", autouse=True)
def setup_git(
        username=os.environ['GIT_USERNAME'],
        email=os.environ['GIT_EMAIL']
    ):

    config = ConfigManager()
    config.set('user.name', username, scope='global')
    config.set('user.email', email, scope='global')
    config.set('annex.security.allowed-ip-addresses', '10.10.10.25', scope='global')

@pytest.fixture(scope="session")
def setup_ssh():
    if platform.system() == "Windows":
        return
    os.makedirs(os.path.join(os.environ['HOME'],'.ssh'), mode=700, exist_ok=True)

    subprocess.call(["sh", '-c', f"ssh-keyscan -H github.com | install -m 600 /dev/stdin /{os.environ['HOME']}/.ssh/known_hosts"])

    ssh_agent_setup.setup()
    # ensure a single line return at the end of the key
    secret_key = os.environ['SECRET_KEY'].rstrip('\n')+"\n"
    # add bot ssh key
    process = subprocess.run(['ssh-add', '-'], input=secret_key.encode())
    assert process.returncode == 0, 'fail to pass the ssh key to ssh-agent'


@pytest.fixture(scope="session")
def dataset(setup_git, setup_ssh):
    yield from install_ds(protocol='ssh')

def install_ds(protocol='ssh'):
    url = f"git@github.com:{os.environ['GITHUB_REPOSITORY']}.git"
    if protocol=='https':
        username_token=""
        if 'GIT_TOKEN' in os.environ:
            username_token = f"{os.environ['GIT_TOKEN']}@"
        url = f"https://{username_token}github.com/{os.environ['GITHUB_REPOSITORY']}.git"
    dest = tempfile.TemporaryDirectory(prefix=f"ds_{protocol}")
    with no_progress():
        ds = install(path=dest.name, source=url)
    if 'git-annex' in os.environ['GITHUB_HEAD_REF']:
        with no_progress():
            ds.repo.fetch('origin', GIT_ANNEX_TEST_BRANCH)
        logger.info(f"testing git-annex branch changes: checking out {GIT_ANNEX_TEST_BRANCH}")
        ds.repo.checkout(GIT_ANNEX_TEST_BRANCH)
    else:
        with no_progress():
            ds.repo.fetch('origin', os.environ['GITHUB_SHA'])
        ref_name = os.environ['GITHUB_REF'].replace('refs/','')
        logger.info(f"checking out {ref_name}")
        ds.repo.checkout(os.environ['GITHUB_SHA'])
        #logger.info(f"resetting branch to {os.environ['GITHUB_SHA']}")
        #ds.repo.call_git(["reset", "--hard", os.environ['GITHUB_SHA']])

    yield ds
    ds.drop(reckless='kill', recursive=True) #teardown

@pytest.fixture(scope="function")
def dataset_https():
    yield from install_ds(protocol="https")
