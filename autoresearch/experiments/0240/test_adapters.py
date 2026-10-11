"""Packing/staging compatibility without building packages or staging a live runtime."""
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


builder = load('builder0240_tests', HERE / 'build_packages.py')
staging = load('stage0240_tests', HERE / 'results/stage.py')


class AdapterTests(unittest.TestCase):
    def test_builder_records_adapter_without_relabeling_inherited_builder(self):
        with tempfile.TemporaryDirectory() as temp:
            dest = Path(temp)
            old_sha = builder.legacy.sha(Path(builder.legacy.__file__))
            result = dict(builder_sha256=old_sha, packages={})
            with patch.object(builder.legacy, 'build', return_value=result) as base:
                actual = builder.build(dest, Path('/unused-toolchain'))
            base.assert_called_once_with(dest, Path('/unused-toolchain'))
            self.assertEqual(builder.legacy.HERE, HERE)
            self.assertEqual(actual['builder_sha256'], old_sha)
            self.assertEqual(actual['builder_adapter_sha256'], builder.legacy.sha(HERE / 'build_packages.py'))
            self.assertEqual(json.loads((dest / 'packages.json').read_text()), actual)

    def test_stage_records_adapter_without_relabeling_inherited_stage(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            runtime = root / 'runtime-smoke.json'
            old_sha = staging.legacy.sha(Path(staging.legacy.__file__))
            staging.legacy.write(root / 'staging.json', dict(stage_sha256=old_sha))
            args = SimpleNamespace(destination=root)
            with patch.object(staging, 'base_stage', return_value=runtime) as base:
                self.assertEqual(staging.stage(args), runtime)
            base.assert_called_once_with(args)
            record = staging.legacy.read(root / 'staging.json')
            self.assertEqual(staging.legacy.EXPERIMENT, HERE)
            self.assertEqual(record['stage_sha256'], old_sha)
            self.assertEqual(record['stage_adapter_sha256'], staging.legacy.sha(HERE / 'results/stage.py'))

    def test_native_dependency_drift_still_refuses_before_destination(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); packs = root / 'packs'; packs.mkdir()
            write = staging.legacy.write
            write(root / 'runtime.json', dict(image=staging.legacy.IMAGE))
            write(root / 'tasks.json', dict(watchdog_seconds=dict(owner=5400)))
            write(packs / 'packages.json', dict(packages={arm: {} for arm in ('B', 'S', 'H', 'P')}))
            dependency = 'config/skills/_shared/platform-support.py'
            native = {f'autoresearch/experiments/0234/{name}': 'deliberately-wrong'
                      for name in ('cell.py', 'evidence.py', 'record_usage.py')}
            write(root / 'review.json', dict(files={'peer.py': staging.legacy.sha(HERE / 'peer.py')},
                  shared_process_dependency=dict(path=dependency, sha256=staging.legacy.sha(staging.legacy.REPO / dependency)),
                  pair_native_dependencies=native))
            args = SimpleNamespace(destination=root / 'absent', template_runtime=root / 'runtime.json',
                  packs=packs, tasks=root / 'tasks.json', review_manifest=root / 'review.json')
            with self.assertRaisesRegex(ValueError, 'reviewed pair native dependency changed'):
                staging.stage(args)
            self.assertFalse(args.destination.exists())

    def test_smoke_changes_only_request_identity_and_preserves_all_routes(self):
        before = json.loads((HERE.parent / '0238/tasks-smoke.json').read_text())
        after = json.loads((HERE / 'tasks-smoke.json').read_text())
        self.assertEqual(before['routes'], after['routes'])
        old = next(t for t in before['tasks'] if t['id'] == 'S2')
        new = next(t for t in after['tasks'] if t['id'] == 'S2')
        self.assertEqual(new['request'].split('\n\n')[0], old['request'].split('\n\n')[0])
        self.assertNotIn('also ask it to use one permitted native child', new['request'])
        self.assertIn('must perform this check without delegation', new['request'])
        self.assertEqual(new['request_sha256'], hashlib.sha256(new['request'].encode()).hexdigest())
        new['request'], new['request_sha256'] = old['request'], old['request_sha256']
        after['schema'] = before['schema']
        self.assertEqual(after, before)
        self.assertEqual((HERE / 'guides/S.md').read_bytes(), (HERE.parent / '0238/guides/S.md').read_bytes())

    def test_inherited_execution_inputs_are_unchanged(self):
        before = json.loads((HERE / 'results/inherited-inputs-before.json').read_text())['files']
        changed = [name for name, expected in before.items()
                   if hashlib.sha256(Path(name).read_bytes()).hexdigest() != expected]
        self.assertEqual(changed, [])


if __name__ == '__main__':
    unittest.main(verbosity=2)
