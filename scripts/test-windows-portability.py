#!/usr/bin/env python3
"""Real npm/native-process portability checks; --package-root tests a downloaded install.

Pass unittest class/method names for focused development checks. No model calls.
"""
from __future__ import annotations

import argparse
import contextlib
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
from unittest.mock import patch

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

    def test_agents_invalid_target_preserves_files(self):
        def snapshot(root):
            return {str(p.relative_to(root)): (p.stat().st_mode, p.read_bytes() if p.is_file() else None)
                    for p in root.rglob('*')}

        for detected in (False, True):
            for index, target in enumerate(('cdoex', '', 'constructor', '__proto__', 'toString')):
                with self.subTest(detected=detected, target=target):
                    case = self.case / f'invalid-{detected}-{index}'; case.mkdir()
                    project = case / 'project'; project.mkdir()
                    home = case / 'agent-home'; home.mkdir()
                    if detected:
                        (project / '.codex').mkdir(); (project / '.agents').mkdir()
                    (project / 'keep.txt').write_bytes(b'project user bytes\r\n')
                    for agent in ('.codex', '.agents', '.grok'):
                        keep = home / agent / 'skills/user-skill/keep'
                        keep.parent.mkdir(parents=True); keep.write_bytes(b'user bytes\x00')
                    before = snapshot(case)
                    env = {**self.env, 'DEVLYN_TEST_HOME': str(home)}
                    result = run(['node', '--require', self.preload, self.package / 'bin/devlyn.js',
                                  'agents', target], cwd=project, env=env, code=None)
                    self.assertNotEqual(result.returncode, 0, result.stdout)
                    output = (result.stdout + result.stderr).decode('utf-8')
                    self.assertIn(json.dumps(target), output)
                    for supported in ('codex', 'omp', 'pi', 'grok', 'all'):
                        self.assertIn(supported, output)
                    self.assertEqual(snapshot(case), before)

    def test_agents_supported_and_automatic_targets(self):
        cases = [([], False, set()), ([], True, {'.codex'}),
                 (['all'], False, {'.codex', '.agents', '.grok'})]
        cases += [([target], True, {directory}) for target, directory in
                  (('codex', '.codex'), ('omp', '.agents'), ('pi', '.agents'), ('grok', '.grok'))]
        for index, (arguments, detected, expected) in enumerate(cases):
            with self.subTest(arguments=arguments, detected=detected):
                case = self.case / f'valid-{index}'; case.mkdir()
                project = case / 'project'; project.mkdir()
                home = case / 'agent-home'; home.mkdir()
                if detected:
                    (project / '.codex').mkdir()
                env = {**self.env, 'DEVLYN_TEST_HOME': str(home)}
                run(['node', '--require', self.preload, self.package / 'bin/devlyn.js',
                     'agents', *arguments], cwd=project, env=env)
                installed = {p.name for p in home.iterdir() if (p / 'skills/.devlyn-install.json').is_file()}
                self.assertEqual(installed, expected)
                self.assertEqual((project / 'AGENTS.md').is_file(), bool(expected))

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
assert spec['stage_from_source'](md, work / '.devlyn') == (True, True, None)
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


@unittest.skipUnless(os.name == 'nt', 'native Windows job ownership and DWORD exit codes')
class NativeOwnershipTests(unittest.TestCase):
    def setUp(self):
        import ctypes
        from ctypes import wintypes
        self.ctypes = ctypes
        self.kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        for name, args, result in (
            ('OpenProcess', [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD], wintypes.HANDLE),
            ('WaitForSingleObject', [wintypes.HANDLE, wintypes.DWORD], wintypes.DWORD),
            ('TerminateProcess', [wintypes.HANDLE, wintypes.UINT], wintypes.BOOL),
            ('CloseHandle', [wintypes.HANDLE], wintypes.BOOL),
            ('GetHandleInformation', [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)], wintypes.BOOL),
            ('CreateEventW', [ctypes.c_void_p, wintypes.BOOL, wintypes.BOOL, wintypes.LPCWSTR], wintypes.HANDLE),
            ('SetEvent', [wintypes.HANDLE], wintypes.BOOL),
            ('QueryInformationJobObject', [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD, ctypes.c_void_p], wintypes.BOOL),
        ):
            function = getattr(self.kernel, name); function.argtypes = args; function.restype = result
        self.temp = tempfile.TemporaryDirectory(prefix='devlyn-job-')
        self.addCleanup(self.temp.cleanup)
        self.work = Path(self.temp.name)
        self.shared = (PACKAGE_ROOT or ROOT) / 'config/skills/_shared'
        self.platform = helper('platform-support')
        self.scope = self.platform['run_process'].__globals__
        self.handles = {}
        self.addCleanup(self.reap_fixture)
        owner = self
        class ObservedLaunch(subprocess.Popen):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                owner.retain(self.pid)
        observer = patch.object(subprocess, 'Popen', ObservedLaunch)
        observer.start(); self.addCleanup(observer.stop)
        self.release = self.work / 'release'
        self.ticks = self.work / 'ticks'
        self.leader = self.work / 'leader.pid'
        leaf = self.work / 'leaf.py'
        leaf.write_text("import os,pathlib,sys,time\np=pathlib.Path(sys.argv[1]); p.with_suffix('.pid').write_text(str(os.getpid()),encoding='utf-8')\nwhile True:\n p.write_bytes(str(time.monotonic_ns()).encode()); time.sleep(.02)\n", encoding='utf-8')
        target = self.work / 'target.py'
        target.write_text("import subprocess,sys,os,pathlib,time,ctypes\nsubprocess.Popen([sys.executable,sys.argv[1],sys.argv[2]])\npathlib.Path(sys.argv[3]).write_text(str(os.getpid()),encoding='utf-8')\ndeadline=time.monotonic()+15\nwhile not pathlib.Path(sys.argv[4]).exists():\n if time.monotonic()>deadline: raise RuntimeError('fixture release timeout')\n time.sleep(.01)\nexit=ctypes.windll.kernel32.ExitProcess; exit.argtypes=[ctypes.c_uint]; exit.restype=None; exit(int(sys.argv[5]))\n", encoding='utf-8')
        self.command = [sys.executable, str(target), str(leaf), str(self.ticks), str(self.leader), str(self.release), '19']

    def retain(self, pid):
        if pid not in self.handles:
            handle = self.kernel.OpenProcess(0x100001 | 0x1000, False, pid)
            if not handle:
                raise self.ctypes.WinError(self.ctypes.get_last_error())
            self.handles[pid] = handle
        return self.handles[pid]

    def alive(self, handle):
        result = self.kernel.WaitForSingleObject(handle, 0)
        self.assertIn(result, (0, 258))
        return result == 258

    def observe_tree(self):
        wait_for(lambda: self.leader.exists() and self.ticks.exists() and self.ticks.with_suffix('.pid').exists())
        leader = self.retain(int(self.leader.read_text(encoding='utf-8')))
        descendant = self.retain(int(self.ticks.with_suffix('.pid').read_text(encoding='utf-8')))
        self.assertTrue(self.alive(leader)); self.assertTrue(self.alive(descendant))
        before = self.ticks.read_bytes()
        wait_for(lambda: self.ticks.read_bytes() != before)
        return leader, descendant

    def assert_ceased(self, handle):
        self.assertFalse(self.alive(handle), 'owned process survived product teardown')

    def assert_all_ceased(self):
        for handle in self.handles.values():
            self.assert_ceased(handle)

    def reap_fixture(self):
        # Retained handles reap failed fixtures; this runs AFTER product assertions.
        self.release.touch()
        for handle in self.handles.values():
            try:
                if self.alive(handle):
                    if not self.kernel.TerminateProcess(handle, 1):
                        raise self.ctypes.WinError(self.ctypes.get_last_error())
                    self.assertEqual(self.kernel.WaitForSingleObject(handle, 5000), 0)
            finally:
                self.assertTrue(self.kernel.CloseHandle(handle))

    @contextlib.contextmanager
    def trace_job_handles(self):
        kernel = self.scope['_kernel']
        create, opened, close, wait = (getattr(kernel, name) for name in
                                     ('CreateJobObjectW', 'OpenProcess', 'CloseHandle', 'WaitForSingleObject'))
        trace = {'jobs': [], 'opened': [], 'closed': [], 'waited': []}
        live = set()

        def created(*args):
            handle = create(*args); trace['jobs'].append(handle)
            live.add(handle)
            return handle

        def retained(access, inherit, pid):
            handle = opened(access, inherit, pid); trace['opened'].append((pid, handle))
            live.add(handle)
            return handle

        def closed(handle):
            result = close(handle)
            value = getattr(handle, 'value', handle)
            if value in live:
                live.remove(value); trace['closed'].append(value)
            flags = self.ctypes.c_ulong()
            self.assertFalse(self.kernel.GetHandleInformation(value, self.ctypes.byref(flags)))
            self.assertEqual(self.ctypes.get_last_error(), 6)
            return result

        def waited(handle, milliseconds):
            trace['waited'].append((handle, milliseconds))
            return wait(handle, milliseconds)

        with patch.object(kernel, 'CreateJobObjectW', created), patch.object(kernel, 'OpenProcess', retained), \
                patch.object(kernel, 'CloseHandle', closed), patch.object(kernel, 'WaitForSingleObject', waited):
            try:
                yield trace
            finally:
                # Failure cleanup is after the test's product assertions, never their oracle.
                for handle in live:
                    close(handle)

    def assert_job_handles_closed(self, trace):
        for handle in trace['jobs'] + [handle for _, handle in trace['opened']]:
            self.assertEqual(trace['closed'].count(handle), 1, trace)

    def pid_array(self, buffer):
        count = self.ctypes.cast(buffer, self.ctypes.POINTER(self.ctypes.c_ulong))[1]
        return (self.ctypes.c_size_t * count).from_address(self.ctypes.cast(buffer, self.ctypes.c_void_p).value + 8)

    def job_pids(self, job):
        buffer = self.ctypes.create_string_buffer(8 + 64 * self.ctypes.sizeof(self.ctypes.c_size_t))
        self.assertTrue(self.kernel.QueryInformationJobObject(job, 3, buffer, len(buffer), None))
        return list(self.pid_array(buffer))

    def gated_job(self):
        work = Path(tempfile.mkdtemp(prefix='gated-', dir=self.work))
        prefix = 'Local\\devlyn-' + self.work.name + '-' + work.name + '-'
        gates = {}
        for name in ('ready', 'a_exit', 'spawn', 'c_ready', 'attempted', 'finish'):
            handle = self.kernel.CreateEventW(None, True, False, prefix + name)
            self.assertTrue(handle)
            self.addCleanup(lambda handle=handle: self.assertTrue(self.kernel.CloseHandle(handle)))
            gates[name] = handle
        script = work / 'gated.py'
        script.write_text(r'''
import ctypes, pathlib, subprocess, sys
from ctypes import wintypes
k = ctypes.WinDLL('kernel32', use_last_error=True)
k.OpenEventW.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.LPCWSTR]
k.OpenEventW.restype = wintypes.HANDLE
k.SetEvent.argtypes = [wintypes.HANDLE]
k.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
k.WaitForSingleObject.restype = wintypes.DWORD
k.CloseHandle.argtypes = [wintypes.HANDLE]
prefix, role = sys.argv[1:]
work = pathlib.Path(__file__).parent
def gate(name, signal=False):
    handle = k.OpenEventW(0x100002, False, prefix + name)
    if not handle: raise ctypes.WinError(ctypes.get_last_error())
    try:
        if signal:
            if not k.SetEvent(handle): raise ctypes.WinError(ctypes.get_last_error())
        elif k.WaitForSingleObject(handle, 15000) != 0:
            raise RuntimeError('native fixture gate timed out: ' + name)
    finally:
        if not k.CloseHandle(handle): raise ctypes.WinError(ctypes.get_last_error())
if role == 'A':
    gate('a_exit')
elif role == 'C':
    (work / 'C.executed').touch()
    gate('c_ready', True)
    gate('finish')
else:
    a = subprocess.Popen([sys.executable, __file__, prefix, 'A'])
    (work / 'A.pid').write_text(str(a.pid), encoding='utf-8')
    gate('ready', True)
    gate('spawn')
    try:
        c = subprocess.Popen([sys.executable, __file__, prefix, 'C'])
    except OSError as exc:
        outcome = str(exc.winerror)
    else:
        (work / 'C.pid').write_text(str(c.pid), encoding='utf-8')
        gate('c_ready')
        outcome = 'admitted'
    (work / 'outcome').write_text(outcome, encoding='utf-8')
    gate('attempted', True)
    gate('finish')
''', encoding='utf-8')
        job = self.scope['_WindowsJob']()
        job.start([sys.executable, str(script), prefix, 'B'], subprocess.DEVNULL)
        self.assertEqual(self.kernel.WaitForSingleObject(gates['ready'], 8000), 0)
        a = self.retain(int((work / 'A.pid').read_text(encoding='utf-8')))
        b = self.retain(job.target_pid)
        self.assertTrue(self.alive(a)); self.assertTrue(self.alive(b))
        return job, gates, work, a, b

    def test_child_after_initial_observation_is_captured_and_pid_buffer_grows(self):
        kernel = self.scope['_kernel']
        with self.trace_job_handles() as trace:
            job, gates, work, a, b = self.gated_job()
            set_limit, query = kernel.SetInformationJobObject, kernel.QueryInformationJobObject
            initial, growth = [], []

            def before_barrier(handle, kind, info, size):
                self.assert_ceased(self.handles[job.child.pid])
                # Signaled bootstrap handles can precede removal from the job PID list.
                wait_for(lambda: job.child.pid not in self.job_pids(handle))
                initial.extend(self.job_pids(handle))
                self.assertEqual(set(initial), {job.target_pid, int((work / 'A.pid').read_text(encoding='utf-8'))})
                self.assertTrue(self.kernel.SetEvent(gates['spawn']))
                self.assertEqual(self.kernel.WaitForSingleObject(gates['attempted'], 8000), 0)
                self.assertEqual((work / 'outcome').read_text(encoding='utf-8'), 'admitted')
                c_pid = int((work / 'C.pid').read_text(encoding='utf-8'))
                self.assertNotIn(c_pid, initial); self.assertTrue(self.alive(self.retain(c_pid)))
                return set_limit(handle, kind, info, size)

            def collect(*args):
                self.assertEqual(args[1], 3, 'pre-kill member PIDs, not accounting')
                try:
                    return query(*args)
                except OSError as exc:
                    growth.append(exc.winerror)
                    raise

            with patch.object(kernel, 'SetInformationJobObject', before_barrier), \
                    patch.object(kernel, 'QueryInformationJobObject', collect):
                job.terminate()
            self.assertEqual(growth, [234])
            self.assertEqual({pid for pid, _ in trace['opened']},
                             {*initial, int((work / 'C.pid').read_text(encoding='utf-8'))})
            self.assertEqual({h for h, _ in trace['waited']}, {h for _, h in trace['opened']})
            self.assert_all_ceased(); self.assert_job_handles_closed(trace)
            print('native initial observation -> admitted C -> zero barrier -> ERROR_MORE_DATA -> capture/wait all', flush=True)

    def test_zero_barrier_rejects_freed_slot_and_current_count_control_admits(self):
        kernel = self.scope['_kernel']
        for control in (False, True):
            with self.subTest(current_count_control=control), self.trace_job_handles() as trace:
                job, gates, work, a, b = self.gated_job()
                set_limit, terminate = kernel.SetInformationJobObject, kernel.TerminateJobObject
                boundaries = []

                def barrier(handle, kind, info, size):
                    limits = self.ctypes.cast(info, self.ctypes.POINTER(self.scope['_ExtendedLimits'])).contents
                    self.assertEqual(limits.BasicLimitInformation.ActiveProcessLimit, 0)
                    self.assertEqual(limits.BasicLimitInformation.LimitFlags, 0x2008)
                    self.assert_ceased(self.handles[job.child.pid])
                    # Establish the exact starting members before testing admission limits.
                    wait_for(lambda: job.child.pid not in self.job_pids(handle))
                    self.assertEqual(set(self.job_pids(handle)), {job.target_pid, int((work / 'A.pid').read_text(encoding='utf-8'))})
                    if control:
                        limits.BasicLimitInformation.ActiveProcessLimit = 2
                    result = set_limit(handle, kind, info, size)
                    readback = self.scope['_ExtendedLimits']()
                    self.assertTrue(self.kernel.QueryInformationJobObject(handle, 9, self.ctypes.byref(readback), size, None))
                    self.assertEqual(readback.BasicLimitInformation.LimitFlags, 0x2008)
                    self.assertEqual(readback.BasicLimitInformation.ActiveProcessLimit, 2 if control else 0)
                    self.assertTrue(self.kernel.SetEvent(gates['a_exit']))
                    self.assertEqual(self.kernel.WaitForSingleObject(a, 8000), 0)
                    wait_for(lambda: int((work / 'A.pid').read_text(encoding='utf-8')) not in self.job_pids(handle))
                    self.assertTrue(self.alive(b))
                    self.assertTrue(self.kernel.SetEvent(gates['spawn']))
                    self.assertEqual(self.kernel.WaitForSingleObject(gates['attempted'], 8000), 0)
                    self.assertEqual((work / 'outcome').read_text(encoding='utf-8'), 'admitted' if control else '1816')
                    self.assertEqual((work / 'C.executed').exists(), control)
                    if control:
                        self.assertTrue(self.alive(self.retain(int((work / 'C.pid').read_text(encoding='utf-8')))))
                    boundaries.append('A exited -> B attempted C')
                    return result

                def kill(handle, code):
                    self.assertEqual(boundaries, ['A exited -> B attempted C'])
                    if not control:
                        self.assertEqual([pid for pid, _ in trace['opened']], [job.target_pid])
                    return terminate(handle, code)

                with patch.object(kernel, 'SetInformationJobObject', barrier), patch.object(kernel, 'TerminateJobObject', kill):
                    job.terminate()
                self.assert_all_ceased(); self.assert_job_handles_closed(trace)
                print(f'native current-count-control={control}: barrier -> A exit -> C outcome=' +
                      (work / 'outcome').read_text(encoding='utf-8') + ' -> retained members ceased', flush=True)

    def test_natural_exit_after_enumeration_before_capture(self):
        kernel = self.scope['_kernel']
        with self.trace_job_handles() as trace:
            job = self.scope['_WindowsJob'](); job.start(self.command, subprocess.DEVNULL)
            leader, descendant = self.observe_tree()
            leader_pid = job.target_pid
            query = kernel.QueryInformationJobObject
            collected = []

            def exit_after_list(*args):
                result = query(*args)
                self.assertEqual(args[1], 3)
                self.assertIn(leader_pid, self.pid_array(args[2]))
                self.release.touch()
                self.assertEqual(self.kernel.WaitForSingleObject(leader, 8000), 0)
                self.assertTrue(self.alive(descendant))
                collected.append('enumerated -> natural leader exit -> live descendant')
                return result

            with patch.object(kernel, 'QueryInformationJobObject', exit_after_list):
                job.terminate()
            self.assertEqual(len(collected), 1)
            self.assertIn(int(self.ticks.with_suffix('.pid').read_text(encoding='utf-8')),
                          [pid for pid, h in trace['opened'] if h in {w for w, _ in trace['waited']}])
            self.assert_all_ceased(); self.assert_job_handles_closed(trace)
            print('native enumeration -> natural exit before capture -> live descendant waited; '
                  f'natural leader acquired={leader_pid in [pid for pid, _ in trace["opened"]]}; '
                  'no claim about pre-capture pending I/O or historical process-object finalization', flush=True)

    def test_stale_list_gone_and_different_job_identity(self):
        kernel = self.scope['_kernel']
        unrelated = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(30)'])
        try:
            with self.trace_job_handles() as trace:
                job = self.scope['_WindowsJob'](); job.start(self.command, subprocess.DEVNULL)
                leader, descendant = self.observe_tree()
                gone = subprocess.Popen([sys.executable, '-c', 'pass'])
                self.assertEqual(gone.wait(timeout=5), 0)
                gone._handle.Close()
                self.assertTrue(self.kernel.CloseHandle(self.handles.pop(gone.pid)))

                def gone_pid():
                    process = self.kernel.OpenProcess(0x101000, False, gone.pid)
                    if not process:
                        self.assertEqual(self.ctypes.get_last_error(), 87)
                        return True
                    try:
                        self.assertFalse(self.alive(process), 'gone-PID fixture refers to a live process')
                    finally:
                        self.assertTrue(self.kernel.CloseHandle(process))
                    return False

                wait_for(gone_pid)
                query, identity = kernel.QueryInformationJobObject, kernel.IsProcessInJob
                rejected = []

                def stale_list(handle, kind, buffer, size, needed):
                    result = query(handle, kind, buffer, size, needed)
                    self.assertEqual(kind, 3)
                    pids = [unrelated.pid if pid == job.target_pid else pid for pid in self.pid_array(buffer)] + [gone.pid]
                    header = self.ctypes.cast(buffer, self.ctypes.POINTER(self.ctypes.c_ulong))
                    header[0] = len(pids)
                    if size < 8 + len(pids) * self.ctypes.sizeof(self.ctypes.c_size_t):
                        raise self.ctypes.WinError(234, 'identity-race fixture needs one stale PID slot')
                    header[1] = len(pids)
                    self.pid_array(buffer)[:] = pids
                    return result

                def checked_identity(handle, owned_job, member):
                    result = identity(handle, owned_job, member)
                    if (unrelated.pid, handle) in trace['opened']:
                        self.assertFalse(self.ctypes.cast(member, self.ctypes.POINTER(self.ctypes.c_long))[0])
                        rejected.append(handle)
                    return result

                with patch.object(kernel, 'QueryInformationJobObject', stale_list), \
                        patch.object(kernel, 'IsProcessInJob', checked_identity):
                    job.terminate()
                self.assertEqual(len(rejected), 1)
                self.assertNotIn(rejected[0], [h for h, _ in trace['waited']])
                self.assertNotIn(gone.pid, [pid for pid, _ in trace['opened']])
                self.assertTrue(self.alive(self.handles[unrelated.pid]))
                self.assert_ceased(descendant)
                self.assert_job_handles_closed(trace)
                print('native stale-list fixture: real gone-87 skipped; substituted unrelated identity '
                      'rejected, unwaited and unaffected; this is not observed OS PID recycling', flush=True)
        finally:
            if unrelated.poll() is None:
                unrelated.kill()
            unrelated.wait(timeout=5)

    def test_retained_handles_block_until_signaled_with_one_deadline(self):
        import threading
        from types import SimpleNamespace
        kernel = self.scope['_kernel']
        with self.trace_job_handles() as trace:
            job = self.scope['_WindowsJob'](); job.start(self.command, subprocess.DEVNULL)
            self.observe_tree()
            terminate, wait = kernel.TerminateJobObject, kernel.WaitForSingleObject
            requested, entered, done = threading.Event(), threading.Event(), threading.Event()
            errors = []

            def deferred_termination(handle, code):
                self.assertEqual((handle, code), (job.handle, 1))
                requested.set()
                return 1  # Scoped gate: the main thread makes this real native call below.

            def blocking_wait(handle, milliseconds):
                if not entered.is_set():
                    self.assertTrue(requested.is_set()); self.assertTrue(self.alive(handle))
                    self.assertGreater(milliseconds, 0)
                    entered.set()
                return wait(handle, milliseconds)

            def teardown():
                try:
                    job.terminate()
                except BaseException as exc:
                    errors.append(exc)
                finally:
                    done.set()

            clock = iter((100, 101, 103))  # One 5s deadline, decreasing remaining waits.
            with patch.object(kernel, 'TerminateJobObject', deferred_termination), \
                    patch.object(kernel, 'WaitForSingleObject', blocking_wait), \
                    patch.dict(self.scope, time=SimpleNamespace(monotonic=lambda: next(clock))):
                worker = threading.Thread(target=teardown); worker.start()
                try:
                    self.assertTrue(entered.wait(timeout=5), errors)
                    self.assertFalse(done.is_set(), 'teardown returned while a retained member was live')
                    terminate(job.handle, 1)
                    self.assertTrue(done.wait(timeout=5))
                finally:
                    worker.join(timeout=6)
            self.assertFalse(worker.is_alive()); self.assertEqual(errors, [])
            self.assertEqual([ms for _, ms in trace['waited']], [4000, 2000])
            self.assert_all_ceased(); self.assert_job_handles_closed(trace)
            print('native deferred termination gate: retained handle nonsignaled -> teardown pending -> '
                  'real TerminateJobObject -> signaled; shared deadline waits=4000,2000ms', flush=True)

    def test_collection_wait_and_cleanup_errors_are_visible(self):
        import signal
        from types import SimpleNamespace
        kernel = self.scope['_kernel']
        teardown = self.scope['terminate_tree']
        boundaries = ('SetInformationJobObject', 'QueryInformationJobObject', 'OpenProcess',
                      'IsProcessInJob', 'TerminateJobObject', 'WaitForSingleObject',
                      'deadline', 'interruption', 'CloseHandle')
        for boundary in boundaries:
            with self.subTest(boundary=boundary), self.trace_job_handles() as trace:
                for path in (self.leader, self.ticks, self.ticks.with_suffix('.pid')):
                    path.unlink(missing_ok=True)
                previous = {sig: signal.getsignal(sig) for sig in (signal.SIGINT, signal.SIGTERM)}
                observations, reached = [], []

                def fail_during_teardown(child, job):
                    observations.extend(self.observe_tree())
                    name = 'WaitForSingleObject' if boundary in ('deadline', 'interruption') else boundary
                    actual = getattr(kernel, name)
                    calls = 0

                    def fault(*args):
                        nonlocal calls
                        calls += 1
                        if boundary in ('OpenProcess', 'IsProcessInJob') and calls == 1:
                            return actual(*args)  # Already acquired handles must still close.
                        reached.append(boundary)
                        if boundary == 'OpenProcess':
                            raise self.ctypes.WinError(5, 'OpenProcess: injected access denied after capture')
                        if boundary == 'interruption':
                            raise KeyboardInterrupt('injected retained-wait interruption')
                        if boundary == 'deadline':
                            self.assertEqual(args[1], 0, 'expired remainder must not become INFINITE')
                            return actual(event, args[1])  # Real WAIT_TIMEOUT on a nonsignaled native event.
                        if boundary == 'CloseHandle':
                            actual(*args)  # Release the real resource, then expose a real close failure.
                            return actual(0)
                        return actual(-1 if boundary == 'QueryInformationJobObject' else 0, *args[1:])  # NULL queries the caller's job.

                    with contextlib.ExitStack() as inject:
                        if boundary == 'deadline':
                            event = self.kernel.CreateEventW(None, True, False, None)
                            self.assertTrue(event); inject.callback(lambda: self.assertTrue(self.kernel.CloseHandle(event)))
                            clock = iter((100, 106))
                            inject.enter_context(patch.dict(self.scope, time=SimpleNamespace(monotonic=lambda: next(clock))))
                        inject.enter_context(patch.object(kernel, name, fault))
                        teardown(child, job)

                expected = KeyboardInterrupt if boundary == 'interruption' else OSError
                with patch.dict(self.scope, terminate_tree=fail_during_teardown), self.assertRaises(expected) as failure:
                    self.platform['run_process'](self.command, subprocess.DEVNULL, .05)
                self.assertTrue(reached, boundary)
                self.assertIn('timed out' if boundary == 'deadline' else
                              'interruption' if boundary == 'interruption' else boundary, str(failure.exception))
                self.assertEqual({sig: signal.getsignal(sig) for sig in previous}, previous)
                if boundary not in ('SetInformationJobObject', 'QueryInformationJobObject'):
                    self.assertTrue(trace['opened'], 'failure must exercise retained-handle cleanup')
                self.assert_job_handles_closed(trace)
                # Error is already asserted. Observe last-job-handle kill safety, then fixture cleanup.
                for handle in observations:
                    self.assertEqual(self.kernel.WaitForSingleObject(handle, 5000), 0)
                self.assert_all_ceased()
                print(f'native {boundary}: visible {failure.exception}; acquired handles closed, '
                      'last-handle kill observed, signal handlers restored', flush=True)

    def test_timeout_selected_then_leader_exit(self):
        import contextlib
        import io
        events = []
        messages = io.StringIO()
        teardown = self.scope['terminate_tree']

        def after_timeout(child, job=None):
            events.append('timeout selected')
            leader, descendant = self.observe_tree()
            bootstrap = self.retain(child.pid)
            self.release.touch()
            wait_for(lambda: not self.alive(leader))
            events.append('actual leader exited')
            self.assertEqual(child.wait(timeout=5), 19)
            self.assert_ceased(bootstrap)
            self.assertTrue(self.alive(descendant))
            events.append('descendant live')
            events.append('teardown')
            teardown(child, job) if job is not None else teardown(child)
            self.assert_ceased(descendant)
            events.append('descendant ceased')
            before = self.ticks.read_bytes(); time.sleep(.15)
            self.assertEqual(self.ticks.read_bytes(), before)

        with patch.dict(self.scope, terminate_tree=after_timeout), contextlib.redirect_stderr(messages):
            result = self.platform['run_process'](self.command, subprocess.DEVNULL, 1, heartbeat=1)
        self.assertEqual(result, 124)
        self.assert_all_ceased()
        self.assertIn('codex pid=' + self.leader.read_text(encoding='utf-8'), messages.getvalue())
        self.assertIn('timeout:', messages.getvalue())
        self.assertEqual(events, ['timeout selected', 'actual leader exited', 'descendant live', 'teardown', 'descendant ceased'])
        print('native ownership: ' + ' -> '.join(events) + ' -> result=124', flush=True)

    def test_normal_exit_early_spawn_and_full_exit_code(self):
        import threading
        for code in (0, 7, 0x80000000, 0xC0000005, 0xFFFFFFFF):
            with self.subTest(code=hex(code)):
                self.release.unlink(missing_ok=True)
                for path in (self.leader, self.ticks, self.ticks.with_suffix('.pid')):
                    path.unlink(missing_ok=True)
                observations, errors = [], []

                def release_live_tree():
                    try:
                        observations.extend(self.observe_tree())
                    except BaseException as exc:
                        errors.append(exc)
                    finally:
                        self.release.touch()

                observer = threading.Thread(target=release_live_tree)
                observer.start()
                try:
                    result = self.platform['run_process']([*self.command[:-1], str(code)], subprocess.DEVNULL, 20)
                finally:
                    observer.join(timeout=10)
                self.assertFalse(observer.is_alive()); self.assertEqual(errors, [])
                self.assertEqual(result, code)
                for handle in observations:
                    self.assert_ceased(handle)
                self.assert_all_ceased()
                print(f'native normal leader exit={code} earliest-spawn descendant ceased', flush=True)

    def test_cli_exit_codes_and_transport_completion(self):
        prompt = self.work / 'prompt'; prompt.write_bytes(PAYLOAD + b'\x00\xff')
        target = 'import ctypes,sys; sys.stdout.buffer.write(sys.stdin.buffer.read()); sys.stdout.buffer.flush(); exit=ctypes.windll.kernel32.ExitProcess; exit.argtypes=[ctypes.c_uint]; exit.restype=None; exit(int(sys.argv[-1]))'
        for code in (0x80000000, 0xC0000005, 0xFFFFFFFF):
            for route in ('bounded', 'monitored-dispatch', 'monitored-bash'):
                with self.subTest(code=hex(code), route=route):
                    carrier = prompt.with_name(prompt.name + '.transport.json')
                    carrier.unlink(missing_ok=True)
                    env = environment()
                    if route == 'bounded':
                        command = [sys.executable, self.shared / 'run-bounded.py', '10', '--stdin-file', prompt,
                                   '--record-transport', '--', sys.executable, '-c', target, str(code)]
                    else:
                        # Native dispatcher used by codex-monitored.sh; preserve real Python CLI finalization.
                        env['DEVLYN_CODEX_PROMPT_FILE'] = str(prompt)
                        command = [sys.executable, self.shared / 'invocation-receipt.py', 'dispatch', '--binary', sys.executable,
                                   '--timeout', '10', '--heartbeat', '0', '--', '-c', target, '-']
                        # Python receives "exec" as a script name from the dispatcher.
                        (self.work / 'exec').write_text(target.replace('int(sys.argv[-1])', str(code)), encoding='utf-8')
                    if route == 'monitored-bash':
                        bash = shutil.which('bash')
                        self.assertIsNotNone(bash, 'Git Bash is required for the monitored boundary')
                        # MSYS encodes native statuses into its shell status. Compare the real
                        # direct exec boundary; the native dispatcher/carrier must still retain DWORD.
                        reference = run([bash, '-c', 'exec "$@"', 'fixture', sys.executable, '-c',
                                         target, str(code)], code=None)
                        env.update(CODEX_BIN=sys.executable, CODEX_MONITORED_TIMEOUT_SEC='10',
                                   CODEX_MONITORED_HEARTBEAT='1')
                        with (self.work / 'stdout').open('wb') as out, (self.work / 'stderr').open('wb') as err:
                            result = subprocess.run([bash, str(self.shared / 'codex-monitored.sh'), '-'],
                                                    cwd=self.work, env=env, stdin=subprocess.DEVNULL,
                                                    stdout=out, stderr=err, timeout=20)
                        self.assertEqual(result.returncode, reference.returncode, (self.work / 'stderr').read_bytes())
                        self.assertEqual((self.work / 'stdout').read_bytes(), prompt.read_bytes())
                    else:
                        result = run(command, cwd=self.work, env=env, code=code)
                        self.assertEqual(result.stdout, prompt.read_bytes())
                    record = json.loads(carrier.read_text(encoding='utf-8'))
                    self.assertEqual(record['exit_code'], code)
                    self.assertEqual(record['status'], 'completed')
                    self.assertEqual(record['argv'][0], sys.executable)
                    self.assert_all_ceased()
                    print(f'native {route} target/transport exit={code} observed CLI exit={result.returncode} exact stdin', flush=True)

    def test_admission_and_launch_errors_do_not_dispatch(self):
        kernel = self.scope['_kernel']
        for boundary in ('setup', 'enrollment', 'bootstrap launch', 'target launch'):
            with self.subTest(boundary=boundary):
                if boundary == 'setup':
                    actual = kernel.SetInformationJobObject
                    injection = patch.object(kernel, 'SetInformationJobObject',
                                             lambda job, kind, info, size: actual(job, -1, info, size))
                elif boundary == 'enrollment':
                    actual = kernel.DuplicateHandle
                    injection = patch.object(kernel, 'DuplicateHandle',
                                             lambda source, job, target, out, access, inherit, options:
                                             actual(source, job, target, out, 4, inherit, 0))  # QUERY, without ASSIGN_PROCESS.
                elif boundary == 'bootstrap launch':
                    injection = patch.object(sys, 'executable', str(self.work / 'missing-python.exe'))
                else:
                    injection = patch.dict(self.scope)  # Real target CreateProcess failure after enrollment.
                command = [str(self.work / 'missing-target.exe')] if boundary == 'target launch' else self.command
                with injection, self.assertRaises(OSError) as failure:
                    self.platform['run_process'](command, subprocess.DEVNULL, 1)
                self.assertTrue(str(failure.exception))
                self.assertFalse(self.leader.exists()); self.assertFalse(self.ticks.exists())
                self.assert_all_ceased()
                print(f'native {boundary}: visible error={failure.exception}; no target dispatch', flush=True)

    def test_target_cannot_break_away(self):
        target = r'''
import subprocess, sys
try:
    escaped = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(30)'],
                               creationflags=subprocess.CREATE_BREAKAWAY_FROM_JOB)
except OSError as exc:
    assert exc.winerror == 5, exc
else:
    escaped.kill(); escaped.wait()
    raise AssertionError('target escaped the owned job')
'''
        self.assertEqual(self.platform['run_process']([sys.executable, '-c', target], subprocess.DEVNULL, 10), 0)
        self.assert_all_ceased()
        print('native target CREATE_BREAKAWAY_FROM_JOB refused with access denied', flush=True)

    def test_error_after_native_launch_before_authorization(self):
        actual = subprocess.Popen
        owner = self
        for failure in (OSError('fixture after native launch'), KeyboardInterrupt('fixture launch interruption')):
            class InterruptedLaunch(actual):
                def __init__(self, *args, **kwargs):
                    super().__init__(*args, **kwargs)
                    owner.retain(self.pid)
                    raise failure

            with patch.object(subprocess, 'Popen', InterruptedLaunch), self.assertRaises(type(failure)):
                self.platform['run_process'](self.command, subprocess.DEVNULL, 1)
            self.assertFalse(self.leader.exists()); self.assertFalse(self.ticks.exists())
            for handle in self.handles.values():
                self.assert_ceased(handle)
        print('native post-CreateProcess error/interruption: bootstrap reaped, authorization withheld', flush=True)

    def test_signal_before_popen_records_native_handle(self):
        import signal
        reached = []
        class InterruptedCreation(subprocess.Popen):
            def _close_pipe_fds(self, *args):
                super()._close_pipe_fds(*args)
                # CPython calls this after CreateProcess, before assigning _handle/pid.
                reached.append(True)
                signal.raise_signal(signal.SIGINT)

        with patch.object(subprocess, 'Popen', InterruptedCreation), self.assertRaises(SystemExit) as failure:
            self.platform['run_process'](self.command, subprocess.DEVNULL, 1)
        self.assertEqual(reached, [True]); self.assertEqual(failure.exception.code, 130)
        self.assertFalse(self.leader.exists()); self.assertFalse(self.ticks.exists())
        self.assert_all_ceased()
        print('native signal before Popen handle assignment: exit=130, bootstrap reaped, no target dispatch', flush=True)

    def test_error_after_target_launch_before_owner_return(self):
        read = self.scope['_read_control']
        observations = []

        def fail_after_target(fd, count):
            result = read(fd, count)
            if count == 4:
                observations.extend(self.observe_tree())
                raise OSError('fixture after target creation before owner return')
            return result

        with patch.dict(self.scope, _read_control=fail_after_target), self.assertRaisesRegex(OSError, 'fixture after target'):
            self.platform['run_process'](self.command, subprocess.DEVNULL, 1)
        for handle in observations:
            self.assert_ceased(handle)
        self.assert_all_ceased()
        print('native target-launch error: owned leader and descendant ceased', flush=True)

    def test_teardown_error_is_visible_and_last_handle_kills(self):
        kernel = self.scope['_kernel']
        actual = kernel.TerminateJobObject
        observations = []

        def deny_teardown(job, code):
            # The runner has reaped its bootstrap; the target still awaits our barrier.
            observations.extend(self.observe_tree())
            return actual(0, code)  # Real ERROR_INVALID_HANDLE, not a simulated success.

        with patch.object(kernel, 'TerminateJobObject', deny_teardown), self.assertRaisesRegex(OSError, 'TerminateJobObject'):
            self.platform['run_process'](self.command, subprocess.DEVNULL, 1)
        for handle in observations:
            wait_for(lambda: not self.alive(handle))
            self.assert_ceased(handle)
        self.assert_all_ceased()
        print('native teardown error propagated; final job-handle release ceased descendants', flush=True)


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
