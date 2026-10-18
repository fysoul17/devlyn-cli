"""Unchanged rp-d6 snapshots, account binding and credential scans."""
import importlib.util
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('auth_rpd6_rpd8', HERE.parent / 'rp-d6-claude-delivery/auth.py')
legacy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(legacy)
claude, codex = legacy.claude, legacy.codex
model_auth, claude_model_auth = legacy.model_auth, legacy.claude_model_auth
bootstrap = legacy.bootstrap
codex_account, preflight, for_engine = legacy.codex_account, legacy.preflight, legacy.for_engine
directory, read_private, write_private = legacy.directory, legacy.read_private, legacy.write_private
digest, encoded = legacy.digest, legacy.encoded

if __name__ == '__main__':
    raise SystemExit(legacy.legacy.main())
