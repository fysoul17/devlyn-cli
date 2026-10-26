"""Add arm C to an existing 0256 control root: control.py <control-root>."""
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import sys

HERE = Path(__file__).resolve().parent
EDIT = (
    ('- **Perfection is achieved not when there is nothing more to add, but when there is nothing left to take away.** — Saint-Exupéry. This is the operating definition of "done." A change is finished when no further line, branch, flag, or doc paragraph can be removed without breaking a learned failure mode. Not before.\n', ''),
    ('Three discipline rules govern HOW the principles are applied:',
     'Two discipline rules govern HOW the principles are applied:'),
)
TARGETS = ('AGENTS.md', 'CLAUDE.md', 'config/skills/_shared/runtime-principles.md')

spec = importlib.util.spec_from_file_location('control0256', HERE.parent / '0256/control.py')
prior = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prior)


def apply_edit(text, name):
    for source, replacement in EDIT:
        count = text.count(source)
        if count != 1:
            raise ValueError(f'{name}: expected {source!r} exactly once, found {count}')
        text = text.replace(source, replacement, 1)
    return text


def build_c(control_root):
    control = Path(control_root)
    source = control / 'packages/B/package'
    target = control / 'packages/C/package'
    manifest_path = control.with_name(control.name + '.manifest.json')
    record = json.loads(manifest_path.read_text())
    if target.parent.exists() or 'C' in record['packages']:
        raise ValueError('arm C already exists')
    if prior.manifest(control / 'packages') != record['manifests']['packages']:
        raise ValueError('B package differs from control manifest')
    edited = {}
    for name in TARGETS:
        edited[name] = apply_edit((source / name).read_bytes().decode('utf8'), name).encode('utf8')
    target.parent.mkdir()
    try:
        shutil.copytree(source, target, symlinks=True, copy_function=shutil.copy2)
        for name, data in edited.items():
            (target / name).write_bytes(data)
        files = prior.manifest(target)
        record['packages']['C'] = dict(source='B', sha256=hashlib.sha256(
            json.dumps(files, sort_keys=True).encode()).hexdigest(), files=files)
        record['manifests']['packages'] = prior.manifest(control / 'packages')
        manifest_path.write_text(json.dumps(record, indent=1, sort_keys=True) + '\n')
    except Exception:
        shutil.rmtree(target.parent)
        raise
    return target


if __name__ == '__main__':
    print(build_c(sys.argv[1]))
