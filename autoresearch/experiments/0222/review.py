"""Request one independent review of /work. Takes no arguments; help or unknown arguments never dispatch."""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time

CONTROL = Path('/control/autoresearch/experiments/0222')


def allocate(root):
    root.mkdir(parents=True, exist_ok=True)
    while True:
        number = 1 + max((int(p.name.split('-')[1]) for p in root.glob('call-*')), default=0)
        try:
            (root / f'call-{number}').mkdir()
            return root / f'call-{number}'
        except FileExistsError:
            continue


def codex_identity(home, model):
    contexts, reroutes = set(), 0
    for path in (home / 'sessions').rglob('*.jsonl'):
        for line in path.read_text().splitlines():
            event = json.loads(line) if line.strip() else {}
            if event.get('type') == 'turn_context':
                contexts.add(event['payload']['model'])
            if event.get('type') == 'event_msg' and event['payload'].get('type') == 'model_reroute':
                reroutes += 1
    return 'MATCH' if contexts == {model} and not reroutes else 'MISMATCH' if contexts else 'UNKNOWN'


def main():
    argparse.ArgumentParser(description=__doc__).parse_args()
    spec = importlib.util.spec_from_file_location('packet', CONTROL / 'packet.py')
    packet = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(packet)
    seconds = json.loads((CONTROL / 'tasks.json').read_text())['watchdog_seconds']['review']
    engine, model, effort = os.environ['DEVLYN_REVIEWER'].split(':')
    work = Path('/work')
    out = allocate(work / '.devlyn/reviews')
    before, prompt = packet.packet(work)
    (out / 'prompt.txt').write_text(prompt)
    started = time.time()
    with tempfile.TemporaryDirectory(prefix='review-') as tmp:
        home = Path(tmp)
        env = {k: os.environ[k] for k in ('PATH', 'LANG', 'LC_ALL') if k in os.environ}
        env.update(HOME=tmp, TMPDIR=tmp)
        if engine == 'claude':
            (home / '.claude').mkdir()
            shutil.copyfile('/credentials/claude.json', home / '.claude/.credentials.json')
            env.update(CLAUDE_CONFIG_DIR=str(home / '.claude'), CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC='1')
            command = ['claude', '-p', '--model', model, '--effort', effort, '--tools', '',
                       '--disable-slash-commands', '--permission-mode', 'dontAsk', '--setting-sources', '',
                       '--strict-mcp-config', '--mcp-config', '{"mcpServers":{}}', '--no-session-persistence',
                       '--output-format', 'stream-json', '--verbose']
        else:
            (home / '.codex').mkdir()
            shutil.copyfile('/credentials/codex.json', home / '.codex/auth.json')
            env.update(CODEX_HOME=str(home / '.codex'))
            command = ['codex', 'exec', '--json', '--ignore-user-config', '--ignore-rules', '--skip-git-repo-check',
                       '--sandbox', 'read-only', '-m', model, '-c', f'model_reasoning_effort="{effort}"', '-C', tmp, '-']
        argv = [sys.executable, '-B', '/control/run-bounded.py', str(seconds), '--stdin-file',
                str(out / 'prompt.txt'), '--', *command]
        (out / 'started.json').write_text(json.dumps(dict(started_at=started, route=[engine, model, effort], argv=argv)))
        with (out / 'stdout').open('xb') as stdout, (out / 'stderr').open('xb') as stderr:
            result = subprocess.run(argv, cwd=tmp, env=env, stdout=stdout, stderr=stderr)
        events = [json.loads(line) for line in (out / 'stdout').read_text().splitlines() if line.strip().startswith('{')]
        if engine == 'claude':
            final = [e for e in events if e.get('type') == 'result']
            answer = final[-1].get('result') if final else None
            usage = final[-1].get('modelUsage') if final else None
            identity = ('UNKNOWN' if not usage else 'MATCH' if model in usage else 'MISMATCH')
        else:
            if (home / '.codex/sessions').exists():
                shutil.copytree(home / '.codex/sessions', out / 'sessions')
            texts = [e['item'].get('text') for e in events if e.get('type') == 'item.completed'
                     and e.get('item', {}).get('type') == 'agent_message']
            answer = texts[-1] if texts else None
            turns = [e['usage'] for e in events if e.get('type') == 'turn.completed']
            usage = turns[-1] if turns else None
            identity = codex_identity(home / '.codex', model)
    record = dict(exit_code=result.returncode, seconds=time.time() - started, identity=identity,
                  usage=usage if usage is not None else 'UNKNOWN',
                  source_unchanged=before == {n: packet.digest(work / n) for n in before})
    (out / 'result.json').write_text(json.dumps(record, indent=2))
    if result.returncode or answer is None:
        raise SystemExit(f'Review failed (exit {result.returncode}); see {out}. No review text.')
    (out / 'answer.txt').write_text(answer)
    print(answer)


if __name__ == '__main__':
    main()
