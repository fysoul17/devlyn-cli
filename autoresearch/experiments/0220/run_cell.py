"""Run one registered 0220 screen cell: the 0219 runner with 0220 completion-reserve preparation."""
import importlib.util
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('run0219', HERE.parent / '0219/run_cell.py')
run0219 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(run0219)
run0219.base.PREPARE = HERE / 'prepare.py'

if __name__ == '__main__':
    sys.exit(run0219.base.run(int(sys.argv[1]), Path(sys.argv[2]).resolve()))
