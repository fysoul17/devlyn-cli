"""Prospective helper-owned custody; unchanged 0244 evidence and accounting."""
import importlib.util
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('runner0244_durable_peer', HERE.parent / '0244/runner.py')
legacy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(legacy)
read, write, digest = legacy.read, legacy.write, legacy.digest


class Runner(legacy.Runner):
    def inputs(self):
        result = super().inputs()
        paths = [HERE / name for name in ('runner.py', 'peer.py', 'build_packages.py',
                 'results/stage.py', 'guides/H.md', 'guides/P.md', 'guides/S.md')]
        result.update({str(path): digest(path) for path in paths})
        return result


if __name__ == '__main__':
    legacy.legacy.legacy.legacy.legacy.Runner = Runner
    sys.exit(legacy.legacy.legacy.legacy.legacy.main())
