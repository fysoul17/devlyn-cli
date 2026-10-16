"""Codex-only private snapshot; empty env-file preserves the frozen 0251 transport."""
import argparse
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('auth0251_rpd3', HERE.parent / '0251/auth.py')
legacy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(legacy)
directory, read_private, write_private = legacy.directory, legacy.read_private, legacy.write_private
digest, encoded = legacy.digest, legacy.encoded


def account(raw):
    try:
        value = json.loads(raw)['tokens']['account_id']
        token = json.loads(raw)['tokens']['access_token']
        if not isinstance(value, str) or not value.strip() or not isinstance(token, str) or not token.strip():
            raise ValueError
    except (ValueError, TypeError, KeyError):
        raise legacy.AuthError('invalid-Codex-account-or-access-token') from None
    return digest(value.encode())[:12]


def model_auth(path):
    root = directory(path)
    if {p.name for p in root.iterdir()} != {'codex.json', 'claude.env', 'manifest.json'}:
        raise legacy.AuthError('Codex-snapshot-file-set-mismatch')
    raw = read_private(root, 'manifest.json')
    manifest = json.loads(raw)
    contents = {name: read_private(root, name) for name in ('codex.json', 'claude.env')}
    expected = dict(schema_version=1, account=account(contents['codex.json']),
                    files={name: digest(data) for name, data in contents.items()})
    if contents['claude.env'] != b'' or manifest != expected or type(manifest['schema_version']) is not int:
        raise legacy.AuthError('Codex-snapshot-binding-mismatch')
    return manifest, digest(raw)


def bootstrap(source, destination):
    raw = Path(source).read_bytes()
    identity = account(raw)
    destination = Path(destination).absolute()
    if destination.parent.resolve(strict=True) != destination.parent:
        raise legacy.AuthError('auth-parent-symlink')
    destination.mkdir(mode=0o700)
    root = directory(destination)
    files = {'codex.json': raw, 'claude.env': b''}
    manifest = dict(schema_version=1, account=identity,
                    files={name: digest(data) for name, data in files.items()})
    for name, data in files.items():
        write_private(root, name, data)
    write_private(root, 'manifest.json', encoded(manifest))
    return model_auth(root)


def preflight(runtime):
    try:
        manifest, binding = model_auth(runtime['auth'])
        if binding != runtime['auth_manifest_sha256'] or manifest['account'] != runtime['codex_account'] or \
                manifest['account'] != runtime['account']:
            raise legacy.AuthError('Codex-account-or-manifest-binding-mismatch')
        return {'codex_account': manifest['account']}, None
    except legacy.AuthError as exc:
        return None, str(exc)
    except (OSError, ValueError, KeyError, TypeError):
        return None, 'Codex-snapshot-validation-failed'


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path, help='explicit Codex auth.json source')
    parser.add_argument('destination', type=Path)
    args = parser.parse_args()
    _, binding = bootstrap(args.source, args.destination)
    print(json.dumps(dict(auth_manifest_sha256=binding)))
