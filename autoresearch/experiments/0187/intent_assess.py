"""Inspect frozen turn snapshots and retain final claims for human/root audit."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys

R = Path(__file__).resolve().parents[3]
E = R / '.devlyn/0187-intent'
H = Path(__file__).resolve().parent


def hashes(root):
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in root.rglob('*') if p.is_file()}


def main():
    reg = json.loads((E / 'REGISTRATION.json').read_text())
    for name, digest in reg['sha256'].items():
        assert hashlib.sha256(Path(name).read_bytes()).hexdigest() == digest, name
    seed = hashes(E / 'seed')
    rows = []
    for index, model in enumerate(reg['order'], 1):
        label = str(index) + '-' + model
        for turn in range(1, 5):
            out = E / label / str(turn)
            receipt = json.loads((out / 'receipt.json').read_text())
            product = out / 'product'
            before = hashes(product)
            p = subprocess.run([sys.executable, '-B', str(H / 'intent_check.py'), str(product)],
                               capture_output=True, text=True, timeout=30)
            assert hashes(product) == before, 'scoring changed product'
            preserved = {name: before.get(name) == digest for name, digest in seed.items() if name != 'palette.py'}
            extra = sorted(set(before) - set(seed) - {'tests/test_regression.py', 'HANDOFF.md'})
            row = {'draw': label, 'turn': turn, 'model': model, 'receipt': receipt,
                   'checks': {'exit_code': p.returncode, 'stdout': p.stdout, 'stderr': p.stderr},
                   'preserved': preserved, 'extra_files': extra, 'sha256': before,
                   'answer': (out / 'answer.txt').read_text(), 'commands': []}
            for line in (out / 'stdout').read_text(errors='replace').splitlines():
                try:
                    event = json.loads(line)
                except ValueError:
                    continue
                for block in event.get('message', {}).get('content', []):
                    if isinstance(block, dict) and block.get('type') == 'tool_use':
                        row['commands'].append({'tool': block['name'], 'input': block.get('input'), 'id': block.get('id')})
            if turn == 4:
                previous = hashes(E / label / '3/product')
                row['post_handoff_changed'] = sorted(name for name in set(previous) | set(before)
                                                     if name != 'HANDOFF.md' and previous.get(name) != before.get(name))
                row['handoff'] = (product / 'HANDOFF.md').read_text() if (product / 'HANDOFF.md').is_file() else None
            row['artifact_pass'] = p.returncode == 0 and all(preserved.values()) and not extra
            rows.append(row)
    with (E / 'ASSESSMENT.json').open('x') as output:
        json.dump(rows, output, ensure_ascii=False, indent=2)
    print(json.dumps([{k: row[k] for k in ('draw', 'turn', 'artifact_pass')} for row in rows]))


if __name__ == '__main__':
    main()
