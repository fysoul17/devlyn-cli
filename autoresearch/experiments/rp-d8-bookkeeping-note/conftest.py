"""Offline boundary: only local Git processes, no sockets or experiment cells."""
from pathlib import Path
import socket
import subprocess
import urllib.request

import pytest


@pytest.fixture(autouse=True)
def offline_boundary(monkeypatch):
    def forbidden(*_args, **_kwargs):
        pytest.fail('network access or experiment dispatch is forbidden in offline tests')

    for target, name in ((socket, 'create_connection'), (socket.socket, 'connect'),
                         (urllib.request, 'urlopen')):
        monkeypatch.setattr(target, name, forbidden)
    original = subprocess.Popen

    def local_git(argv, *args, **kwargs):
        assert isinstance(argv, (list, tuple)) and Path(argv[0]).name == 'git', 'only local Git fixtures may execute'
        assert not kwargs.get('shell') and not any(value in ('push', 'pull', 'fetch', 'ls-remote') for value in argv)
        assert not any(str(value).startswith(('http://', 'https://', 'ssh://', 'git@')) for value in argv)
        return original(argv, *args, **kwargs)

    monkeypatch.setattr(subprocess, 'Popen', local_git)
