"""Separate rp-d3 Codex and rp-d2 Claude snapshots; never transfer Claude's expiry floor."""
import argparse
import importlib.util
import json
from pathlib import Path
import subprocess

HERE = Path(__file__).resolve().parent


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


codex = load('auth_rpd3_rpd4', HERE.parent / 'rp-d3-prompt-ablation/auth.py')
claude_stage = load('stage_rpd2_auth_rpd4', HERE.parent / 'rp-d2-report-lines/stage.py')
claude = claude_stage.auth
model_auth, bootstrap = codex.model_auth, codex.bootstrap
directory, read_private, write_private = codex.directory, codex.read_private, codex.write_private
oauth, digest, encoded = codex.oauth, codex.digest, codex.encoded


def codex_account(path):
    return codex.account(read_private(directory(path), 'codex.json'))


def claude_model_auth(path):
    manifest, binding = claude_stage.model_auth(path)
    codex_account(path)  # Same canonical Codex OAuth validation in both transports.
    return manifest, binding


def for_engine(runtime, engine):
    if engine not in ('codex', 'claude'):
        raise ValueError('unregistered authentication engine')
    selected = dict(runtime, auth_engine=engine)
    if engine == 'claude':
        selected.update(auth=runtime['claude_auth'], account=runtime['claude_account'],
                        auth_manifest_sha256=runtime['claude_auth_manifest_sha256'])
    return selected


def preflight(runtime):
    if runtime.get('auth_engine', 'codex') == 'codex':
        return codex.preflight(runtime)
    try:
        if codex_account(runtime['auth']) != runtime['codex_account']:
            raise claude.AuthError('Codex-account-binding-mismatch')
    except claude.AuthError as exc:
        return None, str(exc)
    except (OSError, ValueError, KeyError, TypeError):
        return None, 'guard-snapshot-validation-failed'
    return claude.preflight(runtime)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='engine', required=True)
    c = sub.add_parser('codex')
    c.add_argument('source', type=Path)
    c.add_argument('destination', type=Path)
    c = sub.add_parser('claude')
    c.add_argument('destination', type=Path)
    args = parser.parse_args()
    try:
        if args.engine == 'codex':
            _, binding = bootstrap(args.source, args.destination)
        else:
            claude.bootstrap(args.destination)
            _, binding = claude_model_auth(args.destination)
        print(json.dumps(dict(auth_manifest_sha256=binding)))
        return 0
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError):
        print(json.dumps(dict(status='BLOCKED', reason='snapshot-bootstrap-failed')))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
