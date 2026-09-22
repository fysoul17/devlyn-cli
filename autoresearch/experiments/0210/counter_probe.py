"""Credential-free native recursive-counter control; never a model draw."""
import hashlib
import http.server
import json
from pathlib import Path
import shutil
import subprocess
import threading

out = Path('/work/output')
out.mkdir()
home = Path('/work/codex-home')
home.mkdir()
repo = Path('/work/repo')
repo.mkdir()
subprocess.run(['git', 'init', '-q', str(repo)], check=True)
requests = []
parent_turns = 0
lock = threading.Lock()


class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass  # Full request/response evidence is retained below.

    def do_POST(self):
        global parent_turns
        request = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
        child = any(item.get('type') == 'agent_message' and
                    item.get('recipient') == '/root/counter_child' for item in request['input'])
        with lock:
            if not child: parent_turns += 1
            turn = parent_turns
            rid = str(len(requests) + 1)
            usage = {'input_tokens': 100 if child else 10,
                     'input_tokens_details': {'cached_tokens': 50 if child else 2},
                     'output_tokens': 10 if child else 1,
                     'output_tokens_details': {'reasoning_tokens': 0},
                     'total_tokens': 110 if child else 11}
            requests.append({'role': 'child' if child else 'owner', 'request': request,
                             'response_id': rid, 'supplied_usage': usage})
        item = {'type': 'message', 'id': 'message-'+rid, 'role': 'assistant',
                'content': [{'type': 'output_text', 'text': 'COUNTER_DONE'}]}
        if not child and turn == 1:
            item = {'type': 'custom_tool_call', 'namespace': 'functions', 'name': 'exec',
                    'call_id': 'call-'+rid,
                    'input': 'text(await tools.exec_command({cmd:"printf COUNTER_SHELL",login:false}));'}
        elif not child and turn in (2, 3):
            item = {'type': 'function_call', 'namespace': 'collaboration',
                    'name': 'spawn_agent' if turn == 2 else 'wait_agent',
                    'call_id': 'call-'+rid,
                    'arguments': json.dumps({'message': 'CHILD_NATIVE_COUNTER. Reply done.',
                                             'task_name': 'counter_child'} if turn == 2 else {'timeout_ms': 10000})}
        events = [{'type': 'response.created', 'response': {'id': 'response-'+rid}},
                  {'type': 'response.output_item.done', 'item': item},
                  {'type': 'response.completed', 'response': {'id': 'response-'+rid, 'usage': usage}}]
        body = ''.join('data: '+json.dumps(e)+'\n\n' for e in events).encode()
        self.send_response(200)
        self.send_header('Content-Type', 'text/event-stream')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)


with http.server.ThreadingHTTPServer(('127.0.0.1', 0), Handler) as server:
    thread = threading.Thread(target=server.serve_forever)
    thread.start()
    config = f'''model = "gpt-6-astra"
model_reasoning_effort = "high"
model_provider = "synthetic"
approval_policy = "never"
sandbox_mode = "workspace-write"
project_doc_max_bytes = 0
web_search = "disabled"
[model_providers.synthetic]
name = "Synthetic native counter control"
base_url = "http://127.0.0.1:{server.server_port}/v1"
wire_api = "responses"
requires_openai_auth = false
request_max_retries = 0
stream_max_retries = 0
[features]
rollout_budget = false
shell_snapshot = false
[features.multi_agent_v2]
enabled = true
[agents]
default_subagent_model = "gpt-6-astra"
default_subagent_reasoning_effort = "high"
'''
    (home/'config.toml').write_text(config)
    try:
        result = subprocess.run(['codex', 'exec', '--strict-config', '--ignore-rules', '--json',
                                 '-C', str(repo), 'ROOT_NATIVE_COUNTER. Reply done.'],
                                env={'PATH': '/opt/codex/bin:/usr/local/bin:/usr/bin:/bin',
                                     'HOME': str(home), 'CODEX_HOME': str(home), 'TMPDIR': '/tmp'},
                                capture_output=True, timeout=30)
        (out/'stdout.jsonl').write_bytes(result.stdout)
        (out/'stderr').write_bytes(result.stderr)
        (out/'exit.json').write_text(json.dumps({'exit_code': result.returncode, 'actual_model_calls': 0}))
    finally:
        server.shutdown()
        thread.join()
        (out/'requests.json').write_text(json.dumps(requests, indent=2))
        shutil.copytree(home, out/'native-home')
