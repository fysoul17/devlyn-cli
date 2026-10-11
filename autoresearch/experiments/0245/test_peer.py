#!/usr/bin/env python3
"""Focused 0245 custody regressions; fake CLIs only, no model calls."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import unittest
import uuid


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
spec = importlib.util.spec_from_file_location(
    'peer_0238_fixture', HERE.parent / '0238' / 'test_peer.py')
fixture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixture)
# Reuse setup and process plumbing, not the old API's test cases.
fixture.HERE = HERE
ANSWER, PROMPT, NATIVE_STDERR = fixture.ANSWER, fixture.PROMPT, fixture.NATIVE_STDERR
fixture.FAKE = '''#!{python}
import json
import os
from pathlib import Path
import sys
import time

args = sys.argv[1:]
engine = Path(sys.argv[0]).name
mode = os.environ.get('FAKE_MODE', 'success')
Path(os.environ['FAKE_CALLED']).write_text(
    json.dumps({{'argv': args, 'cwd': str(Path.cwd())}}), encoding='utf-8')
if mode == 'mutate':
    Path('source.txt').write_text('changed by fake peer', encoding='utf-8')
if engine == 'claude':
    flag = '--resume' if '--resume' in args else '--session-id'
    session = args[args.index(flag) + 1]
    rows = [{{'type': 'result', 'session_id': session, 'is_error': False,
             'result': {answer!r},
             'usage': {{'input_tokens': 3, 'output_tokens': 5}}}}]
else:
    session = args[-2] if args[1] == 'resume' else 'codex-test'
    rows = [{{'type': 'thread.started', 'thread_id': session}},
            {{'type': 'item.completed', 'item': {{'id': 'answer',
                'type': 'agent_message', 'text': {answer!r}}}}},
            {{'type': 'turn.completed', 'usage': {{'input_tokens': 3,
                'cached_input_tokens': 0, 'output_tokens': 5}}}}]
raw = ('\\n'.join(json.dumps(row, ensure_ascii=False) for row in rows) + '\\n').encode('utf-8')
Path(os.environ['FAKE_EXPECTED']).write_bytes(raw)
os.write(1, raw)
os.write(2, {stderr!r})
if mode == 'sleep':
    time.sleep(120)
sys.exit(17 if mode == 'nonzero' else 0)
'''


@unittest.skipUnless(os.name == 'posix', 'fake executables/signals require POSIX')
class CustodyTests(unittest.TestCase):
    setUp = fixture.PeerTests.setUp
    git = fixture.PeerTests.git
    environment = fixture.PeerTests.environment

    def command(self, engine='codex', *, prompt=None, resume=None, seconds=10):
        argv = [sys.executable, '-B', str(self.install / 'peer.py'),
                '--engine', engine, '--model', engine + '-registered-exact',
                '--effort', 'max', '--repo', str(self.repo),
                '--prompt', str(prompt or self.prompt),
                '--watchdog-seconds', str(seconds)]
        if resume:
            argv += ['--resume', resume]
        return argv

    def invoke(self, engine='codex', *, mode='success', **kwargs):
        return subprocess.run(self.command(engine, **kwargs),
                              env=self.environment(mode), capture_output=True, timeout=20)

    def records(self):
        root = self.repo / '.devlyn' / 'pair'
        return set(root.iterdir()) if root.is_dir() else set()

    def receipt(self, out):
        return (json.loads((out / 'attempt.json').read_text()),
                json.loads((out / 'completion.json').read_text()))

    def hashes(self, out):
        return {str(p.relative_to(out)): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in out.rglob('*') if p.is_file()}

    def assert_retained(self, out, *, final_answer):
        self.assertEqual(out.parent, self.repo / '.devlyn' / 'pair')
        self.assertEqual(out.resolve(), out)
        self.assertTrue(out.is_dir())
        attempt, completion = self.receipt(out)
        self.assertEqual(attempt['schema'], 'devlyn-peer-v1')
        self.assertEqual(completion['schema'], 'devlyn-peer-v1')
        capture = out / attempt['capture']
        self.assertEqual(capture.parent, out)
        self.assertEqual(capture.read_bytes(), self.expected.read_bytes())
        self.assertIn(NATIVE_STDERR, (out / 'stderr').read_bytes())
        expected = {'attempt.json', 'completion.json', capture.name, 'stderr'}
        if final_answer:
            expected.add('finalanswer.txt')
            self.assertEqual(completion['final_answer'], str(out / 'finalanswer.txt'))
            self.assertEqual((out / 'finalanswer.txt').read_text().strip(), ANSWER)
        else:
            self.assertIsNone(completion['final_answer'])
        self.assertEqual({p.name for p in out.iterdir()}, expected)
        return attempt, completion

    def assert_native_flags(self, engine, attempt, resume):
        call = json.loads(self.called.read_text())
        args = call['argv']
        self.assertEqual(call['cwd'], str(self.repo))
        self.assertEqual(attempt['argv'], [engine, *args])
        self.assertEqual(attempt['resume'], resume)
        self.assertEqual(args[-1], PROMPT)
        self.assertEqual(attempt['prompt_sha256'],
                         hashlib.sha256(PROMPT.encode()).hexdigest())
        if engine == 'claude':
            native_session = resume or args[-2]
            if not resume:
                uuid.UUID(native_session)
            expected = ['-p', '--model', 'claude-registered-exact',
                        '--effort', 'max', '--permission-mode', 'dontAsk',
                        '--tools', 'Read,Grep,Glob', '--strict-mcp-config',
                        '--mcp-config', '{"mcpServers":{}}', '--output-format', 'json',
                        '--resume' if resume else '--session-id', native_session, PROMPT]
        else:
            expected = ['exec', *(['resume'] if resume else []), '--json',
                        '--skip-git-repo-check', '-m', 'codex-registered-exact',
                        '-c', 'model_reasoning_effort="max"',
                        '-c', 'sandbox_mode="read-only"', '-c', 'approval_policy="never"',
                        '-c', 'agents.enabled=false',
                        '-c', 'features.multi_agent_v2.enabled=false',
                        '-c', 'projects.' + json.dumps(str(self.repo)) + '.trust_level="trusted"',
                        *([resume] if resume else []), PROMPT]
        self.assertEqual(args, expected)

    def test_caller_temporary_cleanup_leaves_one_complete_canonical_set_per_call(self):
        for engine in ('claude', 'codex'):
            with self.subTest(engine=engine):
                initial = self.records()
                source_before = self.peer['source_identity'](self.repo)
                with tempfile.TemporaryDirectory(prefix='caller-', dir=self.root) as scratch:
                    scratch = Path(scratch)
                    prompt = scratch / 'request.md'
                    prompt.write_text(PROMPT)
                    result = self.invoke(engine, prompt=prompt)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    summary = json.loads(result.stdout)
                    out = Path(summary['receipt'])
                    copied = scratch / 'answer-copy.txt'
                    shutil.copy2(summary['final_answer'], copied)
                    self.assertEqual(copied.read_text().strip(), ANSWER)
                    retained = self.hashes(out)
                self.assertFalse(scratch.exists())
                self.assertEqual(self.records() - initial, {out})
                self.assertEqual(self.hashes(out), retained)
                attempt, completion = self.assert_retained(out, final_answer=True)
                self.assertEqual(completion['status'], 'EXITED')
                self.assertEqual(completion['exit_code'], 0)
                self.assertTrue(completion['source_unchanged'])
                self.assertEqual(attempt['source_before'], source_before)
                self.assertEqual(completion['source_after'], source_before)
                self.assertEqual(self.peer['source_identity'](self.repo), source_before)
                self.assertEqual(self.git('status', '--porcelain'), b'')
                self.assertEqual(list(scratch.glob('**/attempt.json')), [])
                self.assert_native_flags(engine, attempt, None)

    def test_fresh_resume_have_distinct_immutable_records_and_same_native_session(self):
        for engine in ('claude', 'codex'):
            with self.subTest(engine=engine):
                before = self.records()
                fresh = self.invoke(engine)
                self.assertEqual(fresh.returncode, 0, fresh.stderr)
                first = Path(json.loads(fresh.stdout)['receipt'])
                attempt, _ = self.assert_retained(first, final_answer=True)
                self.assert_native_flags(engine, attempt, None)
                native = [json.loads(s) for s in (first / attempt['capture']).read_text().splitlines()]
                session = native[0]['session_id' if engine == 'claude' else 'thread_id']
                retained = self.hashes(first)
                resumed = self.invoke(engine, resume=session)
                self.assertEqual(resumed.returncode, 0, resumed.stderr)
                second = Path(json.loads(resumed.stdout)['receipt'])
                self.assertNotEqual(first, second)
                self.assertEqual(self.records() - before, {first, second})
                self.assertEqual(self.hashes(first), retained)
                attempt, completion = self.assert_retained(second, final_answer=True)
                self.assert_native_flags(engine, attempt, session)
                native = [json.loads(s) for s in (second / attempt['capture']).read_text().splitlines()]
                self.assertEqual(native[0]['session_id' if engine == 'claude' else 'thread_id'], session)
                self.assertTrue(completion['source_unchanged'])

    def test_repeated_fresh_calls_preserve_prior_records_and_existing_contents(self):
        root = self.repo / '.devlyn' / 'pair'
        root.mkdir(parents=True)
        sentinel = root / 'preexisting.txt'
        sentinel.write_bytes(b'existing custody must survive')
        first = self.invoke()
        self.assertEqual(first.returncode, 0, first.stderr)
        out1 = Path(json.loads(first.stdout)['receipt'])
        original = self.hashes(root)
        second = self.invoke()
        self.assertEqual(second.returncode, 0, second.stderr)
        out2 = Path(json.loads(second.stdout)['receipt'])
        self.assertNotEqual(out1, out2)
        self.assertEqual(self.records(), {sentinel, out1, out2})
        after = self.hashes(root)
        self.assertTrue(all(after[name] == digest for name, digest in original.items()))
        self.assert_retained(out2, final_answer=True)

    def test_native_nonzero_retains_capture_and_completion_for_both_engines(self):
        for engine in ('claude', 'codex'):
            with self.subTest(engine=engine):
                before = self.records()
                result = self.invoke(engine, mode='nonzero')
                self.assertNotEqual(result.returncode, 0)
                added = self.records() - before
                self.assertEqual(len(added), 1)
                _, completion = self.assert_retained(added.pop(), final_answer=False)
                self.assertEqual(completion['status'], 'EXITED')
                self.assertEqual(completion['exit_code'], 17)
                self.assertTrue(completion['source_unchanged'])

    def test_timeout_retains_native_streams_and_completion_for_both_engines(self):
        for engine in ('claude', 'codex'):
            with self.subTest(engine=engine):
                before = self.records()
                result = self.invoke(engine, mode='sleep', seconds=1)
                self.assertNotEqual(result.returncode, 0)
                added = self.records() - before
                self.assertEqual(len(added), 1)
                out = added.pop()
                _, completion = self.assert_retained(out, final_answer=False)
                self.assertEqual(completion['status'], 'TIMEOUT')
                self.assertEqual(completion['exit_code'], 124)
                self.assertTrue(completion['source_unchanged'])
                self.assertLess(completion['seconds'], 15)
                self.assertIn(b'timeout:', (out / 'stderr').read_bytes())

    def test_sigterm_retains_native_streams_and_interrupted_completion_for_both_engines(self):
        for engine in ('claude', 'codex'):
            with self.subTest(engine=engine):
                before = self.records()
                process = subprocess.Popen(self.command(engine, seconds=60),
                    env=self.environment('sleep'), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                try:
                    deadline = time.monotonic() + 5
                    out = None
                    while process.poll() is None and time.monotonic() < deadline:
                        added = self.records() - before
                        if len(added) == 1:
                            out = next(iter(added))
                            if ((out / 'stderr').exists()
                                    and NATIVE_STDERR in (out / 'stderr').read_bytes()):
                                break
                        time.sleep(0.02)
                    self.assertIsNotNone(out, 'canonical attempt was not allocated')
                    self.assertIn(NATIVE_STDERR, (out / 'stderr').read_bytes(),
                                  'fake native did not reach its captured-output boundary')
                    process.send_signal(signal.SIGTERM)
                    stdout, stderr = process.communicate(timeout=15)
                    self.assertEqual(process.returncode, 128 + signal.SIGTERM, (stdout, stderr))
                    self.assertEqual(self.records() - before, {out})
                    _, completion = self.assert_retained(out, final_answer=False)
                    self.assertEqual(completion['status'], 'INTERRUPTED')
                    self.assertIsNone(completion['exit_code'])
                    self.assertTrue(completion['source_unchanged'])
                    self.assertTrue(completion['error'])
                finally:
                    if process.poll() is None:
                        process.kill()
                        process.communicate()

    def test_source_mutation_fails_and_retains_both_source_identities(self):
        for engine in ('claude', 'codex'):
            with self.subTest(engine=engine):
                (self.repo / 'source.txt').write_text('original\n')
                before = self.records()
                result = self.invoke(engine, mode='mutate')
                self.assertNotEqual(result.returncode, 0)
                added = self.records() - before
                self.assertEqual(len(added), 1)
                attempt, completion = self.assert_retained(added.pop(), final_answer=True)
                self.assertEqual(completion['status'], 'EXITED')
                self.assertEqual(completion['exit_code'], 0)
                self.assertFalse(completion['source_unchanged'])
                self.assertNotEqual(attempt['source_before'], completion['source_after'])
                self.assertEqual((self.repo / 'source.txt').read_text(), 'changed by fake peer')

    def assert_no_dispatch(self, result):
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.called.exists())
        self.assertFalse(self.expected.exists())
        self.assertEqual(list(self.repo.rglob('attempt.json')), [])

    def test_nonignored_custody_root_rejects_without_dispatch_or_ignore_edit(self):
        ignore = self.repo / '.gitignore'
        ignore.write_text('')
        result = self.invoke()
        self.assert_no_dispatch(result)
        self.assertFalse((self.repo / '.devlyn').exists())
        self.assertEqual(ignore.read_bytes(), b'')

    def test_symlinked_parent_or_custody_root_rejects_inside_and_outside_targets(self):
        for level in ('parent', 'pair'):
            for location in ('inside', 'outside'):
                with self.subTest(level=level, location=location):
                    target = (self.repo if location == 'inside' else self.root) / (level + '-target')
                    target.mkdir()
                    sentinel = target / 'keep'
                    sentinel.write_bytes(b'unchanged')
                    link = self.repo / '.devlyn'
                    if level == 'pair':
                        link.mkdir()
                        link /= 'pair'
                    link.symlink_to(target, target_is_directory=True)
                    try:
                        self.assert_no_dispatch(self.invoke())
                        self.assertEqual({p.name for p in target.iterdir()}, {'keep'})
                        self.assertEqual(sentinel.read_bytes(), b'unchanged')
                        self.assertTrue(link.is_symlink())
                    finally:
                        link.unlink()
                        if level == 'pair':
                            link.parent.rmdir()

    def test_file_at_parent_or_custody_root_rejects_without_dispatch(self):
        for level in ('parent', 'pair'):
            with self.subTest(level=level):
                path = self.repo / '.devlyn'
                if level == 'pair':
                    path.mkdir()
                    path /= 'pair'
                path.write_bytes(b'preserve file')
                try:
                    self.assert_no_dispatch(self.invoke())
                    self.assertEqual(path.read_bytes(), b'preserve file')
                finally:
                    path.unlink()
                    if level == 'pair':
                        path.parent.rmdir()

    def test_removed_out_argument_rejects_before_dispatch_or_directory_creation(self):
        for engine in ('claude', 'codex'):
            with self.subTest(engine=engine):
                external = self.root / 'caller-controlled-output'
                result = subprocess.run(self.command(engine) + ['--out', str(external)],
                    env=self.environment(), capture_output=True, timeout=20)
                self.assertEqual(result.returncode, 2)
                self.assertIn(b'unrecognized arguments: --out', result.stderr)
                self.assert_no_dispatch(result)
                self.assertFalse(external.exists())
                self.assertFalse((self.repo / '.devlyn').exists())


if __name__ == '__main__':
    unittest.main(verbosity=2)

