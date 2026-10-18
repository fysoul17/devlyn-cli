"""rp-d4 snapshots, account binding, credential scans and Claude lifetime floor."""
import importlib.util
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('auth_rpd4_rpd6', HERE.parent / 'rp-d4-helper-report/auth.py')
legacy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(legacy)
claude, codex = legacy.claude, legacy.codex
model_auth, claude_model_auth = legacy.model_auth, legacy.claude_model_auth
bootstrap = legacy.bootstrap
codex_account, preflight, for_engine = legacy.codex_account, legacy.preflight, legacy.for_engine
directory, read_private, write_private = legacy.directory, legacy.read_private, legacy.write_private
digest, encoded = legacy.digest, legacy.encoded

if __name__ == '__main__':
    raise SystemExit(legacy.main())
