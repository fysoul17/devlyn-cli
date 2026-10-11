"""Prospective direct-helper provenance with inherited native evidence gates."""
import ast
import copy
import importlib.util
import json
from pathlib import Path
import shlex
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('runner0242_tests', HERE / 'runner.py')
r = importlib.util.module_from_spec(spec)
spec.loader.exec_module(r)
prior = r.load('tests0241_reused', HERE.parent / '0241/test_runner.py')
prior.r = r
prior.inherited.r = r
fixtures = prior.fixtures
fixtures.r = r
RETAINED = json.loads((HERE / 'fixtures/retained-helper-events.json').read_text())


class InvocationTests(unittest.TestCase):
    def setUp(self):
        self.f = fixtures.ApparatusTests()
        self.addCleanup(self.f.doCleanups)
        self.f.setUp()

    def append(self, events):
        path = self.f.out / 'run/stdout'
        fixtures.lines(path, self.f.app.frame.cell_run.evidence.lines(path) + events)

    def paired(self):
        self.f.receipt(); self.f.codex(child=False)
        self.f.receipt(turn=2, resume='peer'); self.f.codex(child=False, turn=2)

    def test_retained_two_calls_and_acceptance_data_count_only_two(self):
        self.paired()
        events = [row['event'] for row in RETAINED['events']]
        self.assertEqual([r.base_policy.helper_invocations(e['item']['command']) for e in events], [1, 1, 0])
        self.append(events)
        old = r.load('frozen_policy0238_proof', HERE.parent / '0238/policy.py')
        previous = old.check(self.f.out, self.f.plan, self.f.app.tasks, self.f.app.frame.cell_run.evidence)
        self.assertEqual(previous['gaps'], ['observed helper launch has no retained attempt receipt'])
        result = self.f.recorded_good_product()
        self.assertEqual((result['status'], result['usage']), ('CHECKS_PASS', 'COMPLETE'))
        self.assertEqual(result['peer_policy']['gaps'], [])
        self.assertEqual((result['input_tokens'], result['output_tokens']), (216, 24))

    def test_third_real_failed_call_without_receipt_still_stops(self):
        self.paired()
        events = [row['event'] for row in RETAINED['events']]
        failed = copy.deepcopy(events[0])
        failed['item'].update(id='failed-before-receipt', exit_code=2, aggregated_output='peer.py: invalid arguments')
        self.append(events + [failed])
        result = self.f.recorded_good_product(expected_return=2)
        self.assertEqual(result['status'], 'STOP')
        self.assertEqual(result['peer_policy']['gaps'], ['observed helper launch has no retained attempt receipt'])
        self.assertEqual(result['known_usage_lower_bound'], dict(input_tokens=216, output_tokens=24))
        self.assertIsNone(result['input_tokens'])
        self.assertFalse((self.f.out / 'checks.json').exists())

    def test_supported_direct_quoted_and_env_wrappers(self):
        command = 'python3 "/path with spaces/peer.py" --engine codex --out "review space"'
        for text in (command, '/usr/bin/python3.12 /repo/peer.py --engine claude',
                     'KEY=value ' + command, 'env KEY="two words" ' + command,
                     'env -- KEY=value ' + command, '/bin/sh -lc ' + shlex.quote(command),
                     '/bin/bash -c ' + shlex.quote('/bin/sh -lc ' + shlex.quote(command))):
            with self.subTest(command=text):
                self.assertEqual(r.base_policy.helper_invocations(text), 1)

    def test_echo_documentation_and_heredoc_strings_are_not_dispatch(self):
        command = 'python3 /repo/peer.py --engine codex'
        for text in ('echo ' + shlex.quote(command), 'printf "%s\\n" ' + shlex.quote(command),
                     'cat <<\'DOC\'\n' + command + '\nDOC',
                     'python - <<\'PY\'\ncommand = ' + repr(command) + '\nPY',
                     'python -c ' + shlex.quote('print(' + repr(command) + ')'),
                     '/bin/sh -lc ' + shlex.quote('echo ' + shlex.quote(command))):
            with self.subTest(command=text):
                self.assertEqual(r.base_policy.helper_invocations(text), 0)

    def test_malformed_typed_receipt_still_stops(self):
        folder = self.f.receipt(); self.f.codex(child=False)
        (folder / 'completion.json').write_text('not JSON')
        result = self.f.recorded_good_product(expected_return=2)
        self.assertEqual(result['status'], 'STOP')
        self.assertTrue(result['peer_policy']['gaps'])
        self.assertFalse((self.f.out / 'checks.json').exists())

    def test_unknown_native_session_still_stops(self):
        self.f.codex(child=False)
        result = self.f.recorded_good_product(expected_return=2)
        self.assertEqual(result['status'], 'STOP')
        self.assertIn('unbound Codex session peer', result['peer_policy']['gaps'])
        self.assertIsNone(result['input_tokens'])

    def test_policy_delta_is_only_parser_import_function_and_count(self):
        old = ast.parse((HERE.parent / '0238/policy.py').read_text())
        new = ast.parse((HERE / 'policy.py').read_text())
        new.body = [node for node in new.body if not (
            isinstance(node, ast.FunctionDef) and node.name == 'helper_invocations' or
            isinstance(node, ast.Import) and [alias.name for alias in node.names] == ['shlex'])]
        previous = [node for node in ast.walk(old) if isinstance(node, ast.AugAssign)
                    and isinstance(node.target, ast.Name) and node.target.id == 'helper_calls']
        changed = [node for node in ast.walk(new) if isinstance(node, ast.AugAssign)
                   and isinstance(node.target, ast.Name) and node.target.id == 'helper_calls']
        self.assertEqual((len(previous), len(changed)), (1, 1))
        self.assertEqual(ast.unparse(changed[0].value), 'helper_invocations(str(command))')
        changed[0].value = previous[0].value
        self.assertEqual(ast.dump(new), ast.dump(old))

    def test_new_policy_and_exact_prior_capture_are_wired_and_sealed(self):
        app = self.f.app
        self.assertIs(r.legacy.legacy.base_policy, r.base_policy)
        self.assertIs(app.frame.cell_run.evidence.claude_envelopes.func, r.discovery.claude_envelopes)
        self.assertEqual(Path(r.discovery.__file__), HERE.parent / '0241/capture_discovery.py')
        paths = app.inputs()
        for path in (HERE / 'policy.py', HERE / 'peer.py', HERE / 'runner.py',
                     HERE.parent / '0241/capture_discovery.py', HERE.parent / '0238/policy.py'):
            self.assertEqual(paths[str(path)], r.digest(path))
        original = r.digest
        with patch.object(r, 'digest', side_effect=lambda path: 'changed' if path == HERE / 'policy.py' else original(path)):
            self.assertNotEqual(app.inputs(), paths)

    def test_request_guides_and_helper_delta_are_exact(self):
        for name in ('tasks-smoke.json', 'guides/H.md', 'guides/P.md', 'guides/S.md'):
            self.assertEqual((HERE / name).read_bytes(), (HERE.parent / '0241' / name).read_bytes())
        addition = b"                '-c', 'features.multi_agent_v2.enabled=false',\n"
        current = (HERE / 'peer.py').read_bytes()
        self.assertEqual(current.count(addition), 1)
        self.assertEqual(current.replace(addition, b''), (HERE.parent / '0241/peer.py').read_bytes())


def load_tests(loader, tests, pattern):
    for name in loader.getTestCaseNames(prior.CaptureTests):
        if name != 'test_inventory_is_private_shared_and_new_discovery_is_sealed':
            tests.addTest(prior.CaptureTests(name))
    for name in loader.getTestCaseNames(prior.inherited.RunnerTests):
        if name != 'test_new_and_imported_adapters_are_prospective_inputs':
            tests.addTest(prior.inherited.RunnerTests(name))
    return prior.inherited.load_tests(loader, tests, pattern)


if __name__ == '__main__':
    unittest.main(verbosity=2)
