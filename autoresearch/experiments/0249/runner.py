"""0249 task routing over unchanged native execution and usage accounting.

Restore the registered B5 orphan oracle and honor new fixture error exits.
Earlier runners and results remain untouched.
"""
import importlib.util
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


legacy = load('runner0247_confirmation', HERE.parent / '0247/runner.py')
read, write, digest = legacy.read, legacy.write, legacy.digest


class Runner(legacy.Runner):
    def __init__(self, runtime_path, tasks_path=None):
        self.orphan = load('check0233_confirmation_orphan', HERE.parent / '0233/check.py')
        super().__init__(runtime_path, tasks_path)
        self.orphan.TASKS = self.orphan.base.TASKS = self.tasks
        self.orphan.SECONDS = self.orphan.base.SECONDS = self.tasks['watchdog_seconds']['evaluator']

    def inputs(self):
        result = super().inputs()
        for name in ('runner.py', 'build_packages.py'):
            result[str(HERE / name)] = digest(HERE / name)
        return result

    def evaluate(self, work, task_id, runtime):
        if task_id == 'B5':
            return self.orphan.evaluate(work, task_id, runtime)
        result = super().evaluate(work, task_id, runtime)
        if task_id in ('OR1', 'OR2') and any(row['exit_code'] != 0 for row in result['raw']):
            raise ValueError('0249 fixture oracle did not produce a completed verdict: ' + json.dumps(result, sort_keys=True))
        return result


if __name__ == '__main__':
    entry = legacy.legacy.legacy.legacy.legacy.legacy.legacy
    entry.Runner = Runner
    sys.exit(entry.main())
