"""0197 native context experiment; persistent sessions, bounded observed calls."""
from pathlib import Path
import datetime
import hashlib
import importlib.util
import json
import os
import shutil
import subprocess

REPO = Path(__file__).resolve().parents[3]
E = REPO / '.devlyn/0197'
SCRATCH = REPO / '.git/devlyn-completion/6679a50a1aea2765d110b7d3/scratch'
spec = importlib.util.spec_from_file_location('controller', REPO / 'autoresearch/scripts/comparison-controller.py')
controller = importlib.util.module_from_spec(spec)
spec.loader.exec_module(controller)


def put(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x') as stream:
        json.dump(data, stream, indent=2)
        stream.write('\n')


def make_home(name):
    home = SCRATCH / name
    home.mkdir()
    for filename in ('auth.json', 'models_cache.json'):
        source = Path('/Users/aipalm/.codex') / filename if filename == 'auth.json' else E / filename
        shutil.copyfile(source, home / filename)
        (home / filename).chmod(0o600)
    (home / 'config.toml').write_text('')
    (home / 'tmp').mkdir()
    return home


def invoke(name, prompt, cwd, *, home=None, resume=None, review=False, budget=1200):
    out = E / 'runs' / name
    if (out / 'telemetry.json').exists():
        cached = json.loads((out / 'telemetry.json').read_text())
        if cached.get('infrastructure_failure'):
            raise RuntimeError('Retained infrastructure failure; do not reroll: ' + name)
        if (out / 'prompt.txt').read_text() != prompt:
            raise RuntimeError('Changed prompt on resume: ' + name)
        return (out / 'answer.txt').read_text(), cached
    if out.exists():
        raise RuntimeError('Interrupted stage requires inspection, never automatic relaunch: ' + name)
    out.mkdir(parents=True)
    (out / 'prompt.txt').write_text(prompt)
    home = home or make_home(name)
    offsets = {str(p): len(p.read_text().splitlines()) for p in (home / 'sessions').rglob('*.jsonl')} if (home / 'sessions').exists() else {}
    previous = dict(os.environ)
    env = {key: previous[key] for key in ('HOME', 'PATH', 'TMPDIR', 'LANG', 'LC_ALL', 'TERM', 'SHELL', 'USER', 'LOGNAME') if key in previous}
    env.update(CODEX_HOME=str(home), TMPDIR=str(home / 'tmp'), PYTHONDONTWRITEBYTECODE='1')
    selector = (REPO / '.devlyn/0179/catalog-setting.txt').read_text().strip()
    common = ['--ignore-user-config', '--strict-config', '--ignore-rules',
              '--model', 'gpt-6-astra', '-c', 'model_reasoning_effort="high"',
              '-c', 'project_doc_max_bytes=0', '-c', 'web_search="disabled"',
              '-c', selector, '-c', 'sandbox_mode="read-only"' if review else 'sandbox_mode="danger-full-access"',
              '--skip-git-repo-check', '--json']
    for feature in ('multi_agent', 'apps', 'plugins', 'hooks', 'skill_search'):
        common += ['--disable', feature]
    common += ['--enable', 'skip_host_skill_discovery']
    if review:
        common += ['--disable', 'shell_tool']
    native = [shutil.which('codex'), 'exec', *(['resume'] if resume else []), *common, *([resume] if resume else []), '-']
    argv = [shutil.which('python3'), '-B', str(REPO / 'config/skills/_shared/run-bounded.py'), str(budget),
            '--stdin-file', str(out / 'prompt.txt'), '--record-transport', '--', *native]
    plan = dict(work=str(cwd), argv=argv, bounds=dict(native_seconds=1800, wrapper_seconds=1810,
        post_return_quiet_seconds=15, term_seconds=10, kill_reap_seconds=5, overall_seconds=1830))
    put(out / 'input.json', dict(home=str(home), resume=resume, review=review, budget=budget,
        started_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        prompt_sha256=hashlib.sha256(prompt.encode()).hexdigest()))
    put(out / 'launch-plan.json', plan)
    try:
        os.environ.clear()
        os.environ.update(env)
        result = controller.execute(plan, out)
        put(out / 'result.json', result)
    finally:
        os.environ.clear()
        os.environ.update(previous)
    events = []
    for line in (out / 'stdout').read_text(errors='replace').splitlines():
        try:
            value = json.loads(line)
        except ValueError:
            continue
        if isinstance(value, dict):
            events.append(value)
    messages = [e['item']['text'] for e in events if e.get('type') == 'item.completed' and e.get('item', {}).get('type') == 'agent_message']
    calls = list({e['item'].get('id', str(i)): e['item'] for i, e in enumerate(events) if e.get('type') in ('item.started', 'item.completed') and e.get('item', {}).get('type') not in ('agent_message', 'reasoning', 'todo_list', 'error')}.values())
    threads = [e['thread_id'] for e in events if e.get('type') == 'thread.started']
    answer = messages[-1] if messages else ''
    (out / 'answer.txt').write_text(answer)
    rollouts = list((home / 'sessions').rglob('*.jsonl')) if (home / 'sessions').exists() else []
    contexts = []
    compactions = []
    for i, path in enumerate(rollouts):
        shutil.copyfile(path, out / f'rollout-{i}.jsonl')
        for line in path.read_text().splitlines()[offsets.get(str(path), 0):]:
            event = json.loads(line)
            if 'compact' in str(event.get('type', '')) or 'compact' in str(event.get('payload', {}).get('type', '')):
                compactions.append(event)
            if event.get('type') == 'turn_context':
                contexts.append(event['payload'])
    effective = contexts
    native_errors = [e for e in events if e.get('type') in ('error', 'turn.failed') or e.get('item', {}).get('type') == 'error']
    fidelity = not review or (bool(effective) and all(c.get('model') == 'gpt-6-astra' and c.get('effort') == 'high' and c.get('sandbox_policy', {}).get('type') == 'read-only' for c in effective))
    timeout = result['exit_code'] == 124 and bool(threads)
    infrastructure = bool(result['error'] or not result['owned_writers_quiescent'] or (result['exit_code'] != 0 and not timeout) or not threads or (resume and threads != [resume]) or not fidelity or (timeout and native_errors))
    meta = dict(infrastructure_failure=infrastructure, budget_exhausted=timeout, no_tool_fidelity=not calls, native_errors=native_errors, seconds=result['wrapper_return_seconds'], exit_code=result['exit_code'],
        quiescent=result['owned_writers_quiescent'], error=result['error'], tool_events=len(calls),
        threads=threads, home=str(home), resume=resume, contexts=contexts, compactions=compactions,
        usage=[e['usage'] for e in events if e.get('type') == 'turn.completed' and 'usage' in e])
    put(out / 'telemetry.json', meta)
    print(json.dumps(dict(run=name, seconds=meta['seconds'], exit_code=meta['exit_code'], tool_events=len(calls))), flush=True)
    if infrastructure:
        raise RuntimeError('Retained infrastructure/fidelity failure: ' + name)
    return answer, meta


if __name__ == '__main__':
    neutral = E / 'probe-neutral'
    neutral.mkdir()
    token = 'violet-6842-copper'
    answer, original = invoke('probe-initial', f'Retain this calibration token in conversation: {token}. Reply only READY. Use no tools.', neutral, review=True, budget=120)
    prompt = 'What calibration token was given earlier in this conversation? Reply exactly the token, or UNKNOWN if no token was given. Use no tools.'
    continued, same = invoke('probe-resume', prompt, neutral, home=Path(original['home']), resume=original['threads'][0], review=True, budget=120)
    fresh, other = invoke('probe-fresh', prompt, neutral, review=True, budget=120)
    put(E / 'qualification.json', dict(continued=continued, fresh=fresh,
        passed=continued.strip() == token and fresh.strip() == 'UNKNOWN', initial=original, resumed=same, new=other))
    assert continued.strip() == token and fresh.strip() == 'UNKNOWN'
