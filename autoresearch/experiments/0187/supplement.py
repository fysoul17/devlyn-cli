"""Uniform post-discovery boundary replay; never overwrite frozen test grades."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys

from assess import E, R, W, files, put


def commands(draw, work):
    records = {}
    captures = [E / 'runs' / draw / 'stdout'] + [p for p in (work / '.devlyn').rglob('*')
        if p.is_file() and p.suffix in ('.jsonl', '.stdout')]
    for path in captures:
        thread = None
        for number, line in enumerate(path.read_text(errors='replace').splitlines(), 1):
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue  # Text captures are retained raw; this extracts JSON events only.
            if not isinstance(event, dict):
                continue
            if event.get('type') == 'thread.started':
                thread = event.get('thread_id')
            item = event.get('item') or {}
            if isinstance(item, dict) and item.get('type') == 'command_execution':
                key = (thread or str(path), item['id'])
                if key not in records or event.get('type') == 'item.completed':
                    records[key] = {'path': str(path), 'line': number, 'thread': thread,
                                    **{k: item.get(k) for k in ('id', 'command', 'exit_code', 'status')}}
    return list(records.values())


def main():
    reg = json.loads((E / 'REGISTRATION.json').read_text())
    seals = json.loads((E / 'SEALED-OUTPUTS.json').read_text())
    rows = []
    for row in reg['order']:
        work = W / row['draw']
        assert files(work) == seals[row['draw']], row['draw']
        result = {'draw': row['draw'], 'canonical_copy_mismatches': [],
                  'observed_json_commands': commands(row['draw'], work)}
        if row['arm'] == 'C':
            for name in reg['sha256']:
                original = Path(name)
                if not original.is_relative_to(R / 'config/skills'):
                    continue
                target = work / '.agents/skills' / original.relative_to(R / 'config/skills')
                expected = original.read_bytes()
                if original.name == 'SKILL.md':
                    expected = expected.replace(b'__DEVLYN_SKILL_DIR__', str(target.parent).encode())
                if not target.is_file() or target.read_bytes() != expected:
                    result['canonical_copy_mismatches'].append(str(target.relative_to(work)))
        if row['case'] == 'root':
            code = '''import json
from duration import parse_duration
rows = []
for name, value in [('trailing-zero-scale', '1.' + '0'*5000 + 's'), ('leading-zero-scale', '0'*5000 + '1s')]:
    row = {'case': name, 'expected': 1000}
    try:
        row['actual'] = parse_duration(value)
        row['pass'] = row['actual'] == 1000 and type(row['actual']) is int
    except Exception as error:
        row.update({'exception': type(error).__name__, 'message': str(error), 'pass': False})
    rows.append(row)
print(json.dumps(rows))
'''
            p = subprocess.run([sys.executable, '-B', '-c', code], cwd=work,
                               capture_output=True, text=True, timeout=30)
            result['boundary_replay'] = {'exit_code': p.returncode, 'stdout': p.stdout, 'stderr': p.stderr}
            result['boundary_pass'] = p.returncode == 0 and all(x['pass'] for x in json.loads(p.stdout))
        assert files(work) == seals[row['draw']], 'supplement mutated product'
        rows.append(result)
    for name, digest in reg['sha256'].items():
        assert hashlib.sha256(Path(name).read_bytes()).hexdigest() == digest, name
    put(E / 'SUPPLEMENT.json', rows)
    print(json.dumps([{k: v for k, v in row.items() if k not in ('observed_json_commands', 'boundary_replay')}
                      for row in rows]))


if __name__ == '__main__':
    main()
