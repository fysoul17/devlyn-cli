"""Check the common local-commit endpoint without prescribing an owner's workflow."""
import json
from pathlib import Path
import subprocess
import tempfile


def check(out, selection, locate, packet):
    baseline = json.loads((out / 'baseline.json').read_text())
    caller = json.loads((out / 'harness/caller.json').read_text())
    anchor = out / 'cell/work'
    folder = anchor if selection['kind'] == 'accepted' else out / selection['path']
    command = locate.command(out, folder)
    revision = selection['sha'] if selection['kind'] == 'accepted' else 'HEAD'
    resolved = subprocess.run([*command, 'rev-parse', '--verify', '--end-of-options', revision + '^{commit}'],
                              capture_output=True, text=True, env=locate.ENV)
    if resolved.returncode:
        return dict(passed=False, reason='selected product has no readable commit')
    sha = resolved.stdout.strip()
    result = dict(passed=False, commit=sha, baseline=baseline['allocation_sha'])
    if sha == baseline['allocation_sha']:
        return dict(result, reason='required edits exist only outside a post-baseline commit')
    descendant = subprocess.run([*command, 'merge-base', '--is-ancestor', baseline['allocation_sha'], sha],
                                capture_output=True, text=True, env=locate.ENV)
    if descendant.returncode == 1:
        return dict(result, reason='delivery commit is not a descendant of the allocation baseline')
    if descendant.returncode:
        raise ValueError('cannot verify delivery ancestry: ' + descendant.stderr.strip())
    with tempfile.TemporaryDirectory(prefix='0237-delivery-') as temp:
        committed = packet.tree(locate.raw_tree(command, sha, Path(temp)))
    snapshot = packet.tree(out / 'snapshot')
    if committed != snapshot:
        return dict(result, reason='delivery commit product differs from the assessed snapshot')
    changed = sorted(name for name in baseline['files'].keys() | committed.keys()
                     if baseline['files'].get(name) != committed.get(name))
    if not any(packet.allowed(name, caller['allowed']) for name in changed):
        return dict(result, reason='delivery commit contains no changed task source')
    return dict(result, passed=True, reason='local commit matches the assessed task source', changed=changed)
