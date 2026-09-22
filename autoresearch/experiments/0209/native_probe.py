"""Exercise installed Codex against loopback synthetic usage, with no credentials."""
import argparse
import http.server
import json
import os
from pathlib import Path
import shutil
import shlex
import subprocess
import tempfile
import threading
import hashlib


def run_case(name, usage, scratch, output, hook=None):
    requests = []

    class Handler(http.server.BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass  # HTTP access logs are replaced by retained request bodies below.

        def do_POST(self):
            requests.append(json.loads(self.rfile.read(int(self.headers['Content-Length']))))
            events = [
                {'type': 'response.created', 'response': {'id': 'synthetic-response'}},
                {'type': 'response.output_item.done', 'item': {
                    'type': 'message', 'id': 'synthetic-message', 'role': 'assistant',
                    'content': [{'type': 'output_text', 'text': 'SYNTHETIC_DONE'}]}},
                {'type': 'response.completed', 'response': {
                    'id': 'synthetic-response', 'usage': usage}},
            ]
            if hook and len(requests) == 1:
                events[1] = {'type': 'response.output_item.done', 'item': {
                    'type': 'function_call', 'namespace': 'collaboration',
                    'name': 'spawn_agent', 'call_id': 'synthetic-spawn',
                    'arguments': json.dumps({'message': 'Reply child done, no tools.',
                                             'task_name': 'synthetic_child'})}}
                if name == 'shell-hook-deny':
                    events[1]['item'] = {'type': 'custom_tool_call', 'namespace': 'functions',
                        'name': 'exec', 'call_id': 'synthetic-shell',
                        'input': 'text(await tools.exec_command({cmd:"printf CONTROL_EXECUTED",login:false}));'}
            body = ''.join('data: ' + json.dumps(event) + '\n\n' for event in events).encode()
            self.send_response(200)
            self.send_header('Content-Type', 'text/event-stream')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    target = output / name
    target.mkdir()
    with tempfile.TemporaryDirectory(prefix=name + '-', dir=scratch) as raw:
        home = Path(raw)
        subprocess.run(['git', 'init', '-q', raw], check=True, capture_output=True)
        with http.server.ThreadingHTTPServer(('127.0.0.1', 0), Handler) as server:
            worker = threading.Thread(target=server.serve_forever)
            worker.start()
            config = f'''model = "gpt-6-astra"
model_provider = "synthetic"
approval_policy = "never"
sandbox_mode = "read-only"
web_search = "disabled"
[model_providers.synthetic]
name = "Loopback synthetic control"
base_url = "http://127.0.0.1:{server.server_port}/v1"
wire_api = "responses"
requires_openai_auth = false
request_max_retries = 0
stream_max_retries = 0
[features]
shell_snapshot = false
[features.rollout_budget]
enabled = true
limit_tokens = 100
reminder_at_remaining_tokens = [50]
prefill_token_weight = 1.0
sampling_token_weight = 1.0
'''
            (home / 'config.toml').write_text(config)
            (target / 'config.toml').write_text(config)
            if hook:
                script = home / 'hook.py'
                script.write_text('import json,sys\nfrom pathlib import Path\n'
                                  'p=json.load(sys.stdin)\n'
                                  f'Path({str(home / "hook-input.json")!r}).write_text(json.dumps(p))\n'
                                  + hook)
                matcher = 'spawn_agent|Agent' if name == 'hook-named-deny' else '*'
                hooks = {'hooks': {'PreToolUse': [{'matcher': matcher, 'hooks': [{
                    'type': 'command', 'command': shlex.join([shutil.which('python3'), str(script)]),
                    'timeout': 2}]}], 'SessionStart': [{'hooks': [{'type': 'command',
                    'command': shlex.join([shutil.which('python3'), '-c',
                        f'from pathlib import Path; Path({str(home / "session-hook-ran")!r}).touch()'])}]}]}}
                (home / 'hooks.json').write_text(json.dumps(hooks))
                (target / 'hook.py').write_text(script.read_text())
            env = {key: os.environ[key] for key in ('PATH', 'LANG', 'LC_ALL') if key in os.environ}
            env.update(HOME=raw, CODEX_HOME=raw, TMPDIR=raw)
            argv = [shutil.which('codex'), 'exec', '--strict-config', '--skip-git-repo-check',
                    '--dangerously-bypass-hook-trust', '--json', '-C', raw,
                    'Reply SYNTHETIC_DONE. Do not use tools.']
            try:
                result = subprocess.run(argv, cwd=raw, env=env, capture_output=True, timeout=30)
                (target / 'stdout.jsonl').write_bytes(result.stdout)
                (target / 'stderr.txt').write_bytes(result.stderr)
                events = [json.loads(line) for line in result.stdout.splitlines() if line.strip()]
                summary = {'case': name, 'exit_code': result.returncode,
                           'requests': len(requests), 'supplied_usage': usage,
                           'events': events, 'provider': 'loopback synthetic; no model call'}
                if hook:
                    witness = home / 'hook-input.json'
                    summary['hook_input'] = json.loads(witness.read_text()) if witness.exists() else None
                    summary['session_hook_ran'] = (home / 'session-hook-ran').exists()
                    summary['sessions'] = [{key: json.loads(line)['payload'].get(key)
                        for key in ('id', 'source', 'parent_thread_id', 'model_provider')}
                        for path in (home / 'sessions').rglob('*.jsonl')
                        for line in path.read_text().splitlines()
                        if json.loads(line).get('type') == 'session_meta']
            finally:
                server.shutdown()
                worker.join()
                (target / 'requests.json').write_text(json.dumps(requests, indent=2))
    (target / 'result.json').write_text(json.dumps(summary, indent=2))
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scratch', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    (args.output / 'identity.json').write_text(json.dumps({
        'source_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'codex': shutil.which('codex'),
        'version': subprocess.check_output(['codex', '--version'], text=True).strip(),
        'prediction': 'Output stops; cache/override differ; valid wildcard denies; hook failures proceed.'
    }, indent=2))
    results = []
    cases = [('below', 10, 0, 10, None), ('output-over', 10, 0, 101, None),
             ('cached-input-over', 1000, 1000, 1, None), ('provider-zero', 1000, 0, 101, 0)]
    for name, input_tokens, cached, output_tokens, units in cases:
        usage = {'input_tokens': input_tokens, 'input_tokens_details': {'cached_tokens': cached},
                 'output_tokens': output_tokens, 'output_tokens_details': {'reasoning_tokens': 0},
                 'total_tokens': input_tokens + output_tokens}
        if units is not None:
            usage['codex_rollout_budget_units'] = units
        result = run_case(name, usage, args.scratch, args.output)
        results.append(result)
        print(json.dumps(result), flush=True)
    hooks = {
        'hook-deny': 'print(json.dumps({"hookSpecificOutput":{"hookEventName":"PreToolUse",'
                     '"permissionDecision":"deny","permissionDecisionReason":"CONTROL_DENY"}}))\n',
        'hook-malformed': 'print("{malformed")\n',
        'hook-exit1': 'sys.exit(1)\n',
        'hook-exit2': 'print("CONTROL_DENY",file=sys.stderr)\nsys.exit(2)\n',
    }
    hooks['shell-hook-deny'] = hooks['hook-deny']
    hooks['hook-named-deny'] = hooks['hook-deny']
    for name, hook in hooks.items():
        result = run_case(name, {'input_tokens': 1, 'output_tokens': 1, 'total_tokens': 2},
                          args.scratch, args.output, hook)
        results.append(result)
        print(json.dumps(result), flush=True)
    failures = []
    for result in results:
        name = result['case']
        over = name == 'output-over'
        expected_exit = 1 if over else 0
        expected_event = 'turn.failed' if over else 'turn.completed'
        if result['exit_code'] != expected_exit or not any(
                event['type'] == expected_event for event in result['events']):
            failures.append(name + ': unexpected terminal')
        if over and not any(event.get('error', {}).get('message') ==
                            'shared rollout token budget exhausted' for event in result['events']):
            failures.append(name + ': missing budget error')
        if name in hooks:
            denied = name in ('hook-deny', 'hook-exit2', 'shell-hook-deny')
            if (not result['session_hook_ran'] or
                    bool(result['hook_input']) != (name != 'hook-named-deny') or
                    len({session['id'] for session in result['sessions']}) != (1 if denied else 2) or
                    result['requests'] not in ([2] if denied else [2, 3])):
                failures.append(name + ': unexpected hook/dispatch evidence')
            wire = json.loads((args.output / name / 'requests.json').read_text())
            spawn_outputs = [item['output'] for request in wire for item in request['input']
                             if item.get('type') == 'function_call_output' and
                             item.get('call_id') == 'synthetic-spawn']
            if name != 'shell-hook-deny' and not any(
                    ('CONTROL_DENY' in value if denied else '"task_name":"/root/synthetic_child"' in value)
                    for value in spawn_outputs):
                failures.append(name + ': missing independent tool-result witness')
            if name == 'shell-hook-deny' and not any(
                    'Command blocked by PreToolUse hook: CONTROL_DENY.' in json.dumps(item.get('output'))
                    for request in wire for item in request['input']
                    if item.get('type') == 'custom_tool_call_output' and
                    item.get('call_id') == 'synthetic-shell'):
                failures.append(name + ': missing shell-denial result')
        elif result['requests'] != 1:
            failures.append(name + ': unexpected request count')
        elif not over:
            totals = [event['usage'] for event in result['events'] if event['type'] == 'turn.completed']
            supplied = result['supplied_usage']
            if len(totals) != 1 or any(totals[0].get(key) != supplied[key]
                                      for key in ('input_tokens', 'output_tokens')):
                failures.append(name + ': terminal usage mismatch')
    verdict = {'status': 'FAIL' if failures else 'EXPECTED_NATIVE_BEHAVIOR_REPRODUCED',
               'cases': len(results), 'failures': failures, 'comparison_admitted': False}
    (args.output / 'verdict.json').write_text(json.dumps(verdict, indent=2))
    print(json.dumps(verdict))
    if failures:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
