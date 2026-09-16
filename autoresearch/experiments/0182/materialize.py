"""Recreate admitted source snapshots from the recorded Git commit, without a checkout."""
from pathlib import Path
import hashlib
import json
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[3]
BASE = Path(__file__).resolve().parent
source = json.loads((BASE/'SOURCE.json').read_text())
for case in ('description', 'static'):
    dest = ROOT/'.devlyn/0182/cases'/case
    (dest/'seed').mkdir(parents=True, exist_ok=False)
    for name, expected in source['paths'].items():
        data = subprocess.check_output(['git', 'show', f"{source['source_commit']}:{name}"], cwd=ROOT)
        assert hashlib.sha256(data).hexdigest() == expected, name
        path = dest/'seed'/name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    shutil.copytree(dest/'seed', dest/'reference')
    subprocess.run(['git', 'apply', '--unsafe-paths', str(BASE/case/'reference.patch')], cwd=dest/'reference', check=True)
