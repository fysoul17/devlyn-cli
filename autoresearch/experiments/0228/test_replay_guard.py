#!/usr/bin/env python3
"""Ownership-guard evidence for the 0228 replay runner (Addendum C2): no experiment step may change a path the
experiment did not create. Usage: test_replay_guard.py <replay.py> [--disable-guard]. Exit 0 = every check passed.

Static: every file-mutating call in the runner sits inside one of the guarded helpers.
Dynamic: each helper refuses an outside target before any mutating primitive runs (every primitive is intercepted, and
every outside target is a path that does not exist), and allows the three experiment-owned roots. `--disable-guard`
replaces the guard with the identity function to show the dynamic checks detect a missing guard (it must be RED)."""
import ast
import io
import os
import runpy
import shutil
import subprocess
import sys
import tarfile
from pathlib import Path

HELPERS = {'owned', 'write_bytes', 'dump', 'append_line', 'open_out', 'make_dir', 'new_dir', 'copy_file', 'copy_tree',
           'remove_file', 'remove_tree', 'make_symlink', 'set_mode', 'chmod_acl', 'acl_tree', 'acl_ensure', 'acl_clear',
           'extract'}
RECEIVER_CALLS = {'os': {'chmod', 'lchmod', 'chown', 'lchown', 'remove', 'unlink', 'rmdir', 'mkdir', 'makedirs', 'rename',
                         'replace', 'link', 'symlink', 'truncate', 'chflags', 'utime', 'open'},
                  'shutil': {'copy', 'copy2', 'copyfile', 'copytree', 'move', 'rmtree', 'chown', 'copymode', 'copystat'}}
ANY_RECEIVER = {'chmod', 'lchmod', 'chown', 'unlink', 'mkdir', 'rmdir', 'write_text', 'write_bytes', 'symlink_to',
                'hardlink_to', 'touch', 'rename', 'extractall', 'extract'}
SAFE_RECEIVERS = {'os', 'shutil', 're', 'json', 'time', 'signal', 'subprocess', 'hashlib', 'runpy', 'shlex'}
COMMANDS = {'chmod', '/bin/chmod', 'chown', 'rm', '/bin/rm', 'mv', 'cp', 'ln', 'touch', 'mkdir', 'tar', 'ditto',
            'rsync', 'install', 'chflags', 'xattr', 'setfacl'}


def static_violations(source):
    tree = ast.parse(source)
    parents = {child: node for node in ast.walk(tree) for child in ast.iter_child_nodes(node)}

    def enclosing(node):
        while node in parents:
            node = parents[node]
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                return node.name
        return None

    def write_mode(node, index):
        mode = node.args[index] if len(node.args) > index else next(
            (keyword.value for keyword in node.keywords if keyword.arg == 'mode'), None)
        if mode is None:
            return False
        return not isinstance(mode, ast.Constant) or any(flag in str(mode.value) for flag in 'wax+')

    found = []
    for node in ast.walk(tree):
        name = None
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Attribute):
                receiver = func.value.id if isinstance(func.value, ast.Name) else None
                if receiver in RECEIVER_CALLS and func.attr in RECEIVER_CALLS[receiver]:
                    name = f'{receiver}.{func.attr}'
                elif receiver not in SAFE_RECEIVERS and (
                        func.attr in ANY_RECEIVER
                        or (func.attr == 'replace' and len(node.args) == 1)  # Path.replace(target), not str.replace
                        or (func.attr == 'open' and write_mode(node, 0))):
                    name = f'.{func.attr}'
            elif isinstance(func, ast.Name) and func.id == 'open' and write_mode(node, 1):
                name = 'open(write)'
        elif isinstance(node, ast.Constant) and isinstance(node.value, str) and node.value in COMMANDS:
            name = f'command {node.value!r}'
        elif isinstance(node, (ast.Import, ast.ImportFrom)) and isinstance(node, ast.ImportFrom) \
                and node.module in ('os', 'shutil') and any(a.name in RECEIVER_CALLS[node.module] for a in node.names):
            name = f'from {node.module} import (mutating alias)'
        if name and enclosing(node) not in HELPERS:
            found.append(f'line {node.lineno}: {name} in {enclosing(node)}')
    return found


def refuses(call):
    try:
        call()
    except SystemExit as exc:
        return any(text in str(exc) for text in ('refusing to modify', 'leaves the destination',
                                                 'not a file or directory', 'duplicate member'))
    except Exception:  # failing some other way is not a refusal
        return False
    return False


class Intercept:
    """Replace every mutating primitive the runner could reach with a recorder, so nothing outside is ever touched."""

    def __init__(self):
        self.calls = []
        self.saved = []

    def patch(self, owner, name, *, writes_only=False):
        original = getattr(owner, name)

        def recorder(*args, **kwargs):
            if writes_only and not (len(args) > 1 and isinstance(args[1], int)
                                    and args[1] & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND)):
                return original(*args, **kwargs)
            self.calls.append(f'{getattr(owner, "__name__", owner)}.{name}')
            raise SystemExit('intercepted mutation')

        self.saved.append((owner, name, original))
        setattr(owner, name, recorder)

    def __enter__(self):
        for name in ('chmod', 'unlink', 'remove', 'rmdir', 'mkdir', 'makedirs', 'rename', 'replace', 'symlink', 'link',
                     'truncate'):
            self.patch(os, name)
        self.patch(os, 'open', writes_only=True)
        for name in ('copyfile', 'copy', 'copy2', 'copytree', 'rmtree', 'move'):
            self.patch(shutil, name)
        for name in ('mkdir', 'unlink', 'symlink_to', 'touch', 'write_text', 'write_bytes', 'rename', 'replace',
                     'chmod'):
            self.patch(Path, name)
        self.patch(subprocess, 'run')
        self.patch(tarfile.TarFile, 'extractall')
        return self

    def __exit__(self, *exc):
        for owner, name, original in reversed(self.saved):
            setattr(owner, name, original)


def dynamic_failures(runner, disable_guard):
    m = runpy.run_path(runner)
    failures = []
    if 'owned' not in m:
        return ['no ownership guard (`owned`) in the runner']
    if disable_guard:  # run_path returns a copy of the globals; patch the dictionary the helpers actually use
        m['dump'].__globals__['owned'] = m['owned'] = lambda path: Path(path)
    absent = Path('/private/tmp/guard-absent-0228')
    outside = [absent / 'x', Path.home() / 'guard-absent-0228/x', Path('/Users/Shared/devlyn-vr/guard-absent/x'),
               Path('/Users/Shared/devlyn-vr-0228-dev/../guard-absent'), Path('relative/x')]
    inside = [m['SRC'] / 'x', m['DEV'] / 'x', Path('/Users/Shared/devlyn-vr-0227-diag/x'), m['DEV']]
    for path in outside:
        if not refuses(lambda: m['owned'](path)):
            failures.append(f'owned() allowed {path}')
    for path in inside:
        if refuses(lambda: m['owned'](path)):
            failures.append(f'owned() refused {path}')
    helpers = {
        'dump': lambda: m['dump'](absent / 'a.json', {}),
        'write_bytes': lambda: m['write_bytes'](absent / 'a', b'x'),
        'append_line': lambda: m['append_line'](absent / 'a', 'x'),
        'open_out': lambda: m['open_out'](absent / 'a'),
        'make_dir': lambda: m['make_dir'](absent / 'd'),
        'new_dir': lambda: m['new_dir'](absent / 'd'),
        'copy_file': lambda: m['copy_file'](Path('/etc/hosts'), absent / 'a'),
        'copy_tree': lambda: m['copy_tree'](Path('/etc/ssh'), absent / 't'),
        'remove_file': lambda: m['remove_file'](absent / 'a'),
        'remove_tree': lambda: m['remove_tree'](absent / 't'),
        'make_symlink': lambda: m['make_symlink'](absent / 'l', Path('/etc')),
        'set_mode': lambda: m['set_mode'](absent / 'a', 0),
        'chmod_acl': lambda: m['chmod_acl'](['+a', 'user:_devlynjudge allow read'], [absent / 'a']),
        'acl_tree': lambda: m['acl_tree'](absent, ['user:_devlynjudge allow read']),
        'acl_ensure': lambda: m['acl_ensure'](absent / 'a', 'user:_devlynjudge allow read'),
        'acl_clear': lambda: m['acl_clear'](absent / 'a'),
        'extract': lambda: m['extract'](b'', absent / 'e'),
    }
    with Intercept() as intercept:
        for name, call in helpers.items():
            before = len(intercept.calls)
            if name not in m:
                failures.append(f'helper {name} missing')
                continue
            refused = refuses(call)
            acted = intercept.calls[before:]
            if acted:
                failures.append(f'{name} reached a mutating primitive for an outside target: {acted}')
            elif not refused:
                failures.append(f'{name} did not refuse an outside target')
    if absent.exists():
        failures.append(f'{absent} was created')
    if disable_guard:
        return failures

    # A parent symlink, a symlink destination and tar members other than unique files and directories are refused.
    # Setup is a real mutation inside the 0228 root; every rejection then runs under interception, so a regression
    # would be recorded instead of writing anywhere.
    scratch = m['DEV'] / 'scratch/guard-test'
    m['remove_tree'](scratch)
    m['make_dir'](scratch)
    m['make_symlink'](scratch / 'link-out', absent)  # dangling: the outside target never exists
    tars = {}
    for label, members in (('dotdot', [('../../../../private/tmp/guard-absent-0228', 'file', None)]),
                           ('absolute', [('/private/tmp/guard-absent-0228', 'file', None)]),
                           ('hardlink', [('h', 'link', 'x')]),
                           ('symlink', [('l', 'sym', '/private/tmp')]),
                           ('duplicate', [('a', 'file', None), ('a', 'file', None)])):
        buffer = io.BytesIO()
        with tarfile.open(fileobj=buffer, mode='w') as archive:
            for name, kind, target in members:
                info = tarfile.TarInfo(name)
                if kind == 'file':
                    info.size = 1
                    archive.addfile(info, io.BytesIO(b'x'))
                else:
                    info.type = tarfile.LNKTYPE if kind == 'link' else tarfile.SYMTYPE
                    info.linkname = target
                    archive.addfile(info)
        tars[label] = buffer.getvalue()
    plain = io.BytesIO()
    with tarfile.open(fileobj=plain, mode='w') as archive:
        info = tarfile.TarInfo('f')
        info.size = 1
        archive.addfile(info, io.BytesIO(b'x'))
    cases = {'parent symlink': lambda: m['owned'](scratch / 'link-out/x'),
             'make_dir on a symlink': lambda: m['make_dir'](scratch / 'link-out'),
             'extract into a symlink': lambda: m['extract'](plain.getvalue(), scratch / 'link-out')}
    cases.update({f'extract {label} tar': (lambda raw=raw, label=label: m['extract'](raw, scratch / label))
                  for label, raw in tars.items()})
    with Intercept() as intercept:
        for label, call in cases.items():
            before = len(intercept.calls)
            refused = refuses(call)
            acted = intercept.calls[before:]
            if acted:
                failures.append(f'{label}: reached a mutating primitive: {acted}')
            elif not refused:
                failures.append(f'{label}: not refused')
    m['remove_tree'](scratch)
    if absent.exists():
        failures.append(f'{absent} was created')
    return failures


def main(runner, disable_guard=False):
    source = Path(runner).read_text(encoding='utf-8')
    static = static_violations(source)
    dynamic = dynamic_failures(runner, disable_guard)
    print(f'runner: {runner}' + (' (guard disabled)' if disable_guard else ''))
    print(f'static: {len(static)} mutating call(s) outside the guarded helpers')
    for line in static:
        print(f'  {line}')
    print(f'dynamic: {len(dynamic)} failure(s)')
    for line in dynamic:
        print(f'  {line}')
    verdict = 'GREEN' if not static and not dynamic else 'RED'
    print(verdict)
    return 0 if verdict == 'GREEN' else 1


if __name__ == '__main__':
    sys.exit(main(sys.argv[1], '--disable-guard' in sys.argv[2:]))
