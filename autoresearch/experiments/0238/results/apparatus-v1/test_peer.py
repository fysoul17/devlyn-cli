#!/usr/bin/env python3
"""Local-only tests for the prospective installed peer helper; never call a model."""
from __future__ import annotations

import json
import os
from pathlib import Path
import runpy
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import unittest


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
ANSWER = '검토 완료 — no issue'
PROMPT = '원본 요청: precise review\nDo not edit.'
NATIVE_STDERR = b'native stderr: \xff\n'
FAKE = '''#!{python}
import json
import os
from pathlib import Path
import sys
import time

Path(os.environ['FAKE_CALLED']).write_text(json.dumps({{'argv':sys.argv[1:], 'cwd':str(Path.cwd())}}), encoding='utf-8')
mode = os.environ.get('FAKE_MODE', 'success')
engine = Path(sys.argv[0]).name
answer = {answer!r}
if mode == 'mutate':
    Path('source.txt').write_text('changed by fake peer', encoding='utf-8')
if engine == 'claude':
    rows = [{{'type':'result', 'session_id':'claude-test', 'is_error':mode == 'terminal-failure', 'result':answer}}]
else:
    rows = [{{'type':'thread.started', 'thread_id':'codex-test'}},
            {{'type':'item.completed', 'item':{{'id':'answer', 'type':'agent_message', 'text':answer}}}},
            {{'type':'turn.failed', 'error':{{'message':'fake failure'}}}} if mode == 'terminal-failure' else
            {{'type':'turn.completed', 'usage':{{'input_tokens':3, 'cached_input_tokens':0, 'output_tokens':5}}}}]
if mode == 'missing-terminal':
    rows = [] if engine == 'claude' else rows[:-1]
raw = ('\\n'.join(json.dumps(row, ensure_ascii=False) for row in rows) + ('\\n' if rows else '')).encode('utf-8')
Path(os.environ['FAKE_EXPECTED']).write_bytes(raw)
os.write(1, raw)
os.write(2, {stderr!r})
if mode == 'sleep':
    time.sleep(120)
sys.exit(17 if mode == 'nonzero' else 0)
'''


@unittest.skipUnless(os.name == 'posix', 'fake executable and signals use the POSIX host')
class PeerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='devlyn-peer-test-')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.install = self.root / 'shared'
        self.install.mkdir()
        shutil.copy2(HERE / 'peer.py', self.install / 'peer.py')
        shutil.copy2(REPO / 'config/skills/_shared/platform-support.py',
                     self.install / 'platform-support.py')
        self.peer = runpy.run_path(str(self.install / 'peer.py'))
        self.repo = self.root / 'checkout'
        self.repo.mkdir()
        self.git('init', '-q')
        self.git('config', 'user.name', 'Peer Test')
        self.git('config', 'user.email', 'peer-test@example.invalid')
        (self.repo / '.gitignore').write_text('.devlyn/\n', encoding='utf-8')
        (self.repo / 'source.txt').write_text('original\n', encoding='utf-8')
        self.git('add', '.')
        self.git('commit', '-qm', 'fixture')
        self.prompt = self.root / 'prompt.txt'
        self.prompt.write_text(PROMPT, encoding='utf-8')
        self.bin = self.root / 'bin'
        self.bin.mkdir()
        fake = FAKE.format(python=sys.executable, answer=ANSWER, stderr=NATIVE_STDERR)
        for engine in ('claude', 'codex'):
            executable = self.bin / engine
            executable.write_text(fake, encoding='utf-8')
            executable.chmod(0o755)
        self.called = self.root / 'called.json'
        self.expected = self.root / 'expected.stdout'
        self.out = self.root / 'receipts'

    def git(self, *args):
        return subprocess.check_output(['git', '-C', str(self.repo), *args], stderr=subprocess.STDOUT)

    def command(self, engine='codex', *, out=None, repo=None, resume=None, seconds=10):
        argv = [sys.executable, str(self.install / 'peer.py'), '--engine', engine,
                '--model', engine + '-registered-exact', '--effort', 'max',
                '--repo', str(repo or self.repo), '--prompt', str(self.prompt),
                '--out', str(out or self.out), '--watchdog-seconds', str(seconds)]
        if resume:
            argv += ['--resume', resume]
        return argv

    def environment(self, mode='success'):
        return {**os.environ, 'PATH':str(self.bin) + os.pathsep + os.environ.get('PATH', ''),
                'FAKE_CALLED':str(self.called), 'FAKE_EXPECTED':str(self.expected), 'FAKE_MODE':mode,
                'PYTHONUTF8':'1'}

    def invoke(self, engine='codex', *, mode='success', **kwargs):
        return subprocess.run(self.command(engine, **kwargs), env=self.environment(mode),
                              capture_output=True, timeout=20)

    def receipt(self, out=None):
        out = out or self.out
        return (json.loads((out / 'attempt.json').read_text(encoding='utf-8')),
                json.loads((out / 'completion.json').read_text(encoding='utf-8')))

    def test_explicit_route_resume_and_read_only_arguments(self):
        for engine in ('claude', 'codex'):
            for resume in (None, 'registered-resume-id'):
                with self.subTest(engine=engine, resume=resume):
                    out = self.root / (engine + ('-resume' if resume else '-new'))
                    result = self.invoke(engine, out=out, resume=resume)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    call = json.loads(self.called.read_text(encoding='utf-8'))
                    args = call['argv']
                    self.assertEqual(call['cwd'], str(self.repo))
                    self.assertEqual(args[-1], PROMPT)
                    attempt, completion = self.receipt(out)
                    self.assertEqual(attempt['argv'][1:], args)
                    self.assertEqual(attempt['resume'], resume)
                    self.assertTrue(completion['source_unchanged'])
                    if engine == 'claude':
                        self.assertEqual(args[:14], ['-p', '--model', 'claude-registered-exact',
                            '--effort', 'max', '--permission-mode', 'dontAsk', '--tools', 'Read,Grep,Glob',
                            '--strict-mcp-config', '--mcp-config', '{"mcpServers":{}}', '--output-format', 'json'])
                        self.assertEqual(args[14], '--resume' if resume else '--session-id')
                        if resume:
                            self.assertEqual(args[15], resume)
                    else:
                        self.assertEqual(args[:2], ['exec', 'resume'] if resume else ['exec', '--json'])
                        self.assertEqual(args[args.index('-m') + 1], 'codex-registered-exact')
                        config = [args[index + 1] for index, arg in enumerate(args) if arg == '-c']
                        self.assertEqual(config, ['model_reasoning_effort="max"', 'sandbox_mode="read-only"',
                            'approval_policy="never"', 'projects.' + json.dumps(str(self.repo)) + '.trust_level="trusted"'])
                        if resume:
                            self.assertEqual(args[-2], resume)

    def test_original_native_stdout_stderr_and_final_answer(self):
        for engine in ('claude', 'codex'):
            with self.subTest(engine=engine):
                out = self.root / engine
                result = self.invoke(engine, out=out)
                self.assertEqual(result.returncode, 0, result.stderr)
                attempt, completion = self.receipt(out)
                self.assertEqual((out / attempt['capture']).read_bytes(), self.expected.read_bytes())
                self.assertIn(NATIVE_STDERR, (out / 'stderr').read_bytes())
                self.assertEqual(completion['status'], 'EXITED')
                self.assertEqual(completion['exit_code'], 0)
                self.assertEqual((out / 'finalanswer.txt').read_text(encoding='utf-8').strip(), ANSWER)
                summary = json.loads(result.stdout)
                self.assertIn(str(out / 'finalanswer.txt'), summary.values())

    def test_source_change_is_recorded_and_fails(self):
        result = self.invoke(mode='mutate')
        self.assertNotEqual(result.returncode, 0)
        attempt, completion = self.receipt()
        self.assertEqual(completion['status'], 'EXITED')
        self.assertEqual(completion['exit_code'], 0)
        self.assertFalse(completion['source_unchanged'])
        self.assertNotEqual(attempt['source_before'], completion['source_after'])

    def test_source_identity_includes_untracked_deletion_mode_and_symlink(self):
        snapshot = self.peer['source_identity']
        initial = snapshot(self.repo)
        source = self.repo / 'source.txt'
        source.chmod(0o755)
        self.assertNotEqual(snapshot(self.repo), initial)
        source.chmod(0o644)
        self.assertEqual(snapshot(self.repo), initial)
        source.unlink()
        self.assertIsNone(snapshot(self.repo)['files']['source.txt'])
        source.write_text('original\n', encoding='utf-8')
        added = self.repo / 'untracked.txt'
        added.write_text('new', encoding='utf-8')
        self.assertNotEqual(snapshot(self.repo), initial)
        added.unlink()
        added.symlink_to('source.txt')
        first_target = snapshot(self.repo)
        added.unlink()
        added.symlink_to('missing.txt')
        self.assertNotEqual(snapshot(self.repo), first_target)

    def test_fresh_output_is_required_without_dispatch(self):
        self.out.mkdir()
        sentinel = self.out / 'existing'
        sentinel.write_bytes(b'keep')
        result = self.invoke()
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.called.exists())
        self.assertEqual(sentinel.read_bytes(), b'keep')
        self.assertFalse((self.out / 'attempt.json').exists())

    def test_inside_checkout_output_must_be_ignored(self):
        rejected = self.repo / 'visible-records'
        result = self.invoke(out=rejected)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.called.exists())
        self.assertFalse(rejected.exists())
        accepted = self.repo / '.devlyn' / 'peer-attempt'
        result = self.invoke(out=accepted)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(self.receipt(accepted)[1]['source_unchanged'])

    def test_nonroot_checkout_and_nonpositive_watchdog_reject_before_dispatch(self):
        nested = self.repo / 'nested'
        nested.mkdir()
        for options in ({'repo':nested}, {'seconds':0}, {'seconds':-1}):
            with self.subTest(options=options):
                result = self.invoke(**options)
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse(self.called.exists())
                self.assertFalse(self.out.exists())

    def test_nonzero_exit_has_completion_and_untouched_stdout(self):
        result = self.invoke(mode='nonzero')
        self.assertNotEqual(result.returncode, 0)
        attempt, completion = self.receipt()
        self.assertEqual(completion['status'], 'EXITED')
        self.assertEqual(completion['exit_code'], 17)
        self.assertTrue(completion['source_unchanged'])
        self.assertEqual((self.out / attempt['capture']).read_bytes(), self.expected.read_bytes())

    def test_terminal_error_or_missing_terminal_never_succeeds(self):
        for engine in ('claude', 'codex'):
            for mode in ('terminal-failure', 'missing-terminal'):
                with self.subTest(engine=engine, mode=mode):
                    out = self.root / (engine + '-' + mode)
                    result = self.invoke(engine, out=out, mode=mode)
                    self.assertNotEqual(result.returncode, 0)
                    attempt, completion = self.receipt(out)
                    self.assertEqual(completion['exit_code'], 0)
                    self.assertTrue(completion.get('error') or completion.get('native_error'), completion)
                    self.assertEqual((out / attempt['capture']).read_bytes(), self.expected.read_bytes())

    def test_timeout_writes_completion_after_shared_process_cleanup(self):
        result = self.invoke(mode='sleep', seconds=1)
        self.assertNotEqual(result.returncode, 0)
        _, completion = self.receipt()
        self.assertEqual(completion['status'], 'TIMEOUT')
        self.assertEqual(completion['exit_code'], 124)
        self.assertTrue(completion['source_unchanged'])
        self.assertLess(completion['seconds'], 15)
        self.assertIn(b'timeout:', (self.out / 'stderr').read_bytes())

    def test_sigterm_writes_interrupted_completion(self):
        process = subprocess.Popen(self.command(seconds=60), env=self.environment('sleep'),
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        try:
            deadline = time.monotonic() + 5
            while not self.called.exists() and process.poll() is None and time.monotonic() < deadline:
                time.sleep(0.02)
            self.assertTrue(self.called.exists(), 'fake CLI did not start')
            process.send_signal(signal.SIGTERM)
            stdout, stderr = process.communicate(timeout=15)
            self.assertEqual(process.returncode, 128 + signal.SIGTERM, (stdout, stderr))
            _, completion = self.receipt()
            self.assertEqual(completion['status'], 'INTERRUPTED')
            self.assertIsNone(completion['exit_code'])
            self.assertTrue(completion['source_unchanged'])
            self.assertTrue(completion['error'])
        finally:
            if process.poll() is None:
                process.kill()
                process.communicate()


if __name__ == '__main__':
    unittest.main(verbosity=2)
