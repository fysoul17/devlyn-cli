"""Run one registered 0219 screen cell: the 0218 runner with 0219 check-parity preparation."""
import importlib.util
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('run0218', HERE.parent / '0218/run_cell.py')
base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)
base.PREPARE = HERE / 'prepare.py'
# User authorized (2026-09-24) the account logged in at launch; pinned so a mid-screen switch pauses.
base.ACCOUNT = ('02b266ea50d2', '531f8e153d6b')

if __name__ == '__main__':
    sys.exit(base.run(int(sys.argv[1]), Path(sys.argv[2]).resolve()))
