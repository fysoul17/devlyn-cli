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
    """Usage on the shared inventory: bound once, attempted calls inventoried, every disagreement a named gap."""

    def setUp(self):
        self.out = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.out)
        for name in ('cell/trace', 'cell/work/.devlyn', 'home/.codex/sessions', 'home/.claude/projects', 'tmp', 'run'):
            (self.out / name).mkdir(parents=True)
        init = dict(type='system', subtype='init', model='claude-opus-5-5', session_id='OWNER')
        result = dict(type='result', session_id='OWNER', modelUsage={'claude-opus-5-5': dict(outputTokens=3)})
        (self.out / 'run/stdout').write_text(json.dumps(init) + '\n' + json.dumps(result) + '\n')
        (self.out / 'plan.json').write_text(json.dumps(dict(engine='claude', config='claude', model='claude-opus-5-5', arm='candidate')))

    def judge(self, session, footer, round_=0):
        header = ('OpenAI Codex v0.156.1\n--------\nworkdir: /cell/work\nmodel: gpt-6-astra\nprovider: openai\n'
                  f'approval: never\nsandbox: read-only\nreasoning effort: high\nsession id: {session}\n--------\nuser\nVERIFY\n')
        (self.out / f'cell/work/.devlyn/codex-judge.r{round_}.stderr').write_text(header + f'codex\nPASS\ntokens used\n{footer}\n')

    def trace(self, rollout, folder=None):
        write_trace(self.out / 'cell/trace' / (folder or ''), rollout,
                    [dict(type='thread_started', thread_id=rollout, agent_path='/root', metadata_payload=ref('m.json')),
                     *inference('c1', rollout), dict(type='rollout_ended', status='completed')],
                    {'m.json': dict(model='gpt-6-astra'), 'r.json': dict(token_usage=USAGE)})

    def gaps(self):
        return ' | '.join(usage.record(self.out)['gaps'])

    def test_plain_root_with_matching_footer_is_complete(self):
        self.judge('S1', '67')
        self.trace('S1')
        recorded = usage.record(self.out)
        self.assertEqual((recorded['completeness'], recorded['output_tokens']), ('COMPLETE', 3 + 7), recorded['gaps'])

    def test_footer_mismatch_unexplained_trace_and_untraced_launch_are_gaps(self):
        self.judge('S1', '68')
        self.trace('S1')
        self.trace('ORPHAN')
        (self.out / 'cell/work/.devlyn/implement.worker-session.0.jsonl').write_text(
            json.dumps(dict(type='thread.started', thread_id='W0')) + '\n')
        gaps = self.gaps()
        for expected in ('plain root S1: footer 68 vs trace 67', 'trace ORPHAN binds to no launch evidence', 'launch W0 has no trace'):
            self.assertIn(expected, gaps)

    def test_a_duplicated_trace_counts_once(self):
        self.judge('S1', '67')
        self.trace('S1')
        self.trace('S1', folder='copy')
        recorded = usage.record(self.out)
        self.assertEqual((recorded['completeness'], recorded['output_tokens']), ('COMPLETE', 10), recorded['gaps'])

    def test_a_dispatched_judge_whose_result_vanished_is_a_gap_and_its_transcript_counts(self):
        (self.out / 'cell/work/.devlyn/verify-judge.r0.dispatch.json').write_text(json.dumps(dict(roles=dict(
            primary_judge=dict(decision='dispatch', engine='claude')))))
        (self.out / 'home/.claude/projects/x').mkdir()
        (self.out / 'home/.claude/projects/x/judge.jsonl').write_text(json.dumps(dict(type='assistant', sessionId='JUDGE', message=dict(
            id='m1', model='claude-opus-5-5', usage=dict(output_tokens=7)))) + '\n')
        recorded = usage.record(self.out)
        self.assertEqual((recorded['completeness'], recorded['output_tokens']), ('PARTIAL', 3 + 7))
        self.assertIn('dispatched claude primary_judge r0 left no result', ' | '.join(recorded['gaps']))

    def test_an_older_run_does_not_mask_a_newer_runs_missing_result(self):
        devlyn = self.out / 'cell/work/.devlyn'
        older = devlyn / 'runs/R1'
        older.mkdir(parents=True)
        for folder, run in ((older, 'R1'), (devlyn, 'R2')):
            (folder / 'pipeline.state.json').write_text(json.dumps(dict(run_id=run)))
            (folder / 'verify-judge.r0.dispatch.json').write_text(json.dumps(dict(roles=dict(
                primary_judge=dict(decision='dispatch', engine='claude')))))
        (older / 'claude-judge.r0.output.json').write_text(json.dumps(dict(type='result', session_id='J1',
                                                                           modelUsage={'claude-opus-5-5': dict(outputTokens=7)})))
        gaps = self.gaps()
        self.assertIn('run R2: dispatched claude primary_judge r0 left no result', gaps)
        self.assertNotIn('run R1', gaps)

    def test_rollout_counters_must_all_agree(self):
        self.judge('S1', '67')
        self.trace('S1')
        rollout = self.out / 'home/.codex/sessions/r.jsonl'
        rollout.write_text(json.dumps(dict(type='session_meta', payload=dict(id='S1'))) + '\n' + json.dumps(dict(
            type='event_msg', payload=dict(type='token_count', info=dict(total_token_usage=dict(USAGE, input_tokens=999))))) + '\n')
        self.assertIn('thread S1: rollout counters', self.gaps())

    def test_an_inference_on_an_undeclared_thread_is_a_gap(self):
        self.judge('S1', '67')
        write_trace(self.out / 'cell/trace', 'S1', [dict(type='thread_started', thread_id='S1', agent_path='/root', metadata_payload=ref('m.json')),
                                                    *inference('c1', 'GHOST'), dict(type='rollout_ended', status='completed')],
                    {'m.json': dict(model='gpt-6-astra'), 'r.json': dict(token_usage=USAGE)})
        self.assertIn('undeclared thread GHOST', self.gaps())


class Identity(unittest.TestCase):
    """Each seat's native model and Codex effort against the route; usage-only loss never makes identity UNVERIFIED."""

    def setUp(self):
        self.cell = load('cell')
        self.out = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.out)
        for name in ('cell/trace', 'cell/work/.devlyn', 'home/.codex/sessions', 'home/.claude/projects', 'tmp', 'run'):
            (self.out / name).mkdir(parents=True)

    def configured(self, rollout, thread, model, effort, path='/root'):
        return [dict(type='thread_started', thread_id=thread, agent_path=path, metadata_payload=ref(f'{thread}.json')),
                dict(type='protocol_event_observed', event_type='session_configured', event_payload=ref(f'{thread}-c.json'))], {
            f'{thread}.json': dict(model=model), f'{thread}-c.json': dict(thread_id=thread, model=model, reasoning_effort=effort)}

    def codex_cell(self, worker_model, worker_effort):
        (self.out / 'run/stdout').write_text(json.dumps(dict(type='thread.started', thread_id='OWN')) + '\n')
        events, payloads = self.configured('OWN', 'OWN', 'gpt-6-astra', 'high')
        write_trace(self.out / 'cell/trace', 'OWN', [*events, dict(type='rollout_ended', status='completed')], payloads)
        events, payloads = self.configured('WRK', 'WRK', worker_model, worker_effort)
        write_trace(self.out / 'cell/trace', 'WRK', [*events, dict(type='rollout_ended', status='completed')], payloads)
        (self.out / 'cell/work/.devlyn/implement.worker-session.0.jsonl').write_text(json.dumps(dict(type='thread.started', thread_id='WRK')) + '\n')
        return dict(config='codex', engine='codex', model='gpt-6-astra', arm='candidate')

    def test_the_registered_worker_matches_and_a_seat_swap_does_not(self):
        self.assertEqual(self.cell.identity(self.out, self.codex_cell('gpt-6-sol', 'high'))['status'], 'MATCH')
        shutil.rmtree(self.out / 'cell/trace')
        (self.out / 'cell/trace').mkdir()
        result = self.cell.identity(self.out, self.codex_cell('gpt-6-astra', 'low'))
        self.assertEqual(result['status'], 'MISMATCH')
        self.assertTrue(any(v.startswith('worker WRK ran gpt-6-astra/low') for v in result['violations']), result['violations'])

    def test_an_inference_on_another_model_is_a_mismatch(self):
        plan = self.codex_cell('gpt-6-sol', 'high')
        shutil.rmtree(self.out / 'cell/trace')
        (self.out / 'cell/trace').mkdir()
        events, payloads = self.configured('OWN', 'OWN', 'gpt-6-astra', 'high')
        write_trace(self.out / 'cell/trace', 'OWN', [*events, *inference('c1', 'OWN', model='gpt-6-sol')],
                    dict(payloads, **{'r.json': dict(token_usage=USAGE)}))
        events, payloads = self.configured('WRK', 'WRK', 'gpt-6-sol', 'high')
        write_trace(self.out / 'cell/trace', 'WRK', events, payloads)
        self.assertTrue(any('owner inference c1 ran gpt-6-sol' in v for v in self.cell.identity(self.out, plan)['violations']))

    def test_a_lost_owner_trace_falls_back_to_its_rollout(self):
        plan = self.codex_cell('gpt-6-sol', 'high')
        shutil.rmtree(self.out / 'cell/trace/trace-t-OWN')
        (self.out / 'home/.codex/sessions/own.jsonl').write_text(json.dumps(dict(type='session_meta', payload=dict(id='OWN'))) + '\n'
            + json.dumps(dict(type='turn_context', payload=dict(model='gpt-6-astra', effort='high'))) + '\n')
        self.assertEqual(self.cell.identity(self.out, plan)['status'], 'MATCH')

    def test_an_unbound_codex_process_is_a_mismatch(self):
        plan = self.codex_cell('gpt-6-sol', 'high')
        events, payloads = self.configured('STRAY', 'STRAY', 'gpt-6-sol', 'high')
        write_trace(self.out / 'cell/trace', 'STRAY', events, payloads)
        self.assertIn('unbound Codex process STRAY', self.cell.identity(self.out, plan)['violations'])

    def test_an_empty_judge_capture_with_a_routed_transcript_stays_verified(self):
        init = dict(type='system', subtype='init', model='claude-opus-5-5', session_id='OWNER')
        (self.out / 'run/stdout').write_text(json.dumps(init) + '\n' + json.dumps(dict(type='result', session_id='OWNER', modelUsage={'claude-opus-5-5': {}})) + '\n')
        (self.out / 'cell/work/.devlyn/claude-judge.r0.output.json').write_text('')
        (self.out / 'home/.claude/projects/x').mkdir()
        (self.out / 'home/.claude/projects/x/j.jsonl').write_text(json.dumps(dict(type='assistant', sessionId='J', message=dict(
            id='m', model='claude-opus-5-5', usage=dict(output_tokens=1)))) + '\n')
        self.assertEqual(self.cell.identity(self.out, dict(config='claude', engine='claude', model='claude-opus-5-5', arm='candidate'))['status'], 'MATCH')

    def test_an_owner_without_any_evidence_is_unknown(self):
        (self.out / 'run/stdout').write_text('')
        self.assertEqual(self.cell.identity(self.out, dict(config='claude', engine='claude', model='claude-opus-5-5', arm='control'))['status'], 'UNKNOWN')


class Locator(unittest.TestCase):
    def setUp(self):
        self.out = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.out)
        anchor = self.out / 'cell/work'
        anchor.mkdir(parents=True)
        (self.out / 'tmp').mkdir()
        self.git = lambda *a, cwd=anchor: subprocess.run(['git', '-c', 'user.name=t', '-c', 'user.email=t@t', *a], cwd=cwd,
                                                         check=True, capture_output=True, text=True).stdout.strip()
        self.git('init', '-q', '-b', 'main')
        (anchor / '.gitignore').write_text('ignored.log\n')
        (anchor / 'product.txt').write_text('base\n')
        self.git('add', '.')
        self.git('commit', '-q', '-m', 'base')
        self.base = self.git('rev-parse', 'HEAD')
        (anchor / 'product.txt').write_text('anchor edit\n')
        (anchor / 'ignored.log').write_text('noise\n')
        (self.out / 'baseline.json').write_text(json.dumps(dict(allocation_sha=self.base)))

    def linked(self, container_path, edit):
        """A worktree as a container leaves it: registered, with container paths in both Git links."""
        worktree = locate.host(self.out, container_path)
        self.git('worktree', 'add', '-q', '-b', 'task/' + worktree.name, str(worktree), self.base)
        (gitdir,) = [d for d in (self.out / 'cell/work/.git/worktrees').iterdir()
                     if Path((d / 'gitdir').read_text().strip()).resolve() == (worktree / '.git').resolve()]
        (gitdir / 'gitdir').write_text(container_path + '/.git\n')
        (worktree / '.git').write_text(f'gitdir: /cell/work/.git/worktrees/{gitdir.name}\n')
        (worktree / 'product.txt').write_text(edit)
        (worktree / 'ignored.log').write_text('noise\n')
        return worktree

    def receipt(self, key, **fields):
        folder = self.out / 'cell/work/.git/devlyn-completion' / key
        folder.mkdir(parents=True)
        (folder / 'receipt.json').write_text(json.dumps(dict(task='t', allocation='owned', **fields)))
        return folder

    def baseline(self):
        return json.loads((self.out / 'baseline.json').read_text())

    def test_anchor_only_when_nothing_was_allocated_and_ignored_files_stay_out(self):
        selection = locate.locate(self.out)
        self.assertEqual(selection['kind'], 'anchor')
        self.assertEqual(sorted(p.name for p in (self.out / 'snapshot').iterdir()), ['.gitignore', 'product.txt'])

    def test_worktree_tree_when_local_only_completion_bound_no_acceptance(self):
        self.linked('/tmp/task', 'linked edit\n')
        self.receipt('a', worktree='/tmp/task', local_only=True)
        selection = locate.locate(self.out)
        self.assertEqual((selection['kind'], selection['path']), ('worktree', 'tmp/task'))
        self.assertEqual((self.out / 'snapshot/product.txt').read_text(), 'linked edit\n')
        self.assertFalse((self.out / 'snapshot/ignored.log').exists())

    def accepted_run(self, worktree, sha, *, seal_head=None, root=None):
        runs = (root or worktree) / '.devlyn/runs/R1'
        runs.mkdir(parents=True)
        (runs / 'pipeline.state.json').write_text(json.dumps(dict(run_id='R1')))
        (runs / 'source-seal.json').write_text(json.dumps(dict(seal=dict(head=seal_head or sha))))

    def test_acceptance_needs_its_run_and_seal_and_survives_cleanup_through_custody(self):
        worktree = self.linked('/cell/task', 'accepted\n')
        sha = self.git('commit-tree', self.git('write-tree'), '-p', self.base, '-m', 'accepted')
        acceptance = dict(task='t', source_sha=sha, kind='pipeline', run_id='R1')
        self.accepted_run(worktree, sha, seal_head=self.base)  # a seal of another commit binds nothing
        self.receipt('a', worktree='/cell/task', acceptance=acceptance)
        self.assertEqual(locate.select(self.out, self.baseline())['kind'], 'worktree')
        shutil.rmtree(worktree / '.devlyn')
        shutil.rmtree(self.out / 'cell/work/.git/devlyn-completion')
        folder = self.receipt('b', worktree='/cell/task', acceptance=acceptance)
        self.accepted_run(None, sha, root=folder / 'custody')  # cleanup kept the archive in custody
        self.assertEqual(locate.select(self.out, self.baseline())['sha'], sha)

    def test_owned_allocation_without_a_preserved_tree_stops(self):
        self.receipt('a', worktree='/var/lost')
        with self.assertRaises(locate.LocatorError):
            locate.select(self.out, self.baseline())


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
        decisions.write_text(json.dumps(dict(audited=[c[0] for c in decide.CELLS], false_completion=[], adjudicated={},
                                             severe={}, reproduced={})))
        return decide.main(self.out, decisions)

    def test_wall_path_passes_with_output_inside_its_allowance(self):  # Astra's d1 fixture: W 80/100, O 105/100
        report = self.write(wall=dict(control=100, candidate=80), output=dict(control=100, candidate=105))
        self.assertEqual(report['configs']['claude']['outcome'], 'ADOPTED')
        self.assertEqual((report['configs']['claude']['wall_test'], report['configs']['claude']['output_test']), ('proven', 'disproved'))

    def test_boundaries_are_inclusive(self):
        report = self.write(wall=dict(control=100, candidate=85), output=dict(control=100, candidate=110))
        self.assertEqual(report['configs']['codex']['wall_test'], 'proven')
        report = self.write_fresh(wall=dict(control=100, candidate=86), output=dict(control=100, candidate=75))
        self.assertEqual((report['configs']['codex']['output_test'], report['configs']['codex']['wall_test']), ('proven', 'disproved'))

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

    def test_a_partial_control_bound_that_fails_is_unresolved_not_disproved(self):  # Astra apparatus #13
        report = self.write(wall=dict(control=100, candidate=100), output=dict(control=100, candidate=120),
                            usage_of=lambda arm: 'COMPLETE' if arm == 'candidate' else 'PARTIAL')
        self.assertEqual(report['configs']['claude']['outcome'], 'INCONCLUSIVE')

    def test_missing_audits_or_severe_dispositions_block_the_computation(self):
        self.write()
        decisions = json.loads((self.out / 'decisions.json').read_text())
        (self.out / 'decisions.json').write_text(json.dumps(dict(decisions, audited=decisions['audited'][1:])))
        with self.assertRaises(ValueError):
            decide.main(self.out, self.out / 'decisions.json')
        first = decide.CELLS[0][0]
        verdict = json.loads((self.out / f'verdict-{first}.json').read_text())
        verdict['assessments'] = [dict(route=dict(engine='codex'), complete=True, severe=1, severe_findings=[dict(severity='HIGH')])]
        (self.out / f'verdict-{first}.json').write_text(json.dumps(verdict))
        (self.out / 'decisions.json').write_text(json.dumps(decisions))
        with self.assertRaises(ValueError):
            decide.main(self.out, self.out / 'decisions.json')

    def test_a_reproduced_defect_needs_its_witness_applied_to_the_paired_control(self):
        self.write(wall=dict(control=100, candidate=60), output=dict(control=100, candidate=60))
        candidate, control = next(c for c in decide.CELLS if c[2] == 'candidate'), None
        control = next(c for c in decide.CELLS if c[1:4:2] == candidate[1:4:2] and c[2] == 'control' and c[4] == candidate[4])
        verdict = json.loads((self.out / f'verdict-{candidate[0]}.json').read_text())
        verdict['assessments'] = [dict(route=dict(engine='codex'), complete=False, severe=1, severe_findings=[dict(severity='HIGH')])]
        (self.out / f'verdict-{candidate[0]}.json').write_text(json.dumps(verdict))
        decisions = json.loads((self.out / 'decisions.json').read_text())
        decisions['severe'] = {candidate[0]: {'codex:0': dict(disposition='reproduced')}}
        (self.out / 'decisions.json').write_text(json.dumps(decisions))
        with self.assertRaises(ValueError):  # a reproduced finding without a witness
            decide.main(self.out, self.out / 'decisions.json')
        decisions['severe'][candidate[0]]['codex:0']['witness'] = 'W1'
        for trees, outcome in (({candidate[0]: True}, 'REJECTED'), ({candidate[0]: True, control[0]: False}, 'REJECTED'),
                               ({candidate[0]: True, control[0]: True}, 'ADOPTED')):
            decisions['witnesses'] = {'W1': trees}
            (self.out / 'decisions.json').write_text(json.dumps(decisions))
            self.assertEqual(decide.main(self.out, self.out / 'decisions.json')['configs'][candidate[3]]['outcome'], outcome, trees)

    def test_a_stop_row_blocks_the_computation(self):
        self.write()
        first = decide.CELLS[0][0]
        verdict = json.loads((self.out / f'verdict-{first}.json').read_text())
        (self.out / f'verdict-{first}.json').write_text(json.dumps(dict(verdict, status='STOP')))
        with self.assertRaises(ValueError):
            decide.main(self.out, self.out / 'decisions.json')


class Quota(unittest.TestCase):
    def test_only_explicit_native_shapes_count(self):
        root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, root)
        prose = root / 'prose.jsonl'
        prose.write_text(json.dumps(dict(type='item.completed', item=dict(type='agent_message', text='the reviewer hit a rate limit (429)'))) + '\n'
                         + json.dumps(dict(type='item.completed', item=dict(type='error', message='upstream gateway responded HTTP 429'))) + '\n')
        native = root / 'native.jsonl'
        native.write_text(json.dumps(dict(type='result', is_error=True, api_error_status=429, result="You've hit your weekly limit")) + '\n'
                          + json.dumps(dict(type='item.completed', item=dict(type='error', message="You've hit your usage limit"))) + '\n'
                          + json.dumps(dict(type='result', is_error=True, api_error_status=401, result='OAuth token expired')) + '\n')
        stderr = root / 'codex-judge.r0.stderr'
        stderr.write_text("OpenAI Codex v0.156.1\nERROR: You've hit your usage limit. Try again later.\n")
        self.assertEqual(quota.scan([prose], root), [])
        self.assertEqual([(h['fault'], h['kind']) for h in quota.scan([native, stderr], root)],
                         [('limit', 'claude limit result'), ('limit', 'codex usage limit'), ('auth', 'claude authentication result'),
                          ('limit', 'codex usage limit (stderr)')])


class Assessor(unittest.TestCase):
    def test_an_invalid_answer_is_no_verdict(self):
        assess = load('assess')
        for answer in ('{}', '{"complete": true}', '{"complete": "unknown"}', '{"complete": true, "findings": "none"}', 'no json'):
            self.assertIsNone(assess.valid(answer), answer)
        self.assertEqual(assess.valid('{"complete": false, "findings": [{"severity": "HIGH"}]}')['complete'], False)


    def test_uncertain_container_teardown_raises(self):
        assess = load('assess')
        daemon_down = subprocess.CompletedProcess([], 1, '', 'Cannot connect to the Docker daemon')
        original = assess.subprocess.run
        assess.subprocess.run = lambda *a, **k: daemon_down
        try:
            with self.assertRaises(RuntimeError):
                assess.reap('devlyn-0231-assess-x')
        finally:
            assess.subprocess.run = original


class Venue(unittest.TestCase):
    """Preflight and evidence collection fail closed and visibly."""

    def setUp(self):
        self.run_cell = load('run_cell')
        self.root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root)
        (self.root / 'auth').mkdir()
        (self.root / 'auth/codex.json').write_text('{}')

    def test_a_timed_out_limit_probe_is_unavailable_evidence_and_is_reaped(self):
        reaped, original_run, original_reap = [], self.run_cell.subprocess.run, self.run_cell.assess.reap
        def timeout(*a, **k):
            raise subprocess.TimeoutExpired(a[0], 180)
        self.run_cell.subprocess.run, self.run_cell.assess.reap = timeout, reaped.append
        try:
            limits = self.run_cell.codex_limits(dict(auth=str(self.root / 'auth'), scratch=str(self.root), image='x'))
        finally:
            self.run_cell.subprocess.run, self.run_cell.assess.reap = original_run, original_reap
        self.assertEqual((limits, len(reaped)), ({}, 1))

    def test_collection_and_verdict_write_failures_are_explicit(self):
        out = self.root / 'cell-out'
        for name in ('run', 'cell', 'tmp', 'home'):
            (out / name).mkdir(parents=True)
        (out / 'evidence.manifest.json').mkdir()  # the manifest cannot be written
        sealed, failures = self.run_cell.seal_after_teardown(out)
        self.assertIsNone(sealed)
        self.assertTrue(failures)
        self.assertEqual(self.run_cell.write_verdict(self.root / 'missing-dir/verdict.json', dict(status='COMPLETE')), 2)


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

    def test_a_newer_unfinished_run_is_the_final_invocation(self):
        work = archived_run(self.out, self.shared)
        state = json.loads(next((work / '.devlyn/runs').glob('*/pipeline.state.json')).read_text())
        live = dict(state, run_id='rs-later', started_at='9999-01-01T00:00:00Z', phases={})
        (work / '.devlyn/pipeline.state.json').write_text(json.dumps(live))
        result = self.meter.meter(self.out)
        self.assertEqual((result['run_id'], result['satisfied']), ('rs-later', False))

    def test_empty_carriers_do_not_satisfy(self):
        work = archived_run(self.out, self.shared)
        capture = next((work / '.devlyn/runs').glob('*/claude-judge.r0.output.json'))
        capture.write_text('')
        result = self.meter.meter(self.out)
        self.assertFalse(result['checks']['round_carriers'], result)

    def test_an_accepted_run_kept_only_in_custody_is_read_there(self):
        work = archived_run(self.out, self.shared)
        run = next((work / '.devlyn/runs').iterdir())
        head = subprocess.run(['git', '-C', str(work), 'rev-parse', 'HEAD'], capture_output=True, text=True).stdout.strip()
        receipt = work / '.git/devlyn-completion/k'
        shutil.copytree(run, receipt / 'custody/.devlyn/runs' / run.name)
        shutil.rmtree(run)
        (receipt / 'receipt.json').write_text(json.dumps(dict(task='t', allocation='owned', worktree='/cell/gone',
                                                              acceptance=dict(task='t', source_sha=head, kind='pipeline', run_id=run.name))))
        (self.out / 'snapshot.json').write_text(json.dumps(dict(kind='accepted', sha=head, receipt='cell/work/.git/devlyn-completion/k/receipt.json')))
        result = self.meter.meter(self.out)
        self.assertTrue(result['satisfied'], result)

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

    def test_an_unchanged_allocation_after_checker_runs_has_no_scope_violations(self):  # Astra apparatus #1
        locate_module, packet = load('locate'), load('check').packet
        for task, config, skills, repository, script in (
                ('D4', 'claude', '.claude/skills', 'pallets/click', 'python3 -m pytest tests/test_basic.py -q >/dev/null && mypy >/dev/null'),
                ('D3', 'codex', '.agents/skills', 'tj/commander.js', 'npm run -s check:type >/dev/null && env -u NO_COLOR node --test >/dev/null')):
            out = self.prepare.prepare(self.runtime, f'scope-{task}', task, 'candidate', config)
            code, text = self.probe(out, f'''set -e
python3 {skills}/_shared/task-complete.py allocate --repo . --task t --branch task/t --worktree /tmp/task-t --repository {repository} --remote origin --base main >/dev/null
cd /tmp/task-t && {script}
echo OK''')
            self.assertEqual(text.strip().splitlines()[-1] if text.strip() else '', 'OK', text)
            sealed, failures = load('run_cell').seal_after_teardown(out)  # the full post-teardown sequence
            self.assertTrue(sealed and not failures, failures)
            selection = locate_module.locate(out)
            baseline = json.loads((out / 'baseline.json').read_text())
            current = packet.tree(out / 'snapshot')
            changed = sorted(n for n in baseline['files'].keys() | current.keys() if baseline['files'].get(n) != current.get(n))
            self.assertEqual((selection['kind'], changed), ('worktree', []), task)

    def test_wrong_arm_is_refused(self):
        with self.assertRaises(ValueError):
            self.prepare.prepare(self.runtime, 'bad', 'SMOKE', 'F', 'claude')


if __name__ == '__main__':
    unittest.main()
