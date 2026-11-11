"""0265 dry end-to-end rehearsal: the real apparatus from the seal to the token, with fakes only at its edges.

Fakes: the `docker`, `security` and `claude` executables (this file run as `fake-docker`, `fake-security`,
`fake-claude`) and, inside each driver process, the Anthropic profile and usage endpoints (this file run as `launch`,
which then runs driver.py unchanged). The fake engines write what the real ones leave: the status line, the HOME
release, Claude's stream and transcript, Codex's stream and rollout trace, and one allowed product edit. Everything
else is the code a real run executes: driver.py, run_cell.py, prepare, cell, the 0233 identity, usage, quota, locate
and check modules, assess, instructions seal and seal-forms, then judge.py, recheck.py, harm_check.py, fc_judge.py and
decide.py. The control tree and the pinned sources are copied from the runtime root (read only there), so the test
skips when that root is not built. No model, keychain, network or real container is touched.

Run: python3 -m pytest -q autoresearch/experiments/0265/test_integration.py (about two minutes).
"""
import copy
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
        release = home / '.devlyn/cli/releases/devlyn-cli/4.3.30'
        release.mkdir(parents=True)
        shutil.copyfile(Path(where['/install']) / 'package/release.json', release / 'release.json')
    caller = json.loads((harness / 'caller.json').read_text())
    target = cell / 'work' / caller['allowed'][0]
    append(target, '\n# fake owner change\n' if target.suffix == '.py' else '\n// fake owner change\n')
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
        thread = str(uuid.uuid4())
        trace = cell / 'trace' / f'trace-1-{thread}'
        (trace / 'payloads').mkdir(parents=True)
        request = copy.deepcopy(shapes['codex_request'])
        if arm_b:
            request['input'].insert(4, {'type': 'message', 'role': 'developer', 'content': [
                {'type': 'input_text', 'text': (state() / 'session_text.txt').read_text()}]})
            folder = home / '.codex/plugins/cache/devlyn-harness-v4-3-30/devlyn/4.3.30'
            (folder / '.codex-plugin').mkdir(parents=True)
            (folder / '.codex-plugin/plugin.json').write_text('{"name": "devlyn"}\n')
            (folder / '.devlyn-harness-projection.json').write_text('{"schemaVersion": 1}\n')
        payloads = {'meta.json': dict(model='gpt-6-astra'), 'request.json': request,
                    'configured.json': dict(thread_id=thread, model='gpt-6-astra', reasoning_effort='high'),
                    'response.json': dict(token_usage=dict.fromkeys(COUNTERS, 7))}
        for file, body in payloads.items():
            (trace / 'payloads' / file).write_text(json.dumps(body))
        (trace / 'manifest.json').write_text(json.dumps(dict(schema_version=1, rollout_id=thread,
                                                             root_thread_id=thread, raw_event_log='trace.jsonl')))
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
    task = 'SMOKE' if cell.startswith('smoke-') or cell.startswith('x0') else cell.split('-')[1]
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
    if command == 'image':  # image inspect <image> --format {{.Id}}
        print(IMAGE)
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
                      command=args[args.index(IMAGE) + 1:], state=dict(Running=False, Pid=0, OOMKilled=False,
                                                                      ExitCode=0, Status='created',
                                                                      StartedAt='0001-01-01T00:00:00Z'))
        save(record)
        if record['name'].startswith('devlyn-0231-'):
            note('owners.jsonl', dict(cell=Path(record['mounts']['/cell']).parent.name, parent=os.getppid()))
        print(record['cid'])
        return 0
    if command == 'start':
        record = container(args[-1])
        code = witness(record) if record['name'].startswith(('witness-', 'probe-')) else owner_engine(record)
        record['state'].update(ExitCode=code, Status='exited', StartedAt='2026-11-11T00:00:00Z')
        save(record)
        return code
    if command == 'inspect':
        record = container(args[-1])
        if record is None:
            sys.stderr.write(f'Error: No such object: {args[-1]}\n')
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
        if name.startswith('devlyn-0265-disk-'):
            print(json.dumps({path: dict(total=460 * GIB, used=400 * GIB, free=60 * GIB) for path in ('/cell', '/tmp')}))
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
    """The profile and usage endpoints; FAKE_429_ONCE makes this process's first usage read an HTTP 429."""
    url = request.full_url if hasattr(request, 'full_url') else str(request)
    if url.endswith('/api/oauth/profile'):
        return Endpoint(json.dumps({'account': {'uuid': 'account-0265'}, 'organization': {'uuid': 'org-0265'}}).encode())
    if url.endswith('/api/oauth/usage'):
        note('usage.jsonl', dict(pid=os.getpid()))
        if os.environ.pop('FAKE_429_ONCE', None):
            raise urllib.error.HTTPError(url, 429, 'Too Many Requests', {}, None)
        reset = '2026-11-12T00:00:00+00:00'
        return Endpoint(json.dumps({'five_hour': {'utilization': 10, 'resets_at': reset},
                                    'seven_day': {'utilization': 20, 'resets_at': reset}}).encode())
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
        (self.fake / 'home/.codex/auth.json').write_text('{"fake": "codex login"}\n')
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
        self.timing = named(rows, 'claude', 'D4', 'A', 1)
        self.unresolved = named(rows, 'codex', 'D3', 'A', 1)
        self.unassessable = named(rows, 'codex', 'F10', 'B', 1)
        (self.fake / 'rules.json').write_text(json.dumps(dict(
            claim=[self.claim], fail_public='-B5-codex-A-',
            reproduces=[[self.claim, 'd4-writer-death']], unresolved=[[self.unresolved, 'd3-regression-child-probe']])))
        for marker in (f'launch-fault-{self.launch_fault}', f'timing-{self.timing}',
                       f'probe-unassessable-{self.unassessable}'):
            (self.fake / marker).write_text('inject once\n')

    def tearDown(self):
        os.environ.pop('FAKE_STATE', None)
        self.temp.cleanup()

    def tool(self, *args, **extra):
        return subprocess.run([sys.executable, '-B', *map(str, args)], env=dict(self.env, **extra),
                              capture_output=True, text=True, timeout=900)

    def driver(self, lane, tsv, **extra):
        return subprocess.Popen([sys.executable, '-I', '-B', str(Path(__file__).resolve()), 'launch',
                                 str(self.runtime[lane]), str(tsv)], env=dict(self.env, **extra),
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

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
        # 1. The no-model seal, then SMOKE: four cells through one driver process, then seal-forms.
        sealed = self.tool(HERE / 'instructions.py', 'seal', self.runtime['smoke'])
        self.assertEqual(sealed.returncode, 0, sealed.stderr)
        seal = json.loads((self.root / 'instructions.seal.json').read_text())
        self.assertEqual(seal['qualification'], dict(status='PENDING'))
        (self.fake / 'session_text.txt').write_text(seal['session_text'])
        code, stderr = self.finish(self.driver('smoke', HERE / 'smoke.tsv'))
        self.assertEqual(code, 0, stderr[-3000:])
        smoke = ['smoke-claude-A', 'smoke-claude-B', 'smoke-codex-A', 'smoke-codex-B']
        self.assertEqual({name: self.verdict(name)['status'] for name in smoke}, dict.fromkeys(smoke, 'COMPLETE'))
        for name in smoke:
            verdict = self.verdict(name)
            self.assertEqual((verdict['identity']['status'], verdict['teardown'], verdict['usage']),
                             ('MATCH', 'CLEAN', 'COMPLETE'), name)
        forms = self.tool(HERE / 'instructions.py', 'seal-forms', self.runtime['smoke'])
        self.assertEqual(forms.returncode, 0, forms.stderr)
        seal = json.loads((self.root / 'instructions.seal.json').read_text())
        self.assertEqual(seal['qualification']['status'], 'PASS')
        self.assertEqual(set(seal['forms']), {'claude', 'codex'})

        # 2. Both lanes at once, in two real processes, over the r <= 2 slice; the host login at the 300 s mark, one
        # injected B launch fault (claude lane) and one injected HTTP 429 hold (codex lane).
        keychain(time.time() + 200)
        lanes = {'claude': self.driver('claude', self.fake / 'slice.tsv'),
                 'codex': self.driver('codex', self.fake / 'slice.tsv', FAKE_429_ONCE='1')}
        pids = {lane: process.pid for lane, process in lanes.items()}
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

        # The launch fault was archived and redispatched without a latch; the 429 was a hold, never a verdict.
        archived = json.loads((self.out / f'verdict-{self.launch_fault}.stop-1.json').read_text())
        self.assertTrue(archived['reason'].startswith('B launch fault: run-argument-unsupported'), archived['reason'])
        self.assertTrue((self.out / f'{self.launch_fault}.stop-1').is_dir())
        self.assertEqual(self.verdict(self.launch_fault)['status'], 'COMPLETE')
        self.assertEqual(sum(e['event'] == 'run' and e['cell'] == self.launch_fault for e in self.log('claude')), 2)
        holds = [e['reason'] for e in self.log('codex') if e['event'] == 'hold']
        self.assertTrue(any(r.startswith('Claude window check failed: HTTP Error 429') for r in holds), holds)
        self.assertFalse(any(self.out.glob('verdict-*-codex-*.stop-*.json')))

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

        # 3. The grading scripts after the last cell, on the slice, with fake seats and fake witness runs.
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
            judge.run_all()
            judge.probe_all()
            timing = recheck.recheck(runtime)
            harmed = harm.main(runtime, [])
            judged = fc.run(runtime)
        self.assertEqual((self.root / 'auth-smoke/codex.json').read_bytes(),
                         (self.fake / 'home/.codex/auth.json').read_bytes())
        witnesses = json.loads((self.out / 'witnesses.json').read_text())
        self.assertIs(witnesses['d4-writer-death'][self.claim]['result'], True)
        self.assertEqual(witnesses['d3-regression-child-probe'][self.unresolved]['result'], 'unresolved')
        probes = json.loads((self.out / 'probes.json').read_text())
        self.assertEqual([a['class'] for a in probes[self.unassessable]['attempts']], ['unassessable', 'json_error_400'])
        self.assertEqual(timing['cells'], {self.timing: {'public:0': dict(
            inline='FAIL', reruns=['PASS', 'PASS'], timing_suspect=True)}})
        self.assertEqual(set(harmed['cells']), {r[0] for r in self.slice})
        self.assertEqual({name: entry['harm'] for name, entry in harmed['cells'].items() if entry['harm']}, {})
        self.assertEqual(sorted((p['cell'], p['witness'], p['witness_result'], p['call']) for p in judged['pairs']),
                         sorted([(self.claim, 'd4-writer-death', 'true', 'true'),
                                 (self.unresolved, 'd3-regression-child-probe', 'unresolved', 'false')]))

        # 4. decide.py on the folder: the slice leaves every reading and line NOT_FINISHED.
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
                                  ('harm.json', documents['harm.json']['cells']),
                                  ('timing-recheck.json', documents['timing-recheck.json']['cells'])):
                if source in document:
                    document[name] = document[source]
            documents['false-completion.json']['pairs'] += [dict(pair, cell=name) for pair in judged['pairs']
                                                            if pair['cell'] == source]
        for name, document in documents.items():
            (self.out / name).write_text(json.dumps(document))
        decided = self.tool(HERE / 'decide.py', self.runtime['codex'])
        self.assertEqual(decided.returncode, 0, decided.stderr)
        token = decided.stdout.splitlines()[-1]
        number = r'-?[\d.e-]+'
        self.assertRegex(token, rf'^0265:claude=R2:REPLICATED\(8/8v0/8,p={number}\),D3:\w+\({number}\[{number},'
                                rf'{number}\]\),HARM:\w+\(\d+v\d+\);codex=R1:REPLICATED\(0/8v8/8,p={number}\),'
                                rf'D3:\w+\({number}\[{number},{number}\]\),HARM:\w+\(\d+v\d+\)$')
        self.assertNotIn('NOT_FINISHED', token)
        decision = json.loads((self.out / 'decision.json').read_text())
        self.assertEqual(decision['reported']['faults']['claude']['B launch fault'],
                         [f'{self.launch_fault} stop-1: {archived["reason"]}'])
        self.assertEqual(decision['lines']['claude']['harm']['harmful'], dict(A=0, B=4))
        self.assertEqual(len(decision['reported']['timing']['suspects']), 4)

        # 5. The latch across processes: a second B launch fault in a row latches the claude lane, and the codex
        # lane, started afterwards, refuses to dispatch and names the lane that latched.
        extra = self.fake / 'latch.tsv'
        extra.write_text('x01-SMOKE-claude-B\tSMOKE\tB\tclaude\t1\nx02-SMOKE-claude-A\tSMOKE\tA\tclaude\t1\n')
        for suffix in ('-1', '-2'):
            (self.fake / f'launch-fault-x01-SMOKE-claude-B{suffix}').write_text('inject\n')
        code, stderr = self.finish(self.driver('claude', extra))
        self.assertNotEqual(code, 0)
        self.assertIn('second B launch fault in a row in lane claude', stderr)
        self.assertFalse((self.out / 'x02-SMOKE-claude-A').exists())
        other = self.fake / 'other.tsv'
        other.write_text('x03-SMOKE-codex-A\tSMOKE\tA\tcodex\t1\n')
        code, stderr = self.finish(self.driver('codex', other))
        self.assertNotEqual(code, 0)
        self.assertIn('harm latch in lane claude', stderr)
        self.assertFalse((self.out / 'x03-SMOKE-codex-A').exists())


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] in FAKES:
        sys.exit(FAKES[sys.argv[1]](sys.argv[2:]))
    if len(sys.argv) > 1 and sys.argv[1] == 'launch':
        launch(sys.argv[2:])
    else:
        unittest.main()
