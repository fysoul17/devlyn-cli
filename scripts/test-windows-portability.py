#!/usr/bin/env python3
"""Real npm/native-process portability checks; --package-root tests a downloaded install.

Pass unittest class/method names for focused development checks. No model calls.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import locale
import os
from pathlib import Path
import runpy
import shutil
import subprocess
import sys
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
PACKAGE_ROOT = None
SHORT_PAYLOAD = '한국어 프롬프트 — “정확 바이트” …\r\n마지막\n\n'.encode('utf-8')
PAYLOAD = SHORT_PAYLOAD * 1024


def environment():
    env = {k: v for k, v in os.environ.items() if not k.startswith(('DEVLYN_', 'CODEX_MONITORED_', 'GIT_'))
           and k not in ('CODEX_BLOCKED', 'CODEX_BIN', 'CODEX_REAL_BIN', 'PYTHONUTF8', 'PYTHONIOENCODING')}
    env.update(GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM='1', PYTHONDONTWRITEBYTECODE='1')
    return env


def run(argv, *, cwd=None, env=None, code=0, timeout=40):
    proc = subprocess.run([str(arg) for arg in argv], cwd=cwd, env=env or environment(),
                          stdin=subprocess.DEVNULL, capture_output=True, timeout=timeout)
    if code is not None:
        assert proc.returncode == code, (argv, proc.returncode, proc.stdout, proc.stderr)
    return proc


def npm(args, temp):
    binary = Path(shutil.which('npm') or 'npm').resolve()
    if os.name == 'nt':
        # Invoke npm's installed Node entrypoint; fixture argv never passes through cmd.exe.
        cli = binary.parent / 'node_modules/npm/bin/npm-cli.js'
        command = [shutil.which('node'), cli]
    else:
        command = [str(binary)]
    return run([*command, *args, '--cache', str(temp / 'npm-cache')], timeout=90)


def helper(name):
    return runpy.run_path(str((PACKAGE_ROOT or ROOT) / 'config/skills/_shared' / (name + '.py')))


def wait_for(predicate, timeout=8):
    deadline = time.monotonic() + timeout
    while not predicate():
        assert time.monotonic() < deadline, 'fixture did not become ready'
        time.sleep(0.03)


def process_running(pid):
    if os.name == 'nt':
        import ctypes
        from ctypes import wintypes
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        kernel.OpenProcess.restype = wintypes.HANDLE
        kernel.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
        kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        handle = kernel.OpenProcess(0x100000, False, pid)
        if not handle:
            if ctypes.get_last_error() == 87:  # PID no longer exists.
                return False
            raise ctypes.WinError(ctypes.get_last_error())
        try:
            result = kernel.WaitForSingleObject(handle, 0)
            assert result in (0, 258), result
            return result == 258
        finally:
            kernel.CloseHandle(handle)
    if sys.platform.startswith('linux'):
        try:
            state = Path(f'/proc/{pid}/stat').read_text(encoding='utf-8').rsplit(')', 1)[1].split()[0]
        except FileNotFoundError:
            return False
        return state != 'Z'
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    return True


class PackageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix='devlyn-package-')
        cls.root = Path(cls.temp.name).resolve()
        if PACKAGE_ROOT:
            cls.package = PACKAGE_ROOT
        else:
            packed = npm(['pack', str(ROOT), '--ignore-scripts', '--json', '--pack-destination', str(cls.root)], cls.root)
            tarball = cls.root / json.loads(packed.stdout)[0]['filename']
            print('packed artifact sha256=' + hashlib.sha256(tarball.read_bytes()).hexdigest(), flush=True)
            npm(['install', '--prefix', str(cls.root / 'installed'), '--offline', '--ignore-scripts',
                 '--no-audit', '--no-fund', str(tarball)], cls.root)
            cls.package = cls.root / 'installed/node_modules/devlyn-cli'
        cls.preload = cls.root / 'homedir.cjs'
        cls.preload.write_text("require('os').homedir = () => process.env.DEVLYN_TEST_HOME;\n", encoding='utf-8')
        cls.invoker = cls.root / 'invoke.cjs'
        cls.invoker.write_text("""const fs = require('fs'), Module = require('module');
const filename = process.argv[2];
const m = new Module(filename); m.filename = filename; m.paths = Module._nodeModulePaths(require('path').dirname(filename));
const source = fs.readFileSync(filename, 'utf8').split('const args = process.argv.slice(2);')[0];
m._compile(source + '\\n' + process.argv[3], filename);
""", encoding='utf-8')

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def setUp(self):
        self.case = Path(tempfile.mkdtemp(dir=self.root, prefix='설치 '))
        self.project = self.case / 'project'; self.project.mkdir()
        self.home = self.case / 'agent-home'; self.home.mkdir()
        self.env = environment(); self.env['DEVLYN_TEST_HOME'] = str(self.home)

    def invoke(self, body, package=None, code=0):
        return run(['node', '--require', self.preload, self.invoker,
                    (package or self.package) / 'bin/devlyn.js', body], cwd=self.project, env=self.env, code=code)

    def roots(self):
        return [self.project / '.claude/skills', self.home / '.codex/skills', self.home / '.agents/skills', self.home / '.grok/skills']

    def test_pack_install_reinstall_optional_stamps(self):
        self.invoke("installClaudeCore(); installSelectedCLITargets(['codex', 'omp', 'pi', 'grok']); installLocalSkill('devlyn:reap');")
        name = 'devlyn\uf03aresolve' if os.name == 'nt' else 'devlyn:resolve'
        optional = 'devlyn\uf03areap' if os.name == 'nt' else 'devlyn:reap'
        for root in self.roots():
            self.assertTrue((root / '.devlyn-install.json').is_file())
            text = (root / name / 'SKILL.md').read_text(encoding='utf-8')
            self.assertIn('name: devlyn:resolve', text)
            self.assertNotIn('${CLAUDE_SKILL_DIR:-__DEVLYN_SKILL_DIR__}', text)
            self.assertIn('__DEVLYN_SKILL_DIR__', text)  # Sentinel guard remains literal.
            self.assertTrue((root / optional / 'SKILL.md').is_file())
            (root / name / 'stale').write_bytes(b'old')
            (root / optional / 'stale').write_bytes(b'old')
            (root / 'user-skill').mkdir(); (root / 'user-skill/keep').write_bytes(b'user')
            old = 'devlyn\uf03aauto-resolve' if os.name == 'nt' else 'devlyn:auto-resolve'
            (root / old).mkdir()
        self.invoke("installClaudeCore(); installSelectedCLITargets(['codex', 'omp', 'pi', 'grok']); installLocalSkill('devlyn:reap');")
        for root in self.roots():
            self.assertFalse((root / name / 'stale').exists())
            self.assertFalse((root / optional / 'stale').exists())
            self.assertEqual((root / 'user-skill/keep').read_bytes(), b'user')
            self.assertFalse((root / old).exists())

    def test_incomplete_source_has_no_marker(self):
        copy = self.case / 'broken'; shutil.copytree(self.package, copy)
        skill = next((copy / 'config/skills').glob('devlyn*resolve'))
        (skill / 'SKILL.md').unlink()
        result = self.invoke("installSkillsForCLI('codex');", package=copy, code=None)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(b'Incomplete devlyn skill install', result.stderr)
        self.assertFalse((self.home / '.codex/skills/.devlyn-install.json').exists())

    @unittest.skipIf(os.name == 'nt', 'ASCII-colon aliases cannot coexist as native Windows directories')
    def test_extraction_alias_and_ambiguity_before_cleanup(self):
        copy = self.case / 'aliased'; shutil.copytree(self.package, copy)
        for root in (copy / 'config/skills', copy / 'optional-skills'):
            for p in root.iterdir():
                if ':' in p.name:
                    p.rename(p.with_name(p.name.replace(':', '\uf03a')))
        self.invoke("installClaudeCore(); installSkillsForCLI('codex'); installLocalSkill('devlyn:reap');", package=copy)
        target = self.home / '.codex/skills'
        alias = target / 'devlyn\uf03aresolve'; alias.mkdir(); (alias / 'keep').write_bytes(b'alias')
        result = self.invoke("installSkillsForCLI('codex');", package=copy, code=None)
        self.assertNotEqual(result.returncode, 0); self.assertIn(b'Ambiguous skill aliases', result.stderr)
        self.assertEqual((alias / 'keep').read_bytes(), b'alias')
        self.assertTrue((target / 'devlyn:resolve/SKILL.md').exists())
        self.assertFalse((target / '.devlyn-install.json').exists())
        shutil.rmtree(alias)
        source = copy / 'config/skills'
        shutil.copytree(source / 'devlyn\uf03aresolve', source / 'devlyn:resolve')
        result = self.invoke("installSkillsForCLI('codex');", package=copy, code=None)
        self.assertNotEqual(result.returncode, 0); self.assertIn(b'Ambiguous skill aliases', result.stderr)
        self.assertTrue((target / 'devlyn:resolve/SKILL.md').exists())


class ProcessTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='devlyn-native-')
        self.addCleanup(self.temp.cleanup)
        self.work = Path(self.temp.name).resolve()
        self.shared = (PACKAGE_ROOT or ROOT) / 'config/skills/_shared'
        self.bounded = self.shared / 'run-bounded.py'
        self.prompt = self.work / '한국어 prompt'; self.prompt.write_bytes(PAYLOAD)

    def test_binary_stdin_and_no_dispatch_errors(self):
        binary = PAYLOAD + b'\x00\xff'
        self.prompt.write_bytes(binary)
        child = self.work / 'child.py'
        child.write_text("import pathlib,sys; pathlib.Path(sys.argv[1]).write_bytes(sys.stdin.buffer.read()); sys.exit(7)", encoding='utf-8')
        out = self.work / 'received'
        run([sys.executable, self.bounded, '10', '--stdin-file', self.prompt, '--', sys.executable, child, out], code=7)
        self.assertEqual(out.read_bytes(), binary)
        out.unlink()
        for path in (self.work / '없는 파일', self.work):
            result = run([sys.executable, self.bounded, '10', '--stdin-file', path, '--', sys.executable, child, out], code=2)
            self.assertIn(b'error:', result.stderr); self.assertFalse(out.exists())
        run([sys.executable, self.bounded, '10', '--', sys.executable, child, out], code=7)
        self.assertEqual(out.read_bytes(), b'')
        result = run([sys.executable, self.bounded, '10', '--', str(self.work / 'missing-command')], code=2)
        self.assertIn(b'error:', result.stderr)

    def test_large_stdin_reuse_without_evidence_output(self):
        self.assertGreaterEqual(len(PAYLOAD), 64 * 1024)
        command = [sys.executable, self.bounded, '10', '--stdin-file', self.prompt, '--',
                   sys.executable, '-c', 'import sys; sys.stdout.buffer.write(sys.stdin.buffer.read())']
        for _ in range(2):
            self.assertEqual(run(command).stdout, PAYLOAD)
            self.assertEqual(list(self.work.iterdir()), [self.prompt])
        carrier = self.prompt.with_name(self.prompt.name + '.transport.json')
        carrier.write_bytes(b'prior sealed invocation')
        self.assertEqual(run(command).stdout, PAYLOAD)
        self.assertEqual(carrier.read_bytes(), b'prior sealed invocation')

    def test_explicit_transport_is_fresh_and_ordinary_read_preserves_it(self):
        child = [sys.executable, '-c', 'import sys; sys.stdout.buffer.write(sys.stdin.buffer.read())']
        command = [sys.executable, self.bounded, '10', '--stdin-file', self.prompt, '--record-transport', '--', *child]
        self.assertEqual(run(command).stdout, PAYLOAD)
        carrier = self.prompt.with_name(self.prompt.name + '.transport.json')
        original = carrier.read_bytes()
        record = helper('invocation-receipt')['validate_transport'](carrier, PAYLOAD)
        self.assertEqual(record['exit_code'], 0)
        rejected = run(command, code=2)
        self.assertIn(b'transport already exists', rejected.stderr)
        self.assertEqual(rejected.stdout, b'')
        self.assertEqual(run([sys.executable, self.bounded, '10', '--stdin-file', self.prompt, '--', *child]).stdout, PAYLOAD)
        self.assertEqual(carrier.read_bytes(), original)

    def test_utf8_imports_and_cli_with_utf8_mode_disabled(self):
        program = r'''
import codecs, io, json, locale, pathlib, runpy, sys
shared, work = map(pathlib.Path, sys.argv[1:])
with io.TextIOWrapper(io.BytesIO()) as default_text:
    default_encoding = default_text.encoding
print(json.dumps({'platform':sys.platform,'utf8_mode':sys.flags.utf8_mode,
                  'locale':locale.getencoding(),'default_textio':default_encoding,
                  'stdin':sys.stdin.encoding,'stdout':sys.stdout.encoding,'stderr':sys.stderr.encoding}), flush=True)
assert sys.flags.utf8_mode == 0
if sys.platform == 'win32':
    assert codecs.lookup(locale.getencoding()).name != 'utf-8', locale.getencoding()
    assert codecs.lookup(default_encoding).name == codecs.lookup(locale.getencoding()).name
payload = '한국어 — “판정” …'
role = runpy.run_path(shared / 'role-config.py')
assert role['adapter']('codex').encode('utf-8') == (shared / 'adapters/codex.md').read_bytes()
completion = runpy.run_path(shared / 'task-complete.py')
p = work / '한국어.json'
completion['atomic_json'](p, {'message':payload})
assert completion['read_json'](p)['message'] == payload
spec = runpy.run_path(shared / 'spec-verify-check.py')
md = work / 'spec.md'
md.write_text('# 한국어\n<!-- devlyn:verification -->\n## Verification\n```json\n'+json.dumps({'verification_commands':[{'cmd':'echo 한국어'}]},ensure_ascii=False)+'\n```\n', encoding='utf-8')
assert spec['stage_from_source'](md, work / '.devlyn') == (True, None)
assert json.loads((work / '.devlyn/spec-verify.json').read_text(encoding='utf-8'))['verification_commands'][0]['cmd'] == 'echo 한국어'
# Explicit cp949 streams are distinct from the observed native ANSI default.
sys.stdout.reconfigure(encoding='cp949', errors='strict')
sys.stderr.reconfigure(encoding='cp949', errors='strict')
print(json.dumps({'stream_fixture':'cp949','stdout':sys.stdout.encoding,'stderr':sys.stderr.encoding}), flush=True)
runpy.run_path(shared / 'platform-support.py')['configure_utf8']()
print(payload)
print(payload, file=sys.stderr)
'''
        result = run([sys.executable, '-X', 'utf8=0', '-c', program, self.shared, self.work])
        observed = json.loads(result.stdout.splitlines()[0]); print('observed encoding ' + json.dumps(observed), flush=True)
        print('explicit cp949 streams ' + result.stdout.splitlines()[1].decode('ascii'), flush=True)
        if os.name != 'nt': print('SKIP native Windows ANSI defaults; cp949 streams and UTF8-disabled imports exercised', flush=True)
        self.assertIn('한국어 — “판정” …'.encode(), result.stdout)
        self.assertIn('한국어 — “판정” …'.encode(), result.stderr)
        env = environment(); env['PYTHONUTF8'] = '0'
        error = run([sys.executable, '-X', 'utf8=0', self.bounded, '5', '--stdin-file', self.work / '없는 파일', '--', sys.executable, '-c', 'raise AssertionError()'], env=env, code=2)
        self.assertIn('없는 파일'.encode(), error.stderr)

    def test_bootstrap_and_completion_native_locks(self):
        repo = self.work / 'repo'; repo.mkdir()
        run(['git', 'init', '-q', repo])
        run(['git', '-C', repo, '-c', 'user.name=Test', '-c', 'user.email=test@example.com', 'commit', '--allow-empty', '-qm', 'base'])
        ready = self.work / 'ready'
        script = self.shared / 'resolve-bootstrap.py'
        holder = "import pathlib,runpy,sys,time; m=runpy.run_path(sys.argv[1]);\nwith m['admission_lock'](pathlib.Path(sys.argv[2])):\n pathlib.Path(sys.argv[3]).touch(); time.sleep(20)"
        proc = subprocess.Popen([sys.executable, '-c', holder, str(script), str(repo), str(ready)], env=environment(), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        try:
            wait_for(ready.exists)
            blocked = json.loads(run([sys.executable, script, '한국어 goal'], cwd=repo, code=1).stdout)
            self.assertEqual(blocked['blocked'], 'BLOCKED:bootstrap-contended')
            self.assertFalse((repo / '.devlyn').exists())
        finally:
            proc.kill(); proc.communicate(timeout=5)
        self.assertTrue(json.loads(run([sys.executable, script, '한국어 goal'], cwd=repo).stdout)['ok'])
        shutil.rmtree(repo / '.devlyn'); lock = repo / '.git/devlyn-bootstrap.lock'; lock.unlink(); lock.mkdir()
        blocked = json.loads(run([sys.executable, script, 'retry'], cwd=repo, code=1).stdout)
        self.assertEqual(blocked['blocked'], 'BLOCKED:bootstrap-lock-unavailable')
        self.assertFalse((repo / '.devlyn').exists())
        complete = helper('task-complete')
        branch = 'task/native-lock'; ident = hashlib.sha256(branch.encode()).hexdigest()[:24]
        receipt = self.work / 'common/devlyn-completion' / ident / 'receipt.json'; receipt.parent.mkdir(parents=True)
        complete['atomic_json'](receipt, {'common_gitdir': str(self.work / 'common'), 'id': ident,
                                        'branch': branch, 'base': 'main', 'allocation': 'owned'})
        holder = "import pathlib,runpy,sys,time; m=runpy.run_path(sys.argv[1]);\nwith m['locked_receipt'](pathlib.Path(sys.argv[2])):\n pathlib.Path(sys.argv[3]).touch(); time.sleep(20)"
        ready.unlink()
        proc = subprocess.Popen([sys.executable, '-c', holder, str(self.shared / 'task-complete.py'), str(receipt), str(ready)], env=environment(), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        contender = None
        try:
            wait_for(ready.exists)
            acquired = self.work / 'acquired'
            contender = subprocess.Popen([sys.executable, '-c', holder.replace('time.sleep(20)', 'pass'), str(self.shared / 'task-complete.py'), str(receipt), str(acquired)], env=environment(), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            time.sleep(0.2); self.assertIsNone(contender.poll()); self.assertFalse(acquired.exists())
            proc.kill(); proc.communicate(timeout=5)
            out, err = contender.communicate(timeout=5)
            self.assertEqual((contender.returncode, out, err), (0, b'', b'')); self.assertTrue(acquired.exists())
        finally:
            for child in (proc, contender):
                if child is not None and child.poll() is None:
                    child.kill(); child.communicate(timeout=5)
        with self.assertRaises(RuntimeError):
            with complete['locked_receipt'](receipt):
                raise RuntimeError('release on exception')
        with complete['locked_receipt'](receipt):
            pass
        (receipt.parent / 'lock').unlink(); (receipt.parent / 'lock').mkdir()
        with self.assertRaisesRegex(complete['CompletionError'], 'lock unavailable'):
            with complete['locked_receipt'](receipt):
                self.fail('unavailable lock admitted')
        if os.name == 'nt':
            with self.assertRaisesRegex(complete['CompletionError'], 'unsupported.*retain workspace'):
                complete['stopped_writers'](repo, linked=False)

    @unittest.skipUnless(os.name == 'nt', 'native Windows junction invariant')
    def test_bootstrap_directory_junction(self):
        repo = self.work / 'repo'; repo.mkdir()
        run(['git', 'init', '-q', repo]); run(['git', '-C', repo, '-c', 'user.name=Test', '-c', 'user.email=test@example.com', 'commit', '--allow-empty', '-qm', 'base'])
        target = self.work / 'elsewhere'; target.mkdir(); (target / 'keep').write_bytes(PAYLOAD)
        for relative in ('.devlyn', '.devlyn/runs'):
            link = repo / relative; link.parent.mkdir(exist_ok=True)
            run(['cmd.exe', '/d', '/c', 'mklink', '/J', link, target])
            try:
                print(f'junction observed: is_symlink={link.is_symlink()} resolved={link.resolve()}', flush=True)
                self.assertFalse(link.is_symlink()); self.assertEqual(link.resolve(), target)
                result = run([sys.executable, self.shared / 'resolve-bootstrap.py', 'goal'], cwd=repo, code=1)
                self.assertEqual(json.loads(result.stdout)['blocked'], 'BLOCKED:devlyn-path-redirect')
                self.assertEqual(list(target.iterdir()), [target / 'keep']); self.assertEqual((target / 'keep').read_bytes(), PAYLOAD)
            finally:
                link.rmdir()

    def test_bounded_timeout_stops_descendants(self):
        leaf = self.work / 'leaf.py'
        leaf.write_text("import pathlib,sys,time,os,signal\nif sys.argv[2] == 'True': signal.signal(signal.SIGTERM, signal.SIG_IGN)\np=pathlib.Path(sys.argv[1]); p.with_suffix('.pid').write_text(str(os.getpid()),encoding='utf-8')\nwhile True:\n p.write_bytes(str(time.monotonic_ns()).encode()); time.sleep(.03)\n", encoding='utf-8')
        parent = 'import subprocess,sys,time; subprocess.Popen([sys.executable,*sys.argv[1:]]); time.sleep(30)'
        for stubborn in ((False,) if os.name == 'nt' else (False, True)):
            with self.subTest(stubborn=stubborn):
                marker = self.work / ('ticks-' + str(stubborn))
                result = run([sys.executable, self.bounded, '1', '--', sys.executable, '-c', parent, leaf, marker, str(stubborn)], code=124, timeout=15)
                self.assertEqual(result.returncode, 124); self.assertTrue(marker.exists())
                before = marker.read_bytes(); time.sleep(.2); self.assertEqual(marker.read_bytes(), before)
                wait_for(lambda: not process_running(int(marker.with_suffix('.pid').read_text(encoding='utf-8'))))
                print('bounded descendant ceased stubborn=' + str(stubborn) + ' native pid=' + marker.with_suffix('.pid').read_text(encoding='utf-8'), flush=True)


class EngineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bash = shutil.which('bash')
        if cls.bash is None:
            raise RuntimeError('Bash unavailable on PATH')
        cls.temp = tempfile.TemporaryDirectory(prefix='devlyn-engines-')
        cls.root = Path(cls.temp.name).resolve()
        cls.prefix = cls.root / 'native 설치'
        engine_source = r"""#!/usr/bin/env node
const fs = require('fs');
const a = process.argv.slice(2);
if (a.includes('--version')) { console.log('fixture-cli 1.2.3'); process.exit(0); }
if (process.env.DEVLYN_TEST_REPLACE_PROMPT) fs.writeFileSync(process.env.DEVLYN_TEST_REPLACE_PROMPT, 'changed after dispatch');
if (process.env.DEVLYN_TEST_LEAF) {
  const cp = require('child_process');
  fs.writeFileSync(process.env.DEVLYN_TEST_NODE_PID, String(process.pid));
  cp.spawn(process.env.DEVLYN_TEST_PYTHON, [process.env.DEVLYN_TEST_LEAF, process.env.DEVLYN_TEST_TICKS], {stdio:'inherit'});
  setTimeout(() => process.exit(0), 30000);
} else {
 const chunks = [];
 process.stdin.on('data', data => chunks.push(data));
 process.stdin.on('end', () => {
  const data = Buffer.concat(chunks);
  fs.writeFileSync(process.env.DEVLYN_TEST_SEEN, JSON.stringify({argv:a, stdin:data.toString('hex')}));
  if (a.includes('read-only')) {
   const val = key => a[a.indexOf(key)+1];
   console.error('OpenAI Codex v1.2.3\n--------\nworkdir: '+val('-C')+'\nmodel: '+val('-m')+'\nsandbox: read-only\nreasoning effort: high\nsession id: fixture-session\n--------\nuser\n'+data.toString('utf8'));
   console.log('PASS');
  } else if (a.includes('--output-format')) {
   console.log(JSON.stringify({type:'result',subtype:'success',is_error:false,stop_reason:'end_turn',session_id:'fixture-claude',result:'PASS',modelUsage:{'fixture-claude-model':{}}}));
  } else console.log(JSON.stringify({type:'fixture'}));
 });
}
"""
        for engine, package in [('codex', '@openai/codex'), ('claude', '@anthropic-ai/claude-code')]:
            folder = cls.root / engine; folder.mkdir()
            (folder / 'package.json').write_text(json.dumps({'name': package, 'version':'1.2.3', 'bin':{engine:'cli.js'}}), encoding='utf-8')
            (folder / 'cli.js').write_text(engine_source, encoding='utf-8'); (folder / 'cli.js').chmod(0o755)
            npm(['install', '--global', '--prefix', str(cls.prefix), '--offline', '--ignore-scripts',
                 '--no-audit', '--no-fund', str(folder)], cls.root)
        cls.bins = cls.prefix if os.name == 'nt' else cls.prefix / 'bin'

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def setUp(self):
        self.work = Path(tempfile.mkdtemp(dir=self.root, prefix='work-')).resolve()
        self.devlyn = self.work / '.devlyn'; self.devlyn.mkdir()
        self.shared = (PACKAGE_ROOT or ROOT) / 'config/skills/_shared'
        self.env = environment(); self.env['PATH'] = str(self.bins) + os.pathsep + self.env['PATH']
        self.env.update(CODEX_BIN=str(self.bins / ('codex.cmd' if os.name == 'nt' else 'codex')),
                        CODEX_MONITORED_HEARTBEAT='1', CODEX_MONITORED_TIMEOUT_SEC='10',
                        DEVLYN_TEST_SEEN=str(self.work / 'seen.json'))

    def seen(self):
        return json.loads((self.work / 'seen.json').read_text(encoding='utf-8'))

    def monitor(self, args, stdout=None, code=0):
        stdout = stdout or self.work / 'stdout'
        stderr = self.work / 'stderr'
        with stdout.open('wb') as out, stderr.open('wb') as err:
            result = subprocess.run([self.bash, str(self.shared / 'codex-monitored.sh'), *map(str, args)],
                                    cwd=self.work, env=self.env, stdin=subprocess.DEVNULL,
                                    stdout=out, stderr=err, timeout=20)
        if code is not None:
            self.assertEqual(result.returncode, code, stderr.read_bytes())
        return result.returncode

    def worker(self):
        prompt = self.devlyn / 'implement.prompt.0'; prompt.write_bytes(PAYLOAD)
        session = self.devlyn / 'implement.worker-session.0.jsonl'
        receipt = self.devlyn / 'implement.invocation.0.json'
        self.env.update(DEVLYN_CODEX_PROMPT_FILE=str(prompt), DEVLYN_INVOCATION_RUN_ID='rs-native',
                        DEVLYN_INVOCATION_PHASE='implement', DEVLYN_INVOCATION_ROUND='0',
                        DEVLYN_INVOCATION_WORKDIR=str(self.work), DEVLYN_INVOCATION_PROMPT_FILE=str(prompt),
                        DEVLYN_INVOCATION_SESSION_FILE=str(session), DEVLYN_INVOCATION_RECEIPT=str(receipt))
        args = ['-C', str(self.work), '-s', 'workspace-write', '-m', 'fixture-model', '--json',
                '-c', 'sandbox_workspace_write.network_access=false']
        return prompt, session, receipt, args

    def test_worker_exact_transport_legacy_and_tampering(self):
        self.assertGreaterEqual(len(PAYLOAD), 64 * 1024)
        prompt, session, receipt, args = self.worker()
        self.monitor([*args, '-'], session)
        self.assertEqual(bytes.fromhex(self.seen()['stdin']), PAYLOAD)
        receipts = helper('invocation-receipt')
        validate = lambda: receipts['validate_receipt_artifacts'](self.work, receipt, run_id='rs-native', phase='implement')
        record = validate()[0]
        self.assertEqual(record['argv_sha256'], hashlib.sha256(json.dumps(self.seen()['argv'][1:], separators=(',', ':')).encode()).hexdigest())
        carrier = prompt.with_name(prompt.name + '.transport.json')
        for path in (prompt, session, carrier):
            before = path.read_bytes(); path.write_bytes(before + b'changed')
            with self.assertRaises((ValueError, OSError)):
                validate()
            path.write_bytes(before)
        original = carrier.read_bytes(); obj = json.loads(original)
        obj['argv'][-1] = 'tampered'; carrier.write_text(json.dumps(obj), encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'digest mismatch'):
            validate()
        carrier.write_bytes(original)
        self.assertNotEqual(self.monitor([*args, '-'], session, code=None), 0)  # Same-round receipt reuse.
        self.env.pop('DEVLYN_CODEX_PROMPT_FILE')
        for key in tuple(self.env):
            if key.startswith('DEVLYN_INVOCATION_'): self.env.pop(key)
        self.monitor([*args, SHORT_PAYLOAD.decode().rstrip('\n')])
        self.assertEqual(bytes.fromhex(self.seen()['stdin']), b'')

    def test_rejects_competing_missing_and_mismatched_before_launch(self):
        prompt, session, receipt, args = self.worker()
        for arguments in ([*args, '-', 'competing'], [*args, '-', '-'], [*args, SHORT_PAYLOAD.decode()], [*args, '--unknown', '-']):
            self.assertNotEqual(self.monitor(arguments, session, code=None), 0)
            self.assertFalse((self.work / 'seen.json').exists()); self.assertFalse(receipt.exists())
        self.env['DEVLYN_CODEX_PROMPT_FILE'] = ''
        self.assertNotEqual(self.monitor([*args, '-'], session, code=None), 0)
        self.assertFalse((self.work / 'seen.json').exists()); self.assertFalse(receipt.exists())
        for source in (self.work / 'missing', self.work, self.work / 'other'):
            if source.name == 'other': source.write_bytes(PAYLOAD + b'mismatch')
            self.env['DEVLYN_CODEX_PROMPT_FILE'] = str(source)
            self.assertNotEqual(self.monitor([*args, '-'], session, code=None), 0)
            self.assertFalse((self.work / 'seen.json').exists()); self.assertFalse(receipt.exists())

    def test_snapshot_delivers_bytes_even_if_source_changes_after_dispatch(self):
        prompt, session, receipt, args = self.worker()
        self.env['DEVLYN_TEST_REPLACE_PROMPT'] = str(prompt)
        self.monitor([*args, '-'], session)
        self.assertEqual(bytes.fromhex(self.seen()['stdin']), PAYLOAD)
        with self.assertRaisesRegex(ValueError, 'prompt digest mismatch'):
            helper('invocation-receipt')['validate_receipt_artifacts'](self.work, receipt, run_id='rs-native', phase='implement')

    def test_archived_transport_completion_uses_custody_bytes(self):
        prompt, session, receipt, args = self.worker()
        self.monitor([*args, '-'], session)
        binding = helper('invocation-receipt')['validate_receipt'](
            self.work, receipt, run_id='rs-native', phase='implement', round_=0, model='fixture-model',
            prompt_sha256=hashlib.sha256(PAYLOAD).hexdigest(), session_path=session)
        phases = {name: {'started_at': '2026-09-10T00:00:00Z', 'completed_at': '2026-09-10T00:00:01Z', 'verdict': 'PASS'}
                  for name in ('plan', 'implement', 'build_gate', 'cleanup', 'verify', 'final_report')}
        phases['implement']['invocation_receipt'] = binding
        phases['cleanup']['post_sha'] = 'a' * 40
        report = b'<!-- devlyn:final-report run_id=rs-native -->\nTransport fixture completed.\n'
        (self.devlyn / 'final-report.md').write_bytes(report)
        phases['final_report'].update(output_sha256=hashlib.sha256(report).hexdigest(),
                                      artifacts={'log_file': '.devlyn/final-report.md'})
        (self.devlyn / 'criteria.generated.md').write_bytes(SHORT_PAYLOAD)
        state = {'run_id': 'rs-native', 'mode': 'free-form', 'phases': phases, 'process_evidence': None,
                 'source': {'type': 'generated', 'criteria_path': '.devlyn/criteria.generated.md',
                            'criteria_sha256': hashlib.sha256(SHORT_PAYLOAD).hexdigest()}}
        for name, value in (('pipeline.state.json', state), ('verify-merge.summary.json', {'verdict': 'PASS'}),
                            ('finish-gate.summary.json', {'mode': 'free-form', 'exit': 0, 'offenders': 0})):
            (self.devlyn / name).write_text(json.dumps(value), encoding='utf-8')
        helper('archive_run')['move_artifacts'](self.devlyn, self.devlyn / 'runs/rs-native')
        self.assertFalse(prompt.exists())
        complete = helper('task-complete')
        files = {path.relative_to(self.work).as_posix(): complete['file_record'](path)
                 for path in self.devlyn.rglob('*') if path.is_file()}
        custody = self.root / ('custody-' + self.work.name)
        complete['custody'](self.work, custody, files)
        prompt.write_bytes(b'mutable prompt from a later invocation')
        acceptance = {'run_id': 'rs-native', 'source_sha': 'a' * 40}
        complete['pipeline_acceptance'](custody, acceptance, files, self.root)
        retained = custody / '.devlyn/runs/rs-native' / prompt.name
        retained.write_bytes(b'tampered custody prompt')
        with self.assertRaisesRegex(complete['CompletionError'], 'prompt digest mismatch'):
            complete['pipeline_acceptance'](custody, acceptance, files, self.root)

    def test_native_shim_literal_argv_and_version(self):
        argv = ['', '한국어 space', '"quotes"', "'single'", 'a&b|c>sentinel', '%PATH%', '$(touch sentinel)', '^', 'line\nline']
        prompt = self.work / 'prompt'; prompt.write_bytes(PAYLOAD)
        self.assertGreaterEqual(len(PAYLOAD), 64 * 1024)
        command = [sys.executable, self.shared / 'run-bounded.py', '10', '--stdin-file', prompt, '--', 'codex', *argv]
        for _ in range(2):
            run(command, env=self.env)
            self.assertEqual(self.seen()['argv'], argv); self.assertEqual(bytes.fromhex(self.seen()['stdin']), PAYLOAD)
        self.assertFalse(prompt.with_name(prompt.name + '.transport.json').exists())
        self.assertFalse((self.work / 'sentinel').exists())
        code = "import runpy,sys; print(runpy.run_path(sys.argv[1])['native_version']('codex'))"
        self.assertEqual(run([sys.executable, '-c', code, self.shared / 'role-config.py'], env=self.env).stdout.strip(), b'1.2.3')
        capture = r'''import pathlib,runpy,sys
m=runpy.run_path(sys.argv[1]); work=pathlib.Path(sys.argv[2])
manifest=work/'.devlyn/process-evidence/rs-native/implement/round-0/manifest.json'
item={'id':'shim','phase':'implement','argv':['codex','--version'],'exit_code':0,'timeout_sec':10}
e=m['capture_process'](work,manifest,'rs-native','implement',0,item)
assert e['expectation_met'] and (work/e['stdout']['path']).read_bytes()==b'fixture-cli 1.2.3\n',e
item.update(id='missing',argv=[str(work/'없는 명령')])
e=m['capture_process'](work,manifest,'rs-native','implement',0,item)
assert e['outcome']['kind']=='spawn_error' and '없는 명령'.encode() in (work/e['stderr']['path']).read_bytes(),e
'''
        run([sys.executable, '-c', capture, self.shared / 'process-evidence.py', self.work], env=self.env)
        if os.name == 'nt':
            bad = self.work / 'unknown.cmd'; bad.write_text('@echo unsafe\n', encoding='utf-8')
            error = run([sys.executable, self.shared / 'run-bounded.py', '5', '--', bad], code=2)
            self.assertIn(b'unsupported native command shim', error.stderr)
            shim = self.bins / 'codex.cmd'; raw = shim.read_bytes()
            try:
                shim.write_bytes(b'@echo malformed\r\n')
                error = run([sys.executable, self.shared / 'run-bounded.py', '5', '--', 'codex'], env=self.env, code=2)
                self.assertIn(b'unrecognized npm engine shim', error.stderr)
            finally:
                shim.write_bytes(raw)
        else:
            print('SKIP Windows .cmd resolution/tamper branch; real POSIX npm argv/version exercised', flush=True)

    def test_both_judge_file_transports_authenticate_actual_dispatch(self):
        role = helper('role-config'); judge = helper('judge-role-evidence')
        config = {'roles': {'primary_judge': {'engine':'claude','model':'fixture-claude-model','effort':'high'},
                            'pair_judge': {'engine':'codex','model':'fixture-model','effort':'high'}}}
        (self.devlyn / 'engines.json').write_bytes(role['encoded'](config))
        state = {'run_id':'fixture', 'engine':'codex', 'role_resolution':role['resolve'](self.work, 'codex', available=lambda e: True),
                 'phases': {'verify': {'engine':'claude','round':0}}}
        for engine, selected in [('claude','primary_judge'), ('codex','pair_judge')]:
            stem = engine + '-judge.r0'; prompt = self.devlyn / (stem + '.prompt'); prompt.write_bytes(PAYLOAD)
            if engine == 'claude':
                argv = [sys.executable, str(self.shared / 'run-bounded.py'), '600', '--stdin-file', str(prompt), '--record-transport', '--', 'claude', '-p',
                        '--model','fixture-claude-model','--effort','high','--permission-mode','dontAsk','--tools','Read,Grep,Glob',
                        '--allowedTools','Read,Grep,Glob','--setting-sources','project','--output-format','json',
                        '--strict-mcp-config','--mcp-config','{"mcpServers":{}}']
                result = run(argv, cwd=self.work, env=self.env)
                (self.devlyn / (stem + '.output.json')).write_bytes(result.stdout)
                (self.devlyn / (stem + '.stderr')).write_bytes(result.stderr)
            else:
                argv = [self.bash, str(self.shared / 'codex-monitored.sh'), '-C', str(self.work), '-s', 'read-only', '-m', 'fixture-model', '-c', 'model_reasoning_effort=high', '-']
                self.env.update(DEVLYN_CODEX_PROMPT_FILE=str(prompt), CODEX_MONITORED_ISOLATED='1', CODEX_MONITORED_TIMEOUT_SEC='600')
                self.monitor(argv[2:], self.devlyn / (stem + '.stdout'))
                (self.devlyn / (stem + '.stderr')).write_bytes((self.work / 'stderr').read_bytes())
            self.assertEqual(bytes.fromhex(self.seen()['stdin']), PAYLOAD)
            argv_path = self.devlyn / (stem + '.argv.json')
            argv_path.write_bytes(role['encoded'](argv))
            if engine == 'claude':
                argv_path.write_bytes(role['encoded']([arg for arg in argv if arg != '--record-transport']))
                with self.assertRaisesRegex(ValueError, 'invalid bounded file transport'):
                    judge['describe'](self.devlyn, state, selected, 0)
                argv_path.write_bytes(role['encoded'](argv))
            disguised = argv[:-1] + [PAYLOAD.decode()] if engine == 'codex' else argv[:3] + argv[5:] + [PAYLOAD.decode()]
            argv_path.write_bytes(role['encoded'](disguised))
            with self.assertRaises(ValueError):
                judge['describe'](self.devlyn, state, selected, 0)
            argv_path.write_bytes(role['encoded'](argv))
            record, derived = judge['describe'](self.devlyn, state, selected, 0)
            (self.devlyn / (stem + '.stdout')).write_bytes(derived)
            (self.devlyn / (engine + '-judge.stdout')).write_bytes(derived)
            (self.devlyn / (stem + '.role-evidence.json')).write_bytes(role['encoded'](record))
            judge['authenticate'](self.devlyn, state, selected)
            for suffix in ('.prompt.transport.json', '.argv.json', '.prompt', '.stderr'):
                path = self.devlyn / (stem + suffix); original = path.read_bytes(); path.write_bytes(original + b'tamper')
                with self.assertRaises((ValueError, OSError)):
                    judge['authenticate'](self.devlyn, state, selected)
                path.write_bytes(original)

    def test_git_bash_timeout_stops_native_node_and_python(self):
        leaf = self.work / 'leaf.py'
        leaf.write_text("import pathlib,sys,time,os\np=pathlib.Path(sys.argv[1]); p.with_suffix('.pid').write_text(str(os.getpid()),encoding='utf-8')\nwhile True:\n p.write_bytes(str(time.monotonic_ns()).encode()); time.sleep(.03)\n", encoding='utf-8')
        ticks = self.work / 'ticks'; node_pid = self.work / 'node.pid'
        self.env.update(DEVLYN_TEST_LEAF=str(leaf), DEVLYN_TEST_PYTHON=sys.executable, DEVLYN_TEST_TICKS=str(ticks),
                        DEVLYN_TEST_NODE_PID=str(node_pid), CODEX_MONITORED_TIMEOUT_SEC='1')
        self.monitor(['-C', str(self.work), '-s', 'read-only', 'timeout fixture'], code=124)
        self.assertTrue(ticks.exists()); self.assertTrue(node_pid.exists())
        before = ticks.read_bytes(); time.sleep(.2); self.assertEqual(ticks.read_bytes(), before)
        for path in (node_pid, ticks.with_suffix('.pid')):
            wait_for(lambda: not process_running(int(path.read_text(encoding='utf-8'))))
        print('monitored native Node/Python pids=' + node_pid.read_text(encoding='utf-8') + '/' + ticks.with_suffix('.pid').read_text(encoding='utf-8'), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--package-root', type=Path)
    args, tests = parser.parse_known_args()
    if args.package_root:
        PACKAGE_ROOT = args.package_root.resolve(strict=True)
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(encoding='utf-8', errors='strict')
    print(json.dumps({'platform': sys.platform, 'utf8_mode': sys.flags.utf8_mode,
                      'locale': locale.getencoding(), 'package_root': str(PACKAGE_ROOT or ROOT)}), flush=True)
    unittest.main(argv=[sys.argv[0], *tests], verbosity=2)
