"""Unchanged rp-d6 credential snapshots, scans and 6300-second Claude floor."""
import importlib.util
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('auth_rpd6_rpd7', HERE.parent / 'rp-d6-claude-delivery/auth.py')
legacy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(legacy)

if __name__ == '__main__':
    raise SystemExit(legacy.legacy.main())
