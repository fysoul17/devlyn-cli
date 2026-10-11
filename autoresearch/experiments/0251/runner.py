"""Prospective fixed-auth adapter; previous runners and studies stay immutable."""
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


legacy = load('runner0249_fixed_auth', HERE.parent / '0249/runner.py')
auth = load('auth0251', HERE / 'auth.py')
cell = load('cell0251', HERE / 'cell.py')
read, write, digest = legacy.read, legacy.write, legacy.digest


class Runner(legacy.Runner):
    def __init__(self, runtime_path, tasks_path=None):
        super().__init__(runtime_path, tasks_path)
        self.frame.cell_run.run = partial(cell.run, native=self.frame.cell_run,
                                          check_auth=auth.preflight)

    def inputs(self):
        result = super().inputs()
        paths = [HERE / name for name in ('runner.py', 'auth.py', 'cell.py')]
        paths.append(Path(self.runtime['auth']) / 'manifest.json')
        result.update({str(path): digest(path) for path in paths})
        return result

    def preflight(self):
        return auth.preflight(self.runtime)

    def assess(self, name):
        raise ValueError('0251 does not provision separate model assessors')


if __name__ == '__main__':
    entry = legacy.legacy.legacy.legacy.legacy.legacy.legacy.legacy
    entry.Runner = Runner
    sys.exit(entry.main())
