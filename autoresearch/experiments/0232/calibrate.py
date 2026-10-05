"""Model-free calibration of the 0231 evaluator: calibrate.py <runtime.json> <out-dir> [repeats].

0222's variants and expectations, unchanged, run through 0231's check (image v3; oracle visible only to check
containers). Acceptance: 0222's 23/23.
"""
import importlib.util
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


calibration = load('calibrate0222', HERE.parent / '0222/calibrate.py')
calibration.check = load('check0231', HERE / 'check.py')

if __name__ == '__main__':
    sys.exit(calibration.main(sys.argv[1], Path(sys.argv[2]).resolve(), int(sys.argv[3]) if len(sys.argv) > 3 else 1))
