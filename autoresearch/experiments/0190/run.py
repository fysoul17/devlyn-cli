"""Frozen factorial repair screen; existing bounded transport/process controller."""
from pathlib import Path
import datetime
import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile

from fixtures import CASES, REMINDER

R = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
E = R / '.devlyn/0190'
INPUTS = E / 'inputs-v2'
W = R.parent / '0190-participants'
S = R / '.git/devlyn-completion/7224a0d160aec4b54c8b8711/scratch'
MODEL = 'claude-opus-5'
spec = importlib.util.spec_from_file_location('controller', R / 'autoresearch/scripts/comparison-controller.py')
controller = importlib.util.module_from_spec(spec)
spec.loader.exec_module(controller)


def put(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write('\n')


def hashes(root):
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in root.rglob('*') if p.is_file() and '.git' not in p.relative_to(root).parts}


def probe(case, root):
    return command([sys.executable, '-B', str(HERE / 'check.py'), case, str(root)], root)


def command(argv, root):
    try:
        result = subprocess.run(argv, cwd=root, capture_output=True, text=True, timeout=30)
    except subprocess.TimeoutExpired as exc:
        return {'exit_code': 124, 'stdout': (exc.stdout or b'').decode(errors='replace'),
                'stderr': (exc.stderr or b'').decode(errors='replace'), 'timeout_seconds': 30}
    return {'exit_code': result.returncode, 'stdout': result.stdout, 'stderr': result.stderr}


def calibrate():
    rows = []
    for case, data in CASES.items():
        variants = {'reference': (data['reference'], None), 'seeded_defect': (data['source'], 'closure')}
        if case == 'template':
            variants['recursive_values'] = (data['reference'].replace(
                'bindings.get(name, text[i:end + 1])',
                'expand(bindings[name], bindings) if name in bindings else text[i:end + 1]'), 'false_review')
            variants['unclosed_raises'] = (data['reference'].replace(
                ' and "}" in text[i + 2:]', ''), 'unclosed')
        else:
            variants.update({
                'no_op_preserves_undo': (data['reference'].replace('self._undo = self._state',
                    'if updated != self._state:\n            self._undo = self._state'), 'false_review'),
                'non_atomic': (data['reference'].replace('updated = dict(self._state)',
                    'before = dict(self._state)\n        updated = self._state').replace(
                    'self._undo = self._state', 'self._undo = before'),
                    'atomic_failure_and_undo'),
                'bool_is_int': (data['reference'].replace('type(quantity) is not int', 'not isinstance(quantity, int)'),
                    'atomic_failure_and_undo'),
                'no_intermediate_bound': (data['reference'].replace('if not 0 <= value <= 1000000:', 'if False:'),
                    'domain_boundaries'),
            })
        for name, (source, expected_failure) in variants.items():
            with tempfile.TemporaryDirectory(prefix='calibration-', dir=S) as temp:
                work = Path(temp)
                (work / 'product.py').write_text(source)
                result = probe(case, work)
            parsed = json.loads(result['stdout'])
            assert (all(v['pass'] for v in parsed.values()) if expected_failure is None
                    else not parsed[expected_failure]['pass']), (case, name, result)
            if name == 'seeded_defect':
                assert parsed['false_review']['pass'], 'Seeded failure must not imply false-review harm'
            rows.append({'case': case, 'variant': name, 'expected_failure': expected_failure, **result})
    return rows


def prepare():
    put(E / 'CALIBRATION.v2.json', calibrate())
    text = (R / 'CLAUDE.md').read_text()
    guidance = '\n'.join(line for line in text.splitlines() if
        line.startswith(('1. **No workaround**', '7. **Production ready**', '**No silent fallbacks.**',
                         '- **Fallbacks are the exception.**')))
    assert len(guidance.splitlines()) == 4
    (E / 'generic-guidance.md').write_text(guidance + '\n')
    cells = [(1, 0), (0, 0), (0, 1), (1, 1)]
    order = []
    for repeat in (1, 2):
        for case in CASES:
            sequence = cells if (repeat == 1) == (case == 'template') else list(reversed(cells))
            for generic, reminder in sequence:
                label = f'{len(order) + 1:02d}-{case}-{repeat}-g{generic}r{reminder}'
                row = dict(label=label, case=case, repeat=repeat, generic=generic, reminder=reminder)
                order.append(row)
                source = INPUTS / label
                source.mkdir(parents=True)
                data = CASES[case]
                for name, body in [('product.py', data['source']), ('caller.py', data['caller']),
                                   ('tests/test_public.py', data['public']), ('request.md', data['request'])]:
                    p = source / name
                    p.parent.mkdir(parents=True, exist_ok=True)
                    p.write_text(body)
                advice = guidance if generic else '(No additional generic error-handling advice.)'
                (source / 'PROJECT_ADVICE.md').write_text(advice + '\n')
                prompt = (
                    'Work only inside this isolated checkout. No resolve, delegates, network task operations, '
                    'global changes, commits, branches or task-completion helpers. The outer owner handles '
                    'custody. Read request.md, product.py, caller.py, tests/test_public.py and '
                    'PROJECT_ADVICE.md. The latter is generic project guidance, below the user request. '
                    'Only product.py and optional tests/test_regression.py may change; preserve all other '
                    'files exactly. Run python3 -B -m unittest discover -s tests -v and focused checks. '
                    'Installed executable/runtime reads and native CLI bookkeeping are allowed; do not '
                    'read or write siblings, prior research, /tmp or global files. Use the provided in-checkout '
                    'TMPDIR for experiments and remove your own debris before returning.\n\n'
                    + ('REPAIR INSTRUCTION\n' + REMINDER + '\n\n' if reminder else '')
                    + 'USER REQUEST\n' + data['request'] + '\n\nREVIEW TO ADJUDICATE\n' + data['review'])
                (source / 'prompt.txt').write_text(prompt)
    paths = [*HERE.glob('*'), E / 'generic-guidance.md', R / 'config/skills/_shared/run-bounded.py',
             R / 'autoresearch/scripts/comparison-controller.py', *list(INPUTS.rglob('*'))]
    put(E / 'REGISTRATION.json', {
        'at': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'order': order,
        'model': MODEL, 'effort': 'high', 'seconds_per_draw': 360,
        'version': subprocess.check_output(['claude', '--version'], text=True).strip(),
        'sha256': {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths if p.is_file()},
    })


def verify_inputs():
    reg = json.loads((E / 'REGISTRATION.json').read_text())
    for name, digest in reg['sha256'].items():
        assert hashlib.sha256(Path(name).read_bytes()).hexdigest() == digest, name
    return reg


def native(label, prompt, work, model=MODEL, review=False):
    out = E / 'runs' / label
    out.mkdir(parents=True, exist_ok=False)
    (out / 'prompt.txt').write_text(prompt)
    tools = '' if review else 'Read,Edit,Write,Glob,Grep,Bash'
    argv = [sys.executable, '-B', str(R / 'config/skills/_shared/run-bounded.py'), '360',
            '--stdin-file', str(out / 'prompt.txt'), '--record-transport', '--', shutil.which('claude'),
            '-p', '--safe-mode', '--model', model, '--effort', 'high', '--tools', tools,
            '--permission-mode', 'dontAsk', '--setting-sources', '', '--strict-mcp-config',
            '--mcp-config', '{"mcpServers":{}}', '--disable-slash-commands', '--no-session-persistence',
            '--output-format', 'stream-json', '--verbose']
    if tools:
        argv += ['--allowedTools', tools]
    plan = dict(work=str(work), argv=argv, bounds=dict(native_seconds=1800, wrapper_seconds=1810,
        post_return_quiet_seconds=15, term_seconds=10, kill_reap_seconds=5, overall_seconds=1830))
    put(out / 'launch-plan.json', plan)
    previous = dict(os.environ)
    try:
        os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
        os.environ['TMPDIR'] = str(work / '.scratch')
        result = controller.execute(plan, out)
    finally:
        os.environ.clear()
        os.environ.update(previous)
    put(out / 'result.json', result)
    # Seal even timeouts/truncated streams before interpreting protocol output.
    put(out / 'sealed.json', hashes(work))
    events, invalid = [], []
    for number, line in enumerate((out / 'stdout').read_text(errors='replace').splitlines(), 1):
        if line.strip():
            try:
                events.append(json.loads(line))
            except ValueError:
                invalid.append(number)
    init = [e for e in events if e.get('type') == 'system' and e.get('subtype') == 'init']
    terminal = [e for e in events if e.get('type') == 'result']
    put(out / 'native.json', dict(init=init, terminal=terminal, invalid_json_lines=invalid))
    assert not invalid, 'Malformed native protocol; retain raw stream and stop'
    assert not result['error'] and result['owned_writers_quiescent'] and result['exit_code'] == 0, result
    assert terminal and not terminal[-1].get('is_error'), terminal
    assert set(terminal[-1]['modelUsage']) == {model}, 'model identity mismatch'
    assert init and all(e.get('model') == model and not e.get('mcp_servers')
                        and not e.get('skills') and not e.get('plugins') for e in init), 'customization isolation mismatch'
    if review:
        assert all(not e.get('tools') for e in init), 'review tools enabled'
    (out / 'answer.txt').write_text(terminal[-1]['result'])
    print(json.dumps(dict(label=label, seconds=result['wrapper_return_seconds'],
                         cost=terminal[-1].get('total_cost_usd'))), flush=True)


def run():
    reg = verify_inputs()
    for row in reg['order']:
        label = row['label']
        assert not (E / 'runs' / label).exists(), 'Existing run: inspect, never replay scored cells'
        work = W / label
        shutil.copytree(INPUTS / label, work)
        (work / '.scratch').mkdir()
        subprocess.run(['git', 'init', '-q', str(work)], check=True)
        native(label, (work / 'prompt.txt').read_text(), work)


def assess():
    rows = []
    for row in verify_inputs()['order']:
        out = E / 'runs' / row['label']
        work = W / row['label']
        if not (out / 'sealed.json').exists():
            rows.append(dict(row, status='INCOMPLETE' if out.exists() else 'NOT_RUN'))
            continue
        sealed = json.loads((out / 'sealed.json').read_text())
        assert hashes(work) == sealed, row['label']
        baseline = hashes(INPUTS / row['label'])
        changed = sorted(k for k in sealed.keys() | baseline.keys() if sealed.get(k) != baseline.get(k))
        checks = probe(row['case'], work)
        public = command([sys.executable, '-B', '-m', 'unittest', 'discover', '-s', 'tests', '-v'], work)
        native_data = json.loads((out / 'native.json').read_text()) if (out / 'native.json').exists() else {}
        native_result = native_data.get('terminal', [{}])[-1] if native_data.get('terminal') else {}
        record = dict(row, status='SEALED', checks=checks, public=public, changed=changed,
            scratch_files=[k for k in sealed if k.startswith('.scratch/')],
            artifact_scope=all(k in ('product.py', 'tests/test_regression.py')
                for k in changed if not k.startswith('.scratch/')),
            seconds=json.loads((out / 'result.json').read_text())['wrapper_return_seconds'],
            cost_usd=native_result.get('total_cost_usd'), permission_denials=native_result.get('permission_denials', []))
        record['artifact_complete'] = record['artifact_scope'] and checks['exit_code'] == public['exit_code'] == 0
        record['execution_scope'] = 'PENDING_ROOT_TOOL_AUDIT'
        rows.append(record)
        assert hashes(work) == sealed, 'Assessment changed sealed bytes'
    put(E / 'ASSESSMENT.json', rows)
    print(json.dumps([{k: row.get(k) for k in ('label', 'status', 'artifact_complete', 'seconds')} for row in rows], indent=2))


if __name__ == '__main__':
    {'prepare': prepare, 'run': run, 'assess': assess}[sys.argv[1]]()
