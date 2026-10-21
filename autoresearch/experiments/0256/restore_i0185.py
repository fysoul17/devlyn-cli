"""Restore 0233's I0185 participant inputs into <apparatus>/.devlyn/0185/inputs/install from Git history; verify every sealed sha256."""
import hashlib, json, subprocess, sys
from pathlib import Path
repo = Path(sys.argv[1]).resolve()
task = next(t for t in json.loads((repo / 'autoresearch/experiments/0233/tasks.json').read_text())['tasks'] if t['id'] == 'I0185')
dest = repo / task['source_dir']
blob = lambda spec: subprocess.run(['git', '-C', str(repo), 'cat-file', 'blob', spec], check=True, capture_output=True).stdout
exp = repo / 'autoresearch/experiments/0185'
files = {
    'bin/devlyn.js': blob('66d6396dc0f7ac0838984354d7e4f72766bb1de3'),
    'package.json': blob('62b08173f7b9beda61b2fea6acd37638662eee6d'),
    'spec.md': (exp / 'request.md').read_bytes(),
    'tests/support.js': (exp / 'support.js').read_bytes(),
    'tests/acceptance.js': (exp / 'acceptance.js').read_bytes(),
    '.gitignore': b'.devlyn/\n.agents/\n__pycache__/\n*.pyc\n',
    'spec.expected.json': (json.dumps(dict(required_files=['bin/devlyn.js'], forbidden_files=['spec.md', 'spec.expected.json', 'package.json', '.gitignore', 'tests/support.js', 'tests/acceptance.js'], verification_commands=[dict(cmd='node --test tests/acceptance.js', exit_code=0, timeout_sec=90)]), indent=2) + '\n').encode(),
}
assert set(files) == set(task['source_sha256']), sorted(set(files) ^ set(task['source_sha256']))
for name, data in files.items():
    assert hashlib.sha256(data).hexdigest() == task['source_sha256'][name], name
if dest.exists():
    raise SystemExit(f'{dest} exists; not overwriting')
for name, data in files.items():
    (dest / name).parent.mkdir(parents=True, exist_ok=True)
    (dest / name).write_bytes(data)
print('restored', len(files), 'files to', dest)
