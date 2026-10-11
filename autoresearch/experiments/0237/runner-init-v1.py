"""Prospective 0237 owner-init runner; use a separately registered runtime.

run|prepare <runtime.json> <name> <task> <A|B|C> <claude|codex>
assess remains the inherited, separately authorized model expense.
"""
import argparse
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


frozen = load('runner0237_init_v1_base', HERE / 'runner.py')


class Runner(frozen.Runner):
    def __init__(self, runtime_path, tasks_path=None):
        super().__init__(runtime_path, tasks_path)
        self.frame.cell_run = load('cell0237_init_v1', HERE / 'cell-init-v1.py')
        self.frame.cell_run.evidence.TASKS = self.tasks

    def inputs(self):
        paths = (Path(__file__), HERE / 'cell-init-v1.py')
        return {**super().inputs(), **{str(path): frozen.digest(path) for path in paths}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_subparsers(dest='action', required=True)
    for name in ('run', 'prepare', 'assess'):
        action = actions.add_parser(name)
        action.add_argument('runtime', type=Path)
        action.add_argument('name')
        if name != 'assess':
            action.add_argument('task')
            action.add_argument('arm', choices=('A', 'B', 'C'))
            action.add_argument('config', choices=('claude', 'codex'))
    args = parser.parse_args()
    try:
        runner = Runner(args.runtime)
        if args.action == 'assess':
            return runner.assess(args.name)
        if args.action == 'prepare':
            print(runner.prepare(args.name, args.task, args.arm, args.config))
            return 0
        return runner.run(args.name, args.task, args.arm, args.config)
    except (OSError, ValueError, KeyError, TypeError, RuntimeError, subprocess.SubprocessError) as exc:
        print(json.dumps(dict(status='STOP', reason=f'{type(exc).__name__}: {exc}')), file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
