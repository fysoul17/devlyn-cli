"""Local staging controls; no Docker, auth, model or process execution."""
import importlib.util
import io
import json
from pathlib import Path
import tarfile
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('stage_native_test', HERE / 'stage.py')
stage = importlib.util.module_from_spec(spec)
spec.loader.exec_module(stage)


class NativeDependencyTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix='0238-stage-native-')
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name).resolve()
        self.repo = self.root / 'repo'
        self.experiment = self.repo / 'autoresearch/experiments/0238'
        self.experiment.mkdir(parents=True)
        for attr, value in (('REPO', self.repo), ('EXPERIMENT', self.experiment)):
            setting = patch.object(stage, attr, value)
            setting.start()
            self.addCleanup(setting.stop)
        (self.experiment / 'peer.py').write_text('synthetic reviewed peer\n')
        (self.experiment / 'f23_precision.py').write_text('synthetic reviewed oracle\n')
        shared = self.repo / 'config/skills/_shared/platform-support.py'
        shared.parent.mkdir(parents=True)
        shared.write_text('synthetic shared process primitive\n')
        prior = self.experiment.parent / '0234'
        prior.mkdir()
        for name in ('cell.py', 'evidence.py', 'record_usage.py', 'oracle.js', 'fixture_oracle.js'):
            (prior / name).write_text('synthetic historical ' + name + '\n')
        self.native = {str(path.relative_to(self.repo)): stage.sha(path)
                       for path in (prior / name for name in ('cell.py', 'evidence.py', 'record_usage.py'))}
        self.freeze = self.root / 'review.json'
        stage.write(self.freeze, dict(files={name: stage.sha(self.experiment / name)
                                            for name in ('peer.py', 'f23_precision.py')},
                                     shared_process_dependency=dict(path=str(shared.relative_to(self.repo)),
                                                                    sha256=stage.sha(shared)),
                                     pair_native_dependencies=self.native))
        control = self.root / 'old-control'
        for name in ('public', 'oracle'):
            (control / name).mkdir(parents=True)
            (control / name / 'fixture.txt').write_text(name + '\n')
        runtime = self.root / 'template-runtime.json'
        stage.write(runtime, dict(image=stage.IMAGE, control=str(control), sources='/synthetic/sources',
                                  models_cache='/synthetic/models-cache', account=['synthetic-fingerprint']))
        tasks = self.root / 'tasks.json'
        stage.write(tasks, dict(watchdog_seconds=dict(owner=5400)))
        packs = self.root / 'packs'
        packs.mkdir()
        contents = {'package/config/skills/_shared/peer.py': (self.experiment / 'peer.py').read_bytes(),
                    'package/config/skills/_shared/platform-support.py': shared.read_bytes()}
        packages = {}
        for arm in ('B', 'S', 'H', 'P'):
            archive = packs / (arm + '.tgz')
            with tarfile.open(archive, 'w:gz') as tar:
                for name, data in contents.items():
                    info = tarfile.TarInfo(name)
                    info.size = len(data)
                    tar.addfile(info, io.BytesIO(data))
            packages[arm] = dict(sha256=stage.sha(archive),
                                 files={name: stage.hashlib.sha256(data).hexdigest() for name, data in contents.items()})
        stage.write(packs / 'packages.json', dict(packages=packages))
        self.args = SimpleNamespace(destination=self.root / 'staged', template_runtime=runtime,
                                    review_manifest=self.freeze, packs=packs, tasks=tasks)

    def test_valid_native_dependency_manifest_stages_offline(self):
        result = stage.stage(self.args)
        self.assertEqual(result, self.args.destination / 'runtime-smoke.json')
        copied = stage.read(self.args.destination / 'review-manifest.json')
        self.assertEqual(copied['pair_native_dependencies'], self.native)
        self.assertEqual(stage.read(self.args.destination / 'staging.json')['selected_review_manifest_sha256'],
                         stage.sha(self.freeze))
        self.assertEqual(list((self.args.destination / 'auth').iterdir()), [])

    def test_each_native_dependency_drift_is_rejected_before_destination(self):
        for relative in self.native:
            with self.subTest(dependency=relative):
                path = self.repo / relative
                original = path.read_bytes()
                path.write_bytes(original + b'changed\n')
                try:
                    with self.assertRaisesRegex(ValueError, 'reviewed pair native dependency changed'):
                        stage.stage(self.args)
                    self.assertFalse(self.args.destination.exists())
                finally:
                    path.write_bytes(original)

    def test_missing_native_dependency_binding_is_rejected(self):
        manifest = stage.read(self.freeze)
        manifest['pair_native_dependencies'].pop(next(iter(self.native)))
        stage.write(self.freeze, manifest)
        with self.assertRaisesRegex(ValueError, 'must bind the three pair native dependencies'):
            stage.stage(self.args)
        self.assertFalse(self.args.destination.exists())


if __name__ == '__main__':
    unittest.main(verbosity=2)
