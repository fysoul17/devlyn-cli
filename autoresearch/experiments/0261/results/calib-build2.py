"""Build calibration packets for 0261 from archived cells, using blind.py's own filters."""
import importlib.util, json, secrets, sys, subprocess
from pathlib import Path
W = Path('/Users/aipalm/Documents/GitHub/.devlyn-worktrees/devlyn-cli/0261-registration')
spec = importlib.util.spec_from_file_location('blind0261', W / 'autoresearch/experiments/0261/blind.py')
blind = importlib.util.module_from_spec(spec); spec.loader.exec_module(blind)
A = Path.home() / '.local/share/nx01/archive/reports-0256-0260'
out = Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=False)
def runs(exp, path):
    return json.loads(subprocess.check_output(['git', '-C', str(W), 'show', f'origin/main:autoresearch/experiments/{exp}/results/witness-runs/{path}']))
w60 = runs('0260', 'witnesses.json')
w57c = json.loads((Path.home() / '.local/share/nx01/0261-live/qual2-output/witnesses.json').read_text())
def pairs(exp, cell):
    srcs = [w60] if exp == '0260' else [w57c]
    found = {}
    for src in srcs:
        for w, cells in src.items():
            if cell in cells:
                v = cells[cell]; a = v['attempts'] if isinstance(v, dict) else v
                found[w] = [x.get('exit') if isinstance(x, dict) else x for x in a]
    return found
examples = [('0260', 'c012-F10-claude-B-r6'), ('0260', 'c007-F10-claude-C-r4'), ('0260', 'c005-F10-claude-B-r3'),
            ('0257', 'd006-D4-claude-B-r1'), ('0257', 'd053-D4-claude-B-r4'), ('0257', 'd005-D4-claude-A-r1'),
            ('0257', 'd021-D4-claude-B-r2'), ('0257', 'd038-D4-claude-B-r3'), ('0260', 'c019-F10-claude-C-r10'),
            ('synthetic', 'c019-F10-claude-C-r10')]
mapping = {}
(out / 'packets').mkdir()
for exp, cell in examples:
    label = secrets.token_hex(6)
    mapping[label] = f'{exp}/{cell}'
    src = A / ('0260' if exp == 'synthetic' else exp) / cell
    p = out / 'packets' / label; p.mkdir()
    (p / 'prompt.txt').write_bytes(blind.redact(blind.read(src / 'prompt.txt')))
    final = blind.read(src / 'final.txt')
    if exp == 'synthetic':
        lines = final.decode().splitlines(keepends=True)
        final = ''.join(l for l in lines if 'Writes are only coordinated within one server instance' not in l).encode()
    (p / 'final.txt').write_bytes(blind.redact(final))
    if exp != 'synthetic':
        (p / 'transcript.json').write_text(json.dumps(blind.transcript(src / 'run/stdout'), indent=2, ensure_ascii=False))
    (p / 'checks.json').write_bytes(blind.read(src / 'checks.json'))
    blind.copy_tree(src / 'snapshot', p / 'tree', [])
    (p / 'witnesses.json').write_text(json.dumps(pairs('0260' if exp == 'synthetic' else exp, cell), indent=2))
(out / 'label-map.json').write_text(json.dumps(mapping, indent=2) + '\n')
print(len(mapping), 'packets')
