"""Run one sealed research call in a private container; no multi-cell scheduler."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import time
import uuid

ACCOUNTING = Path(__file__).with_name('native_accounting.py')
spec = importlib.util.spec_from_file_location('accounting', ACCOUNTING)
accounting = importlib.util.module_from_spec(spec)
spec.loader.exec_module(accounting)


def docker(*args, timeout=5):
    return subprocess.run(['docker', *args], capture_output=True, text=True,
                          check=True, timeout=timeout).stdout.strip()


def reviews(work):
    total = dict(input_tokens=0, output_tokens=0, calls=0)
    pending = []
    for folder in sorted((work / '.devlyn/reviews').glob('call-*')):
        if not (folder / 'started.json').exists():
            raise ValueError('incomplete reviewer setup: ' + str(folder))
        total['calls'] += 1
        result = folder / 'result.json'
        if not result.exists():
            started = json.loads((folder / 'started.json').read_text())
            if time.time() - started['started_at'] > 240:
                raise TimeoutError('review deadline exceeded with UNKNOWN usage')
            pending.append(str(folder))
            continue
        outcome = json.loads(result.read_text())
        if outcome['exit_code'] == 124 or outcome['seconds'] > 240:
            raise TimeoutError('review deadline with UNKNOWN usage: ' + str(folder))
        if outcome['exit_code'] or not outcome['source_unchanged']:
            raise ValueError('failed reviewer: ' + str(folder))
        events = [json.loads(line) for line in (folder / 'stdout').read_text().split('\n') if line.strip()]
        terminal = [event for event in events if event.get('type') == 'result']
        if (len(terminal) != 1 or terminal[0].get('is_error') or
                set(terminal[0].get('modelUsage', {})) != {'claude-fable-5-1'}):
            raise ValueError('unknown reviewer identity/usage')
        if any(item.get('type') == 'tool_use' for event in events
               for item in event.get('message', {}).get('content', [])):
            raise ValueError('unexpected reviewer tool use')
        usage = terminal[0]['modelUsage']['claude-fable-5-1']
        keys = ('inputTokens', 'cacheReadInputTokens', 'cacheCreationInputTokens', 'outputTokens')
        if any(type(usage.get(key)) is not int or usage[key] < 0 for key in keys):
            raise ValueError('invalid reviewer counters')
        thinking = usage.get('thinkingTokens')
        if type(thinking) is not int or not 0 <= thinking <= usage['outputTokens']:
            raise ValueError('unknown reviewer reasoning counter')
        # Anthropic input excludes caches; OUTPUT already includes thinking.
        total['input_tokens'] += sum(usage[key] for key in keys[:3])
        total['output_tokens'] += usage['outputTokens']
    return total, pending


def run(plan, out):
    out.mkdir(exist_ok=False)
    work, home = Path(plan['work']), Path(plan['home'])
    name = 'devlyn-0210-' + uuid.uuid4().hex
    argv = ['create', '--name', name, '--label', 'devlyn.task=0210',
            '--network', plan['network'], '--cap-drop', 'ALL', '--security-opt', 'no-new-privileges',
            '--security-opt', 'seccomp=unconfined', '--read-only', '--restart=no',
            '--pids-limit', '256', '--memory', '4g', '--cpus', '2',
            '--tmpfs', '/tmp:rw,nosuid,exec,size=536870912',
            '--mount', f'type=bind,src={work},dst=/work',
            '--mount', f'type=bind,src={home},dst=/home/participant',
            '--mount', f'type=bind,src={plan["control"]},dst=/control,readonly',
            '--mount', f'type=bind,src={plan["auth"]}/codex.json,dst=/home/participant/.codex/auth.json,readonly',
            '--mount', f'type=bind,src={plan["auth"]}/claude.json,dst=/credentials/claude.json,readonly',
            '--mount', f'type=bind,src={work}/.devlyn/caller.json,dst=/work/.devlyn/caller.json,readonly',
            '--env', 'HOME=/home/participant', '--env', 'CODEX_HOME=/home/participant/.codex',
            '--env', 'GIT_CONFIG_GLOBAL=/dev/null', '--env', 'GIT_CONFIG_NOSYSTEM=1',
            '--env', 'GIT_TEMPLATE_DIR=', plan['image'], *plan['argv']]
    record = dict(plan=plan, plan_sha256=hashlib.sha256(json.dumps(plan, sort_keys=True).encode()).hexdigest(), create_argv=argv,
                  source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  accounting_sha256=hashlib.sha256(ACCOUNTING.read_bytes()).hexdigest())
    (out / 'started.json').write_text(json.dumps(record, indent=2))
    try:
        cid = docker(*argv)
    except (OSError, subprocess.SubprocessError) as exc:
        record.update(failure=str(exc), classes=['INFRA_INVALID'], model_dispatched=False)
        (out / 'result.json').write_text(json.dumps(record, indent=2))
        raise
    record['container_id'] = cid
    (out / 'started.json').write_text(json.dumps(record, indent=2))
    start = time.monotonic()
    meter, failure, terminal = None, None, None
    budget_exceeded = False
    process = None
    snapshots = []
    try:
        initial = json.loads(docker('inspect', cid))[0]
        (out / 'initial-inspect.json').write_text(json.dumps(initial, indent=2))
        host = initial['HostConfig']
        mounts = {m['Destination']: (m['Source'], m['RW'])
                  for m in initial['Mounts'] if m['Type'] == 'bind'}
        expected_mounts = {'/work': (str(work), True), '/home/participant': (str(home), True),
            '/control': (plan['control'], False),
            '/home/participant/.codex/auth.json': (plan['auth'] + '/codex.json', False),
            '/credentials/claude.json': (plan['auth'] + '/claude.json', False),
            '/work/.devlyn/caller.json': (str(work / '.devlyn/caller.json'), False)}
        if (not plan['image'].startswith('sha256:') or initial['Image'] != plan['image'] or
                initial['Config']['User'] != '501:501' or host['Privileged'] or host['PidMode'] or
                host['RestartPolicy']['Name'] != 'no' or not host['ReadonlyRootfs'] or
                host['CapDrop'] != ['ALL'] or set(host['SecurityOpt']) != {'no-new-privileges', 'seccomp=unconfined'} or
                host['PidsLimit'] != 256 or host['Memory'] != 4294967296 or host['NanoCpus'] != 2000000000 or
                host['NetworkMode'] != plan['network'] or mounts != expected_mounts or
                host['Tmpfs'] != {'/tmp': 'rw,nosuid,exec,size=536870912'}):
            raise ValueError('unexpected container identity/isolation/mounts')
        with (out / 'stdout').open('xb') as stdout, (out / 'stderr').open('xb') as stderr:
            process = subprocess.Popen(['docker', 'start', '-a', cid], stdout=stdout, stderr=stderr)
            while process.poll() is None:
                if time.monotonic() - start >= plan['wall_seconds'] - 30:
                    budget_exceeded = True
                    raise TimeoutError('cell deadline reserve reached')
                raw = (out / 'stdout').read_bytes()
                events = [json.loads(line) for line in raw.split(b'\n')[:-1] if line.strip()]
                if any(e.get('type') in ('error', 'turn.failed') for e in events):
                    raise ValueError('native error/retry event; stop')
                owner = next((e['thread_id'] for e in events if e.get('type') == 'thread.started'), None)
                if owner and meter is None:
                    meter = accounting.Rollouts(home / '.codex/sessions', owner,
                        input_limit=plan['input_tokens'], output_limit=plan['output_tokens'],
                        dispatch_limit=plan['model_calls'], stale_seconds=float('inf'), started=start)
                if meter:
                    value = meter.poll(time.monotonic())
                    review, pending = reviews(work)
                    combined = {key: value['totals'][key] + review[key]
                                for key in ('input_tokens', 'output_tokens')}
                    combined['calls'] = value['dispatches'] + review['calls']
                    if not snapshots or combined != snapshots[-1]['combined']:
                        snapshots.append(dict(seconds=time.monotonic()-start, combined=combined,
                                              native=value, reviews=review, pending=pending))
                    if (value['exceeded'] or combined['input_tokens'] > plan['input_tokens'] or
                            combined['output_tokens'] > plan['output_tokens'] or
                            combined['calls'] > plan['model_calls'] or review['calls'] > 2):
                        budget_exceeded = True
                        raise ValueError('observed budget exceeded')
                time.sleep(.1)
        if process.returncode:
            raise ValueError('native/container exit ' + str(process.returncode))
        final_events = [json.loads(line) for line in (out / 'stdout').read_text().split('\n') if line.strip()]
        if any(e.get('type') in ('error', 'turn.failed') for e in final_events):
            raise ValueError('terminal native error/retry event; stop')
        if meter is None:
            events = [json.loads(line) for line in (out / 'stdout').read_text().split('\n') if line.strip()]
            owner = next((e['thread_id'] for e in events if e.get('type') == 'thread.started'), None)
            if owner is None:
                raise ValueError('missing owner telemetry')
            meter = accounting.Rollouts(home / '.codex/sessions', owner,
                input_limit=plan['input_tokens'], output_limit=plan['output_tokens'],
                dispatch_limit=plan['model_calls'], stale_seconds=float('inf'), started=start)
        native = meter.finish(time.monotonic())
        review, pending = reviews(work)
        if pending:
            raise ValueError('unfinished reviewer usage')
        combined = {key: native['totals'][key] + review[key]
                    for key in ('input_tokens', 'output_tokens')}
        combined['calls'] = native['dispatches'] + review['calls']
        terminal = dict(native=native, reviews=review, combined=combined)
        if (native['exceeded'] or combined['input_tokens'] > plan['input_tokens'] or
                combined['output_tokens'] > plan['output_tokens'] or
                combined['calls'] > plan['model_calls'] or review['calls'] > 2):
            budget_exceeded = True
            raise ValueError('terminal observed budget exceeded')
        for path in (home / '.codex/sessions').rglob('*.jsonl'):
            contexts = []
            for line in path.read_text().split('\n'):
                if not line.strip(): continue
                event = json.loads(line)
                if event.get('type') == 'turn_context':
                    contexts.append((event['payload']['model'], event['payload'].get('effort')))
                if event.get('type') == 'event_msg' and event['payload'].get('type') == 'model_reroute':
                    raise ValueError('native model reroute')
            if not contexts or set(contexts) != {(plan['model'], plan['effort'])}:
                raise ValueError('native model context mismatch or missing')
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as exc:
        failure = f'{type(exc).__name__}: {exc}'
        budget_exceeded = budget_exceeded or isinstance(exc, TimeoutError)
    finally:
        record.update(failure=failure, terminal=terminal, snapshots=snapshots)
        (out / 'result.json').write_text(json.dumps(record, indent=2))
        try:
            before = json.loads(docker('inspect', cid))[0]['State']
            if before['Running']:
                try:
                    docker('kill', cid)
                except subprocess.SubprocessError as exc:
                    current = json.loads(docker('inspect', cid))[0]['State']
                    record['kill_error'] = str(exc)
                    if current['Running'] or current['Pid'] != 0:
                        raise
                    record['kill_raced_with_exit'] = True
            state = json.loads(docker('inspect', cid))[0]['State']
            record['state'] = state
            if state['Running'] or state['Pid'] != 0:
                raise ValueError('container survivor; retain and stop')
            if process is not None:
                process.wait(timeout=5)
            docker('rm', cid)
            record['container_removed'] = True
        except (OSError, ValueError, subprocess.SubprocessError) as exc:
            record['teardown_error'] = str(exc)
            record['failure'] = record['failure'] or 'local teardown failed'
        record['seconds'] = time.monotonic()-start
        if record['seconds'] > plan['wall_seconds']:
            budget_exceeded = True
            record['deadline_exceeded'] = True
            record['failure'] = record['failure'] or 'overall deadline exceeded'
        record['classes'] = []
        if budget_exceeded: record['classes'].append('BUDGET_EXCEEDED')
        if terminal is None: record['classes'].append('UNKNOWN')
        if terminal is None or record.get('teardown_error') or (record['failure'] and not budget_exceeded):
            record['classes'].append('INFRA_INVALID')
        (out / 'result.json').write_text(json.dumps(record, indent=2))
    print(json.dumps(dict(seconds=record['seconds'], failure=record['failure'], terminal=terminal)))
    return 1 if record['failure'] or record['seconds'] > plan['wall_seconds'] else 0


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('plan', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    sys.exit(run(json.loads(args.plan.read_text()), args.output))
