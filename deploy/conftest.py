import os
import subprocess
import pytest
import ssh_agent_setup
from datalad.api import install
from datalad.config import ConfigManager

@pytest.fixture(scope="session", autouse=True)
def setup_git(
        username='CNeuromod Bot',
        email='courtois.neuromod@gmail.com'):

    config = ConfigManager()
    config.set('user.name', username, scope='global')
    config.set('user.email', email, scope='global')

    os.makedirs(os.path.join(os.environ['HOME'],'.ssh'), mode=700, exist_ok=True)

    subprocess.call(["bash", '-c', f"ssh-keyscan -H github.com | install -m 600 /dev/stdin /{os.environ['HOME']}/.ssh/known_hosts"])

    ssh_agent_setup.setup()
    # add bot ssh key
    process = subprocess.run(['ssh-add', '-'], input=os.environ['SECRET_KEY'].encode())
    assert process.returncode == 0, 'fail to pass the ssh key to e'


@pytest.fixture(scope="session")
def dataset():
    ds = install(f"git@github.com:{os.environ['GITHUB_REPOSITORY']}.git")
    ds.repo.checkout(os.environ['GITHUB_SHA'])
    return ds
