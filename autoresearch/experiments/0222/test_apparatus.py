"""Model-free tests. Container cases need APPARATUS_IMAGE (and APPARATUS_CONTROL for the reviewer stub)."""
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
SOURCES = REPO / '.devlyn/0206'
IMAGE = os.environ.get('APPARATUS_IMAGE')
CONTROL = os.environ.get('APPARATUS_CONTROL')


def load(name):
    spec = importlib.util.spec_from_file_location(name + '_t', HERE / f'{name}.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


prepare, packet, usage, cell, run_cell, check = (load(n) for n in ('prepare', 'packet', 'record_usage', 'cell',
                                                             'run_cell', 'check'))


def git(work, *args):
    return subprocess.run(['git', *args], cwd=work, check=True, capture_output=True, text=True).stdout.strip()


def rollout(path, sid, source, model, input_tokens, output_tokens=10):
    total = dict(input_tokens=input_tokens, cached_input_tokens=0, cache_write_input_tokens=0,
                 output_tokens=output_tokens, reasoning_output_tokens=0, total_tokens=input_tokens + output_tokens)
    events = [dict(type='session_meta', payload=dict(id=sid, source=source)),
              dict(type='turn_context', payload=dict(model=model, effort='high')),
              dict(type='event_msg', payload=dict(type='task_started', turn_id='t-' + sid)),
              dict(type='event_msg', payload=dict(type='token_count', info=dict(total_token_usage=total,
                                                                                last_token_usage=total))),
              dict(type='event_msg', payload=dict(type='task_complete', turn_id='t-' + sid))]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(''.join(json.dumps(e) + '\n' for e in events))


def forked_child(path, sid, parent, parent_model, model, input_tokens):
    """The archived 0210 native-child shape: copied parent context, boundary, then the child's own turn."""
    total = dict(input_tokens=input_tokens, cached_input_tokens=0, cache_write_input_tokens=0, output_tokens=1,
                 reasoning_output_tokens=0, total_tokens=input_tokens + 1)
    spawn = dict(subagent=dict(thread_spawn=dict(parent_thread_id=parent)))
    events = [dict(type='session_meta', payload=dict(id=sid, forked_from_id=parent, parent_thread_id=parent, source=spawn)),
              dict(type='session_meta', payload=dict(id=parent, source='exec')),
              dict(type='event_msg', payload=dict(type='task_started', turn_id='t-' + parent)),
              dict(type='turn_context', payload=dict(model=parent_model, turn_id='t-' + parent)),
              dict(type='event_msg', payload=dict(type='thread_settings_applied', thread_id=sid)),
              dict(type='event_msg', payload=dict(type='task_started', turn_id='own')),
              dict(type='turn_context', payload=dict(model=model, turn_id='own')),
              dict(type='event_msg', payload=dict(type='token_count', info=dict(total_token_usage=total,
                                                                                last_token_usage=total))),
              dict(type='event_msg', payload=dict(type='task_complete', turn_id='own'))]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(''.join(json.dumps(e) + '\n' for e in events))


class Pure(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    @unittest.skipUnless(SOURCES.exists(), 'registered sources absent')
    def test_routes_prompts_and_bindings(self):
        runtime = dict(sources=str(SOURCES), control='/c', image='sha256:x', output=str(self.root), auth='/a')
        codex = prepare.prepare(runtime, 'a', 'D4', 'A', 'codex')
        claude = prepare.prepare(runtime, 'c', 'SMOKE', 'C', 'claude')
        toml = (codex / 'home/.codex/config.toml').read_text()
        self.assertIn('model = "gpt-6-astra"', toml)
        self.assertIn('default_subagent_model = "gpt-6-sol"', toml)
        self.assertNotIn('observed-openai', toml)
        for out in (codex, claude):
            plan = json.loads((out / 'plan.json').read_text())
            self.assertEqual(plan['argv'][-1], (out / 'prompt.txt').read_text())
            self.assertEqual(json.loads((out / 'baseline.json').read_text())['prompt_sha256'],
                             packet.digest(out / 'prompt.txt'))
            self.assertEqual(git(out / 'work', 'status', '--porcelain', '--untracked-files=all'), '')
        claude_plan = json.loads((claude / 'plan.json').read_text())
        self.assertEqual(claude_plan['argv'][:4], ['claude', '-p', '--model', 'claude-opus-5-5'])
        self.assertEqual(claude_plan['env']['DEVLYN_REVIEWER'], 'codex:gpt-6-astra:high')
        self.assertNotIn('DEVLYN_REVIEWER', json.loads((codex / 'plan.json').read_text())['env'])
        harness = (HERE / 'common.txt').read_text() + prepare.REVIEW
        self.assertIsNone(re.search(r'budget|target|telemetry|invocation|cache-inclusive|240|yield_time_ms|OUTPUT',
                                    harness, re.I))

    def test_packet_diffs_against_base_and_includes_untracked(self):
        work = self.root / 'work'
        (work / 'tests/deep').mkdir(parents=True)
        git(work.parent, 'init', '-q', '-b', 'main', str(work))
        git(work, 'config', 'user.email', 'x@y'), git(work, 'config', 'user.name', 'x')
        (work / 'a.py').write_text('old\n')
        git(work, 'add', '-A'), git(work, 'commit', '-qm', 'base')
        base = git(work, 'rev-parse', 'HEAD')
        (work / 'a.py').write_text('new\n')
        git(work, 'commit', '-qam', 'owner commit')
        (work / 'tests/deep/test_new.py').write_text('fresh\n')
        (work / '.devlyn').mkdir()
        (work / '.devlyn/caller.json').write_text(json.dumps(dict(
            request='r', allowed=['a.py', 'tests/**'], review_files=['a.py'], base_sha=base)))
        (work / '.git/info/exclude').write_text('.devlyn/\n')
        _, text = packet.packet(work)
        self.assertEqual(git(work, 'diff', 'HEAD'), '')
        self.assertIn('+new', text)
        self.assertIn('FILE tests/deep/test_new.py\nfresh', text)
        self.assertIn('UNTRACKED FILES\ntests/deep/test_new.py', text)

    def test_usage_is_recorded_above_old_caps_across_exec_roots(self):
        sessions = self.root / 'sessions'
        rollout(sessions / 'owner.jsonl', 'owner', 'exec', 'gpt-6-astra', 1_200_001)
        rollout(sessions / 'child.jsonl', 'child', dict(subagent=dict(thread_spawn=dict(parent_thread_id='owner'))),
                'gpt-6-sol', 500)
        rollout(sessions / 'judge.jsonl', 'judge', 'exec', 'gpt-6-astra', 700)
        totals, failures = usage.codex(sessions)
        self.assertEqual(failures, [])
        self.assertEqual(totals['gpt-6-astra']['input'], 1_200_701)
        self.assertEqual(totals['gpt-6-sol']['input'], 500)

    def test_nested_claude_results_are_counted_once(self):
        devlyn = self.root / '.devlyn'
        run = devlyn / 'runs/r'
        run.mkdir(parents=True)
        judge = dict(session_id='j', modelUsage={'claude-opus-5-5': dict(inputTokens=1, outputTokens=261)})
        close = dict(session_id='s', modelUsage={'claude-opus-5-5[1m]': dict(inputTokens=1, outputTokens=362)})
        (run / 'claude-judge.r0.output.json').write_text(json.dumps(judge))
        (run / 'surface-close.output.json').write_text(json.dumps(close))
        (devlyn / 'claude-judge.r0.output.json').write_text(json.dumps(judge))  # pre-archive copy of the same run
        (devlyn / 'broken.output.json').write_text('{"modelUs')
        self.assertEqual(usage.claude_nested(devlyn)['claude-opus-5-5']['output'], 623)

    def test_truncated_rollout_is_partial_not_zero(self):
        sessions = self.root / 'sessions'
        rollout(sessions / 'owner.jsonl', 'owner', 'exec', 'gpt-6-astra', 100)
        lines = (sessions / 'owner.jsonl').read_text().splitlines()
        (sessions / 'owner.jsonl').write_text('\n'.join(lines[:-1]) + '\n')
        totals, failures = usage.codex(sessions)
        self.assertEqual(totals, {})
        self.assertEqual(len(failures), 1)

    @unittest.skipUnless((REPO / '.devlyn/0219-screen').exists(), 'archived 0219 cell absent')
    def test_archived_0219_native_usage_replays(self):
        totals, _ = usage.codex(REPO / '.devlyn/0219-screen/0219-screen-20260924/01-D1-1-A/home/.codex/sessions')
        row = totals['gpt-6-astra']
        self.assertEqual((row['input'] + row['cache_read'] + row['cache_write'], row['output']), (203245, 3406))

    def identity(self, engine, sessions, model_usage=None):
        work = Path(tempfile.mkdtemp(dir=self.root))
        (work / 'run').mkdir()
        stdout = [dict(type='thread.started', thread_id='owner')]
        if model_usage is not None:
            stdout = [dict(type='system', subtype='init', model=next(iter(model_usage))),
                      dict(type='result', modelUsage=model_usage)]
        (work / 'run/stdout').write_text(''.join(json.dumps(e) + '\n' for e in stdout))
        for name, model in sessions.items():
            rollout(work / f'home/.codex/sessions/rollout-{name}.jsonl', name, 'exec', model, 1)
        model = 'claude-opus-5-5' if engine == 'claude' else 'gpt-6-astra'
        return cell.identity(work, dict(engine=engine, model=model, config=engine, arm='A'))

    def test_identity_is_checked_per_role(self):
        self.assertEqual(self.identity('codex', {'owner': 'gpt-6-astra', 'kid': 'gpt-6-sol'})['status'], 'MATCH')
        self.assertEqual(self.identity('codex', {'owner': 'gpt-6-sol'})['status'], 'MISMATCH')

    def test_stray_codex_model_is_mismatch(self):
        self.assertEqual(self.identity('codex', {'owner': 'gpt-6-astra', 'x': 'gpt-5'})['status'], 'MISMATCH')

    def test_claude_owner_identity(self):
        self.assertEqual(self.identity('claude', {}, {'claude-opus-5-5': {}, 'claude-haiku-4-5': {}})['status'], 'MATCH')
        self.assertEqual(self.identity('claude', {}, {'claude-sonnet-5': {}})['status'], 'MISMATCH')
        # A wrong-model owner is not rescued by a routed model elsewhere in aggregate usage.
        self.assertEqual(self.identity('claude', {}, {'claude-sonnet-5': {}, 'claude-opus-5-5': {}})['status'],
                         'MISMATCH')

    def test_forked_native_child_is_bound_to_its_own_model(self):
        work = Path(tempfile.mkdtemp(dir=self.root))
        (work / 'run').mkdir()
        (work / 'run/stdout').write_text(json.dumps(dict(type='thread.started', thread_id='owner')) + '\n')
        rollout(work / 'home/.codex/sessions/rollout-owner.jsonl', 'owner', 'exec', 'gpt-6-astra', 100)
        forked_child(work / 'home/.codex/sessions/rollout-kid.jsonl', 'kid', 'owner', 'gpt-6-astra', 'gpt-6-sol', 500)
        plan = dict(engine='codex', model='gpt-6-astra', config='codex', arm='A')
        self.assertEqual(cell.identity(work, plan)['status'], 'MATCH')
        totals, failures = usage.codex(work / 'home/.codex/sessions')
        self.assertEqual((failures, totals['gpt-6-astra']['input'], totals['gpt-6-sol']['input']), ([], 100, 500))
        forked_child(work / 'home/.codex/sessions/rollout-kid.jsonl', 'kid', 'owner', 'gpt-6-astra', 'gpt-6-astra', 5)
        self.assertEqual(cell.identity(work, plan)['status'], 'MISMATCH')

    def f_cell(self, state):
        work = Path(tempfile.mkdtemp(dir=self.root))
        (work / 'run').mkdir()
        (work / 'run/stdout').write_text(json.dumps(dict(type='thread.started', thread_id='owner')) + '\n')
        rollout(work / 'home/.codex/sessions/rollout-owner.jsonl', 'owner', 'exec', 'gpt-6-astra', 1)
        (work / 'work/.devlyn/runs/r').mkdir(parents=True)
        (work / 'work/.devlyn/runs/r/pipeline.state.json').write_text(state)
        return cell.identity(work, dict(engine='codex', model='gpt-6-astra', config='codex', arm='F'))

    def test_f_role_mixing_is_mismatch(self):
        worker = dict(engine='codex', model_requested='gpt-6-sol')
        good = dict(role_resolution=dict(roles=dict(worker=worker)),
                    phases=dict(implement=dict(model_requested='gpt-6-sol', model_effective=None)))
        self.assertEqual(self.f_cell(json.dumps(good))['status'], 'MATCH')
        swapped = dict(good, role_resolution=dict(roles=dict(worker=dict(engine='codex', model_requested='gpt-6-astra'))))
        self.assertEqual(self.f_cell(json.dumps(swapped))['status'], 'MISMATCH')
        ran_other = dict(good, phases=dict(verify=dict(model_requested='gpt-6-sol', model_effective='gpt-6-astra')))
        self.assertEqual(self.f_cell(json.dumps(ran_other))['status'], 'MISMATCH')

    def test_f_codex_worker_session_is_bound_to_the_worker_model(self):
        for model, status in (('gpt-6-sol', 'MATCH'), ('gpt-6-astra', 'MISMATCH')):
            state = dict(phases=dict(implement=dict(model_requested='gpt-6-sol', model_effective=None)))
            work = Path(tempfile.mkdtemp(dir=self.root))
            (work / 'run').mkdir()
            (work / 'run/stdout').write_text(json.dumps(dict(type='thread.started', thread_id='owner')) + '\n')
            rollout(work / 'home/.codex/sessions/rollout-owner.jsonl', 'owner', 'exec', 'gpt-6-astra', 1)
            rollout(work / 'home/.codex/sessions/rollout-w.jsonl', 'w', 'exec', model, 1)
            (work / 'work/.devlyn').mkdir(parents=True)
            (work / 'work/.devlyn/pipeline.state.json').write_text(json.dumps(state))
            (work / 'work/.devlyn/implement.worker-session.1.jsonl').write_text(
                json.dumps(dict(type='thread.started', thread_id='w')) + '\n')
            # 3.2.1 SURFACE_CLOSE keeps a Claude transcript under the same file pattern; it is not a Codex worker.
            (work / 'work/.devlyn/surface-close.worker-session.0.jsonl').write_text(
                json.dumps(dict(type='system', subtype='init', model='claude-opus-5-5')) + '\n')
            got = cell.identity(work, dict(engine='codex', model='gpt-6-astra', config='codex', arm='F'))
            self.assertEqual(got['status'], status, got['violations'])

    def test_one_m_context_suffix_is_the_same_model(self):
        state = dict(phases=dict(verify=dict(model_requested='claude-opus-5-5', model_effective='claude-opus-5-5[1m]')))
        work = Path(tempfile.mkdtemp(dir=self.root))
        (work / 'run').mkdir()
        (work / 'run/stdout').write_text(json.dumps(dict(type='system', subtype='init', model='claude-opus-5-5[1m]')) + '\n')
        (work / 'work/.devlyn').mkdir(parents=True)
        (work / 'work/.devlyn/pipeline.state.json').write_text(json.dumps(state))
        got = cell.identity(work, dict(engine='claude', model='claude-opus-5-5', config='claude', arm='F'))
        self.assertEqual(got['status'], 'MATCH', got['violations'])

    def test_claude_surface_close_transcript_does_not_stop_f_claude(self):
        work = Path(tempfile.mkdtemp(dir=self.root))
        (work / 'run').mkdir()
        (work / 'run/stdout').write_text(json.dumps(dict(type='system', subtype='init', model='claude-opus-5-5')) + '\n')
        (work / 'work/.devlyn').mkdir(parents=True)
        (work / 'work/.devlyn/surface-close.worker-session.0.jsonl').write_text(
            json.dumps(dict(type='system', subtype='init', model='claude-opus-5-5')) + '\n')
        got = cell.identity(work, dict(engine='claude', model='claude-opus-5-5', config='claude', arm='F'))
        self.assertEqual(got['status'], 'MATCH', got['violations'])

    def test_torn_pipeline_state_is_a_gap_not_a_crash(self):
        result = self.f_cell('{"role_resolution": {"ro')
        self.assertEqual((result['status'], len(result['gaps'])), ('MATCH', 1))

    def test_synthetic_claude_error_is_not_a_model(self):
        work = Path(tempfile.mkdtemp(dir=self.root))
        (work / 'run').mkdir()
        (work / 'run/stdout').write_text(json.dumps(dict(type='system', subtype='init', model='claude-opus-5-5')) + '\n')
        transcript = work / 'home/.claude/projects/p/s.jsonl'
        transcript.parent.mkdir(parents=True)
        transcript.write_bytes(json.dumps(dict(type='assistant', isApiErrorMessage=True, error='rate_limit',
                                               message=dict(model='<synthetic>', usage={}))).encode() + b'\n\xff\xfe\n')
        self.assertEqual(cell.identity(work, dict(engine='claude', model='claude-opus-5-5', config='claude',
                                                  arm='A'))['status'], 'MATCH')

    def test_owner_unknown_with_model_evidence_is_unverified(self):
        self.assertEqual(self.identity('codex', {'someone': 'gpt-6-astra'})['status'], 'UNVERIFIED')

    def test_reviewer_mismatch_propagates(self):
        work = Path(tempfile.mkdtemp(dir=self.root))
        (work / 'run').mkdir()
        (work / 'run/stdout').write_text(json.dumps(dict(type='thread.started', thread_id='owner')) + '\n')
        rollout(work / 'home/.codex/sessions/rollout-owner.jsonl', 'owner', 'exec', 'gpt-6-astra', 1)
        (work / 'work/.devlyn/reviews/call-1').mkdir(parents=True)
        (work / 'work/.devlyn/reviews/call-1/result.json').write_text(json.dumps(dict(identity='MISMATCH')))
        self.assertEqual(cell.identity(work, dict(engine='codex', model='gpt-6-astra', config='codex', arm='C'))['status'],
                         'MISMATCH')

    def test_torn_rollout_line_is_tolerated(self):
        sessions = self.root / 'sessions'
        rollout(sessions / 'owner.jsonl', 'owner', 'exec', 'gpt-6-astra', 100)
        with (sessions / 'owner.jsonl').open('a') as stream:
            stream.write('{"type": "event_msg", "payl')
        totals, failures = usage.codex(sessions)  # must not raise: a hang kill can tear the last line
        self.assertEqual((totals, len(failures)), ({}, 1))

    def test_verdict_mapping(self):
        ok = dict(complete=True, severe=0)
        passing = dict(product_check_pass=True, adjudication_needed=False)
        self.assertEqual(run_cell.verdict(passing, [ok, ok]), 'COMPLETE')
        self.assertEqual(run_cell.verdict(passing, [ok, dict(complete=True, severe=1)]), 'PRODUCT_INCOMPLETE')
        self.assertEqual(run_cell.verdict(passing, [ok, dict(complete=None, severe=0)]), 'PRODUCT_INCOMPLETE')
        self.assertEqual(run_cell.verdict(dict(product_check_pass=False, adjudication_needed=True), [ok, ok]),
                         'ADJUDICATE')

    def test_evaluator_crash_stops_but_product_crash_is_a_row(self):
        with self.assertRaises(check.NoVerdict):
            check.last_json(dict(exit_code=125, timeout=False, stdout='', stderr='docker: error'))
        self.assertIsNone(check.last_json(dict(exit_code=1, timeout=False, stdout='SyntaxError', stderr='')))
        self.assertIsNone(check.last_json(dict(exit_code=None, timeout=True, stdout='', stderr='host timeout')))
        self.assertIsNone(check.last_json(dict(exit_code=124, timeout=True, stdout='{"passed": true}', stderr='')))
        self.assertEqual(check.last_json(dict(exit_code=0, timeout=False, stdout='x\n{"passed": true}', stderr='')),
                         {'passed': True})

    @unittest.skipUnless(SOURCES.exists(), 'registered sources absent')
    def test_changed_issue_snapshot_refuses_to_prepare(self):
        sources = self.root / 'sources'
        sources.mkdir()
        (sources / 'click').symlink_to(SOURCES / 'click')
        (sources / 'D4-issue.json').write_text('{"tampered": true}')
        runtime = dict(sources=str(sources), control='/c', image='sha256:x', output=str(self.root / 'o'), auth='/a')
        with self.assertRaisesRegex(ValueError, 'issue snapshot changed'):
            prepare.prepare(runtime, 'x', 'D4', 'A', 'codex')

    def test_review_arguments_never_dispatch(self):
        for args, code in ((['--help'], 0), (['--extra'], 2)):
            done = subprocess.run([sys.executable, '-B', str(HERE / 'review.py'), *args], cwd=self.root,
                                  capture_output=True, text=True)
            self.assertEqual(done.returncode, code)
            self.assertNotIn('/control', done.stderr)

    def test_no_budget_machinery(self):
        banned = re.compile(r'BUDGET_EXCEEDED|observed budget|/control/usage\.py|yield_time_ms|cache-inclusive|'
                            r'request_max_retries|CLAUDE_CODE_MAX_RETRIES|observed-openai|input_limit=plan')
        for path in HERE.iterdir():
            if path.suffix in ('.py', '.txt', '.toml', '.json', '.sh') and not path.name.startswith('test_'):
                self.assertIsNone(banned.search(path.read_text()), path.name)


@unittest.skipUnless(IMAGE, 'APPARATUS_IMAGE not set')
class Container(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name).resolve()
        for name in ('work/.devlyn', 'home/.codex', 'home/.claude', 'auth', 'control'):
            (self.root / name).mkdir(parents=True)
        (self.root / 'work/.devlyn/caller.json').write_text('{}')
        for name in ('claude.json', 'codex.json'):
            (self.root / 'auth' / name).write_text('{}')

    def tearDown(self):
        subprocess.run('docker ps -aq --filter label=devlyn.task=0222 | xargs -r docker rm -f', shell=True,
                       capture_output=True)
        self.temp.cleanup()

    def run_cell(self, argv, wall):
        out = self.root / 'cell'
        out.mkdir()
        plan = dict(name='t', work=str(self.root / 'work'), home=str(self.root / 'home'),
                    control=str(self.root / 'control'), env={}, image=IMAGE, argv=argv, wall_seconds=wall,
                    engine='codex', model='gpt-6-astra', config='codex', arm='A')
        (out / 'plan.json').write_text(json.dumps(plan))
        return cell.run(out, dict(auth=str(self.root / 'auth'), scratch=str(self.root)))

    def test_hang_wall_kills_setsid_term_ignoring_descendant(self):
        record = self.run_cell(['sh', '-c', 'setsid sh -c "trap \'\' TERM; sleep 600" & sleep 600'], 3)
        self.assertEqual((record['owner_status'], record['teardown']), ('HANG_TIMEOUT', 'CLEAN'))
        self.assertEqual(subprocess.run('docker ps -aq --filter label=devlyn.task=0222', shell=True,
                                        capture_output=True, text=True).stdout.strip(), '')

    def test_nonzero_exit_is_recorded_not_raised(self):
        record = self.run_cell(['sh', '-c', 'exit 7'], 30)
        self.assertEqual((record['owner_status'], record['teardown']), ('EXITED_NONZERO', 'CLEAN'))

    def test_teardown_failure_is_reported(self):
        real = cell.docker

        def failing(*args, **kwargs):
            if args[0] == 'rm':
                raise subprocess.SubprocessError('injected rm failure')
            return real(*args, **kwargs)
        with mock.patch.object(cell, 'docker', failing):
            record = self.run_cell(['true'], 30)
        self.assertEqual(record['teardown'], 'FAILED')

    @unittest.skipUnless(CONTROL, 'APPARATUS_CONTROL not set')
    def test_reviewer_failure_is_recorded_and_more_calls_allowed(self):
        work = self.root / 'repo'
        work.mkdir()
        git(work, 'init', '-q', '-b', 'main')
        git(work, 'config', 'user.email', 'x@y'), git(work, 'config', 'user.name', 'x')
        (work / 'a.py').write_text('x\n')
        git(work, 'add', '-A'), git(work, 'commit', '-qm', 'base')
        (work / '.devlyn').mkdir()
        (work / '.devlyn/caller.json').write_text(json.dumps(dict(
            request='r', allowed=['a.py'], review_files=['a.py'], base_sha=git(work, 'rev-parse', 'HEAD'))))
        (work / '.git/info/exclude').write_text('.devlyn/\n')
        stub = self.root / 'stub'
        stub.mkdir()
        (stub / 'claude').write_text('#!/bin/sh\nexit 124\n')
        (stub / 'claude').chmod(0o755)
        base = ['docker', 'run', '--rm', '--network', 'none', '--mount', f'type=bind,src={work},dst=/work',
                '--mount', f'type=bind,src={CONTROL},dst=/control,readonly', '--mount', f'type=bind,src={stub},dst=/stub,readonly',
                '--mount', f'type=bind,src={self.root}/auth/claude.json,dst=/credentials/claude.json,readonly',
                '--env', 'PATH=/stub:/usr/local/bin:/usr/bin:/bin', '--env', 'DEVLYN_REVIEWER=claude:x:high',
                '--env', 'HOME=/tmp', '-w', '/work', IMAGE, 'python3', '/control/review.py']
        for _ in range(2):
            self.assertNotEqual(subprocess.run(base, capture_output=True).returncode, 0)
        for call in ('call-1', 'call-2'):
            result = json.loads((work / '.devlyn/reviews' / call / 'result.json').read_text())
            self.assertEqual((result['exit_code'], result['usage']), (124, 'UNKNOWN'))

    @unittest.skipUnless(CONTROL, 'APPARATUS_CONTROL not set')
    def test_f_roles_resolve_under_published_role_config(self):
        routes = json.loads((HERE / 'tasks.json').read_text())['routes']
        for config in ('claude', 'codex'):
            work = self.root / config
            (work / '.devlyn').mkdir(parents=True)
            (work / '.devlyn/engines.json').write_text(json.dumps(dict(roles=routes[config]['F_roles'])))
            done = subprocess.run(['docker', 'run', '--rm', '--network', 'none', '--mount',
                                   f'type=bind,src={self.root},dst=/w', '--mount', f'type=bind,src={CONTROL},dst=/control,readonly',
                                   '--env', 'HOME=/w/home', IMAGE, 'python3',
                                   '/control/devlyn-cli/package/config/skills/_shared/role-config.py',
                                   '--workdir', f'/w/{config}', '--default-engine', config], capture_output=True, text=True)
            self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
            roles = json.loads(done.stdout)['roles']
            for role, entry in routes[config]['F_roles'].items():
                self.assertEqual(roles[role]['engine'], entry['engine'])
                self.assertEqual(roles[role]['model_requested'], entry.get('model'))

    @unittest.skipUnless(SOURCES.exists() and CONTROL, 'registered sources or APPARATUS_CONTROL absent')
    def test_d4_file_beside_package_breaks_collection_but_package_file_does_not(self):
        codes = []
        for relative in ('tests/test_utils.py', 'tests/test_utils/test_fifo_regression.py'):
            work = self.root / relative.replace('/', '_')
            subprocess.run(['git', 'clone', '-q', str(SOURCES / 'click'), str(work)], check=True)
            (work / relative).write_text('def test_ok():\n    assert True\n')
            codes.append(subprocess.run(['docker', 'run', '--rm', '--network', 'none', '--mount',
                                         f'type=bind,src={work},dst=/work', '--mount',
                                         f'type=bind,src={CONTROL},dst=/control,readonly',
                                         '--env', 'PYTHONPATH=/work/src:/control/python', '-w', '/work', IMAGE,
                                         'python', '-m', 'pytest', '-q', '--collect-only', 'tests'],
                                        capture_output=True, text=True))
        self.assertEqual(codes[0].returncode, 2)
        self.assertIn('import file mismatch', codes[0].stdout + codes[0].stderr)
        self.assertEqual(codes[1].returncode, 0, codes[1].stdout[-2000:])


if __name__ == '__main__':
    unittest.main()
