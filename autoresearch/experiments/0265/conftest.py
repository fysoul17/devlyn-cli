"""Every test in this folder runs with the host's logins and the network out of reach (a test once reached the real
login snapshot before it was patched, 2026-11-11). For each test: a `security` first on PATH that only records its
call (the keychain), a urllib.request.urlopen that records and refuses (the profile and usage endpoints), and
Path.home() in an empty folder (the default Codex login under ~/.codex, ~/.claude) unless the test itself points HOME
at a fake home of its own. A test that reaches the keychain or the network fails, by what it called; one that reads the
home finds nothing. A test's own fakes still win while it holds them. HOME itself is left as it is (Git's global
configuration in the tests' repositories), and module constants computed at import (the runtime and archive roots)
keep the real home: read-only, no credential."""
import os
from pathlib import Path
import urllib.error
import urllib.request

import pytest


@pytest.fixture(autouse=True)
def host_logins_out_of_reach(tmp_path_factory, monkeypatch):
    fence = tmp_path_factory.mktemp('fence')
    reached = fence / 'reached'
    (fence / 'bin').mkdir()
    (fence / 'home').mkdir()
    security = fence / 'bin/security'
    security.write_text(f'#!/bin/sh\necho "security $*" >> "{reached}"\nexit 1\n')
    security.chmod(0o755)
    monkeypatch.setenv('PATH', f'{fence / "bin"}{os.pathsep}{os.environ["PATH"]}')
    host = os.environ.get('HOME')

    def home(cls):
        own = os.environ.get('HOME')
        return cls(own) if own and own != host else cls(fence / 'home')
    monkeypatch.setattr(Path, 'home', classmethod(home))

    def refused(request, *args, **kwargs):
        with reached.open('a') as stream:
            stream.write(f'urlopen {getattr(request, "full_url", request)}\n')
        raise urllib.error.URLError('the network is out of reach in tests')
    monkeypatch.setattr(urllib.request, 'urlopen', refused)
    yield
    if reached.exists():
        pytest.fail('the test reached the host keychain or the network:\n' + reached.read_text())
