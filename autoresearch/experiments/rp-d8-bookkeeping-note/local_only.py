"""rp-d6's no-origin cell, with sealed baseline/final configuration identities."""
import importlib.util
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('local_rpd6_rpd8', HERE.parent / 'rp-d6-claude-delivery/local_only.py')
legacy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(legacy)
capture = legacy.base.load('capture_rpd8_local', HERE / 'capture.py')
github = legacy.github
read, write, digest, require = legacy.read, legacy.write, legacy.digest, legacy.require
prepare, storage, preservation = legacy.prepare, legacy.storage, legacy.preservation
harness_unchanged, publication = legacy.harness_unchanged, legacy.publication
inherited_archive = legacy.archive


def archive(out, root, verdict):
    bound = capture.sealed(out, verdict)
    require(bound is not None, 'local bookkeeping observation missing')
    before, observation, _ = bound
    result = inherited_archive(out, root, verdict)
    path = root / 'local-only.json'
    value = read(path)
    value.update(schema='rp-d8-local-archive-v1',
                 baseline_config_sha256=before['config_sha256'],
                 final_config_sha256=observation['final']['config_sha256'])
    write(path, value)
    write(root / 'manifest.json', dict(repository=None, files=github.archive_files(root)))
    require(read(root / 'manifest.json')['files'] == github.archive_files(root), 'local archive changed')
    return dict(result, manifest_sha256=digest(root / 'manifest.json'))


legacy.archive = archive
run = legacy.run
