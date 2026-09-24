"""Dual blinded assessment of one sealed cell: assess.py <cell> <runtime.json>. No repair feedback; record only."""
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import time

HERE = Path(__file__).resolve().parent
TASKS = json.loads((HERE / 'tasks.json').read_text())
_spec = importlib.util.spec_from_file_location('packet0222', HERE / 'packet.py')
packet = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(packet)


def events(path):
    out = []
    for line in path.read_text().splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if isinstance(event, dict):
            out.append(event)
    return out


def one(cell, runtime, route, prompt):
    out = cell / 'assessment' / route['engine']
    out.mkdir(parents=True, exist_ok=False)
    (out / 'prompt.txt').write_text(prompt)
    with tempfile.TemporaryDirectory(prefix='assess-', dir=runtime['scratch']) as temp:
        home = Path(temp)
        env = {k: os.environ[k] for k in ('PATH', 'LANG', 'LC_ALL') if k in os.environ}
        env.update(HOME=temp, TMPDIR=temp)
        if route['engine'] == 'claude':
            (home / '.claude').mkdir()
            shutil.copyfile(Path(runtime['auth']) / 'claude.json', home / '.claude/.credentials.json')
            env.update(CLAUDE_CONFIG_DIR=str(home / '.claude'), CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC='1')
            command = ['claude', '-p', '--model', route['model'], '--effort', route['effort'], '--tools', '',
                       '--disable-slash-commands', '--permission-mode', 'dontAsk', '--setting-sources', '',
                       '--strict-mcp-config', '--mcp-config', '{"mcpServers":{}}', '--no-session-persistence',
                       '--output-format', 'stream-json', '--verbose']
        else:
            (home / '.codex').mkdir()
            shutil.copyfile(Path(runtime['auth']) / 'codex.json', home / '.codex/auth.json')
            env.update(CODEX_HOME=str(home / '.codex'))
            command = ['codex', 'exec', '--json', '--ignore-user-config', '--ignore-rules', '--skip-git-repo-check',
                       '--sandbox', 'read-only', '-m', route['model'], '-c',
                       f'model_reasoning_effort="{route["effort"]}"', '-C', temp, '-']
        argv = [sys.executable, '-B', str(Path(runtime['control']) / 'run-bounded.py'),
                str(TASKS['watchdog_seconds']['assessor']), '--stdin-file', str(out / 'prompt.txt'), '--', *command]
        start = time.monotonic()
        with (out / 'stdout').open('xb') as stdout, (out / 'stderr').open('xb') as stderr:
            result = subprocess.run(argv, cwd=temp, env=env, stdout=stdout, stderr=stderr)
        seconds = time.monotonic() - start
        if route['engine'] == 'codex' and (home / '.codex/sessions').exists():
            shutil.copytree(home / '.codex/sessions', out / 'sessions')
    stream = events(out / 'stdout')
    if route['engine'] == 'claude':
        final = [e for e in stream if e.get('type') == 'result']
        answer = final[-1].get('result') if final else None
        usage = final[-1].get('modelUsage') if final else None
    else:
        texts = [e['item'].get('text') for e in stream
                 if e.get('type') == 'item.completed' and e['item'].get('type') == 'agent_message']
        answer = texts[-1] if texts else None
        turns = [e['usage'] for e in stream if e.get('type') == 'turn.completed']
        usage = turns[-1] if turns else None
    try:
        parsed = json.loads(re.search(r'\{.*\}', answer or '', re.S).group(0))
    except (AttributeError, ValueError):
        parsed = None
    severe = [f for f in (parsed or {}).get('findings', []) if str(f.get('severity', '')).lower() in ('high', 'critical')]
    record = dict(route=route, exit_code=result.returncode, seconds=seconds, usage=usage or 'UNKNOWN',
                  complete=None if parsed is None else parsed.get('complete') is True, severe=len(severe))
    (out / 'result.json').write_text(json.dumps(record, indent=2))
    return record


def assess(cell, runtime):
    before, prompt = packet.packet(cell / 'work')
    prompt = prompt.replace('This is exposed regression material, not blind research.',
                            'This is blinded outcome assessment. No arm label is supplied.')
    prompt = ('Assess the complete caller contract, source, regressions and actual checks. '
              'Return JSON with complete:boolean, findings with severity and concrete witnesses, '
              'and limitations. No tools or repairs. Do not infer an arm from coding style.\n' + prompt)
    prompt += '\nROOT DETERMINISTIC CHECKS\n' + (cell / 'checks.json').read_text()
    prompt = prompt.replace(str(cell), '/sealed-cell')
    records = [one(cell, runtime, route, prompt) for route in TASKS['assessors']]
    if before != {n: packet.digest(cell / 'work' / n) for n in before}:
        raise RuntimeError('sealed source changed during assessment')
    return records


if __name__ == '__main__':
    print(json.dumps(assess(Path(sys.argv[1]).resolve(), json.loads(Path(sys.argv[2]).read_text()))))
