"""Retain the sealed B archive and change only its completion-guide sentence for C."""
import argparse
import copy
import hashlib
import io
import json
from pathlib import Path
import shutil
import tarfile

BASE_SHA = '8c4dcdfa79ba7fed8541418f09475aa9edd5bbaaa010690b26254ed42e34a6e8'
GUIDE = 'package/config/skills/_shared/task-completion.md'
OLD = 'Wait for your children, stop your dev servers and task writers, then leave the\ntask tree.'
NEW = ('Wait for your children before the final response, using explicit foreground execution '
       'or a supported native wait for results needed to finish the request. Stop your dev '
       'servers and task writers, then leave the task tree.')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def files(path):
    with tarfile.open(path) as archive:
        return {m.name: sha(archive.extractfile(m).read()) for m in archive if m.isfile()}


def build(source, destination):
    if sha(source.read_bytes()) != BASE_SHA:
        raise ValueError('source must be the frozen two-fix B archive')
    with tarfile.open(source) as archive:
        original = archive.extractfile(GUIDE).read().decode()
    if original.count(OLD) != 1:
        raise ValueError('baseline sentence is not unique')
    replacement = original.replace(OLD, NEW).encode()
    destination.mkdir(parents=True, exist_ok=False)
    shutil.copyfile(source, destination / 'B.tgz')
    with tarfile.open(source) as before, tarfile.open(destination / 'C.tgz', 'w:gz') as after:
        for member in before:
            data = before.extractfile(member) if member.isfile() else None
            if member.name == GUIDE:
                member = copy.copy(member)
                member.size = len(replacement)
                data = io.BytesIO(replacement)
            after.addfile(member, data)
    packages = {arm: {'sha256': sha((destination / (arm + '.tgz')).read_bytes()),
                      'files': files(destination / (arm + '.tgz'))} for arm in ('B', 'C')}
    a, b = (packages[arm]['files'] for arm in ('B', 'C'))
    changed = sorted(name for name in a.keys() | b.keys() if a.get(name) != b.get(name))
    if changed != [GUIDE]:
        raise ValueError('unexpected package payload change: ' + repr(changed))
    result = {'baseline_archive_sha256': BASE_SHA, 'builder_sha256': sha(Path(__file__).read_bytes()),
              'old': OLD, 'new': NEW, 'changed': changed, 'packages': packages}
    (destination / 'packages.json').write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
    return {arm: row['sha256'] for arm, row in packages.items()}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('destination', type=Path)
    args = parser.parse_args()
    print(json.dumps(build(args.source, args.destination)))
