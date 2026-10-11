"""Model-free checks of isolation, EQ3 calibration and fail-closed accounting."""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import tomllib
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('runner0237', HERE / 'runner.py')
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


class RunnerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='0237-apparatus-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.env = patch.dict(os.environ, {'GIT_CONFIG_NOSYSTEM': '1', 'GIT_CONFIG_GLOBAL': '/dev/null',
                                         'GIT_CONFIG_COUNT': '0', 'PYTHONDONTWRITEBYTECODE': '1'})
        self.env.start()
        self.addCleanup(self.env.stop)
        self.control = self.root / 'control'
        for name in ('public', 'oracle', 'packages'):
            (self.control / name).mkdir(parents=True)
        (self.control / 'oracle/fixture').write_text('hidden evaluator')
        runner.write(str(self.control) + '.manifest.json', dict(manifests={
            name: {str(p.relative_to(self.control / name)): runner.digest(p)
                   for p in (self.control / name).rglob('*') if p.is_file()}
            for name in ('public', 'oracle', 'packages')}))
        self.runtime = self.root / 'runtime.json'
        runner.write(self.runtime, dict(image='sha256:' + 'a' * 64, control=str(self.control), phase='smoke',
                                       output=str(self.root / 'out'), auth=str(self.root / 'auth')))
        self.app = runner.Runner(self.runtime)

    def test_routes_are_bound_to_every_independent_import(self):
        m = self.app.frame
        for module in (m.prepare, m.check, m.check.base, m.assess, m.cell_run.evidence, m.usage.evidence):
            self.assertIs(module.TASKS, self.app.tasks)
        self.assertEqual(m.cell_run.evidence.seats({'config': 'claude'})['owner']['effort'], 'max')
        self.assertEqual(m.usage.evidence.seats({'config': 'codex'})['owner']['effort'], 'ultra')

    def test_codex_prepare_trusts_actual_cwd_and_still_rejects_config_drift(self):
        self.app.runtime['sources'] = str(self.root)
        runner.write(self.runtime, self.app.runtime)
        with patch.object(self.app, 'validate'):
            out = self.app.prepare('codex-trust', 'EQ3-UA1', 'A', 'codex')
        config = out / 'home/.codex/config.toml'
        plan = runner.read(out / 'plan.json')
        cwd = plan['argv'][plan['argv'].index('-C') + 1]
        self.assertEqual(cwd, '/cell/work')
        self.assertEqual(tomllib.loads(config.read_text())['projects'], {cwd: {'trust_level': 'trusted'}})
        self.assertEqual(runner.read(out / 'seal.json')['prepared']['home/.codex/config.toml'],
                         runner.digest(config))
        config.write_text(config.read_text() + '\n')
        with self.assertRaisesRegex(ValueError, 'prepared cell changed'):
            self.app.unchanged(out)

    def test_codex_prepare_rejects_unexpected_inherited_trust_contract(self):
        self.app.runtime['sources'] = str(self.root)
        runner.write(self.runtime, self.app.runtime)
        inherited_prepare = self.app.frame.prepare.prepare

        def changed_template(*args):
            out = inherited_prepare(*args)
            config = out / 'home/.codex/config.toml'
            config.write_text(config.read_text().replace('[projects."/work"]', '[projects."/unexpected"]'))
            return out

        with patch.object(self.app, 'validate'), \
                patch.object(self.app.frame.prepare, 'prepare', side_effect=changed_template):
            with self.assertRaisesRegex(ValueError, 'unexpected inherited Codex project trust'):
                self.app.prepare('unexpected-trust', 'EQ3-UA1', 'A', 'codex')

    def test_common_delivery_endpoint_and_checker_are_prospectively_bound(self):
        caller = dict(request='Fix the task', allowed=['product.txt'])
        prompt = self.app.frame.prepare.native_prompt(caller)
        self.assertEqual(prompt, self.app.native_prompt(caller))
        self.assertIn((HERE / 'local-delivery.txt').read_text(), prompt)
        self.assertEqual(json.loads(prompt.split('CALLER CONTRACT\n', 1)[1]), caller)
        for name in ('delivery.py', 'local-delivery.txt'):
            self.assertEqual(self.app.inputs()[str(HERE / name)], runner.digest(HERE / name))

    def delivery_fixture(self):
        out = self.root / 'delivery'
        work = out / 'cell/work'
        work.mkdir(parents=True)
        (out / 'harness').mkdir()
        git = self.app.frame.prepare.git
        git(work, 'init', '-q', '-b', 'main')
        for key, value in (('user.name', 'Fixture'), ('user.email', 'fixture@localhost'),
                           ('commit.gpgsign', 'false')):
            git(work, 'config', key, value)
        (work / 'product.txt').write_text('before\n')
        git(work, 'add', 'product.txt')
        git(work, 'commit', '-qm', 'baseline')
        baseline = git(work, 'rev-parse', 'HEAD')
        runner.write(out / 'baseline.json', dict(allocation_sha=baseline, files=self.app.packet.tree(work)))
        runner.write(out / 'harness/caller.json', dict(allowed=['product.txt']))
        return out, work, git

    def check_delivery(self, out):
        selected = self.app.frame.locate.locate(out)
        return runner.delivery.check(out, selected, self.app.frame.locate, self.app.packet)

    def test_delivery_accepts_native_local_commit_without_receipt(self):
        out, work, git = self.delivery_fixture()
        (work / 'product.txt').write_text('after\n')
        git(work, 'commit', '-qam', 'complete task')
        result = self.check_delivery(out)
        self.assertTrue(result['passed'], result)
        self.assertEqual(result['commit'], git(work, 'rev-parse', 'HEAD'))

    def test_delivery_rejects_uncommitted_only_changes(self):
        out, work, _ = self.delivery_fixture()
        (work / 'product.txt').write_text('after\n')
        result = self.check_delivery(out)
        self.assertFalse(result['passed'])
        self.assertIn('outside a post-baseline commit', result['reason'])

    def test_delivery_rejects_commit_snapshot_mismatch(self):
        out, work, git = self.delivery_fixture()
        (work / 'product.txt').write_text('intermediate\n')
        git(work, 'commit', '-qam', 'intermediate')
        (work / 'product.txt').write_text('required final fix\n')
        result = self.check_delivery(out)
        self.assertFalse(result['passed'])
        self.assertIn('differs from the assessed snapshot', result['reason'])

    def test_delivery_rejects_noop_commit(self):
        out, work, git = self.delivery_fixture()
        git(work, 'commit', '--allow-empty', '-qm', 'no source changes')
        result = self.check_delivery(out)
        self.assertFalse(result['passed'])
        self.assertIn('no changed task source', result['reason'])

    def test_delivery_rejects_unrelated_history(self):
        out, work, git = self.delivery_fixture()
        git(work, 'checkout', '-q', '--orphan', 'unrelated')
        (work / 'product.txt').write_text('after\n')
        git(work, 'commit', '-qam', 'unrelated history')
        result = self.check_delivery(out)
        self.assertFalse(result['passed'])
        self.assertIn('not a descendant', result['reason'])

    def test_delivery_accepts_linked_worktree_without_receipt(self):
        out, work, git = self.delivery_fixture()
        linked = out / 'cell/linked'
        git(work, 'worktree', 'add', '-qb', 'task', str(linked))
        (linked / 'product.txt').write_text('after\n')
        git(linked, 'commit', '-qam', 'complete in worktree')
        sha = git(linked, 'rev-parse', 'HEAD')
        # Reproduce the container paths that the safe locator translates on the host.
        gitdir = Path((linked / '.git').read_text().removeprefix('gitdir:').strip())
        (gitdir / 'gitdir').write_text('/cell/linked/.git\n')
        (linked / '.git').write_text('gitdir: /cell/work/.git/worktrees/linked\n')
        result = self.check_delivery(out)
        self.assertTrue(result['passed'], result)
        self.assertEqual(result['commit'], sha)

    def test_delivery_accepts_receipt_commit_even_when_anchor_differs(self):
        out, work, git = self.delivery_fixture()
        (work / 'product.txt').write_text('accepted\n')
        git(work, 'commit', '-qam', 'accepted task')
        sha = git(work, 'rev-parse', 'HEAD')
        receipt = work / '.git/devlyn-completion/task/receipt.json'
        receipt.parent.mkdir(parents=True)
        runner.write(receipt, dict(allocation='owned', baseline=runner.read(out / 'baseline.json')['allocation_sha'],
                                  anchor='/cell/work', task='task', source_sha=sha,
                                  acceptance=dict(kind='direct', task='task', source_sha=sha)))
        (work / 'product.txt').write_text('unrelated later working copy\n')
        result = self.check_delivery(out)
        self.assertTrue(result['passed'], result)
        self.assertEqual(result['commit'], sha)
        self.assertEqual(runner.read(out / 'snapshot.json')['kind'], 'accepted')

    def test_checks_pass_requires_source_delivery_and_successful_owner(self):
        cases = [(True, True, 'EXITED_0', False, 'CHECKS_PASS'),
                 (True, False, 'EXITED_0', False, 'PRODUCT_INCOMPLETE'),
                 (False, True, 'EXITED_0', False, 'PRODUCT_INCOMPLETE'),
                 (True, True, 'EXITED_1', False, 'PRODUCT_INCOMPLETE'),
                 (False, True, 'EXITED_0', True, 'ADJUDICATE'),
                 (False, False, 'EXITED_0', True, 'PRODUCT_INCOMPLETE')]
        for number, (source, delivered, exit_status, adjudicate, expected) in enumerate(cases):
            with self.subTest(source=source, delivery=delivered, owner=exit_status, adjudicate=adjudicate):
                name = 'delivery-status-' + str(number)
                out = self.root / 'out' / name
                checks = dict(product_check_pass=source, adjudication_needed=adjudicate)

                def prepare(*args):
                    (out / 'snapshot').mkdir(parents=True)
                    (out / 'snapshot/product.txt').write_text('checked source\n')
                    runner.write(out / 'checks.json', checks)
                    return out

                owner = dict(owner_status=exit_status, seconds=1, teardown='CLEAN', identity=dict(status='MATCH'))
                usage = dict(completeness='COMPLETE', input_tokens=12, output_tokens=3, gaps=[])
                with patch.object(self.app, 'validate'), patch.object(self.app, 'preflight', return_value=({}, None)), \
                        patch.object(self.app, 'prepare', side_effect=prepare), patch.object(self.app, 'unchanged'), \
                        patch.object(self.app, 'boot_catalogs', return_value={}), \
                        patch.object(self.app.frame.cell_run, 'run', return_value=owner), \
                        patch.object(self.app.frame, 'seal_after_teardown', return_value=('sealed', [])), \
                        patch.object(self.app.frame.usage, 'record', return_value=usage), \
                        patch.object(self.app.frame.quota, 'classify', return_value=dict(execution=False)), \
                        patch.object(self.app.frame.locate, 'locate', return_value=dict(kind='anchor', path='cell/work')), \
                        patch.object(self.app.frame.check, 'check', return_value=checks), \
                        patch.object(runner.delivery, 'check', return_value=dict(passed=delivered)):
                    self.assertEqual(self.app.run(name, 'E1', 'A', 'claude'), 0)
                verdict = runner.read(out.parent / ('verdict-' + name + '.json'))
                self.assertEqual(verdict['status'], expected)
                self.assertEqual(verdict['source_check_pass'], source)
                self.assertEqual(verdict['delivery_pass'], delivered)
                self.assertEqual(runner.read(out / 'checked.json')['delivery_sha256'],
                                 runner.digest(out / 'delivery.json'))

    def test_runtime_task_file_is_independent_and_explicit_override_wins(self):
        alternate = (self.root / 'tasks-discovery.json').resolve()
        tasks = runner.read(HERE / 'tasks.json')
        tasks['tasks'][0]['request'] = 'A prospectively registered discovery request'
        runner.write(alternate, tasks)
        runtime = runner.read(self.runtime)
        runtime['tasks_file'] = str(alternate)
        runner.write(self.runtime, runtime)
        selected = runner.Runner(self.runtime)
        self.assertEqual(selected.tasks_path, alternate)
        self.assertEqual(selected.tasks['tasks'][0]['request'], tasks['tasks'][0]['request'])
        m = selected.frame
        for module in (m.prepare, m.check, m.check.base, m.assess, m.cell_run.evidence, m.usage.evidence):
            self.assertIs(module.TASKS, selected.tasks)
        self.assertIn(str(alternate), selected.inputs())
        self.assertNotIn(str(HERE / 'tasks.json'), selected.inputs())
        explicit = runner.Runner(self.runtime, HERE / 'tasks.json')
        self.assertEqual(explicit.tasks, self.app.tasks)

    def test_eq3_source_exposes_visible_tree_only_and_preserves_goal_paths(self):
        task = self.app.task('EQ3-UA1')
        work = self.root / 'source'
        self.app.source(task, self.app.runtime, work, None)
        self.assertTrue((work / 'visible/checks/run_checks.py').is_file())
        for forbidden in ('hidden', 'patches', 'task.json', 'visible/hidden', 'visible/patches'):
            self.assertFalse((work / forbidden).exists())
        self.assertEqual(self.app.packet.content(self.app.packet.tree(work)), task['source_sha256'])
        changed = dict(task, source_sha256={})
        with self.assertRaisesRegex(ValueError, 'registered source changed'):
            self.app.source(changed, self.app.runtime, self.root / 'wrong-seal', None)

    def test_eq3_noop_gold_and_symptom_calibrate_the_real_hidden_oracles(self):
        for task_id in ('EQ3-UA1', 'EQ3-MI1', 'EQ3-AF1', 'EQ3-BD1'):
            task = self.app.task(task_id)
            source = runner.REPO / task['eq3_dir']
            for variant in ('noop', 'gold', 'symptom'):
                with self.subTest(task=task_id, variant=variant):
                    work = self.root / (task_id + '-' + variant)
                    shutil.copytree(source / 'visible', work / 'visible')
                    delta = source / 'patches' / (variant + '.patch')
                    if delta.read_bytes().strip():
                        subprocess.run(['patch', '-s', '-p1', '-i', str(delta)], cwd=work / 'visible',
                                       check=True, capture_output=True)

                    def in_image(runtime, actual_work, command):
                        self.assertEqual(actual_work, work)
                        if command[0] == 'sh':
                            invocation = ['sh', '-c', task['public_checks'][0]]
                        else:
                            self.assertEqual(command[-1], '/cell/work/visible')
                            self.assertEqual(command[-2], f'/control/autoresearch/eq3/{task_id}/oracle.py')
                            invocation = [sys.executable, '-B', str(source / 'hidden/oracle.py'), str(work / 'visible')]
                        result = subprocess.run(invocation, cwd=work, capture_output=True, text=True, timeout=20)
                        return dict(argv=command, exit_code=result.returncode, timeout=False,
                                    stdout=result.stdout, stderr=result.stderr)

                    with patch.object(self.app.frame.check, 'in_image', side_effect=in_image):
                        result = self.app.evaluate(work, task_id, self.app.runtime)
                    passes = all(row['status'] == 'PASS' for row in result['rows'])
                    self.assertEqual(passes, variant == 'gold', result)
                    if variant == 'gold':
                        self.assertTrue(all(row['exit_code'] == 0 for row in result['public']), result)

    def test_hidden_manifestation_coverage_cannot_silently_shrink(self):
        result = dict(argv=[], exit_code=0, timeout=False, stdout='{"manifestations":[]}', stderr='')
        with patch.object(self.app.frame.check, 'in_image', return_value=result):
            with self.assertRaisesRegex(ValueError, 'manifestation coverage mismatch'):
                self.app.evaluate(self.root, 'EQ3-UA1', self.app.runtime)

    def test_oracle_nonzero_exit_cannot_pass_with_success_json(self):
        rows = [dict(id=name, passed=True) for name in self.app.task('EQ3-UA1')['oracle']]
        result = dict(argv=[], exit_code=1, timeout=False,
                      stdout=json.dumps(dict(manifestations=rows)), stderr='failed after emitting result')
        with patch.object(self.app.frame.check, 'in_image', return_value=result):
            checked = self.app.evaluate(self.root, 'EQ3-UA1', self.app.runtime)
        self.assertTrue(all(row['status'] == 'FAIL' for row in checked['rows']))

    def test_cross_engine_session_preserves_usage_but_never_grades(self):
        out = self.root / 'out/cross-engine'
        owner = dict(owner_status='EXITED_0', seconds=1, teardown='CLEAN', identity=dict(
            status='MATCH', owner_launched_sessions=[dict(engine='codex', model='gpt-6-astra', effort='ultra')]))
        usage = dict(completeness='COMPLETE', input_tokens=12, output_tokens=3, gaps=[])

        def prepare(*args):
            out.mkdir()
            return out

        with patch.object(self.app, 'validate'), patch.object(self.app, 'preflight', return_value=({}, None)), \
                patch.object(self.app, 'prepare', side_effect=prepare), \
                patch.object(self.app.frame.cell_run, 'run', return_value=owner), \
                patch.object(self.app.frame, 'seal_after_teardown', return_value=('sealed', [])), \
                patch.object(self.app.frame.usage, 'record', return_value=usage), \
                patch.object(self.app.frame.check, 'check') as check:
            self.assertEqual(self.app.run('cross-engine', 'EQ3-UA1', 'A', 'claude'), 2)
        check.assert_not_called()
        verdict = runner.read(out.parent / 'verdict-cross-engine.json')
        self.assertEqual(verdict['input_tokens'], 12)
        self.assertIn('S1 solo protocol', verdict['reason'])

    def test_control_mutation_and_mutable_image_stop_before_model_dispatch(self):
        with patch.object(runner.subprocess, 'check_output', return_value=self.app.runtime['image']):
            self.app.validate('valid-cell')
        (self.control / 'oracle/fixture').write_text('changed hidden evaluator')
        with self.assertRaisesRegex(ValueError, 'control changed'):
            self.app.validate('valid-cell')
        self.app.runtime['image'] = 'devlyn:latest'
        with self.assertRaisesRegex(ValueError, 'exact sha256'):
            self.app.validate('valid-cell')
        with self.assertRaisesRegex(ValueError, 'safe path'):
            self.app.validate('../other-cell')

    def test_measured_missing_catalog_stops_before_auth_or_model(self):
        self.app.runtime['phase'] = 'measured'
        with patch.object(self.app, 'validate'), patch.object(self.app, 'preflight') as auth, \
                patch.object(self.app.frame.cell_run, 'run') as model:
            with self.assertRaisesRegex(ValueError, 'measured Claude requires'):
                self.app.run('uncalibrated', 'E1', 'A', 'claude')
        auth.assert_not_called()
        model.assert_not_called()

    def test_observed_catalog_contamination_never_grades(self):
        self.app.runtime.update(phase='measured', boot_catalogs=dict(claude=dict(A=dict(
            skills=[], plugins=[], mcp_servers=[]))))
        out = self.root / 'out/contaminated'
        owner = dict(owner_status='EXITED_0', seconds=1, teardown='CLEAN', identity=dict(status='MATCH'))
        usage = dict(completeness='COMPLETE', input_tokens=12, output_tokens=3, gaps=[])

        def prepare(*args):
            (out / 'run').mkdir(parents=True)
            runner.write(out / 'run/stdout', dict(type='system', subtype='init',
                         skills=['account-synced-skill'], plugins=[], mcp_servers=[]))
            # A native stream is newline-delimited JSON, not a pretty-printed object.
            (out / 'run/stdout').write_text(json.dumps(runner.read(out / 'run/stdout')) + '\n')
            return out

        with patch.object(self.app, 'validate'), patch.object(self.app, 'preflight', return_value=({}, None)), \
                patch.object(self.app, 'prepare', side_effect=prepare), \
                patch.object(self.app.frame.cell_run, 'run', return_value=owner), \
                patch.object(self.app.frame, 'seal_after_teardown', return_value=('sealed', [])), \
                patch.object(self.app.frame.usage, 'record', return_value=usage), \
                patch.object(self.app.frame.check, 'check') as check:
            self.assertEqual(self.app.run('contaminated', 'E1', 'A', 'claude'), 2)
        check.assert_not_called()
        verdict = runner.read(out.parent / 'verdict-contaminated.json')
        self.assertEqual(verdict['boot_catalogs']['skills'], ['account-synced-skill'])
        self.assertIn('catalog contamination', verdict['reason'])

    def test_usage_gaps_preserve_unknown_totals_and_never_grade(self):
        out = self.root / 'out/gap'
        out.mkdir(parents=True)
        owner = dict(owner_status='EXITED_0', seconds=1, teardown='CLEAN', identity=dict(status='MATCH'))
        usage = dict(completeness='PARTIAL', input_tokens=12, output_tokens=3, gaps=['missing child usage'])
        # run() requires a fresh path; prepare creates it after preflight.
        out.rmdir()

        def prepare(*args):
            out.mkdir()
            return out

        with patch.object(self.app, 'validate'), patch.object(self.app, 'preflight', return_value=({}, None)), \
                patch.object(self.app, 'prepare', side_effect=prepare), \
                patch.object(self.app.frame.cell_run, 'run', return_value=owner), \
                patch.object(self.app.frame, 'seal_after_teardown', return_value=('sealed', [])), \
                patch.object(self.app.frame.usage, 'record', return_value=usage), \
                patch.object(self.app.frame.check, 'check') as check:
            self.assertEqual(self.app.run('gap', 'EQ3-UA1', 'A', 'claude'), 2)
        check.assert_not_called()
        verdict = runner.read(out.parent / 'verdict-gap.json')
        self.assertIsNone(verdict['input_tokens'])
        self.assertIsNone(verdict['output_tokens'])
        self.assertEqual(verdict['known_usage_lower_bound'], dict(input_tokens=12, output_tokens=3))
        self.assertEqual(verdict['status'], 'STOP')

    def test_changed_checked_source_stops_before_optional_assessor(self):
        out = self.root / 'out/checked'
        (out / 'snapshot').mkdir(parents=True)
        (out / 'snapshot/product.py').write_text('original')
        runner.write(out / 'checks.json', {'product_check_pass': True})
        runner.write(out / 'checked.json', dict(snapshot=self.app.packet.tree(out / 'snapshot'),
                                                checks_sha256=runner.digest(out / 'checks.json')))
        (out / 'snapshot/product.py').write_text('changed after checks')
        with patch.object(self.app, 'validate'), patch.object(self.app, 'unchanged'), \
                patch.object(self.app.frame.assess, 'assess') as assessor:
            with self.assertRaisesRegex(ValueError, 'checked source or evidence changed'):
                self.app.assess('checked')
        assessor.assert_not_called()


if __name__ == '__main__':
    unittest.main()
