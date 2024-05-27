import os
import pytest
from . import utils

import logging
logger = logging.getLogger(__name__)

# check for https://github.com/datalad/datalad/issues/7604
# has to run first, before `setup_ssh`
@pytest.mark.order(1)
def test_get_submodules_https_parent(dataset_https):
    dataset_https.get('.', recursive=True, recursion_limit=1, get_data=False)

def test_get_submodules(dataset):
    dataset.get('.', recursive=True, recursion_limit=1, get_data=False)

def test_autoenable(dataset):
    siblings = dataset.siblings()
    sibling_names = [sib['name'] for sib in siblings]
    assert not any('sensitive' in sn for sn in sibling_names), 'Sensitive sibling is autoenabled'
    #assert any('mri' in sn for sn in sibling_names), 'MRI sibling is not autoenabled'
    ora_siblings = [sib for sib in siblings if
        sib.get('annex-type', None)=='external' and
        sib['annex-externaltype']=='ora' and
        not sib.get('annex-httpalso', None) == 'true']
    ora_siblings_names = list(sib['name'] for sib in ora_siblings)
    assert len(ora_siblings) == 0, f"ORA remotes {','.join(ora_siblings_names)} are autoenabled"

def test_files_in_remote(dataset):
    ds_repo = dataset.repo

    public_siblings = get_public_siblings(dataset)
    #sensitive_siblings = [sn for sn in sibling_names if 'sensitive' in sn]
    #assert len(sensitive_siblings) == 0, 'sensitive data remote is not expected to be enabled'

    # check that shared files are listed on the share remote
    for public_sibling in public_siblings:
        logger.info(f"checking file availability in {public_sibling}")
        wanted_opts = utils.expr_to_opts(public_sibling.get('annex-wanted'))

        shared_files_missing = list(ds_repo.call_annex_items_([
            'find', '--not', '--metadata', 'distribution-restrictions=*',
            '--not', '--in',  public_sibling['name']] + wanted_opts))
        assert len(shared_files_missing) == 0, f"Files missing in shared remote { public_sibling['name']}: \n{shared_files_missing}"

        # check all files are in the shared remote
        fsck_res = ds_repo.fsck(remote=public_sibling['name'], fast=True)
        assert len(fsck_res) > 0, f"git-annex fsck did not give any result, check that remote exists"
        fsck_fails = [fr for fr in fsck_res if not fr['success']]
        assert len(fsck_fails) == 0, f"git-annex fsck on {public_sibling} failed: {fsck_fails}"

        # check that sensitive files are not in the shared remote
        sensitive_files_shared = list(ds_repo.call_annex_items_([
            'find', '--metadata', 'distribution-restrictions=*',
            '--in', public_sibling['name']]))
        assert len(sensitive_files_shared) == 0, f"Sensitive files mistakenly shared: \n{sensitive_files_shared}"


def get_public_siblings(dataset):
    siblings = dataset.siblings()
    public_siblings = [sib for sib in siblings if not sib.get('annex-ignore', False) and sib['name']!='here']
    #sibling_names = [sib['name'] for sib in public_siblings]
    #mri_siblings = [sn for sn in sibling_names if sn.split('.')[-1] == 'mri']
    if len(dataset.repo.get_annexed_files()) > 0:
        assert len(public_siblings) > 0 , 'at least 1 public remote is required'
    return public_siblings
