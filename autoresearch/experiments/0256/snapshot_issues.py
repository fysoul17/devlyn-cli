"""Freeze D3/D4 issue JSON: snapshot_issues.py <sources-dir> <out-override-json>."""
import datetime
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ISSUES = {'D3': ('tj/commander.js', 2530), 'D4': ('pallets/click', 2645)}


def snapshot(sources, override):
    sources, override = Path(sources), Path(override)
    targets = {key: sources / f'{key}-issue.json' for key in ISSUES}
    if override.exists() or any(path.exists() for path in targets.values()):
        raise FileExistsError('issue snapshot or override already exists')
    if not sources.is_dir():
        raise ValueError('sources directory missing')
    frozen = {}
    for key, (repo, number) in ISSUES.items():
        endpoint = f'repos/{repo}/issues/{number}'
        data = subprocess.run(['gh', 'api', endpoint], check=True, capture_output=True).stdout
        json.loads(data)
        frozen[key] = (data, dict(issue_snapshot_sha256=hashlib.sha256(data).hexdigest(),
                                  fetched_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                                  url=f'https://api.github.com/{endpoint}'))
    for key, (data, _) in frozen.items():
        with targets[key].open('xb') as stream:
            stream.write(data)
    with override.open('x') as stream:
        json.dump({key: value for key, (_, value) in frozen.items()}, stream, indent=2)
        stream.write('\n')


if __name__ == '__main__':
    snapshot(*sys.argv[1:3])
