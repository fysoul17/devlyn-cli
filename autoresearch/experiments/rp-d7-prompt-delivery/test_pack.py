"""Unmodified registry X bytes, both digests and extracted-tree custody."""
from copy import deepcopy

import pytest

from .conftest import HERE, load


@pytest.fixture
def packed(tmp_path, monkeypatch):
    p = load('pack')
    fixture = load('pack_fixture', HERE.parent / 'rp-d6-claude-delivery/test_pack.py')
    source, _, _, _ = fixture.fixture(p.legacy, tmp_path, monkeypatch)
    return p, source, p.build(source, tmp_path / 'release', **p.identity(source))


def test_single_registry_release(packed):
    p, source, path = packed
    arms = p.verify_arms(path)
    assert set(arms) == {'X'}
    assert arms['X']['source'] == {'registry': 'devlyn-cli@4.2.22'}
    assert (path.parent / 'X.tgz').read_bytes() == source.read_bytes()
    assert sorted(item.name for item in path.parent.iterdir()) == ['X.tgz', 'arms.json']


@pytest.mark.parametrize('field', ['sha256', 'integrity'])
def test_registration_checks_both_hashes(packed, tmp_path, field):
    p, source, _ = packed
    identity = p.identity(source)
    identity[field] = 'wrong'
    with pytest.raises(ValueError, match='SHA-256/integrity'):
        p.build(source, tmp_path / 'bad', **identity)
    assert not (tmp_path / 'bad').exists()


@pytest.mark.parametrize('fault', ['Y', 'sha256', 'integrity', 'source', 'manifest', 'bytes'])
def test_rebound_release_rejected(packed, fault):
    p, _, path = packed
    arms = p.read(path)
    if fault == 'Y':
        arms['Y'] = deepcopy(arms['X'])
    elif fault in ('sha256', 'integrity'):
        arms['X'][fault] = 'bad'
    elif fault == 'source':
        arms['X']['source']['candidate_commit'] = 'a' * 40
    elif fault == 'manifest':
        arms['X']['manifest_sha256'] = 'bad'
    else:
        with (path.parent / 'X.tgz').open('ab') as stream:
            stream.write(b'mutation')
    p.write(path, arms)
    with pytest.raises(ValueError):
        p.verify_arms(path)
