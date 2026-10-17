"""Synthetic helper outputs/actions only; no live engines or credentials."""
from copy import deepcopy
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('smoke_rpd4_test', HERE / 'smoke.py')
s = importlib.util.module_from_spec(spec)
spec.loader.exec_module(s)


def result(status='COMPLETE', scratch='CLEAN', workspace=None):
    value = dict(status=status, delivery_status=status, receipt='/cell/work/.git/devlyn-completion/task/receipt.json',
                 scratch_cleanup={'status': scratch}, workspace_cleanup=workspace, resume='wrong result-level resume')
    if status == 'COMPLETE' and (scratch == 'RETAINED' or workspace):
        value['status'] = 'CLEANUP_PENDING'
    if scratch == 'RETAINED':
        value['scratch_cleanup'].update(reason='scratch writer', resume='clean-scratch --receipt task')
    return value


def actions(**overrides):
    return dict(ran=True, linked=True, worktree_removed=True, local_ref_deleted=True,
                remote_branch_deleted=True) | overrides


def resources(**overrides):
    return dict(worktree_exists=False, worktree_registered=False, local_branch=False,
                remote_branch=False, scratch_files=[]) | overrides


class SentenceTests(unittest.TestCase):
    def test_removed_resources_and_emptied_scratch(self):
        value = result()
        value['cleanup'] = ('Removed the task worktree; deleted the local task branch; '
                            'deleted the remote task branch; emptied the task scratch.')
        self.assertEqual(s.check_call(value, actions(), resources()), value['cleanup'])

    def test_already_absent_resources(self):
        action = actions(worktree_removed=False, local_ref_deleted=False, remote_branch_deleted=False)
        self.assertEqual(s.render_cleanup(result(scratch='NOT_OWNED'), action),
                         'The task worktree was absent; the local task branch was absent; the remote task branch was absent.')

    def test_in_place_checkout_can_remain(self):
        action = actions(linked=False, worktree_removed=None)
        value = result()
        value['cleanup'] = s.render_cleanup(value, action)
        self.assertTrue(value['cleanup'].startswith('The in-place checkout is not a cleanup target;'))
        s.check_call(value, action, resources(worktree_exists=True, worktree_registered=True))

    def test_already_recorded_complete(self):
        self.assertEqual(s.render_cleanup(result(scratch='NOT_OWNED'), {'ran': False}),
                         'The receipt already records workspace cleanup complete.')

    def test_workspace_retention_only_claims_performed_deletions(self):
        workspace = dict(status='RETAINED', reason='writer active', resume='complete --receipt task')
        value = result(workspace=workspace)
        action = actions(worktree_removed=True, local_ref_deleted=None, remote_branch_deleted=False)
        value['cleanup'] = s.render_cleanup(value, action)
        self.assertEqual(value['cleanup'], 'Removed the task worktree; workspace cleanup deferred: writer active; '
                         'resume with complete --receipt task; emptied the task scratch.')
        s.check_call(value, action, resources(local_branch=True, remote_branch=True))

    def test_scratch_retention_uses_its_own_resume(self):
        value = result(scratch='RETAINED')
        rendered = s.render_cleanup(value, actions())
        self.assertIn('scratch cleanup incomplete: scratch writer; resume with clean-scratch --receipt task.', rendered)
        self.assertNotIn(value['resume'], rendered)

    def test_each_noncomplete_outcome(self):
        for status, phrase in (
                ('PR', 'Workspace cleanup deferred: the PR is not merged.'),
                ('PENDING', 'Workspace cleanup deferred: the PR is not merged.'),
                ('LOCAL_ONLY', 'Workspace cleanup skipped: local-only delivery.'),
                ('FAILED', 'Workspace cleanup skipped; publication skipped by this call.')):
            with self.subTest(status=status):
                self.assertEqual(s.render_cleanup(result(status, scratch='NOT_OWNED'), {'ran': False}), phrase)

    def test_claim_needs_exact_sentence(self):
        value = result()
        value['cleanup'] = s.render_cleanup(value, actions()).replace('emptied', 'removed')
        with self.assertRaisesRegex(ValueError, 'not entailed'):
            s.check_call(value, actions(), resources())

    def test_each_removal_and_absence_claim_needs_final_absence(self):
        for absent in (False, True):
            action = actions(worktree_removed=not absent, local_ref_deleted=not absent, remote_branch_deleted=not absent)
            value = result()
            value['cleanup'] = s.render_cleanup(value, action)
            for field in ('worktree_exists', 'worktree_registered', 'local_branch', 'remote_branch'):
                with self.subTest(absent=absent, field=field), self.assertRaisesRegex(ValueError, 'final resource'):
                    s.check_call(value, action, resources(**{field: True}))

    def test_empty_scratch_claim_needs_no_remaining_file(self):
        value = result()
        value['cleanup'] = s.render_cleanup(value, actions())
        with self.assertRaisesRegex(ValueError, 'scratch claim'):
            s.check_call(value, actions(), resources(scratch_files=['owned.log']))

    def test_unknown_action_cannot_be_reported_absent(self):
        with self.assertRaisesRegex(ValueError, 'missing helper absence observation'):
            s.render_cleanup(result(), actions(local_ref_deleted=None))

    def test_inconsistent_status_and_in_place_removal_fail_closed(self):
        value = result(scratch='RETAINED')
        value['status'] = 'COMPLETE'
        with self.assertRaisesRegex(ValueError, 'completion status'):
            s.render_cleanup(value, actions())
        with self.assertRaisesRegex(ValueError, 'in-place'):
            s.render_cleanup(result(), actions(linked=False))


class EvidenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.out = Path(self.temp.name)
        for name in ('harness', 'run', 'cell/work/.agents/skills/_shared', 'cell/trace'):
            (self.out / name).mkdir(parents=True, exist_ok=True)
        self.helper = self.out / 'cell/work/.agents/skills/_shared/task-complete.py'
        self.helper.write_text('"""Synthetic helper, never touches credentials or services."""\n')
        self.write('plan.json', dict(engine='codex', task='SM', arm='Y', env={'PYTHONPATH': '/harness:src:/control/python'}))
        self.write('baseline.json', dict(installed_files={'.agents/skills/_shared/task-complete.py': {}}))
        s.install_observer(self.out)
        self.value = result()
        self.value['cleanup'] = s.render_cleanup(self.value, actions())
        self.write('cell/work/.git/devlyn-completion/task/receipt.json', {'id': 'task'})
        self.write('report-checklist.json', dict(resources=resources(), evidence={'cleanup': {
            'receipt': 'cell/work/.git/devlyn-completion/task/receipt.json'}}))
        self.record(self.value)
        self.stream(self.value)
        self.seal()

    def write(self, name, value):
        path = self.out / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value) + '\n')

    def record(self, value, name='1-1.json', action=None):
        self.write('cell/helper-actions/' + name, dict(schema='rp-d4-helper-call-v1', actions=action or actions(),
            result=value, helper_sha256=s.digest(self.helper)))

    def rows(self, value, id_='call'):
        return [dict(type='item.started', item=dict(id=id_, type='command_execution',
                    command='python3 .agents/skills/_shared/task-complete.py complete --receipt task')),
                dict(type='item.completed', item=dict(id=id_, type='command_execution', exit_code=0,
                    aggregated_output='helper diagnostic\n' + json.dumps(value, indent=2) + '\n'))]

    def stream(self, value):
        rows = [dict(type='thread.started', thread_id='owner')] + self.rows(value)
        (self.out / 'run/stdout').write_text(''.join(json.dumps(row) + '\n' for row in rows))

    def seal(self):
        files = {str(path.relative_to(self.out)): s.digest(path)
                 for root in ('run', 'cell') for path in (self.out / root).rglob('*') if path.is_file()}
        self.write('evidence.manifest.json', dict(files=files, failures=[]))

    def test_sealed_stdout_action_and_final_resources_qualify(self):
        qualification = s.qualify(self.out)
        self.assertEqual((qualification['status'], qualification['calls']), ('PASS', 1))
        self.assertEqual(qualification['action_records'], {'cell/helper-actions/1-1.json':
            s.digest(self.out / 'cell/helper-actions/1-1.json')})

    def test_read_only_observer_bound_to_plan_and_baseline(self):
        s.verify_observer(self.out)
        (self.out / 'harness/sitecustomize.py').write_text('modified')
        with self.assertRaisesRegex(ValueError, 'observer implementation'):
            s.qualify(self.out)

    def test_observer_cannot_be_installed_on_measured_or_x(self):
        for field, value in (('task', 'BV'), ('arm', 'X'), ('engine', 'claude')):
            plan = s.read(self.out / 'plan.json')
            plan[field] = value
            self.write('plan.json', plan)
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, 'restricted'):
                s.install_observer(self.out)
            plan[field] = {'task': 'SM', 'arm': 'Y', 'engine': 'codex'}[field]
            self.write('plan.json', plan)

    def test_missing_action_evidence_does_not_infer_actions_from_sentence(self):
        (self.out / 'cell/helper-actions/1-1.json').unlink()
        self.seal()
        with self.assertRaisesRegex(ValueError, 'action evidence missing'):
            s.qualify(self.out)

    def test_action_evidence_modified_after_seal_is_refused(self):
        self.record(self.value, action=actions(worktree_removed=False))
        with self.assertRaisesRegex(ValueError, 'after sealing'):
            s.qualify(self.out)

    def test_extra_unsealed_action_record_is_refused(self):
        self.record(self.value, name='2-1.json')
        with self.assertRaisesRegex(ValueError, 'outside seal'):
            s.qualify(self.out)

    def test_stdout_must_equal_actual_observed_return(self):
        value = deepcopy(self.value)
        value['cleanup'] = 'A fabricated helper sentence.'
        self.stream(value)
        self.seal()
        with self.assertRaisesRegex(ValueError, 'stdout and observed'):
            s.qualify(self.out)

    def test_duplicate_complete_results_need_matching_call_count(self):
        self.record(self.value, name='1-2.json')
        self.seal()
        with self.assertRaisesRegex(ValueError, 'stdout and observed'):
            s.qualify(self.out)

    def test_another_receipt_is_not_a_qualifying_call(self):
        value = dict(self.value, receipt='/cell/work/.git/devlyn-completion/other/receipt.json')
        self.record(value)
        self.stream(value)
        self.seal()
        with self.assertRaisesRegex(ValueError, 'different receipt'):
            s.qualify(self.out)

    def test_richer_owner_trace_supplies_helper_stdout(self):
        self.write('cell/trace/trace-owner/manifest.json', dict(root_thread_id='owner', raw_event_log='trace.jsonl'))
        events = []
        for index, row in enumerate(self.rows(self.value)):
            name = f'payloads/{index}.json'
            self.write('cell/trace/trace-owner/' + name, dict(row, thread_id='owner'))
            events.append(dict(payload=dict(type='protocol_event_observed', event_type=row['type'], event_payload={'path': name})))
        (self.out / 'cell/trace/trace-owner/trace.jsonl').write_text(''.join(json.dumps(row) + '\n' for row in events))
        (self.out / 'run/stdout').write_text(json.dumps(dict(type='thread.started', thread_id='owner')) + '\n')
        self.seal()
        self.assertEqual(s.qualify(self.out)['calls'], 1)

    def test_trace_payload_cannot_escape_evidence_directory(self):
        self.write('cell/trace/trace-owner/manifest.json', dict(root_thread_id='owner', raw_event_log='../../../../outside'))
        self.seal()
        with self.assertRaisesRegex(ValueError, 'unsafe helper evidence path'):
            s.qualify(self.out)

    def call_rows(self, tool, input_, output, id_, engine):
        if engine == 'claude':
            return [dict(type='assistant', message={'content': [dict(
                        type='tool_use', id=id_, name=tool, input=input_)]}),
                    dict(type='user', message={'content': [dict(
                        type='tool_result', tool_use_id=id_, content=output)]})]
        return [dict(type='item.started', item=dict(id=id_, tool=tool, input=input_)),
                dict(type='item.completed', item=dict(id=id_, exit_code=0, aggregated_output=output))]

    def write_calls(self, *calls, engine='codex'):
        self.write('plan.json', s.read(self.out / 'plan.json') | {'engine': engine})
        rows = [dict(type='thread.started', thread_id='owner')] if engine == 'codex' else []
        for index, (tool, input_, output) in enumerate(calls):
            rows.extend(self.call_rows(tool, input_, output, str(index), engine))
        (self.out / 'run/stdout').write_text(''.join(json.dumps(row) + '\n' for row in rows))

    def test_split_helper_json_reassembles_across_polls_and_qualifies(self):
        encoded = json.dumps(self.value)
        middle = len(encoded) // 2
        self.write_calls(
            ('exec_command', {'cmd': 'finish-task'}, json.dumps({'session_id': 42, 'output': encoded[:middle]})),
            ('write_stdin', {'session_id': 42}, json.dumps({'session_id': 42, 'output': ''})),
            ('write_stdin', {'session_id': 42}, json.dumps({'output': encoded[middle:], 'exit_code': 0})))
        self.seal()
        self.assertEqual(s.qualify(self.out)['calls'], 1)

    def test_actual_python_profile_observes_unmodified_helper_return(self):
        # A harmless process exercises sitecustomize, with an explicitly synthetic
        # destination. This is neither an engine launch nor a real helper call.
        self.helper.write_text('import json\ndef complete():\n    actions = {"ran": False}\n'
                               '    return {"status": "PR", "cleanup": "synthetic"}\n'
                               'print(json.dumps(complete()))\n')
        config = s.read(self.out / 'harness/helper-observer.json')
        config.update(helper_sha256=s.digest(self.helper), records=str(self.out / 'cell/helper-actions'))
        self.write('harness/helper-observer.json', config)
        (self.out / 'cell/helper-actions/1-1.json').unlink()
        done = subprocess.run([sys.executable, '-B', str(self.helper)], env={**os.environ,
            'PYTHONPATH': str(self.out / 'harness')}, capture_output=True, text=True, check=True)
        self.assertEqual(done.stderr, '')
        records = list((self.out / 'cell/helper-actions').glob('*.json'))
        self.assertEqual(len(records), 1)
        captured = s.read(records[0])
        self.assertEqual(captured['actions'], {'ran': False})
        self.assertEqual(captured['result'], json.loads(done.stdout))

    def test_observer_failures_leave_helper_return_and_locals_untouched(self):
        for failure in ('missing-actions', 'serialize', 'open'):
            with self.subTest(failure=failure):
                action = {'missing-actions': '', 'serialize': '    actions = {"unserializable": set()}\n',
                          'open': '    actions = {"ran": False}\n'}[failure]
                self.helper.write_text('import json\ndef complete():\n' + action +
                    '    return {"status": "PR", "cleanup": "synthetic"}\n'
                    'print(json.dumps(complete(), sort_keys=True))\n')
                config = s.read(self.out / 'harness/helper-observer.json')
                config.update(helper_sha256=s.digest(self.helper),
                              records=str(self.out / ('missing-records' if failure == 'open' else 'cell/helper-actions')))
                self.write('harness/helper-observer.json', config)
                for path in (self.out / 'cell/helper-actions').glob('*.json'):
                    path.unlink()
                done = subprocess.run([sys.executable, '-B', str(self.helper)], env={**os.environ,
                    'PYTHONPATH': str(self.out / 'harness')}, capture_output=True, text=True)
                self.assertEqual(done.returncode, 0)
                self.assertEqual(done.stderr, '')
                self.assertEqual(json.loads(done.stdout), {'status': 'PR', 'cleanup': 'synthetic'})
                self.assertEqual(list((self.out / 'cell/helper-actions').glob('*.json')), [])


if __name__ == '__main__':
    unittest.main()
