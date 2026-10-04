"""Model-free tests of the 0231 apparatus: python3 -B -m unittest discover -s autoresearch/experiments/0231 -p 'test_*.py'.

Container cases need APPARATUS_IMAGE (the devlyn-0231 image id) and APPARATUS_CONTROL (the built control tree).
"""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent


def load(name):
    spec = importlib.util.spec_from_file_location(name + 'test0231', HERE / f'{name}.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


traces, usage, locate, decide, quota = (load(n) for n in ('trace_usage', 'record_usage', 'locate', 'decide', 'quota'))
USAGE = dict(input_tokens=100, cached_input_tokens=40, cache_write_input_tokens=0, output_tokens=7, reasoning_output_tokens=2)


def write_trace(root, rollout, events, payloads, *, manifest=True):
    folder = root / f'trace-t-{rollout}'
    (folder / 'payloads').mkdir(parents=True)
    if manifest:
        (folder / 'manifest.json').write_text(json.dumps(dict(schema_version=1, rollout_id=rollout, root_thread_id=rollout,
                                                               raw_event_log='trace.jsonl', payloads_dir='payloads')))
    for name, value in payloads.items():
        (folder / 'payloads' / name).write_text(json.dumps(value))
    (folder / 'trace.jsonl').write_text(''.join(line if isinstance(line, str) else json.dumps(dict(payload=line)) + '\n'
                                                for line in events))
    return folder


def ref(name):
    return dict(path=f'payloads/{name}')


def inference(call, thread, model='gpt-6-astra', response='r.json'):
    return [dict(type='inference_started', inference_call_id=call, thread_id=thread, model=model),
            dict(type='inference_completed', inference_call_id=call, response_payload=ref(response))]


class Traces(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root)

    def test_complete_rollout_counts_once_and_reproduces_the_footer(self):
        write_trace(self.root, 'R', [dict(type='thread_started', thread_id='R', agent_path='/root', metadata_payload=ref('m.json')),
                                     *inference('c1', 'R'), dict(type='rollout_ended', status='completed')],
                    {'m.json': dict(model='gpt-6-astra'), 'r.json': dict(token_usage=USAGE)})
        measured = traces.usage(self.root)
        self.assertEqual(measured['gaps'], [])
        self.assertEqual(measured['totals']['gpt-6-astra']['output_tokens'], 7)
        self.assertEqual(measured['rollouts'][0]['footer_tokens'], 100 - 40 + 7)

    def test_child_thread_models_and_usage_are_attributed(self):
        write_trace(self.root, 'R', [*inference('c1', 'R'), *inference('c2', 'K', model='gpt-6-sol', response='k.json'),
                                     dict(type='rollout_ended', status='completed')],
                    {'r.json': dict(token_usage=USAGE), 'k.json': dict(token_usage=USAGE)})
        self.assertEqual(traces.models(self.root), {'R': {'gpt-6-astra'}, 'K': {'gpt-6-sol'}})
        self.assertEqual(set(traces.usage(self.root)['totals']), {'gpt-6-astra', 'gpt-6-sol'})

    def test_interrupted_torn_and_missing_evidence_are_named_gaps_never_zero(self):
        write_trace(self.root, 'R', [*inference('c1', 'R'),
                                     dict(type='inference_started', inference_call_id='c2', thread_id='R', model='gpt-6-astra'),
                                     *inference('c3', 'R', response='absent.json'), '{"torn\n'],
                    {'r.json': dict(token_usage=USAGE)})
        measured = traces.usage(self.root)
        gaps = ' | '.join(measured['gaps'])
        for expected in ('c2 started without completed usage', 'c3 completed without usage', 'torn line', 'rollout did not end'):
            self.assertIn(expected, gaps)
        self.assertEqual(measured['totals']['gpt-6-astra']['output_tokens'], 7)  # the known inference still counts
        self.assertIsNone(measured['rollouts'][0]['footer_tokens'])

    def test_missing_manifest_is_a_gap(self):
        write_trace(self.root, 'R', [], {}, manifest=False)
        self.assertIn('missing or unreadable manifest', traces.usage(self.root)['gaps'][0])


class Binding(unittest.TestCase):
    """Every traced process binds to launch evidence and every launch to a trace (record_usage.codex)."""

    def setUp(self):
        self.out = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.out)
        for name in ('cell/trace', 'cell/work/.devlyn', 'home/.codex/sessions', 'tmp', 'run'):
            (self.out / name).mkdir(parents=True)
        (self.out / 'run/stdout').write_text('')
        self.plan = dict(engine='claude')

    def judge(self, session, footer):
        header = ('OpenAI Codex v0.156.1\n--------\nworkdir: /cell/work\nmodel: gpt-6-astra\nprovider: openai\n'
                  f'approval: never\nsandbox: read-only\nreasoning effort: high\nsession id: {session}\n--------\nuser\nVERIFY\n')
        (self.out / 'cell/work/.devlyn/codex-judge.r0.stderr').write_text(header + f'codex\nPASS\ntokens used\n{footer}\n')

    def trace(self, rollout):
        write_trace(self.out / 'cell/trace', rollout, [*inference('c1', rollout), dict(type='rollout_ended', status='completed')],
                    {'r.json': dict(token_usage=USAGE)})

    def test_plain_root_with_matching_footer_binds(self):
        self.judge('S1', '67')
        self.trace('S1')
        self.assertEqual(usage.codex(self.out, self.plan)[1], [])

    def test_footer_mismatch_unexplained_trace_and_untraced_launch_are_gaps(self):
        self.judge('S1', '68')
        self.trace('S1')
        self.trace('ORPHAN')
        (self.out / 'cell/work/.devlyn/implement.worker-session.0.jsonl').write_text(
            json.dumps(dict(type='thread.started', thread_id='W0')) + '\n')
        gaps = ' | '.join(usage.codex(self.out, self.plan)[1])
        self.assertIn('plain root S1: footer 68 vs trace 67', gaps)
        self.assertIn('trace ORPHAN binds to no launch evidence', gaps)
        self.assertIn('launch W0 has no trace', gaps)



class Identity(unittest.TestCase):
    """Routed models only; an unrouted traced model is a MISMATCH, an unreadable record a gap (UNVERIFIED)."""

    def setUp(self):
        self.cell = load('cell')
        self.out = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.out)
        for name in ('cell/trace', 'cell/work/.devlyn', 'home/.codex/sessions', 'home/.claude/projects', 'tmp', 'run'):
            (self.out / name).mkdir(parents=True)
        init = dict(type='system', subtype='init', model='claude-opus-5-5')
        result = dict(type='result', modelUsage={'claude-opus-5-5': {}})
        (self.out / 'run/stdout').write_text(json.dumps(init) + '\n' + json.dumps(result) + '\n')
        self.plan = dict(config='claude', engine='claude', model='claude-opus-5-5', arm='candidate')

    def test_routed_models_match(self):
        write_trace(self.out / 'cell/trace', 'J', inference('c1', 'J'), {'r.json': dict(token_usage=USAGE)})
        self.assertEqual(self.cell.identity(self.out, self.plan)['status'], 'MATCH')

    def test_an_unrouted_traced_model_is_a_mismatch(self):
        write_trace(self.out / 'cell/trace', 'J', inference('c1', 'J', model='gpt-6-sol'), {'r.json': dict(token_usage=USAGE)})
        result = self.cell.identity(self.out, self.plan)
        self.assertEqual(result['status'], 'MISMATCH')
        self.assertIn('codex gpt-6-sol unrouted (trace J)', result['violations'])

    def test_an_unreadable_judge_result_is_a_gap(self):
        (self.out / 'cell/work/.devlyn/claude-judge.r0.output.json').write_text('{torn')
        result = self.cell.identity(self.out, self.plan)
        self.assertEqual(result['status'], 'UNVERIFIED')
        self.assertTrue(result['gaps'])

class Locator(unittest.TestCase):
    def setUp(self):
        self.out = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.out)
        anchor = self.out / 'cell/work'
        anchor.mkdir(parents=True)
        (self.out / 'tmp').mkdir()
        run = lambda *a, cwd=anchor: subprocess.run(['git', *a], cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()
        self.git = run
        run('init', '-q', '-b', 'main')
        run('-c', 'user.name=t', '-c', 'user.email=t@t', 'commit', '-q', '--allow-empty', '-m', 'base')
        self.base = run('rev-parse', 'HEAD')
        (anchor / 'product.txt').write_text('anchor edit\n')
        (self.out / 'baseline.json').write_text(json.dumps(dict(allocation_sha=self.base)))

    def receipt(self, key, **fields):
        folder = self.out / 'cell/work/.git/devlyn-completion' / key
        folder.mkdir(parents=True)
        (folder / 'receipt.json').write_text(json.dumps(dict(task='t', allocation='owned', **fields)))

    def linked(self, path, files):
        worktree = locate.host(self.out, path)
        worktree.mkdir(parents=True)
        for name, text in files.items():
            (worktree / name).write_text(text)
        return worktree

    def test_anchor_only_when_nothing_was_allocated(self):
        self.assertEqual(locate.select(self.out, json.loads((self.out / 'baseline.json').read_text()))['kind'], 'anchor')

    def test_worktree_tree_when_local_only_completion_bound_no_acceptance(self):
        self.linked('/tmp/task', {'product.txt': 'linked edit\n'})
        self.receipt('a', worktree='/tmp/task', local_only=True)
        selection = locate.locate(self.out)
        self.assertEqual((selection['kind'], selection['path']), ('worktree', 'tmp/task'))
        self.assertEqual((self.out / 'snapshot/product.txt').read_text(), 'linked edit\n')

    def test_valid_acceptance_wins_and_an_invalid_one_falls_back(self):
        worktree = self.linked('/cell/task', {})
        (worktree / '.devlyn/runs/R1').mkdir(parents=True)
        self.git('-c', 'user.name=t', '-c', 'user.email=t@t', 'commit', '-q', '--allow-empty', '-m', 'accepted')
        accepted = self.git('rev-parse', 'HEAD')
        self.receipt('a', worktree='/cell/task', acceptance=dict(task='other', source_sha=accepted, kind='pipeline', run_id='R1'))
        baseline = json.loads((self.out / 'baseline.json').read_text())
        self.assertEqual(locate.select(self.out, baseline)['kind'], 'worktree')
        shutil.rmtree(self.out / 'cell/work/.git/devlyn-completion')
        self.receipt('b', worktree='/cell/task', acceptance=dict(task='t', source_sha=accepted, kind='pipeline', run_id='R1'))
        self.assertEqual(locate.select(self.out, baseline), dict(kind='accepted', sha=accepted,
                         receipt='cell/work/.git/devlyn-completion/b/receipt.json', candidates=locate.select(self.out, baseline)['candidates']))

    def test_owned_allocation_without_a_preserved_tree_stops(self):
        self.receipt('a', worktree='/var/lost')
        with self.assertRaises(locate.LocatorError):
            locate.select(self.out, json.loads((self.out / 'baseline.json').read_text()))


class Decision(unittest.TestCase):
    def setUp(self):
        self.out = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.out)

    def write(self, wall=None, output=None, usage_of=lambda arm: 'COMPLETE', complete_of=lambda name, arm: True):
        for name, task, arm, config, replicate in decide.CELLS:
            (self.out / name).mkdir()
            (self.out / name / 'checks.json').write_text(json.dumps(dict(public=[dict(exit_code=0)])))
            done = complete_of(name, arm)
            (self.out / f'verdict-{name}.json').write_text(json.dumps(dict(
                cell=name, status='COMPLETE' if done else 'PRODUCT_INCOMPLETE', oracle=[dict(id='row', status='PASS')],
                scope_violations=[], assessments=[], owner_status='EXITED_0', usage=usage_of(arm),
                owner_seconds=(wall or {}).get(arm, 100) / 6, output_tokens=(output or {}).get(arm, 600) / 6,
                obligations=dict(satisfied=True))))
        decisions = self.out / 'decisions.json'
        decisions.write_text('{}')
        return decide.main(self.out, decisions)

    def test_wall_path_passes_with_output_inside_its_allowance(self):  # Astra's d1 fixture: W 80/100, O 105/100
        report = self.write(wall=dict(control=100, candidate=80), output=dict(control=100, candidate=105))
        self.assertEqual(report['configs']['claude']['outcome'], 'ADOPTED')
        self.assertTrue(report['configs']['claude']['wall_test'] and not report['configs']['claude']['output_test'])

    def test_boundaries_are_inclusive(self):
        report = self.write(wall=dict(control=100, candidate=85), output=dict(control=100, candidate=110))
        self.assertTrue(report['configs']['codex']['wall_test'])
        report = self.write_fresh(wall=dict(control=100, candidate=86), output=dict(control=100, candidate=75))
        self.assertTrue(report['configs']['codex']['output_test'] and not report['configs']['codex']['wall_test'])

    def write_fresh(self, **kw):
        shutil.rmtree(self.out)
        self.out.mkdir()
        return self.write(**kw)

    def test_partial_control_lower_bound_still_proves_the_output_test(self):  # Astra's d1 fixture: 60 vs >=100
        report = self.write(wall=dict(control=100, candidate=100), output=dict(control=100, candidate=60),
                            usage_of=lambda arm: 'COMPLETE' if arm == 'candidate' else 'PARTIAL')
        self.assertEqual(report['configs']['claude']['outcome'], 'ADOPTED')

    def test_incomplete_candidate_usage_is_inconclusive(self):
        report = self.write(wall=dict(control=100, candidate=50), usage_of=lambda arm: 'PARTIAL' if arm == 'candidate' else 'COMPLETE')
        self.assertEqual(report['configs']['claude']['outcome'], 'INCONCLUSIVE')

    def test_counts_rule_admits_symmetric_discordance_and_rejects_a_net_loss(self):
        def symmetric(name, arm):  # D4-claude: candidate wins replicate 1, control wins replicate 2
            return not (('D4-claude' in name) and ((arm == 'control') == name.endswith('r1')))
        self.assertEqual(self.write(wall=dict(control=100, candidate=50), complete_of=symmetric)['configs']['claude']['outcome'], 'ADOPTED')
        loss = lambda name, arm: not ('D4-claude' in name and arm == 'candidate' and name.endswith('r1'))
        self.assertEqual(self.write_fresh(wall=dict(control=100, candidate=50), complete_of=loss)['configs']['claude']['outcome'], 'REJECTED')

    def test_a_stop_row_blocks_the_computation(self):
        self.write()
        first = decide.CELLS[0][0]
        verdict = json.loads((self.out / f'verdict-{first}.json').read_text())
        (self.out / f'verdict-{first}.json').write_text(json.dumps(dict(verdict, status='STOP')))
        with self.assertRaises(ValueError):
            decide.main(self.out, self.out / 'decisions.json')


class Quota(unittest.TestCase):
    def test_only_native_error_fields_count(self):
        root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, root)
        prose = root / 'prose.jsonl'
        prose.write_text(json.dumps(dict(type='item.completed', item=dict(type='agent_message', text='the reviewer hit a rate limit (429)'))) + '\n')
        native = root / 'native.jsonl'
        native.write_text(json.dumps(dict(type='result', is_error=True, api_error_status=429, result="You've hit your weekly limit")) + '\n'
                          + json.dumps(dict(type='item.completed', item=dict(type='error', message='You have hit your usage limit'))) + '\n')
        self.assertEqual(quota.scan([prose], root), [])
        self.assertEqual([h['kind'] for h in quota.scan([native], root)], ['claude 429 result', 'codex error item'])



def archived_run(out, shared_source, codex_mode='pass'):
    """A real candidate run, model-free: the installed scripts drive PLAN -> IMPLEMENT -> VERIFY (MECHANICAL, seal,
    stub judges, merge) -> finish gate -> FINAL_REPORT -> archive, in a repository that commits its skills like a cell."""
    import hashlib
    import runpy
    work = out / 'cell/work'
    devlyn = work / '.devlyn'
    work.mkdir(parents=True)
    git = lambda *a: subprocess.run(['git', '-c', 'user.name=f', '-c', 'user.email=f@f', *a], cwd=work, check=True,
                                    capture_output=True, text=True).stdout.strip()
    git('init', '-q', '-b', 'main')
    shutil.copytree(shared_source.parent, work / '.agents/skills')  # the renderer reads devlyn-resolve/ beside _shared
    (work / '.gitignore').write_text('.devlyn/\n')
    (work / 'source.txt').write_text('original\n')
    git('add', '.')
    git('commit', '-qm', 'base')
    shared = work / '.agents/skills/_shared'
    devlyn.mkdir()
    (devlyn / 'untracked.baseline').write_text(runpy.run_path(str(shared / 'spec-verify-check.py'))['EMPTY_BASELINE'])
    spec = b'# Spec\n\n## Requirements\n\n- source.txt says implemented\n'
    (devlyn / 'spec.md').write_bytes(spec)
    (devlyn / 'pipeline.state.json').write_text(json.dumps({
        'version': '3.0', 'run_id': 'rs-fixture', 'engine': 'claude', 'mode': 'spec', 'base_ref': {'sha': git('rev-parse', 'HEAD')},
        'source': {'type': 'spec', 'spec_path': '.devlyn/spec.md', 'spec_sha256': hashlib.sha256(spec).hexdigest()},
        'untracked_baseline_sha256': None, 'rounds': {'global': 0, 'max_rounds': 4}, 'phases': {}}))
    (devlyn / 'engines.json').write_text(json.dumps({'roles': {'worker': {'engine': 'claude'},
        'primary_judge': {'engine': 'claude', 'model': 'claude-opus-5-5'},
        'pair_judge': {'engine': 'codex', 'model': 'gpt-6-astra', 'effort': 'high'}}}))
    stubs = out / 'bin'
    stubs.mkdir()
    for engine in ('claude', 'codex'):
        (stubs / engine).write_text(runpy.run_path(str(shared / 'verify-judges.py'))['STUB'])
        (stubs / engine).chmod(0o755)
    (out / 'codex-home').mkdir()
    (out / 'codex-home/models_cache.json').write_text(json.dumps({'client_version': '9.9.9', 'models': [
        {'slug': 'gpt-6-astra', 'supported_reasoning_levels': [{'effort': 'medium'}, {'effort': 'high'}]}]}))
    (out / 'stub-state/barrier').mkdir(parents=True)
    env = {k: v for k, v in os.environ.items() if not k.startswith('DEVLYN_INVOCATION_') and k != 'CLAUDECODE'}
    env.update(PATH=f'{stubs}{os.pathsep}{env["PATH"]}', CODEX_HOME=str(out / 'codex-home'), PYTHONDONTWRITEBYTECODE='1',
               STUB_DIR=str(out / 'stub-state'), STUB_CODEX=codex_mode)
    run = lambda script, *a: subprocess.run([sys.executable, str(shared / script), *a], cwd=work, env=env, capture_output=True, text=True)
    spw = lambda *a: run('state-phase-write.py', '--devlyn-dir', '.devlyn', *a)
    spw('--freeze-roles', '--default-engine', 'claude')
    spw('--phase', 'plan', 'spawn', '--round', '0')
    (devlyn / 'plan.md').write_text('<!-- devlyn:authorized-surface -->\n# Files\n```json\n{"authorized_surface":["source.txt"]}\n```\n')
    spw('--phase', 'plan', 'complete', '--verdict', 'PASS')
    spw('--phase', 'implement', 'spawn', '--round', '0', '--engine', 'claude')
    (work / 'source.txt').write_text('implemented\n')
    git('commit', '-qam', 'chore(pipeline): implement')
    spw('--phase', 'implement', 'transition', '--verdict', 'PASS', '--next-phase', 'verify', '--next-round', '0', '--next-engine', 'claude')
    for step in (('spec-verify-check.py',), ('spec-verify-check.py', '--seal'), ('verify-judges.py', '--devlyn-dir', str(devlyn))):
        run(*step)
    spw('--phase', 'verify', 'complete')
    state = json.loads((devlyn / 'pipeline.state.json').read_text())
    if state['phases']['verify']['verdict'] == 'NEEDS_WORK':  # end on an exhausted repair budget, as a real run can
        state['rounds'] = {'global': 1, 'max_rounds': 1}
        (devlyn / 'pipeline.state.json').write_text(json.dumps(state))
        spw('--phase', 'implement', 'spawn', '--round', '1', '--triggered-by', 'verify', '--engine', 'claude')
    spw('--phase', 'final_report', 'spawn', '--round', '0')
    run('finish-gate.py')
    spw('--phase', 'final_report', 'complete')
    run('archive_run.py', '--devlyn-dir', '.devlyn')
    (out / 'plan.json').write_text(json.dumps(dict(arm='candidate')))
    (out / 'snapshot.json').write_text(json.dumps(dict(kind='anchor', path='cell/work')))
    return work


@unittest.skipUnless(os.environ.get('APPARATUS_CONTROL'), 'needs the built control tree (the candidate package)')
class Obligations(unittest.TestCase):
    def setUp(self):
        self.meter = load('obligations')
        self.shared = Path(os.environ['APPARATUS_CONTROL']) / 'packages/candidate/package/config/skills/_shared'
        self.out = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.out)

    def test_reviewed_runs_satisfy_and_a_blocked_judge_does_not(self):
        for mode, verdict, satisfied in (('pass', 'PASS', True), ('high', 'NEEDS_WORK', True), ('blocked', 'BLOCKED', False)):
            out = self.out / mode
            out.mkdir()
            archived_run(out, self.shared, mode)
            result = self.meter.meter(out)
            self.assertEqual((result['verify_verdict'], result['satisfied']), (verdict, satisfied), f'{mode}: {result}')

    def test_a_change_after_the_seal_or_a_tampered_report_fails(self):
        work = archived_run(self.out, self.shared)
        self.assertTrue(self.meter.meter(self.out)['satisfied'])
        (work / 'source.txt').write_text('changed after review\n')
        self.assertFalse(self.meter.meter(self.out)['checks']['seal_head_is_final_source'])
        (work / 'source.txt').write_text('implemented\n')
        report = next((work / '.devlyn/runs').glob('*/final-report.md'))
        report.write_text(report.read_text() + 'tampered\n')
        self.assertFalse(self.meter.meter(self.out)['checks']['report_bound'])

@unittest.skipUnless(os.environ.get('APPARATUS_IMAGE') and os.environ.get('APPARATUS_CONTROL'), 'container cases need the image and control tree')
class Cells(unittest.TestCase):
    """Prepared cells for each arm and config, then probes inside the cell container (no model call, no network)."""

    @classmethod
    def setUpClass(cls):
        cls.prepare = load('prepare')
        cls.root = Path(tempfile.mkdtemp(prefix='0231-cells-'))
        cls.runtime = dict(sources=str(HERE.parents[2] / '.devlyn/0206'), control=os.environ['APPARATUS_CONTROL'],
                           image=os.environ['APPARATUS_IMAGE'], output=str(cls.root / 'out'), scratch=str(cls.root),
                           auth=str(cls.root / 'auth'))

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.root)

    def probe(self, out, script):
        control = Path(self.runtime['control'])
        argv = ['docker', 'run', '--rm', '--network', 'none', '--read-only', '--cap-drop', 'ALL', '--security-opt',
                'no-new-privileges', '--user', '501:501', '--mount', f'type=bind,src={out / "cell"},dst=/cell',
                '--mount', f'type=bind,src={out / "tmp"},dst=/tmp', '--mount', f'type=bind,src={out / "home"},dst=/home/participant',
                '--mount', f'type=bind,src={control / "public"},dst=/control,readonly',
                '--mount', f'type=bind,src={out / "harness"},dst=/harness,readonly']
        for key, value in json.loads((out / 'plan.json').read_text())['env'].items():
            argv += ['-e', f'{key}={value}']
        done = subprocess.run([*argv, '-w', '/cell/work', self.runtime['image'], 'bash', '-c', script],
                              capture_output=True, text=True, timeout=600)
        return done.returncode, done.stdout + done.stderr

    def test_each_arm_and_config_installs_its_own_package_and_allocates_from_the_mirror(self):
        for config, skills in (('claude', '.claude/skills'), ('codex', '.agents/skills')):
            for arm in ('control', 'candidate'):
                out = self.prepare.prepare(self.runtime, f'smoke-{config}-{arm}', 'SMOKE', arm, config)
                baseline = json.loads((out / 'baseline.json').read_text())
                self.assertTrue((out / 'cell/work' / skills / 'devlyn-resolve/SKILL.md').is_file())
                self.assertEqual((out / 'cell/work/.task/goal.txt').read_text().count('/harness/caller.json'), 1)
                code, text = self.probe(out, f'''set -e
S={skills}/_shared
python3 $S/task-complete.py allocate --repo . --task t --branch task/t --worktree /cell/task-t --repository fysoul17/devlyn-cli --remote origin --base main >/dev/null
test "$(git -C /cell/task-t rev-parse HEAD)" = {baseline["allocation_sha"]}
cmp -s .task/goal.txt /cell/task-t/.task/goal.txt
if git -C /cell/task-t push origin HEAD:refs/heads/x 2>/dev/null; then echo PUSHED; exit 1; fi
if git ls-remote git@github.com:other/repo.git 2>/dev/null; then echo FOREIGN; exit 1; fi
test -z "$(ls -A /control/autoresearch)" && test ! -e /install && test ! -e /control/packages
cd /cell/task-t && python3 $S/resolve-bootstrap.py --goal-file .task/goal.txt --role-config /harness/roles.json --max-rounds 4 >/dev/null
echo OK''')
                self.assertEqual((code, text.strip().splitlines()[-1] if text.strip() else ''), (0, 'OK'), f'{config}/{arm}: {text}')

    def test_declared_checkers_read_the_linked_task_source(self):
        cases = (('D4', 'claude', '.claude/skills', 'pallets/click', '''cd /cell/task-t
python3 -c "import click; assert click.__file__.startswith('/cell/task-t/src/')"
if (cd /tmp && python3 -c "import click" 2>/dev/null); then echo SHADOW; exit 1; fi
mypy >/dev/null && pyright --ignoreexternal --verifytypes click >/dev/null
echo 'x_planted: int = "s"' >> src/click/core.py
if mypy >/dev/null 2>&1; then echo MYPY-MISSED; exit 1; fi
if pyright src/click/core.py >/dev/null 2>&1; then echo PYRIGHT-MISSED; exit 1; fi'''),
                 ('D3', 'codex', '.agents/skills', 'tj/commander.js', '''cd /cell/task-t
npm run -s check:type >/dev/null && eslint . >/dev/null
echo 'const planted: number = "s";' > lib/planted.ts
if npm run -s check:type >/dev/null 2>&1; then echo TSC-MISSED; exit 1; fi'''))
        for task, config, skills, repository, script in cases:
            out = self.prepare.prepare(self.runtime, f'tools-{task}', task, 'control', config)
            code, text = self.probe(out, f'''set -e
python3 {skills}/_shared/task-complete.py allocate --repo . --task t --branch task/t --worktree /cell/task-t --repository {repository} --remote origin --base main >/dev/null
{script}
echo OK''')
            self.assertEqual((code, text.strip().splitlines()[-1] if text.strip() else ''), (0, 'OK'), f'{task}: {text}')

    def test_wrong_arm_is_refused(self):
        with self.assertRaises(ValueError):
            self.prepare.prepare(self.runtime, 'bad', 'SMOKE', 'F', 'claude')


if __name__ == '__main__':
    unittest.main()
