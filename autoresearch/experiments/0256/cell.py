"""0256 owner lifecycle: import 0237's unchanged --init run."""
import importlib.util
from pathlib import Path

_path = Path(__file__).resolve().parent.parent / '0237/cell-init-v1.py'
_spec = importlib.util.spec_from_file_location('cell_init_0237_0256', _path)
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)
run = _module.run
