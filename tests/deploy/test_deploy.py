import os
import pytest
import pytest_order
import utils

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
    assert not any('sensitive' in sn for sn in sibling_names), '🚨 Sensitive sibling is autoenabled'
    #assert any('mri' in sn for sn in sibling_names), 'MRI sibling is not autoenabled'
    ora_siblings = [sib for sib in siblings if
        sib.get('annex-type', None)=='external' and
        sib['annex-externaltype']=='ora' and
        not sib.get('annex-httpalso', None) == 'true']
    ora_siblings_names = list(sib['name'] for sib in ora_siblings)
    assert len(ora_siblings) == 0, f"💣 ORA remotes {','.join(ora_siblings_names)} are autoenabled"

def test_files_in_remote(dataset):
    ds_repo = dataset.repo

    public_siblings = get_public_siblings(dataset)
    #sensitive_siblings = [sn for sn in sibling_names if 'sensitive' in sn]
    #assert len(sensitive_siblings) == 0, 'sensitive data remote is not expected to be enabled'

    # check that shared files are listed on the share remote
    for public_sibling in public_siblings:
        logger.info(f"⏳️ checking file availability in {public_sibling['name']}")
        logger.debug(public_sibling['name'])
        sibling_wanted = public_sibling.get('annex-wanted')
        if sibling_wanted == 'groupwanted':
            sibling_group = ds_repo.call_annex_oneline(['group', public_sibling['name']])
            sibling_wanted = ds_repo.get_groupwanted(sibling_group)
        wanted_opts = utils.expr_to_opts(sibling_wanted)

        shared_files_missing = list(ds_repo.call_annex_items_([
            'find', '--not', '--metadata', 'distribution-restrictions=*',
            '--not', '--in',  public_sibling['name']] + wanted_opts))
        assert len(shared_files_missing) == 0, f"💥 Files missing in shared remote { public_sibling['name']}: \n{shared_files_missing}"

        if public_sibling.get('annex-type') == 's3' and not public_sibling.get("annex-public",None)=="yes":
            assert len(os.environ.get('AWS_ACCESS_KEY_ID')) > 0, "	🗝️ missing AWS_ACCESS_KEY_ID"
            assert len(os.environ.get('AWS_SECRET_ACCESS_KEY')) > 0, "	🗝️ missing AWS_SECRET_ACCESS_KEY"

        # check for 30sec
        quick_fsck_res = ds_repo.fsck(remote=public_sibling['name'], fast=True, annex_options=["--time-limit=10s"])
        quick_fsck_fails = [fr for fr in quick_fsck_res if not fr['success']]
        quick_fsck_num_fail = len(quick_fsck_fails)
        assert quick_fsck_num_fail == 0, f"💥 git-annex quick fsck on {public_sibling['name']} failed example error:{quick_fsck_fails[0]}"


        # check all files are in the shared remote
        fsck_res = ds_repo.fsck(remote=public_sibling['name'], fast=True)
        assert len(fsck_res) > 0, f"❓️git-annex fsck did not give any result, check that remote exists"
        fsck_fails = [fr for fr in fsck_res if not fr['success']]
        fsck_fail_files = [fr['file'] for fr in fsck_fails]
        fsck_num_fail = len(fsck_fails)
        assert fsck_num_fail == 0, f"💥 git-annex fsck on {public_sibling['name']} failed example error:{fsck_fails[0]} for files: {fsck_fail_files}"

        # check that sensitive files are not in the shared remote
        sensitive_files_shared = list(ds_repo.call_annex_items_([
            'find', '--metadata', 'distribution-restrictions=*',
            '--in', public_sibling['name']]))
        assert len(sensitive_files_shared) == 0, f"🚨 Sensitive files mistakenly shared: \n{sensitive_files_shared}"


def get_public_siblings(dataset):
    siblings = dataset.siblings()
    public_siblings = [sib for sib in siblings if not sib.get('annex-ignore', False) and sib['name']!='here']
    sibling_names = [sib['name'] for sib in public_siblings]
    #mri_siblings = [sn for sn in sibling_names if sn.split('.')[-1] == 'mri']
    if len(dataset.repo.get_annexed_files()) > 0:
        assert len(public_siblings) > 0 , '❓️at least 1 public remote is required'
    sib_list = os.environ.get("PUBLIC_SIBLINGS", "").split()
    for sib in sib_list:
        assert sib in sibling_names, f"public remote {sib} not configured"
    return public_siblings
