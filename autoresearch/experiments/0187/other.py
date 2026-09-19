"""Conditional fresh-self versus Fable review/repair on sealed natural products."""
from pathlib import Path
import datetime
import hashlib
import json
import shutil
import subprocess
import sys
import time

R = Path(__file__).resolve().parents[3]
E = R / '.devlyn/0187-other'
I = R / '.devlyn/0187-intent'
W = R.parent / '0187-other-participants'
REVIEW = '''Review the supplied task and original/current source independently. Return only a JSON object
{"findings":[{"file":"path:line","severity":"HIGH|MEDIUM|LOW","problem":"specific violated requirement","evidence":"source evidence and concrete counterexample"}]}.
Report demonstrated in-scope defects, including compatibility and user-constraint violations, even when tests pass.
The user request outranks general project advice. Do not invent a stronger input contract or speculate about future features.
An empty findings list means you found no demonstrated defect; it does not certify universal correctness.
Do not run tools, edit files, infer another reviewer's verdict, or use any other case. The snippets are the complete application.
'''


def hashes(root):
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in root.rglob('*') if p.is_file() and '.git' not in p.relative_to(root).parts}


def put(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x') as output:
        json.dump(value, output, ensure_ascii=False, indent=2)


def packet(work):
    request = json.loads((I / 'REGISTRATION.json').read_text())['turns'][0]
    parts = [REVIEW, 'USER REQUEST\n' + request,
             'ORIGINAL palette.py\n' + (I / 'seed/palette.py').read_text()]
    for name in ['palette.py', 'adapters.py', 'tests/test_acceptance.py', 'tests/native_bridge_check.py', 'tests/test_regression.py']:
        p = work / name
        if p.exists():
            parts.append('CURRENT ' + name + '\n' + '\n'.join(f'{n}: {line}' for n, line in enumerate(p.read_text().splitlines(), 1)))
    return '\n\n'.join(parts)


def prepare():
    E.mkdir(exist_ok=False)
    for label, source in [('x1', I / '2-claude-opus-5/1/product'), ('x2', I / '3-claude-opus-5/1/product'),
                          ('x3', I / '2-claude-opus-5/1/product')]:
        target = E / 'inputs' / label
        shutil.copytree(source, target)
        if label == 'x3':
            p = target / 'palette.py'
            p.write_text((I / 'seed/palette.py').read_text().replace('if engine != "claude":', 'if engine not in ENGINES:'))
    order = [('x1', 'self'), ('x1', 'other'), ('x3', 'other'), ('x3', 'self'), ('x2', 'other'), ('x2', 'self')]
    put(E / 'REGISTRATION.json', {
        'at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'order': order, 'models': {'self': 'claude-opus-5', 'other': 'claude-fable-5-1'},
        'repair_model': 'claude-opus-5', 'effort_requested': 'high',
        'whole_cell_bound_seconds': 900, 'per_call_bounds': {'review': 240, 'repair': 360, 'recheck': 240},
        'maximum_repairs': 1, 'case_map_hidden_from_reviewers': {'x1': 'natural first Opus5 output', 'x2': 'natural second Opus5 output', 'x3': 'root compatibility-restored clean control'},
        'decision': 'OTHER added-value only if it closes more of the two natural compatibility regressions than fresh-self, with no newly failed functional/preservation checks or clean-control harm. A tie is no demonstrated OTHER benefit, not equivalence. One task/two product draws, exploratory conditional screen; no default promotion.',
        'source_selection': 'Both Opus5 first-turn products, not chosen by reviewer outcomes; original primary grades preserved. Compatibility finding is context-derived and post-seal, not a changed original oracle.',
        'sha256': {str(p): hashlib.sha256(p.read_bytes()).hexdigest()
                   for p in [Path(__file__), *list((E / 'inputs').rglob('*'))] if p.is_file()}
    })


def call(label, prompt, model, work, review, bound):
    out = E / 'runs' / label
    out.mkdir(parents=True, exist_ok=False)
    (out / 'prompt.txt').write_text(prompt)
    toolset = '' if review else 'Read,Edit,Write,Glob,Grep,Bash'
    argv = [sys.executable, '-B', str(R / 'config/skills/_shared/run-bounded.py'), str(bound),
            '--stdin-file', str(out / 'prompt.txt'), '--record-transport', '--', shutil.which('claude'),
            '-p', '--model', model, '--effort', 'high', '--tools', toolset,
            '--permission-mode', 'dontAsk', '--setting-sources', '', '--strict-mcp-config',
            '--mcp-config', '{"mcpServers":{}}', '--disable-slash-commands', '--no-session-persistence',
            '--output-format', 'stream-json', '--verbose']
    if not review:
        argv += ['--allowedTools', toolset]
    started = time.monotonic()
    with (out / 'stdout').open('wb') as stdout, (out / 'stderr').open('wb') as stderr:
        p = subprocess.run(argv, cwd=work, stdout=stdout, stderr=stderr)
    events = [json.loads(line) for line in (out / 'stdout').read_text().splitlines() if line.strip()]
    terminal = [x for x in events if x.get('type') == 'result']
    init = [x for x in events if x.get('type') == 'system' and x.get('subtype') == 'init']
    record = {'exit_code': p.returncode, 'seconds': time.monotonic()-started, 'init': init, 'terminal': terminal}
    put(out / 'receipt.json', record)
    assert p.returncode == 0 and terminal and not terminal[-1].get('is_error'), 'Native failure; no substitution/reroll'
    assert set(terminal[-1]['modelUsage']) == {model}, 'Exact usage identity mismatch'
    assert init and all(x.get('model') == model and not x.get('mcp_servers') and not x.get('skills')
                        and all(y.get('source') == 'agents-md@builtin' for y in x.get('plugins', [])) for x in init)
    if review:
        assert all(not x.get('tools') for x in init), 'Reviewer unexpectedly has tools'
    answer = terminal[-1]['result']
    (out / 'answer.txt').write_text(answer)
    return answer


def findings(text):
    text = text.strip()
    if text.startswith('```') and text.endswith('```'):
        text = '\n'.join(text.splitlines()[1:-1])
    value = json.loads(text)
    assert isinstance(value, dict) and isinstance(value.get('findings'), list)
    assert all(isinstance(x, dict) and x.get('severity') in ('HIGH', 'MEDIUM', 'LOW')
               and all(isinstance(x.get(k), str) and x[k] for k in ('file', 'problem', 'evidence')) for x in value['findings'])
    return value


def main():
    if sys.argv[1] == 'prepare':
        prepare()
        return
    reg = json.loads((E / 'REGISTRATION.json').read_text())
    for name, digest in reg['sha256'].items():
        assert hashlib.sha256(Path(name).read_bytes()).hexdigest() == digest, name
    for index, (case, arm) in enumerate(reg['order'], 1):
        label = case + '-' + arm
        work = W / ('case-' + str(index))
        shutil.copytree(E / 'inputs' / case, work)
        subprocess.run(['git', 'init', '-q', str(work)], check=True)
        started = time.monotonic()
        answer = call(label + '-review', packet(work), reg['models'][arm], work, True, 240)
        review = findings(answer)
        put(E / (label + '-review.json'), review)
        if review['findings']:
            request = json.loads((I / 'REGISTRATION.json').read_text())['turns'][0]
            prompt = ('Local-only task. No resolve, delegates, external operations, commits, branches, task-completion helpers or global changes. '
                      'Original user request follows. Validate the review findings against the original behavior and request; fix only substantiated in-scope defects, '
                      'reject unsupported claims with evidence. Run the required checks and remove your debris. '
                      'Only palette.py and tests/test_regression.py may change.\n\n' + request + '\n\nORIGINAL palette.py\n' +
                      (I / 'seed/palette.py').read_text() + '\n\nREVIEW\n' + answer)
            call(label + '-repair', prompt, 'claude-opus-5', work, False, min(360, max(1, int(900-(time.monotonic()-started)))))
            final = call(label + '-recheck', packet(work), reg['models'][arm], work, True,
                         min(240, max(1, int(900-(time.monotonic()-started)))))
            put(E / (label + '-recheck.json'), findings(final))
        seal = hashes(work)
        put(E / (label + '-sealed.json'), seal)
        put(E / (label + '-result.json'), {'seconds': time.monotonic()-started, 'sha256': seal})
        print(json.dumps({'cell': label, 'initial_findings': len(review['findings']), 'seconds': time.monotonic()-started}), flush=True)


if __name__ == '__main__':
    main()
