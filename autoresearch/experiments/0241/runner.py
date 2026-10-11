"""Prospective capture provenance and peer configuration repairs over frozen 0240."""
from functools import partial
import importlib.util
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


legacy = load('runner0240_capture_provenance', HERE.parent / '0240/runner.py')
discovery = load('capture0241', HERE / 'capture_discovery.py')
read, write, digest, delivery = legacy.read, legacy.write, legacy.digest, legacy.delivery
policy, base_policy, BaseRunner = legacy.policy, legacy.base_policy, legacy.Runner


class Runner(BaseRunner):
    def __init__(self, runtime_path, tasks_path=None):
        super().__init__(runtime_path, tasks_path)
        evidence = self.frame.cell_run.evidence
        if self.frame.usage.evidence is not evidence:
            raise ValueError('identity and usage must share one evidence inventory')
        evidence.claude_envelopes = partial(discovery.claude_envelopes, evidence=evidence)

    def inputs(self):
        result = super().inputs()
        paths = [HERE / name for name in ('runner.py', 'peer.py', 'capture_discovery.py',
                 'build_packages.py', 'results/stage.py', 'guides/H.md', 'guides/P.md', 'guides/S.md')]
        result.update({str(path): digest(path) for path in paths})
        return result


if __name__ == '__main__':
    legacy.legacy.Runner = Runner
    sys.exit(legacy.legacy.main())
