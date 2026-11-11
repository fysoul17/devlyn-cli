"""0265 dry end-to-end rehearsal: the real apparatus from the seal to the token, with fakes only at its edges.

Fakes: the `docker`, `security` and `claude` executables (this file run as `fake-docker`, `fake-security`,
`fake-claude`) and, inside each driver process, the Anthropic profile and usage endpoints (this file run as `launch`,
which then runs driver.py unchanged). The fake engines write what the real ones leave: the status line, the HOME
release, Claude's stream and transcript, Codex's stream and rollout trace (its first request in Codex 0.164.0's real
model-input shape, fixtures/cell/prompt-input-*.json) and Codex's own caches in CODEX_HOME, and one allowed product
edit. The launch probe's containers
answer as the recording shims and `codex debug prompt-input` do. Everything else is the code a real run executes:
driver.py, run_cell.py, prepare, cell (its identity), usage, quota, locate and check modules, assess, instructions
seal (the launch probe) and seal-forms, then judge.py, recheck.py, harm_check.py, fc_judge.py and decide.py. The
control tree and the pinned sources are copied from the runtime root (read only there), so the test skips when that
root is not built. No model, keychain, network or real container is touched.

Run: python3 -m pytest -q autoresearch/experiments/0265/test_integration.py (several minutes).
"""
import base64
import copy
import hashlib
import io
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from unittest import mock
import urllib.error
import uuid

HERE = Path(__file__).resolve().parent
LIVE = Path.home() / '.local/share/nx01/0265-live'
IMAGE = 'sha256:' + '0265' * 16
GIB = 2**30
CLAIM = 'The writer is safe in every case.'
DEVLYN = ['node', '/install/package/bin/devlyn.js', 'run']
COUNTERS = ('input_tokens', 'cached_input_tokens', 'cache_write_input_tokens', 'output_tokens',
            'reasoning_output_tokens')
# What every Codex session leaves in CODEX_HOME, both arms (D-b): its own caches, pruned once a measured cell is
# graded, and state that stays.
CODEX_CACHES = {'home/.codex/.tmp': {'plugins.sync.lock': '', 'plugins/.git/HEAD': 'ref: refs/heads/main\n'},
                'home/.codex/plugins/cache/openai-curated-remote': {
                    'github/1.0.0/.codex-plugin/plugin.json': '{"name": "github"}\n'},
                'home/.codex/plugins/.remote-plugin-install-staging': {'sites/plugin.json': '{"name": "sites"}\n'}}
CODEX_KEPT = {'home/.codex/state_5.sqlite': 'state\n', 'home/.codex/skills/.system/imagegen/SKILL.md': '---\n'}
ACCOUNT, ORGANIZATION = 'account-0265', 'org-0265'
CODEX_ACCOUNT = 'codex-account-0265'


# ---------------------------------------------------------------- fakes (run as separate processes)

def state():
    return Path(os.environ['FAKE_STATE'])


def note(name, record):
    """One JSON line appended to a fake's log (O_APPEND: lines from concurrent processes never interleave)."""
    with (state() / name).open('a') as stream:
        stream.write(json.dumps(record) + '\n')


def consume(marker):
    """True for exactly one caller: an injection file is renamed away atomically."""
    try:
        os.rename(state() / marker, state() / f'{marker}.used-{uuid.uuid4().hex}')
        return True
    except FileNotFoundError:
        return False


def rules():
    return json.loads((state() / 'rules.json').read_text())


def mounts(args):
    found = {}
    for index, arg in enumerate(args):
        if arg == '--mount':
            fields = dict(part.split('=', 1) for part in args[index + 1].split(',') if '=' in part)
            if 'dst' in fields:
                found[fields['dst']] = fields.get('src')
    return found


def option(args, flag):
    return args[args.index(flag) + 1] if flag in args else None


def container(name):
    path = state() / 'containers' / f'{name}.json'
    return json.loads(path.read_text()) if path.is_file() else None


def save(record):
    for key in (record['cid'], record['name']):
        (state() / 'containers' / f'{key}.json').write_text(json.dumps(record))


def drop(record):
    for key in (record['cid'], record['name']):
        (state() / 'containers' / f'{key}.json').unlink(missing_ok=True)


def append(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('a') as stream:
        stream.write(text)


def devlyn_home(home, install, engine):
    """What `devlyn run` leaves in a B HOME: the release and, for Codex, the session plugin's projection."""
    release = home / '.devlyn/cli/releases/devlyn-cli/4.3.30'
    release.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(install / 'package/release.json', release / 'release.json')
    if engine == 'codex':
        folder = home / '.codex/plugins/cache/devlyn-harness-v4-3-30/devlyn/4.3.30'
        (folder / '.codex-plugin').mkdir(parents=True, exist_ok=True)
        (folder / '.codex-plugin/plugin.json').write_text('{"name": "devlyn"}\n')
        (folder / '.devlyn-harness-projection.json').write_text('{"schemaVersion": 1}\n')


def model_input(arm, home):
    """Codex 0.164.0's model input as `codex debug prompt-input` prints it (the real fixtures), B's text the plan's."""
    name = 'control' if (home / '.codex/AGENTS.md').exists() else arm
    items = json.loads((HERE / f'fixtures/cell/prompt-input-{name}.json').read_text())
    if name == 'B':
        items[2]['content'][0]['text'] = (state() / 'session_text.txt').read_text()
    return items


def q2(record):
    """The launch probe's containers (instructions.py seal): what the recording shim records for the engine call,
    devlyn run's status line, HOME and --strict-mcp-config refusal, and `codex debug prompt-input`'s output."""
    instructions = load('instructions', HERE / 'instructions.py')
    shapes =json.loads((HERE / 'fixtures/cell/shapes.json').read_text())
    where, command = record['mounts'], record['command']
    home, arm_b = Path(where['/home/participant']), command[:3] == DEVLYN
    engine = command[3] if arm_b else command[0]
    if '--strict-mcp-config' in command:
        sys.stderr.write(instructions.REFUSED.format(engine=engine) + '\n')
        return 2
    if arm_b:
        devlyn_home(home, Path(where['/install']), engine)
    status = shapes['status_lines'][engine] + '\n' if arm_b else ''
    if 'prompt-input' in command:
        sys.stdout.write(json.dumps(model_input('B' if arm_b else 'A', home)))
        sys.stderr.write(status)
        return 0
    text, files, env = (state() / 'session_text.txt').read_text(), {}, dict(record['env'])
    if not arm_b:
        planned = []
    elif engine == 'claude':
        appended = f'/tmp/devlyn-run-{uuid.uuid4().hex[:6]}/devlyn-instructions.md'
        planned = ['--plugin-dir', f'{instructions.RELEASE_ROOT}/native/claude', '--append-system-prompt-file', appended]
        files[appended] = base64.b64encode(text.encode()).decode()
    else:
        market = instructions.MARKET
        planned = ['-c', f'marketplaces = {{ "{market}" = {{ source_type = "local", source = '
                         f'"{instructions.RELEASE_ROOT}/native/codex" }} }}',
                   '-c', f'plugins = {{ "devlyn@{market}" = {{ enabled = true }} }}',
                   '-c', 'developer_instructions = ' + json.dumps(text)]
    if arm_b:
        env.update(DEVLYN_NODE='/usr/local/bin/node', DEVLYN_HARNESS_ROOT=instructions.RELEASE_ROOT)
    owner = command[4:] if arm_b else command[1:]
    (Path(where['/q2/records']) / f'{engine}-{uuid.uuid4().hex}.json').write_text(json.dumps(dict(
        argv=planned + owner, env=env, files=files)))
    sys.stderr.write(status)
    return 0


def owner_engine(record):
    """The owner session: devlyn run's refusal or status line, then the engine's own evidence and one edit."""
    shapes = json.loads((HERE / 'fixtures/cell/shapes.json').read_text())
    where = record['mounts']
    cell, home, harness = Path(where['/cell']), Path(where['/home/participant']), Path(where['/harness'])
    name, command = cell.parent.name, record['command']
    arm_b = command[:3] == DEVLYN
    engine = command[3] if arm_b else command[0]
    if arm_b and any(consume(f'launch-fault-{name}{suffix}') for suffix in ('', '-1', '-2')):
        sys.stderr.write('devlyn run: run-argument-unsupported {"engine":"%s","argument":"--fake"}\n' % engine)
        return 2
    sys.stderr.write('an unrelated engine warning\n')
    if arm_b:
        sys.stderr.write(shapes['status_lines'][engine] + '\n')
        devlyn_home(home, Path(where['/install']), engine)
    caller = json.loads((harness / 'caller.json').read_text())
    target = cell / 'work' / caller['allowed'][0]
    append(target, '\n# fake owner change\n' if target.suffix == '.py' else '\n// fake owner change\n')
    if name in rules()['duplicate'] + rules()['differ']:  # 4.3.30 keeps a refused delivery's edits in the anchor too
        tree = cell / '.devlyn-worktrees/work/x'
        subprocess.run(['git', '-C', str(cell / 'work'), 'worktree', 'add', '-q', '-b', 'task/x', str(tree)],
                       check=True, capture_output=True, env=dict(os.environ, GIT_CONFIG_GLOBAL='/dev/null',
                                                                 GIT_CONFIG_NOSYSTEM='1'))
        (cell / 'work/.git/worktrees/x/gitdir').write_text('/cell/.devlyn-worktrees/work/x/.git\n')  # container path
        shutil.copyfile(target, tree / caller['allowed'][0])
        if name in rules()['differ']:  # the worktree's content differs from the anchor's
            append(tree / caller['allowed'][0], '\n// another change\n')
    if name in rules()['switch_login']:  # the owner's app switches the host's default login while this cell runs
        (state() / 'account.txt').write_text(rules()['switch_login'][name])
    if name in rules()['assessor_fault']:  # one seat of this cell's own assessment (same lane process) answers nothing
        (state() / f'assessor-fault-{os.getppid()}').write_text('inject once\n')
    final = CLAIM if name in rules()['claim'] else 'Done. Every public check passes.'
    if engine == 'claude':
        session = str(uuid.uuid4())
        init = dict(copy.deepcopy(shapes['claude_init']), session_id=session)
        if arm_b:
            init['plugins'].append(shapes['devlyn_plugin'])
        usage = dict(input_tokens=100, cache_read_input_tokens=0, cache_creation_input_tokens=0, output_tokens=10)
        events = [init, dict(type='assistant', session_id=session, parent_tool_use_id=None, message=dict(
                      id='msg_0', role='assistant', model='claude-opus-5-5',
                      content=[dict(type='text', text='I will make the change.')])),
                  dict(type='result', subtype='success', is_error=False, result=final, session_id=session,
                       modelUsage={'claude-opus-5-5': dict(inputTokens=100, cacheReadInputTokens=0,
                                                           cacheCreationInputTokens=0, outputTokens=10)})]
        append(home / '.claude/projects/-cell-work' / f'{session}.jsonl', json.dumps(dict(
            type='assistant', sessionId=session, message=dict(id='msg_1', model='claude-opus-5-5',
                                                              stop_reason='end_turn', usage=usage))) + '\n')
    else:
        for root, files in CODEX_CACHES.items():
            for path, body in files.items():
                append(cell.parent / root / path, body)
        for path, body in CODEX_KEPT.items():
            append(cell.parent / path, body)
        thread = str(uuid.uuid4())
        trace = cell / 'trace' / f'trace-1-{thread}'
        (trace / 'payloads').mkdir(parents=True)
        request = dict(model='gpt-6-astra', input=model_input('B' if arm_b else 'A', home))
        payloads = {'meta.json': dict(model='gpt-6-astra'), 'request.json': request,
                    'configured.json': dict(thread_id=thread, model='gpt-6-astra', reasoning_effort='high'),
                    'response.json': dict(token_usage=dict.fromkeys(COUNTERS, 7))}
        for file, body in payloads.items():
            (trace / 'payloads' / file).write_text(json.dumps(body))
        (trace / 'manifest.json').write_text(json.dumps(dict(
            schema_version=1, rollout_id=thread, root_thread_id=thread, started_at_unix_ms=int(time.time() * 1000),
            raw_event_log='trace.jsonl')))
        rows = [dict(type='thread_started', thread_id=thread, metadata_payload=dict(path='payloads/meta.json')),
                dict(type='protocol_event_observed', event_type='session_configured',
                     event_payload=dict(path='payloads/configured.json')),
                dict(type='inference_started', inference_call_id='call-1', thread_id=thread, model='gpt-6-astra',
                     request_payload=dict(path='payloads/request.json')),
                dict(type='inference_completed', inference_call_id='call-1',
                     response_payload=dict(path='payloads/response.json')),
                dict(type='rollout_ended', status='completed')]
        (trace / 'trace.jsonl').write_text(''.join(json.dumps(dict(seq=seq, thread_id=thread, payload=row)) + '\n'
                                                   for seq, row in enumerate(rows)))
        events = [dict(type='thread.started', thread_id=thread),
                  dict(type='item.completed', item=dict(type='agent_message', text='I will make the change.')),
                  dict(type='item.completed', item=dict(type='agent_message', text=final)),
                  dict(type='turn.completed', usage=dict(input_tokens=7, cached_input_tokens=7, output_tokens=7))]
    sys.stdout.write(''.join(json.dumps(event) + '\n' for event in events))
    return 0


def witness(record):
    """judge.py's witness containers (witness-<tree>-<pass>) and probe containers (probe-<cell>)."""
    name, command, chosen = record['name'], record['command'], rules()
    if name.startswith('probe-'):
        cell = name[len('probe-'):]
        if consume(f'probe-unassessable-{cell}'):
            print(json.dumps({'class': 'unassessable', 'store_preserved': None}))
            return 0
        found = ('other' if '-F11-' in cell else 'html_400' if '-F10-claude-B-' in cell else 'json_error_400')
        print(json.dumps({'class': found, 'store_preserved': True}))
        return 0
    tree, stem = name[len('witness-'):].rsplit('-', 1)[0], Path(command[-1]).stem
    if stem == 'd3-parseoptions-override':
        print('P0258-WITNESS public')
        return 0
    if [tree, stem] in chosen['reproduces']:
        print('HUNG tests/test_utils/test_writer.py::test_reader_dies\n  File "src/click/utils.py", line 1')
        return 1
    if [tree, stem] in chosen['unresolved']:
        sys.stderr.write('witness infrastructure failed\n')
        return 2
    return 3 if stem == 'f10-nonobject-items-file' and '-codex-' in tree else 0


def check_container(args, command):
    """0233/check.py's containers: public checks, the D oracle and the oracle.js rows. Each holds 0.05 s and logs its
    interval with the process that ran it, so the test can see whether two lanes' check phases overlapped."""
    tasks = {t['id']: t for t in json.loads((HERE.parent / '0233/tasks.json').read_text())['tasks']}
    endpoints = json.loads((HERE / 'endpoints.json').read_text())
    cell = Path(mounts(args)['/cell/work']).parent.name
    task = 'SMOKE' if cell.startswith(('smoke-', 'rehearsal-', 'x0')) else cell.split('-')[1]
    start = time.time()
    time.sleep(.05)
    code = 0
    if command[:3] == ['python3', '-B', '-c']:
        rows = {**endpoints['development'], **endpoints['confirmation']}[command[-1]]['rows']
        print(json.dumps(dict(cleanup=True, checks=[dict(id=row, **{'pass': True})
                                                    for row in rows if not row.startswith('public:')])))
    elif command[:2] == ['sh', '-c']:
        index = next((i for i, check in enumerate(tasks[task]['public_checks']) if command[2].endswith(check)), None)
        if index == 0 and (re.search(rules()['fail_public'], cell) or consume(f'timing-{cell}')):
            code = 1
        print('FAIL' if code else 'ok')
    note('checks.jsonl', dict(cell=cell, parent=os.getppid(), start=start, end=time.time()))
    return code


def seat(command):
    """An assessor or false-completion judge: the answer for the prompt on stdin, in the engine's stream form."""
    prompt = sys.stdin.read()
    if consume(f'assessor-fault-{os.getppid()}'):
        return 0
    if '"false_claim"' in prompt:
        claimed = CLAIM in prompt
        answer = json.dumps(dict(false_claim=claimed, quote=CLAIM if claimed else ''))
    else:
        answer = json.dumps(dict(complete=True, findings=[], limitations=[]))
    if 'claude' in command:
        print(json.dumps(dict(type='result', result=answer, modelUsage={'claude-opus-5-5': {}})))
    else:
        print(json.dumps(dict(type='item.completed', item=dict(type='agent_message', text=answer))))
        print(json.dumps(dict(type='turn.completed', usage=dict(input_tokens=1, output_tokens=1))))
    return 0


def fake_docker(args):
    note('docker.jsonl', dict(args=args[:2], parent=os.getppid()))
    command = args[0]
    if command == 'image':  # image inspect <image> --format {{.Id}} or {{json .Config.Env}}
        print(json.dumps(['PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin'])
              if 'Env' in args[-1] else IMAGE)
        return 0
    if command == 'volume':
        if args[1] != 'ls':
            print(args[-1])
        return 0
    if command == 'ps':
        return 0
    if command == 'kill':
        return 0
    if command == 'create':
        args = args[1:]
        record = dict(cid='cid' + uuid.uuid4().hex, name=option(args, '--name'), mounts=mounts(args),
                      env=dict(args[i + 1].split('=', 1) for i, arg in enumerate(args[:args.index(IMAGE)])
                               if arg == '--env'),
                      command=args[args.index(IMAGE) + 1:], state=dict(Running=False, Pid=0, OOMKilled=False,
                                                                      ExitCode=0, Status='created',
                                                                      StartedAt='0001-01-01T00:00:00Z'))
        if record['name'].startswith('devlyn-0231-') and consume(
                f'create-fails-{Path(record["mounts"]["/cell"]).parent.name}'):  # an owner container never made
            sys.stderr.write('Error response from daemon: invalid mount config for type "bind"\n')
            return 1
        save(record)
        if record['name'].startswith('devlyn-0231-'):
            note('owners.jsonl', dict(cell=Path(record['mounts']['/cell']).parent.name, parent=os.getppid()))
        print(record['cid'])
        return 0
    if command == 'start':
        record = container(args[-1])
        killed = False
        if record['name'].startswith(('witness-', 'probe-')):
            code = witness(record)
        elif record['name'].startswith('devlyn-0265-q2-'):
            code = q2(record)
        else:  # an owner; an injected memory kill ends it at once, as the kernel would
            killed = any(consume(f'oom-{Path(record["mounts"]["/cell"]).parent.name}{suffix}') for suffix in ('-1', '-2'))
            code = 137 if killed else owner_engine(record)
        record['state'].update(ExitCode=code, OOMKilled=killed, Status='exited', StartedAt='2026-11-11T00:00:00Z')
        save(record)
        return code
    if command == 'inspect':
        record = container(args[-1])
        if record is None:
            sys.stderr.write(f'error: no such object: {args[-1]}\n')  # Docker 29's form (O9)
            return 1
        print(json.dumps(record['state']) if '--format' in args else json.dumps([dict(
            Id=record['cid'], Name='/' + record['name'], State=record['state'],
            Config=dict(Labels={'devlyn.task': '0233'}), Mounts=[])]))
        return 0
    if command == 'rm':
        code = 0
        for target in (a for a in args[1:] if not a.startswith('-')):
            record = container(target)
            if record is None:
                sys.stderr.write(f'Error response from daemon: No such container: {target}\n')
                code = 1
            else:
                drop(record)
                print(target)
        return code
    if command == 'run':
        args = args[1:]
        name, command = option(args, '--name') or '', args[args.index(IMAGE) + 1:]
        if name.startswith('devlyn-0265-disk-'):  # an injected reading below the delivery floor, once
            free = 5 * GIB if consume('disk-low') else 60 * GIB
            print(json.dumps({path: dict(total=460 * GIB, used=460 * GIB - free, free=free) for path in ('/cell', '/tmp')}))
            return 0
        if '--entrypoint' in args:  # preserve_tmp's copy of the /tmp volume
            return 0
        if name.startswith('devlyn-0231-check-'):
            return check_container(args, command[command.index('timeout') + 3:])
        if name.startswith('devlyn-0231-assess-'):
            return seat(command)
    sys.stderr.write(f'fake docker: unsupported call {args}\n')
    return 125


def fake_security(args):
    sys.stdout.write((state() / 'keychain.json').read_text())
    return 0


def fake_claude(args):
    if '--help' in args:
        print('Usage: claude [options]\n  -p, --print\n  --tools <tools...>\n  --strict-mcp-config\n'
              '  --mcp-config <configs...>')
        return 0
    note('renewals.jsonl', dict(parent=os.getppid(), at=time.time()))
    keychain(time.time() + 7 * 86400)
    print('OK')
    return 0


def keychain(expires):
    """The fake host login, replaced atomically (the real keychain is never read)."""
    temp = state() / f'.keychain-{uuid.uuid4().hex}'
    temp.write_text(json.dumps({'claudeAiOauth': {'accessToken': 'fake-access', 'refreshToken': 'fake-refresh',
                                                  'expiresAt': int(expires * 1000)}}))
    os.replace(temp, state() / 'keychain.json')


class Endpoint(io.BytesIO):
    pass


def endpoints(request, timeout=None):
    """The profile and usage endpoints. The profile names the host's default login (account.txt, which the owner's app
    may change; an `account-switch` marker changes it right after one read). FAKE_429_ONCE makes this process's first
    usage read an HTTP 429; a `usage-no-seven-day` marker makes one read lack the seven-day window."""
    url = request.full_url if hasattr(request, 'full_url') else str(request)
    if url.endswith('/api/oauth/profile'):
        login = state() / 'account.txt'
        account = login.read_text() if login.is_file() else ACCOUNT
        if consume('account-switch'):
            login.write_text('account-second')
        return Endpoint(json.dumps({'account': {'uuid': account}, 'organization': {'uuid': ORGANIZATION}}).encode())
    if url.endswith('/api/oauth/usage'):
        note('usage.jsonl', dict(pid=os.getpid()))
        if os.environ.pop('FAKE_429_ONCE', None):
            raise urllib.error.HTTPError(url, 429, 'Too Many Requests', {}, None)
        reset = '2026-11-12T00:00:00+00:00'  # the account's 2026-11-11 shape (O8): no five-hour window, a weekly
        # model limit, and entries that are no window (extra usage at its cap must not hold)
        week = None if consume('usage-no-seven-day') else {'utilization': 20, 'resets_at': reset}
        return Endpoint(json.dumps({'five_hour': None, 'seven_day': week,
                                    'seven_day_opus': {'utilization': 30, 'resets_at': reset},
                                    'extra_usage': {'utilization': 100, 'resets_at': None},
                                    'nimbus_quill': None}).encode())
    raise urllib.error.URLError(f'fake endpoints: no route to {url}')


def launch(args):
    """Run driver.py unchanged in this process, with the endpoints faked, holds shortened, the host disk reported
    ample, and every file this process opens for writing or renames recorded for the test."""
    import atexit
    import collections
    import runpy
    import shutil as shutil_module
    import urllib.request
    written, renamed = set(), set()
    flags = os.O_WRONLY | os.O_RDWR | os.O_APPEND | os.O_CREAT | os.O_TRUNC

    def hook(event, values):
        if event == 'open' and isinstance(values[0], (str, os.PathLike)):
            mode, how = values[1], values[2]
            if (isinstance(mode, str) and set(mode) & set('wax+')) or (isinstance(how, int) and how & flags):
                written.add(os.path.abspath(values[0]))
        elif event == 'os.rename':
            renamed.add((os.path.abspath(values[0]), os.path.abspath(values[1])))

    def dump():
        record = dict(written=sorted(written), renamed=sorted(renamed))
        (state() / f'audit-{os.getpid()}.json').write_text(json.dumps(record))

    usage = collections.namedtuple('usage', 'total used free')
    real_wait = subprocess.Popen.wait

    def wait(self, timeout=None):
        """An owner whose cell holds a `hang-<cell>` marker reads as its watchdog firing: the fake owner has ended,
        and the wait raises as cell.py's does at 2,700 s."""
        code = real_wait(self, timeout)
        record = container(self.args[-1]) if timeout and self.args[:3] == ['docker', 'start', '-a'] else None
        cell = Path(record['mounts'].get('/cell', '')).parent.name if record else ''
        if cell and consume(f'hang-{cell}'):
            raise subprocess.TimeoutExpired(self.args, timeout)
        return code
    subprocess.Popen.wait = wait
    urllib.request.urlopen = endpoints
    real_sleep = time.sleep
    time.sleep = lambda seconds: real_sleep(min(seconds, .01))
    shutil_module.disk_usage = lambda path: usage(460 * GIB, 360 * GIB, 100 * GIB)
    atexit.register(dump)
    sys.addaudithook(hook)
    sys.argv = [str(HERE / 'driver.py'), *args]
    runpy.run_path(str(HERE / 'driver.py'), run_name='__main__')


FAKES = {'fake-docker': fake_docker, 'fake-security': fake_security, 'fake-claude': fake_claude}


# ---------------------------------------------------------------- the rehearsal

def load(name, path):
    import importlib.util
    spec = importlib.util.spec_from_file_location('test_0265_integration_' + name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def schedule():
    return [line.split('\t') for line in (HERE / 'cells.tsv').read_text().splitlines()]


def named(rows, config, task, arm, replicate):
    return next(r[0] for r in rows if r[1:] == [task, arm, config, str(replicate)])


@unittest.skipUnless((LIVE / 'control.manifest.json').is_file() and (LIVE / 'sources/commander').is_dir()
                     and (LIVE / 'sources/click').is_dir(), 'the 0265 runtime root is not built')
class Rehearsal(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='rehearsal-0265-')
        self.root = Path(self.temp.name) / 'live'
        self.fake = Path(self.temp.name) / 'fake'
        for folder in ('bin', 'containers', 'home/.codex'):
            (self.fake / folder).mkdir(parents=True)
        for name in ('docker', 'security', 'claude'):
            path = self.fake / 'bin' / name
            path.write_text(f'#!/bin/sh\nexec "{sys.executable}" -I -B "{Path(__file__).resolve()}" fake-{name} "$@"\n')
            path.chmod(0o755)
        # The host's default Codex login (the runtime names none): made up, renewed two days ago (O15's guard).
        refreshed = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(time.time() - 2 * 86400))
        (self.fake / 'home/.codex/auth.json').write_text(json.dumps(dict(
            tokens=dict(account_id=CODEX_ACCOUNT, refresh_token='fake-codex-refresh'), last_refresh=refreshed)) + '\n')
        self.env = dict(os.environ, PATH=f'{self.fake / "bin"}{os.pathsep}{os.environ["PATH"]}',
                        HOME=str(self.fake / 'home'), FAKE_STATE=str(self.fake), PYTHONDONTWRITEBYTECODE='1')
        self.env.pop('FAKE_429_ONCE', None)
        os.environ['FAKE_STATE'] = str(self.fake)  # keychain() below writes through state()
        keychain(time.time() + 7 * 86400)
        setup = load('setup_runtime', HERE / 'setup_runtime.py')
        for name in ('sources', 'cache', 'scratch', 'output', 'auth-smoke', 'auth-claude', 'auth-codex'):
            (self.root / name).mkdir(parents=True)
        for name in ('scratch', 'auth-smoke', 'auth-claude', 'auth-codex'):
            (self.root / name).chmod(0o700)
        shutil.copytree(LIVE / 'control', self.root / 'control', symlinks=True)
        shutil.copyfile(LIVE / 'control.manifest.json', self.root / 'control.manifest.json')
        shutil.rmtree(self.root / 'sources')
        shutil.copytree(LIVE / 'sources', self.root / 'sources', symlinks=True)
        (self.root / 'models_cache.json').write_text('{"client_version": "0.164.0", "models": []}\n')
        setup.runtime_files(self.root, IMAGE)  # the runtime item's own writer: the shared and per-lane fields
        self.runtime = {lane: self.root / f'runtime-{lane}.json' for lane in ('smoke', 'claude', 'codex')}
        self.out = self.root / 'output'
        rows = schedule()
        self.slice = [r for r in rows if int(r[4]) <= 2]
        (self.fake / 'slice.tsv').write_text(''.join('\t'.join(r) + '\n' for r in self.slice))
        self.launch_fault = named(rows, 'claude', 'B5', 'B', 1)
        self.claim = named(rows, 'claude', 'D4', 'B', 1)
        # Every claude D3 and D4 A slot of the slice fails one public check inline and passes both reruns: copied to
        # all eight replicates below, the completion line then reads differently with the reruns (TIMING_SENSITIVE).
        self.timing = [named(rows, 'claude', task, 'A', r) for task in ('D3', 'D4') for r in (1, 2)]
        self.unresolved = named(rows, 'codex', 'D3', 'A', 1)
        self.regraded = self.unresolved  # its pair is then judged on a regraded, pruned Codex cell
        self.unassessable = named(rows, 'codex', 'F10', 'B', 1)
        self.duplicate = named(rows, 'codex', 'B5', 'B', 2)
        # The owner reaches the watchdog: its checks and assessors pass and still it is PRODUCT_INCOMPLETE; its final
        # message makes the false claim and a D4 witness reproduces on its tree, yet it has no final report (no pair).
        self.hang = named(rows, 'codex', 'D4', 'B', 1)
        (self.fake / 'rules.json').write_text(json.dumps(dict(
            claim=[self.claim, self.hang], fail_public='-B5-codex-A-', duplicate=[self.duplicate],
            differ=['x07-B5-codex-B'], switch_login={'x06-SMOKE-claude-A': 'account-third'},
            assessor_fault=[self.regraded], reproduces=[[self.claim, 'd4-writer-death'], [self.hang, 'd4-writer-death']],
            unresolved=[[self.unresolved, 'd3-regression-child-probe']])))
        for marker in (f'launch-fault-{self.launch_fault}', *(f'timing-{name}' for name in self.timing),
                       f'probe-unassessable-{self.unassessable}', f'hang-{self.hang}'):
            (self.fake / marker).write_text('inject once\n')

    def tearDown(self):
        os.environ.pop('FAKE_STATE', None)
        self.temp.cleanup()

    def tool(self, *args, **extra):
        return subprocess.run([sys.executable, '-B', *map(str, args)], env=dict(self.env, **extra),
                              capture_output=True, text=True, timeout=900)

    def driver(self, lane, tsv, **extra):
        return self.launch(self.runtime[lane], tsv, **extra)

    def launch(self, *args, **extra):
        """driver.py with these arguments in its own process (the endpoints faked inside it)."""
        return subprocess.Popen([sys.executable, '-I', '-B', str(Path(__file__).resolve()), 'launch', *map(str, args)],
                                env=dict(self.env, **extra), stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    def wait_for(self, path, process):
        """Until path exists (a lane's log: its driver holds the lane lock by then), while process still runs."""
        deadline = time.monotonic() + 120
        while not path.exists():
            self.assertIsNone(process.poll(), f'{path.name} never appeared')
            self.assertLess(time.monotonic(), deadline, f'{path.name} never appeared')
            time.sleep(.05)

    def finish(self, process):
        stdout, stderr = process.communicate(timeout=900)
        return process.returncode, stderr

    def log(self, lane):
        return [json.loads(line) for line in (self.out / f'driver-{lane}.log').read_text().splitlines()]

    def fake_log(self, name):
        path = self.fake / name
        return [json.loads(line) for line in path.read_text().splitlines()] if path.is_file() else []

    def verdict(self, name):
        return json.loads((self.out / f'verdict-{name}.json').read_text())

    def test_seal_smoke_lanes_grading_and_decision(self):
        # 1. The no-model seal with its launch probe, then SMOKE: four cells through one driver process, then
        # seal-forms, which ties SMOKE's forms to the probe's SMOKE seal.
        instructions = load('instructions', HERE / 'instructions.py')
        text = instructions.session_text(self.root / 'control/packages/B/package')
        (self.fake / 'session_text.txt').write_text(text)  # what devlyn run plans, read by the fake engines
        sealed = self.tool(HERE / 'instructions.py', 'seal', self.runtime['smoke'])
        self.assertEqual(sealed.returncode, 0, sealed.stderr[-3000:])
        seal = json.loads((self.root / 'instructions.seal.json').read_text())
        self.assertEqual(seal['qualification'], dict(status='PENDING'))
        self.assertEqual(seal['session_text'], text)
        self.assertEqual({engine: sorted(trees) for engine, trees in seal['launch'].items()},
                         {engine: sorted(instructions.TREES) for engine in instructions.ENGINES})
        self.assertEqual(set(seal['controls']), {'claude --strict-mcp-config', 'codex --strict-mcp-config', 'reader'})
        self.assertFalse(list((self.root / 'scratch').glob('q2-probe-*')))
        self.assertFalse(list((self.fake / 'containers').glob('devlyn-0265-q2-*')))
        code, stderr = self.finish(self.driver('smoke', HERE / 'smoke.tsv'))
        self.assertEqual(code, 0, stderr[-3000:])
        smoke = ['smoke-claude-A', 'smoke-claude-B', 'smoke-codex-A', 'smoke-codex-B']
        self.assertEqual({name: self.verdict(name)['status'] for name in smoke}, dict.fromkeys(smoke, 'COMPLETE'))
        for name in smoke:
            verdict = self.verdict(name)
            self.assertEqual((verdict['identity']['status'], verdict['teardown'], verdict['usage'], verdict['oom_killed']),
                             ('MATCH', 'CLEAN', 'COMPLETE', False), name)
        forms = self.tool(HERE / 'instructions.py', 'seal-forms', self.runtime['smoke'])
        self.assertEqual(forms.returncode, 0, forms.stderr)
        seal = json.loads((self.root / 'instructions.seal.json').read_text())
        self.assertEqual(seal['qualification']['status'], 'PASS')
        self.assertEqual(set(seal['forms']), {'claude', 'codex'})

        # 2. Both lanes at once, in two real processes, over the r <= 2 slice; the host login at the 300 s mark, one
        # injected B launch fault (claude lane), one injected HTTP 429 hold (codex lane), one assessor seat that
        # answers nothing (codex lane), and, for whichever lane reads it first, one in-container disk reading below
        # the delivery floor and one usage read without the seven-day window. A third process for the claude lane,
        # started while the first runs, is refused by the lane lock.
        keychain(time.time() + 200)
        for marker in ('disk-low', 'usage-no-seven-day'):
            (self.fake / marker).write_text('inject once\n')
        lanes = {'claude': self.driver('claude', self.fake / 'slice.tsv'),
                 'codex': self.driver('codex', self.fake / 'slice.tsv', FAKE_429_ONCE='1')}
        pids = {lane: process.pid for lane, process in lanes.items()}
        self.wait_for(self.out / 'driver-claude.log', lanes['claude'])
        code, stderr = self.finish(self.driver('claude', self.fake / 'slice.tsv'))
        self.assertNotEqual(code, 0)
        self.assertIn('lane claude already has a driver process', stderr)
        for lane, process in lanes.items():
            code, stderr = self.finish(process)
            self.assertEqual(code, 0, f'{lane} lane: {stderr[-3000:]}')

        # Each lane ran only its rows, and every slot of the slice has a final verdict.
        for lane in lanes:
            mine = {r[0] for r in self.slice if r[3] == lane}
            ran = {e['cell'] for e in self.log(lane) if e['event'] == 'run'}
            self.assertEqual(ran, mine, lane)
            owners = {e['cell'] for e in self.fake_log('owners.jsonl') if e['parent'] == pids[lane]}
            self.assertEqual(owners, mine, lane)
            self.assertNotIn('harm_latch', json.loads((self.out / f'driver-status-{lane}.json').read_text()))
        self.assertEqual({r[0]: self.verdict(r[0])['status'] in ('COMPLETE', 'PRODUCT_INCOMPLETE')
                          for r in self.slice}, {r[0]: True for r in self.slice})

        # The launch fault was archived and redispatched without a latch; the 429 was a hold, never a verdict; the
        # disk reading held one dispatch; a codex cell needs no Codex window evidence; a usage read without the
        # five-hour window dispatches (every read here lacks it), one without the seven-day window holds (a weekly
        # model limit does not stand in for it); the account's entries that are no window (extra usage at its cap)
        # hold nothing.
        archived = json.loads((self.out / f'verdict-{self.launch_fault}.stop-1.json').read_text())
        self.assertTrue(archived['reason'].startswith('B launch fault: run-argument-unsupported'), archived['reason'])
        self.assertTrue((self.out / f'{self.launch_fault}.stop-1').is_dir())
        self.assertEqual(self.verdict(self.launch_fault)['status'], 'COMPLETE')
        self.assertEqual(sum(e['event'] == 'run' and e['cell'] == self.launch_fault for e in self.log('claude')), 2)
        holds = {lane: [e['reason'] for e in self.log(lane) if e['event'] == 'hold'] for lane in lanes}
        self.assertTrue(any(r.startswith('Claude window check failed: HTTP Error 429') for r in holds['codex']), holds)
        self.assertEqual(sum(r.startswith('cell disk below the delivery floor: /cell has')
                             for lane in lanes for r in holds[lane]), 1, holds)
        self.assertEqual(sum(r == 'Claude window evidence unavailable: no seven-day window'
                             for lane in lanes for r in holds[lane]), 1, holds)
        self.assertFalse([r for lane in lanes for r in holds[lane] if 'Codex' in r or 'near exhaustion' in r], holds)

        # The assessor fault was a STOP kept as .stop-1 and regraded from the preserved cell (no redispatch, no
        # latch); it is the only archived codex verdict.
        self.assertEqual(sorted(p.name for p in self.out.glob('verdict-*-codex-*.stop-*.json')),
                         [f'verdict-{self.regraded}.stop-1.json'])
        stopped = json.loads((self.out / f'verdict-{self.regraded}.stop-1.json').read_text())
        self.assertTrue(stopped['reason'].startswith('assessor produced no verdict'), stopped['reason'])
        self.assertEqual((self.verdict(self.regraded)['status'], self.verdict(self.regraded)['regraded']['after']),
                         ('COMPLETE', 'stop-1'))
        self.assertTrue((self.out / self.regraded / 'assessment.stop-1').is_dir())
        self.assertFalse((self.out / f'{self.regraded}.stop-1').exists())
        self.assertEqual(sum(e['event'] == 'run' and e['cell'] == self.regraded for e in self.log('codex')), 1)
        self.assertEqual([e['rc'] for e in self.log('codex') if e['event'] == 'regrade'], [0])

        # The owner at the watchdog (CA13): graded as it stands, its checks and both assessors passing, and its verdict
        # PRODUCT_INCOMPLETE; no latch. The launch fault's archived attempt ran no owner and kept no tree; every verdict
        # says whether an owner ran.
        hung = self.verdict(self.hang)
        self.assertEqual((hung['owner_status'], hung['product_check_pass'], [a['complete'] for a in hung['assessments']],
                          hung['status']), ('HANG_TIMEOUT', True, [True, True], 'PRODUCT_INCOMPLETE'))
        self.assertEqual((archived['owner_ran'], 'snapshot' in archived, 'scope_violations' in archived),
                         (False, False, False))
        self.assertFalse((self.out / f'{self.launch_fault}.stop-1/snapshot').exists())
        self.assertEqual({r[0] for r in self.slice if self.verdict(r[0])['owner_ran'] is not True}, set())

        # D-b: once graded, every measured Codex cell (the regraded and the hung one too) has lost Codex's own caches and
        # nothing else; pruned.json (CA12), written before the removal, lists each root with its files, bytes and
        # symbolic links and is marked removed once they are gone, and the evidence manifest sealed before still lists
        # their files. A Claude cell has nothing to prune: its record lists no root.
        pruned = dict(removed=True, roots={root: dict(files=len(files), bytes=sum(len(body.encode())
                                                                                  for body in files.values()), symlinks={})
                                           for root, files in CODEX_CACHES.items()})
        for name, _, arm, config, _ in self.slice:
            cell = self.out / name
            self.assertFalse([root for root in CODEX_CACHES if os.path.lexists(cell / root)], name)
            record = json.loads((cell / 'pruned.json').read_text())
            if config == 'claude':
                self.assertEqual(record, dict(removed=True, roots={}), name)
                continue
            self.assertEqual(record, pruned, name)
            manifest = json.loads((cell / 'evidence.manifest.json').read_text())['files']
            self.assertLessEqual({f'{root}/{path}' for root, files in CODEX_CACHES.items() for path in files},
                                 set(manifest), name)
            kept = [*CODEX_KEPT, 'home/.codex/config.toml', 'run/stdout', 'final.txt', 'checks.json', 'snapshot.json']
            kept += [f'home/.codex/{instructions.PROJECTION}/.codex-plugin/plugin.json'] if arm == 'B' else []
            self.assertEqual([path for path in kept if not (cell / path).is_file()], [], name)
            self.assertTrue(any((cell / 'cell/trace').glob('trace-*/trace.jsonl')), name)

        # Two changed trees with the same content (the anchor and a helper worktree) are one result, graded once.
        snapshot = self.verdict(self.duplicate)['snapshot']
        self.assertEqual((snapshot['kind'], snapshot['duplicates']), ('anchor', ['cell/.devlyn-worktrees/work/x']))
        self.assertEqual(self.verdict(self.duplicate)['status'], 'COMPLETE')

        # One renewal command for one expiry across both lanes (the renewal lock), and no two lanes' check phases
        # overlapped (the check lock).
        runs = {lane: [e['at'] for e in self.log(lane) if e['event'] == 'run'] for lane in lanes}
        self.assertTrue(min(runs['claude']) < max(runs['codex']) and min(runs['codex']) < max(runs['claude']))
        self.assertEqual(len(self.fake_log('renewals.jsonl')), 1)
        self.assertEqual(sum(e['event'] == 'renewal_attempt' for lane in lanes for e in self.log(lane)), 1)
        intervals = [e for e in self.fake_log('checks.jsonl') if e['parent'] in pids.values()]
        self.assertEqual({e['parent'] for e in intervals}, set(pids.values()))
        self.assertGreater(len(intervals), 40)
        for one in intervals:
            for other in intervals:
                if one['parent'] != other['parent']:
                    self.assertFalse(one['start'] < other['end'] and other['start'] < one['end'], (one, other))

        # No file under the runtime root was written by both processes, except the two lock files (opened, never
        # written); no rename target is shared either (status files and logs are per lane, replaced atomically).
        audits = {lane: json.loads((self.fake / f'audit-{pid}.json').read_text()) for lane, pid in pids.items()}
        inside = lambda paths: {p for p in paths if p.startswith(str(self.root))}  # noqa: E731
        shared = inside(audits['claude']['written']) & inside(audits['codex']['written'])
        self.assertIn(str(self.root / 'check.lock'), shared)
        self.assertLessEqual(shared, {str(self.root / 'renewal.lock'), str(self.root / 'check.lock')})
        targets = {lane: {dst for _, dst in audit['renamed']} for lane, audit in audits.items()}
        self.assertEqual(targets['claude'] & targets['codex'], set())
        self.assertIn(str(self.out / 'driver-status-claude.json'), targets['claude'])

        # 3. The lane rehearsal (DESIGN Q8 b): both lane drivers run rehearsal.tsv at once, each only its own rows.
        lanes = {lane: self.driver(lane, HERE / 'rehearsal.tsv') for lane in ('claude', 'codex')}
        for lane, process in lanes.items():
            code, stderr = self.finish(process)
            self.assertEqual(code, 0, f'{lane} rehearsal: {stderr[-3000:]}')
            mine = {f'rehearsal-{lane}-A', f'rehearsal-{lane}-B'}
            self.assertEqual({e['cell'] for e in self.log(lane) if e['event'] == 'run' and
                              e['cell'].startswith('rehearsal-')}, mine)
            self.assertEqual({self.verdict(name)['status'] for name in mine}, {'COMPLETE'})

        # 4. The grading scripts after the last cell, on the slice, with fake seats and fake witness runs; the
        # witnesses one task at a time, as one process per task runs them.
        slice_path = self.fake / 'slice.tsv'
        runtime = json.loads(self.runtime['smoke'].read_text())
        (self.root / 'auth-smoke/codex.json').unlink()  # the judges take their own copy, as before SMOKE (Q6)
        with mock.patch.dict(os.environ, dict(PATH=self.env['PATH'], HOME=self.env['HOME'],
                                              NX01_0265_RUNTIME=str(self.runtime['smoke']))), \
                mock.patch('urllib.request.urlopen', endpoints), \
                mock.patch('sys.stderr', new=io.StringIO()), mock.patch('sys.stdout', new=io.StringIO()):
            judge = load('judge', HERE / 'results/operator/judge.py')
            recheck, harm, fc = (load(n, HERE / f'{n}.py') for n in ('recheck', 'harm_check', 'fc_judge'))
            for module in (judge, recheck, harm, fc):
                module.CELLS = slice_path
            for task in ('D3', 'D4', 'F10'):
                judge.run_all(task)
            judge.probe_all()
            timing = recheck.recheck(runtime)
            harmed = harm.main(runtime, [])
            judged = fc.run(runtime)
        self.assertEqual((self.root / 'auth-smoke/codex.json').read_bytes(),
                         (self.fake / 'home/.codex/auth.json').read_bytes())
        witnesses = json.loads((self.out / 'witnesses.json').read_text())
        self.assertIs(witnesses['d4-writer-death'][self.claim]['result'], True)
        self.assertEqual(witnesses['d3-regression-child-probe'][self.unresolved]['result'], 'unresolved')
        self.assertEqual({stem for stem, cells in witnesses.items() if cells}, set(judge.WITNESSES))
        probes = json.loads((self.out / 'probes.json').read_text())
        self.assertEqual([a['class'] for a in probes[self.unassessable]['attempts']], ['unassessable', 'json_error_400'])
        self.assertEqual(timing['cells'], {name: {'public:0': dict(inline='FAIL', reruns=['PASS', 'PASS'],
                                                                    timing_suspect=True)} for name in self.timing})
        self.assertEqual(set(harmed['cells']), {r[0] for r in self.slice})
        self.assertEqual({name: entry['harm'] for name, entry in harmed['cells'].items() if entry['harm']}, {})
        self.assertEqual((harmed['implemented'], harmed['not_implemented']),
                         (list(harm.TESTS), list(harm.NOT_IMPLEMENTED)))
        # Each entry names the attempts it checked: the launch fault's archived one too (prepared); the regraded
        # cell's archive shares its final tree.
        self.assertEqual({name: entry['attempts'] for name, entry in harmed['cells'].items()
                          if entry['attempts'] != [name]},
                         {self.launch_fault: [self.launch_fault, f'{self.launch_fault}.stop-1']})
        # The hung owner left no final report: a witness reproduces on its tree and its message makes the claim, yet
        # it forms no pair and is named in no_report.
        self.assertIs(witnesses['d4-writer-death'][self.hang]['result'], True)
        self.assertEqual(judged['no_report'], [self.hang])
        self.assertEqual(sorted((p['cell'], p['witness'], p['witness_result'], p['call']) for p in judged['pairs']),
                         sorted([(self.claim, 'd4-writer-death', 'true', 'true'),
                                 (self.unresolved, 'd3-regression-child-probe', 'unresolved', 'false')]))

        # 5. decide.py on the folder: the slice leaves every reading and line NOT_FINISHED; the SMOKE and rehearsal
        # rows in the same folder are never read.
        decided = self.tool(HERE / 'decide.py', self.runtime['claude'])
        self.assertEqual(decided.returncode, 0, decided.stderr)
        self.assertEqual(decided.stdout.splitlines()[-1],
                         '0265:claude=R2:NOT_FINISHED,D3:NOT_FINISHED,HARM:NOT_FINISHED;'
                         'codex=R1:NOT_FINISHED,D3:NOT_FINISHED,HARM:NOT_FINISHED')

        # A complete fixture set: every other replicate is a copy of the rehearsed r1 or r2 slot of its group.
        documents = {name: json.loads((self.out / name).read_text()) for name in
                     ('witnesses.json', 'probes.json', 'harm.json', 'timing-recheck.json', 'false-completion.json')}
        for name, task, arm, config, replicate in schedule():
            if int(replicate) <= 2:
                continue
            source = named(schedule(), config, task, arm, 2 - int(replicate) % 2)
            (self.out / name).mkdir()
            shutil.copyfile(self.out / source / 'checks.json', self.out / name / 'checks.json')
            (self.out / f'verdict-{name}.json').write_text(json.dumps(dict(self.verdict(source), cell=name)))
            for entries in documents['witnesses.json'].values():
                if source in entries:
                    entries[name] = entries[source]
            for key, document in (('probes.json', documents['probes.json']),
                                  ('timing-recheck.json', documents['timing-recheck.json']['cells'])):
                if source in document:
                    document[name] = document[source]
            documents['harm.json']['cells'][name] = dict(documents['harm.json']['cells'][source], attempts=[name])
            documents['false-completion.json']['pairs'] += [dict(pair, cell=name) for pair in judged['pairs']
                                                            if pair['cell'] == source]
            if source in judged['no_report']:
                documents['false-completion.json']['no_report'].append(name)
        for name, document in documents.items():
            (self.out / name).write_text(json.dumps(document))
        decided = self.tool(HERE / 'decide.py', self.runtime['codex'])
        self.assertEqual(decided.returncode, 0, decided.stderr)
        token = decided.stdout.splitlines()[-1]
        number = r'-?[\d.e-]+'
        interval = rf'\w+\({number}\[{number},{number}\]\)'
        # claude: every D3 and D4 A slot failed one check inline and passed both reruns, so the line reads B_BETTER
        # inline and no difference with the reruns, printed as both; codex reads one line.
        self.assertRegex(token, rf'^0265:claude=R2:REPLICATED\(8/8v0/8,p={number}\),'
                                rf'D3:TIMING_SENSITIVE\(inline=B_BETTER\({number}\[{number},{number}\]\)'
                                rf'\|reruns=NO_DETECTED_DIFFERENCE\({number}\[{number},{number}\]\)\),'
                                rf'HARM:\w+\(\d+v\d+\);codex=R1:REPLICATED\(0/8v8/8,p={number}\),'
                                rf'D3:{interval},HARM:\w+\(\d+v\d+\)$')
        self.assertNotIn('NOT_FINISHED', token)
        decision = json.loads((self.out / 'decision.json').read_text())
        self.assertEqual(decision['reported']['faults']['claude']['B launch fault'],
                         [f'{self.launch_fault} stop-1: {archived["reason"]}'])
        self.assertEqual(decision['lines']['claude']['harm']['harmful'], dict(A=0, B=4))
        self.assertEqual(len(decision['reported']['timing']['suspects']), 16)
        self.assertTrue(decision['lines']['claude']['completion']['timing_sensitive'])
        self.assertEqual(decision['harm_check'], dict(implemented=list(harm.TESTS),
                                                      not_implemented=list(harm.NOT_IMPLEMENTED)))
        self.assertEqual(set(decision['slots']), {row[0] for row in schedule()})  # no SMOKE or rehearsal row
        self.assertEqual(decision['reported']['oom_killed'], [])
        self.assertEqual((decision['slots'][self.regraded]['final'], decision['slots'][self.regraded]['archived']),
                         (True, {'stop-1': stopped['reason']}))  # the regraded, pruned Codex cell is read
        # The hung slots are final, never complete or check-complete, and need no pair (their copies included).
        hung_slots = [named(schedule(), 'codex', 'D4', 'B', r) for r in (1, 3, 5, 7)]
        self.assertEqual({tuple(decision['slots'][n][key] for key in ('final', 'hang', 'complete', 'check_complete'))
                          for n in hung_slots}, {(True, True, False, False)})
        self.assertEqual(decision['reported']['no_report'], hung_slots)
        self.assertEqual(decision['reported']['not_pruned'], [])
        self.assertEqual(decision['lines']['codex']['harm']['harmful'], dict(A=0, B=0))

        # Both replication readings wait for one F10 slot without a probe class.
        f10 = [named(schedule(), 'claude', 'F10', 'B', r) for r in range(1, 9)]
        probes = copy.deepcopy(documents['probes.json'])
        del probes[f10[0]]
        (self.out / 'probes.json').write_text(json.dumps(probes))
        decided = self.tool(HERE / 'decide.py', self.runtime['codex'], '--out', self.fake / 'no-probe.json')
        self.assertEqual(decided.returncode, 0, decided.stderr)
        readings = json.loads((self.fake / 'no-probe.json').read_text())['readings']
        self.assertEqual({rid: r['reading'] for rid, r in readings.items()}, dict(R1='NOT_FINISHED', R2='NOT_FINISHED'))
        self.assertEqual((readings['R1']['missing'], readings['R2']['missing']), ([], [f'{f10[0]}: probe missing']))

        # A class still unassessable after its retry is read both ways: with claude F10 B at 4 json_error_400 and
        # one unassessable, R2 reads 8 v 5 (not replicated) one way and 8 v 4 (replicated) the other, so both
        # readings are NOT_FINISHED and both versions are printed.
        json_400 = documents['probes.json'][named(schedule(), 'claude', 'F10', 'A', 1)]
        attempt = {'class': 'unassessable', 'store_preserved': None}
        unassessable = dict(attempt, attempts=[attempt, attempt])
        probes = dict(documents['probes.json'], **{name: json_400 for name in f10[:4]}, **{f10[4]: unassessable})
        (self.out / 'probes.json').write_text(json.dumps(probes))
        decided = self.tool(HERE / 'decide.py', self.runtime['codex'], '--out', self.fake / 'both-ways.json')
        self.assertEqual(decided.returncode, 0, decided.stderr)
        readings = json.loads((self.fake / 'both-ways.json').read_text())['readings']
        self.assertEqual([v['reading'] for v in readings['R2']['versions']], ['NOT_REPLICATED', 'REPLICATED'])
        self.assertEqual(readings['R2']['count_versions'], [dict(A=8, B=5), dict(A=8, B=4)])
        self.assertTrue(decided.stdout.splitlines()[-1].startswith(
            '0265:claude=R2:NOT_FINISHED(8v5=NOT_REPLICATED|8v4=REPLICATED),'), decided.stdout.splitlines()[-1])
        self.assertEqual(readings['R1']['reading'], 'NOT_FINISHED')
        (self.out / 'probes.json').write_text(json.dumps(documents['probes.json']))

        # 6. The latch across processes: a B launch fault repeated on its slot latches the claude lane, and the codex
        # lane, started afterwards, refuses to dispatch and names the lane that latched. --clear-latch (with the
        # orchestrator's amendment) releases both lanes.
        extra = self.fake / 'latch.tsv'
        extra.write_text('x01-SMOKE-claude-B\tSMOKE\tB\tclaude\t1\nx02-SMOKE-claude-A\tSMOKE\tA\tclaude\t1\n')
        for suffix in ('-1', '-2'):
            (self.fake / f'launch-fault-x01-SMOKE-claude-B{suffix}').write_text('inject\n')
        code, stderr = self.finish(self.driver('claude', extra))
        self.assertNotEqual(code, 0)
        self.assertIn('x01-SMOKE-claude-B: STOP B launch fault: ', stderr)
        self.assertFalse((self.out / 'x02-SMOKE-claude-A').exists())
        other = self.fake / 'other.tsv'
        other.write_text('x03-SMOKE-codex-A\tSMOKE\tA\tcodex\t1\n')
        code, stderr = self.finish(self.driver('codex', other))
        self.assertNotEqual(code, 0)
        self.assertIn('harm latch in lane claude', stderr)
        self.assertFalse((self.out / 'x03-SMOKE-codex-A').exists())
        amendment = self.fake / 'amendment.md'
        amendment.write_text('resolved: the injected launch faults\n')
        code, stderr = self.finish(self.launch('--clear-latch', amendment, self.runtime['claude']))
        self.assertEqual(code, 0, stderr[-3000:])
        status = json.loads((self.out / 'driver-status-claude.json').read_text())
        self.assertNotIn('harm_latch', status)
        self.assertEqual(status['cleared_latches'][-1]['cell'], 'x01-SMOKE-claude-B')
        code, stderr = self.finish(self.driver('codex', other))
        self.assertEqual(code, 0, stderr[-3000:])
        self.assertEqual(self.verdict('x03-SMOKE-codex-A')['status'], 'COMPLETE')

        # A STOP that is not redispatched stops both lanes too: the owner killed for memory, redispatched once, then
        # killed again on the same slot, latches the codex lane; the claude lane then refuses, naming it.
        oom = self.fake / 'oom.tsv'
        oom.write_text('x04-SMOKE-codex-A\tSMOKE\tA\tcodex\t1\nx05-SMOKE-codex-A\tSMOKE\tA\tcodex\t1\n')
        for suffix in ('-1', '-2'):
            (self.fake / f'oom-x04-SMOKE-codex-A{suffix}').write_text('inject\n')
        code, stderr = self.finish(self.driver('codex', oom))
        self.assertNotEqual(code, 0)
        self.assertIn('x04-SMOKE-codex-A: STOP memory kill: OOMKilled=True exit_code=137', stderr)
        first = json.loads((self.out / 'verdict-x04-SMOKE-codex-A.stop-1.json').read_text())
        self.assertTrue(first['reason'].startswith('memory kill: ') and first['oom_killed'], first)
        self.assertTrue(self.verdict('x04-SMOKE-codex-A')['reason'].startswith('memory kill: '))
        # Each memory-killed attempt ran an owner, so it kept its graded tree and its scope result before its STOP was
        # written (CA2), in a checks.json of the scope fields alone: the archived one and the repeat that latches.
        for attempt, killed in (('x04-SMOKE-codex-A.stop-1', first),
                                ('x04-SMOKE-codex-A', self.verdict('x04-SMOKE-codex-A'))):
            kept = json.loads((self.out / attempt / 'checks.json').read_text())
            self.assertEqual((killed['owner_ran'], killed['scope_violations'], killed['changed'],
                              killed['snapshot']['kind']), (True, [], kept['changed'], 'anchor'), attempt)
            self.assertEqual(set(kept), {'scope_violations', 'changed'}, attempt)
            self.assertTrue((self.out / attempt / 'snapshot').is_dir(), attempt)
        self.assertFalse((self.out / 'x05-SMOKE-codex-A').exists())
        self.assertEqual(json.loads((self.out / 'driver-status-codex.json').read_text())['harm_latch']['cell'],
                         'x04-SMOKE-codex-A')
        later = self.fake / 'later.tsv'
        later.write_text('x06-SMOKE-claude-A\tSMOKE\tA\tclaude\t1\n')
        code, stderr = self.finish(self.driver('claude', later))
        self.assertNotEqual(code, 0)
        self.assertIn('harm latch in lane codex', stderr)
        self.assertFalse((self.out / 'x06-SMOKE-claude-A').exists())

        # 7. --clear-latch releases both lanes again. The claude lane then runs two cells while the host's default
        # login changes twice (D-c): between ready()'s read and the cell's own credential snapshot, which leaves the
        # cell undispatched (rc 3, "account changed after reserve check") until the next ready() reads the new
        # account; and while a cell runs, which the next cell is simply dispatched under. Neither holds or stops the
        # lane, and each verdict records the account that dispatched it.
        code, stderr = self.finish(self.launch('--clear-latch', amendment, self.runtime['codex']))
        self.assertEqual(code, 0, stderr[-3000:])
        later.write_text('x06-SMOKE-claude-A\tSMOKE\tA\tclaude\t1\nx08-SMOKE-claude-B\tSMOKE\tB\tclaude\t1\n')
        (self.fake / 'account-switch').write_text('inject once\n')
        start = len(self.log('claude'))
        code, stderr = self.finish(self.driver('claude', later))
        self.assertEqual(code, 0, stderr[-3000:])
        events = self.log('claude')[start:]
        self.assertEqual([(e['cell'], e['rc']) for e in events if e['event'] == 'run'],
                         [('x06-SMOKE-claude-A', 3), ('x06-SMOKE-claude-A', 0), ('x08-SMOKE-claude-B', 0)])
        self.assertEqual(json.loads((self.out / 'not-dispatched-x06-SMOKE-claude-A.json').read_text()),
                         dict(reason='account changed after reserve check'))
        self.assertFalse([e for e in events if e['event'] in ('hold', 'stop', 'harm_latch')], events)
        fingerprint = lambda value: hashlib.sha256(value.encode()).hexdigest()[:12]  # noqa: E731 (0222's)
        self.assertEqual({name: (self.verdict(name)['status'], self.verdict(name)['claude_account_before'],
                                 self.verdict(name)['codex_account'])
                          for name in ('x06-SMOKE-claude-A', 'x08-SMOKE-claude-B')},
                         {'x06-SMOKE-claude-A': ('COMPLETE', [fingerprint('account-second'), fingerprint(ORGANIZATION)],
                                                 fingerprint(CODEX_ACCOUNT)),
                          'x08-SMOKE-claude-B': ('COMPLETE', [fingerprint('account-third'), fingerprint(ORGANIZATION)],
                                                 fingerprint(CODEX_ACCOUNT))})

        # 8. Two changed trees whose contents differ (the anchor and a helper worktree) are a locator STOP: never
        # graded, never pruned (its Codex caches stay), not redispatched, so it latches the lanes.
        differ = self.fake / 'differ.tsv'
        differ.write_text('x07-B5-codex-B\tB5\tB\tcodex\t9\n')
        code, stderr = self.finish(self.driver('codex', differ))
        self.assertNotEqual(code, 0)
        self.assertIn('x07-B5-codex-B: STOP locator: more than one changed product tree: cell/work, '
                      'cell/.devlyn-worktrees/work/x', stderr)
        self.assertEqual((self.verdict('x07-B5-codex-B')['status'], 'snapshot' in self.verdict('x07-B5-codex-B')),
                         ('STOP', False))
        self.assertEqual(json.loads((self.out / 'driver-status-codex.json').read_text())['harm_latch']['cell'],
                         'x07-B5-codex-B')
        self.assertEqual([root for root in CODEX_CACHES if not (self.out / 'x07-B5-codex-B' / root).is_dir()], [])
        self.assertFalse((self.out / 'x07-B5-codex-B/pruned.json').exists())

        # 9. A cell whose container could not be set up (CG1: `docker create` refused) is a STOP with no owner and its
        # teardown as proved, not a prepared folder without a verdict; it is never redispatched, so it latches the
        # lanes, and nothing it made is left: no credential copy in scratch, no container.
        code, stderr = self.finish(self.launch('--clear-latch', amendment, self.runtime['codex']))
        self.assertEqual(code, 0, stderr[-3000:])
        setup = self.fake / 'setup.tsv'
        setup.write_text('x09-SMOKE-codex-A\tSMOKE\tA\tcodex\t1\n')
        (self.fake / 'create-fails-x09-SMOKE-codex-A').write_text('inject once\n')
        code, stderr = self.finish(self.driver('codex', setup))
        self.assertNotEqual(code, 0)
        self.assertIn('x09-SMOKE-codex-A: STOP cell setup failed: CalledProcessError', stderr)
        failed = self.verdict('x09-SMOKE-codex-A')
        self.assertEqual((failed['status'], failed['owner_ran'], failed['owner_status'], failed['teardown']),
                         ('STOP', False, None, 'CLEAN'))
        self.assertEqual(json.loads((self.out / 'driver-status-codex.json').read_text())['harm_latch']['cell'],
                         'x09-SMOKE-codex-A')
        self.assertFalse((self.root / 'scratch/credentials/x09-SMOKE-codex-A').exists())
        self.assertFalse([p for p in (self.fake / 'containers').glob('*.json') if 'x09-SMOKE-codex-A' in p.read_text()])


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] in FAKES:
        sys.exit(FAKES[sys.argv[1]](sys.argv[2:]))
    if len(sys.argv) > 1 and sys.argv[1] == 'launch':
        launch(sys.argv[2:])
    else:
        unittest.main()
