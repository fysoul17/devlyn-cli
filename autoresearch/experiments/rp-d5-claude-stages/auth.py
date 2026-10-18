"""rp-d4 Claude snapshot semantics, including its bundled Codex transport file."""
import argparse
import importlib.util
import json
from pathlib import Path
import subprocess

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('auth_rpd4_rpd5', HERE.parent / 'rp-d4-helper-report/auth.py')
legacy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(legacy)
claude, codex = legacy.claude, legacy.codex
model_auth = claude_model_auth = legacy.claude_model_auth
codex_account, preflight, for_engine = legacy.codex_account, legacy.preflight, legacy.for_engine
directory, read_private, write_private = legacy.directory, legacy.read_private, legacy.write_private
digest, encoded = legacy.digest, legacy.encoded


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('destination', type=Path)
    args = parser.parse_args()
    try:
        claude.bootstrap(args.destination)
        _, binding = model_auth(args.destination)
        print(json.dumps(dict(auth_manifest_sha256=binding)))
        return 0
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError):
        print(json.dumps(dict(status='BLOCKED', reason='snapshot-bootstrap-failed')))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
