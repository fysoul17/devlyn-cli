"""Prospective fixed auth: snapshot once, then validate only the sealed private copy."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re
import stat
import subprocess
import time
import urllib.error
import urllib.request

MIN_TOKEN_SECONDS = 6300
PROFILE_URL = 'https://api.anthropic.com/api/oauth/profile'
TOKEN = 'CLAUDE_CODE_OAUTH_TOKEN'
SCOPES = 'CLAUDE_CODE_OAUTH_SCOPES'
OPTIONAL = {'subscriptionType': 'CLAUDE_CODE_SUBSCRIPTION_TYPE',
            'rateLimitTier': 'CLAUDE_CODE_RATE_LIMIT_TIER'}
HOST_OVERRIDES = ('CLAUDE_CONFIG_DIR', 'CLAUDE_SECURESTORAGE_CONFIG_DIR', 'CODEX_HOME',
                  TOKEN, 'ANTHROPIC_AUTH_TOKEN', 'ANTHROPIC_API_KEY', 'OPENAI_API_KEY')


class AuthError(ValueError):
    """Only fixed, nonsecret refusal descriptions belong in this exception."""


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def encoded(value):
    return (json.dumps(value, indent=2, sort_keys=True) + '\n').encode()


def value(text):
    if not isinstance(text, str) or any(c in text for c in '\r\n\0'):
        raise AuthError('invalid-auth-environment-value')
    return text


def lifetime(expires):
    if type(expires) not in (int, float) or not math.isfinite(expires):
        raise AuthError('invalid-auth-expiry')
    remaining = expires / 1000 - time.time()
    if remaining < MIN_TOKEN_SECONDS:
        raise AuthError('frozen-auth-lifetime-below-6300-seconds')
    return int(remaining)


def profile(token):
    request = urllib.request.Request(PROFILE_URL, headers={
        'Authorization': 'Bearer ' + token, 'anthropic-beta': 'oauth-2025-04-20'})
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            result = json.load(response)
        identities = [result['account']['uuid'], result['organization']['uuid']]
        if any(not isinstance(item, str) or not item for item in identities):
            raise ValueError('invalid identity')
        return [digest(item.encode())[:12] for item in identities]
    except urllib.error.HTTPError as exc:
        exc.close()
        raise AuthError('frozen-auth-profile-unavailable') from None
    except (OSError, ValueError, KeyError, TypeError):
        raise AuthError('frozen-auth-profile-unavailable') from None


def directory(path):
    path = Path(path).absolute()
    if path.resolve(strict=True) != path:
        raise AuthError('auth-directory-symlink')
    info = path.lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) != 0o700:
        raise AuthError('auth-directory-not-private')
    return path


def read_private(root, name):
    fd = os.open(root / name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, 'rb') as stream:
        info = os.fstat(stream.fileno())
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid()
                or stat.S_IMODE(info.st_mode) != 0o400 or info.st_nlink != 1):
            raise AuthError('auth-file-not-private-regular')
        return stream.read()


def write_private(root, name, raw):
    fd = os.open(root / name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o400)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(raw)


def bootstrap(destination: Path):
    """Read default macOS Keychain Claude OAuth and ~/.codex/auth.json exactly once."""
    if any(os.environ.get(name) for name in HOST_OVERRIDES):
        raise AuthError('auth-bootstrap-requires-default-host-sources')
    destination = Path(destination).absolute()
    if destination.parent.resolve(strict=True) != destination.parent:
        raise AuthError('auth-parent-symlink')
    destination.mkdir(mode=0o700)
    root = directory(destination)
    # Capture both sources once; never persist the Claude refresh credential.
    raw = subprocess.run(['security', 'find-generic-password', '-s', 'Claude Code-credentials', '-w'],
                         capture_output=True, check=True, timeout=20).stdout
    codex = (Path.home() / '.codex/auth.json').read_bytes()
    oauth = json.loads(raw)['claudeAiOauth']
    token = value(oauth['accessToken'])
    if not token:
        raise AuthError('missing-claude-access-token')
    scopes = oauth['scopes']
    if (not isinstance(scopes, list) or not scopes
            or any(not isinstance(scope, str) or not scope or any(c.isspace() for c in scope) for scope in scopes)):
        raise AuthError('invalid-claude-scopes')
    env = {TOKEN: token, SCOPES: value(' '.join(scopes))}
    for field, key in OPTIONAL.items():
        if oauth.get(field) is not None:
            env[key] = value(oauth[field])
    expires = oauth['expiresAt']
    lifetime(expires)
    if not isinstance(json.loads(codex), dict):
        raise AuthError('invalid-codex-auth-object')
    account = profile(token)
    lifetime(expires)
    files = {'claude.env': ''.join(f'{key}={item}\n' for key, item in env.items()).encode(),
             'codex.json': codex}
    manifest = {'schema_version': 1, 'account': account, 'expires_at_ms': expires,
                'files': {name: digest(content) for name, content in files.items()}}
    try:
        for name, content in files.items():
            write_private(root, name, content)
        write_private(root, 'manifest.json', encoded(manifest))
    except OSError:
        raise AuthError('auth-write-failed-private-destination-retained') from None
    return manifest


def preflight(runtime: dict):
    """No host reads or refresh: mismatch/expiry rejects this cell before dispatch."""
    try:
        root = directory(runtime['auth'])
        expected = runtime['auth_manifest_sha256']
        if not isinstance(expected, str) or not re.fullmatch('[a-f0-9]{64}', expected):
            raise AuthError('missing-auth-manifest-binding')
        if {p.name for p in root.iterdir()} != {'manifest.json', 'claude.env', 'codex.json'}:
            raise AuthError('auth-snapshot-file-set-mismatch')
        raw = read_private(root, 'manifest.json')
        if digest(raw) != expected:
            raise AuthError('auth-manifest-hash-mismatch')
        manifest = json.loads(raw)
        if (set(manifest) != {'schema_version', 'account', 'expires_at_ms', 'files'}
                or manifest['schema_version'] != 1 or type(manifest['schema_version']) is not int
                or set(manifest['files']) != {'claude.env', 'codex.json'}):
            raise AuthError('invalid-auth-manifest')
        account = manifest['account']
        if (not isinstance(account, list) or len(account) != 2
                or any(not isinstance(item, str) or not re.fullmatch('[a-f0-9]{12}', item) for item in account)
                or account != runtime['account']):
            raise AuthError('auth-account-binding-mismatch')
        lifetime(manifest['expires_at_ms'])
        contents = {name: read_private(root, name) for name in manifest['files']}
        if any(digest(raw) != manifest['files'][name] for name, raw in contents.items()):
            raise AuthError('auth-file-hash-mismatch')
        env = {}
        for line in contents['claude.env'].decode().splitlines():
            key, separator, item = line.partition('=')
            if not separator or key in env or key not in {TOKEN, SCOPES, *OPTIONAL.values()}:
                raise AuthError('invalid-frozen-claude-environment')
            env[key] = value(item)
        if not env.get(TOKEN) or not env.get(SCOPES):
            raise AuthError('missing-frozen-claude-environment')
        if profile(env[TOKEN]) != account:
            raise AuthError('auth-account-profile-mismatch')
        return {'account': account, 'token_seconds_left': lifetime(manifest['expires_at_ms'])}, None
    except AuthError as exc:
        return None, str(exc)
    except (OSError, ValueError, KeyError, TypeError):
        return None, 'fixed-auth-validation-failed'


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('destination', type=Path)
    args = parser.parse_args(argv)
    try:
        manifest = bootstrap(args.destination)
        print(json.dumps({'manifest': manifest, 'auth_manifest_sha256': digest(encoded(manifest))}))
        return 0
    except Exception as exc:
        print(json.dumps({'status': 'BLOCKED', 'reason': str(exc) if isinstance(exc, AuthError)
                          else 'auth-bootstrap-failed'}))
        return 3


if __name__ == '__main__':
    raise SystemExit(main())
