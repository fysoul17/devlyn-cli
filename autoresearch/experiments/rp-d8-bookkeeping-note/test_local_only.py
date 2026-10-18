"""No-origin configuration identities remain product evidence, not a STOP."""
import importlib.util
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('capture_fixtures_rpd8_local', HERE / 'test_capture.py')
fixtures = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixtures)
cell = fixtures.cell


@pytest.mark.parametrize('change', ['none', 'remote', 'identity'])
def test_config_digests_recorded_in_local_observation_with_remote_change_allowed_by_harness(cell, change):
    capture, out, git = cell('g06')
    module = capture.local.base.load('local_rpd8_tests', HERE / 'local_only.py')
    (out / 'harness').mkdir()
    for name in ('caller', 'roles'):
        (out / 'harness' / (name + '.json')).write_text('{}')
    baseline = module.read(out / 'baseline.json')
    baseline.update(transport=dict(repository=None, local=dict(remotes=[], remote_refs=[])),
        caller_sha256=module.digest(out / 'harness/caller.json'), roles_sha256=module.digest(out / 'harness/roles.json'))
    module.write(out / 'baseline.json', baseline)
    if change == 'remote':
        git('remote', 'add', 'unexpected', '/local/fixture')
    elif change == 'identity':
        git('config', 'user.name', 'Changed')
    assert module.harness_unchanged(out, baseline) is True
    record = fixtures.seal(capture, out)
    facts = capture.assess(out, record)
    assert facts['config_changed'] is (change != 'none')
    root = out.parent / 'archives/g06'
    archived = module.archive(out, root, dict(record, snapshot={}))
    observation = module.read(root / 'local-only.json')
    assert observation['baseline_config_sha256'] == baseline['bookkeeping']['config_sha256']
    assert observation['final_config_sha256'] == module.digest(out / 'cell/work/.git/config')
    assert archived['manifest_sha256'] == module.digest(root / 'manifest.json')
    assert module.read(root / 'manifest.json')['files'] == module.github.archive_files(root)


@pytest.mark.parametrize('fault', ['include', 'alternates', 'commondir'])
def test_g06_storage_safety_still_stops(cell, fault):
    capture, out, git = cell('g06')
    if fault == 'include':
        git('config', 'include.path', '/local/untrusted')
    else:
        relative = 'objects/info/alternates' if fault == 'alternates' else 'commondir'
        (out / 'cell/work/.git' / relative).write_text('/local/untrusted')
    with pytest.raises(RuntimeError):
        capture.finalize(out)
