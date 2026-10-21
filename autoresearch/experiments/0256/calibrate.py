"""Run 0233's frozen calibration overlays by path."""
import importlib.util
from pathlib import Path

_path = Path(__file__).resolve().parent.parent / '0233/calibrate.py'
_spec = importlib.util.spec_from_file_location('calibrate_0233_0256', _path)
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)
run = _module.run


if __name__ == '__main__':
    import json
    result = run()
    print(json.dumps(dict(references=len(result), results=result), indent=2))
