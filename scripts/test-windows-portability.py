#!/usr/bin/env python3
"""Real npm/native-process portability checks; --package-root tests a downloaded install.

Pass unittest class/method names for focused development checks. No model calls.
"""
from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import locale
import os
from pathlib import Path
import re
import runpy
import shutil
import subprocess
import sys
import tarfile
import tempfile
import textwrap
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
PACKAGE_ROOT = None
SHORT_PAYLOAD = '한국어 프롬프트 — “정확 바이트” …\r\n마지막\n\n'.encode('utf-8')
PAYLOAD = SHORT_PAYLOAD * 1024
CURRENT_DEFAULTS = b'Without a pin, you are the executor.'
# The block's delivery default and cleanup rule.
CURRENT_RULES = (
    ('- Delivery — direct work edits the current checkout; deliver completed, verified requests with changes by project policy'
     ' (default PR and merge), following `_shared/task-completion.md` in `.claude/skills/` or `.agents/skills/` (project, else `~`).'
     ' With known concurrent writers, isolate before editing; on unexplained changes, pause writes until safe or isolated.'
     ' An ideate drain delivers every task. Explicit limits win; commit alone stays local.').encode(),
    b'Remove code your change makes unused; only report unrelated pre-existing dead code.')


def environment():
    env = {k: v for k, v in os.environ.items() if not k.startswith(('DEVLYN_', 'CODEX_MONITORED_', 'GIT_'))
           and k not in ('CODEX_BLOCKED', 'CODEX_BIN', 'CODEX_REAL_BIN', 'PYTHONUTF8', 'PYTHONIOENCODING', 'CODEX_HOME', 'CLAUDE_CONFIG_DIR')}
    env.update(GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM='1', PYTHONDONTWRITEBYTECODE='1')
    return env


def run(argv, *, cwd=None, env=None, code=0, timeout=40):
    proc = subprocess.run([str(arg) for arg in argv], cwd=cwd, env=env or environment(),
                          stdin=subprocess.DEVNULL, capture_output=True, timeout=timeout)
    if code is not None:
        assert proc.returncode == code, (argv, proc.returncode, proc.stdout, proc.stderr)
    return proc


def npm(args, temp):
    binary = Path(shutil.which('npm') or 'npm').resolve()
    if os.name == 'nt':
        # Invoke npm's installed Node entrypoint; fixture argv never passes through cmd.exe.
        cli = binary.parent / 'node_modules/npm/bin/npm-cli.js'
        command = [shutil.which('node'), cli]
    else:
        command = [str(binary)]
    return run([*command, *args, '--cache', os.environ.get('npm_config_cache', str(temp / 'npm-cache'))], timeout=90)


def helper(name):
    return runpy.run_path(str((PACKAGE_ROOT or ROOT) / 'config/skills/_shared' / (name + '.py')))


def wait_for(predicate, timeout=8):
    deadline = time.monotonic() + timeout
    while not predicate():
        assert time.monotonic() < deadline, 'fixture did not become ready'
        time.sleep(0.03)


def process_running(pid):
    if os.name == 'nt':
        import ctypes
        from ctypes import wintypes
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        kernel.OpenProcess.restype = wintypes.HANDLE
        kernel.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
        kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        handle = kernel.OpenProcess(0x100000, False, pid)
        if not handle:
            if ctypes.get_last_error() == 87:  # PID no longer exists.
                return False
            raise ctypes.WinError(ctypes.get_last_error())
        try:
            result = kernel.WaitForSingleObject(handle, 0)
            assert result in (0, 258), result
            return result == 258
        finally:
            kernel.CloseHandle(handle)
    if sys.platform.startswith('linux'):
        try:
            state = Path(f'/proc/{pid}/stat').read_text(encoding='utf-8').rsplit(')', 1)[1].split()[0]
        except FileNotFoundError:
            return False
        return state != 'Z'
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    return True


class PackageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix='devlyn-package-')
        cls.root = Path(cls.temp.name).resolve()
        if PACKAGE_ROOT:
            cls.package = PACKAGE_ROOT
        else:
            # Packed with its own prepack and postpack, as the publish workflow packs it: they write and then remove the
            # release manifest and the generated payload the package carries.
            packed = npm(['pack', str(ROOT), '--json', '--pack-destination', str(cls.root)], cls.root)
            tarball = cls.root / json.loads(packed.stdout)[0]['filename']
            print('packed artifact sha256=' + hashlib.sha256(tarball.read_bytes()).hexdigest(), flush=True)
            npm(['install', '--prefix', str(cls.root / 'installed'), '--offline', '--ignore-scripts',
                 '--no-audit', '--no-fund', str(tarball)], cls.root)
            cls.package = cls.root / 'installed/node_modules/devlyn-cli'
        cls.preload = cls.root / 'homedir.cjs'
        cls.preload.write_text("require('os').homedir = () => process.env.DEVLYN_TEST_HOME;\n", encoding='utf-8')
        cls.invoker = cls.root / 'invoke.cjs'
        cls.invoker.write_text("""const fs = require('fs'), Module = require('module');
const filename = process.argv[2];
const m = new Module(filename); m.filename = filename; m.paths = Module._nodeModulePaths(require('path').dirname(filename));
const source = fs.readFileSync(filename, 'utf8').split('const args = process.argv.slice(2);')[0];
m._compile(source + '\\n' + process.argv[3], filename);
""", encoding='utf-8')

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def setUp(self):
        self.case = Path(tempfile.mkdtemp(dir=self.root, prefix='설치 '))
        self.project = self.case / 'project'; self.project.mkdir()
        self.home = self.case / 'agent-home'; self.home.mkdir()
        self.env = environment(); self.env['DEVLYN_TEST_HOME'] = str(self.home)

    def invoke(self, body, package=None, code=0):
        self.env.update(HOME=str(self.home), USERPROFILE=str(self.home))
        return run(['node', '--require', self.preload, self.invoker,
                    (package or self.package) / 'bin/devlyn.js', body], cwd=self.project, env=self.env, code=code)

    def cli(self, *args, code=0):
        self.env.update(HOME=str(self.home), USERPROFILE=str(self.home))
        return run(['node', '--require', self.preload, self.package / 'bin/devlyn.js', *args],
                   cwd=self.project, env=self.env, code=code)

    def interact(self, prompts, options='{}', code=0):
        # A terminal that types one list of keys into each menu as it opens (raw mode on).
        return self.invoke(f"""
const prompts = {json.dumps(prompts)};
const stdin = Object.assign(new (require('events'))(), {{ isTTY: true, resume() {{}}, pause() {{}}, setEncoding() {{}},
  setRawMode(on) {{ if (on) setImmediate(() => prompts.shift().forEach((key) => stdin.emit('data', key))); }} }});
Object.defineProperty(process, 'stdin', {{ value: stdin }});
init({options});
""", code=code)

    def roots(self):
        return [self.project / '.agents/skills', self.project / '.claude/skills',
                self.home / '.agents/skills', self.home / '.codex/skills', self.home / '.claude/skills']

    def markers(self, base):
        return {p.parent.parent.name for p in base.glob('.*/skills/.devlyn-install.json')}

    def test_the_installed_package_is_a_release_an_app_installs(self):
        # Prediction (4.2.26 and 4.3.0 were packed without their prepack, so without release.json): the package npm
        # installs carries its release, which materializes into a store and verifies there, as Devlyn's built-in
        # harness installs it.
        last = lambda result: json.loads(result.stdout.decode('utf-8').strip().splitlines()[-1])
        made = last(self.cli('release', '--materialize', '--source', str(self.package), '--store', str(self.case / 'store'),
                             '--json'))
        self.assertTrue(made['ok'], made)
        release = made['data']['release']
        self.assertEqual(release['version'], json.loads((self.package / 'package.json').read_bytes())['version'])
        verified = last(self.cli('release', '--verify', '--root', release['root'], '--json'))
        self.assertEqual(verified['data']['release']['digest'], release['digest'])

    def test_claude_target_leaves_user_claude_files_alone(self):
        # 4.1.0 sets prompt caching in the project settings; ~/.claude/settings.json is the user's.
        # A global install writes skills only, so the user's ~/.claude/commands stay too.
        dest = self.home / '.claude/settings.json'
        command = self.home / '.claude/commands/devlyn.resolve.md'
        command.parent.mkdir(parents=True); command.write_bytes(b'my command\r\n')
        for before in (None, b'SECRET-not-json', b'{"env": {"ENABLE_PROMPT_CACHING_1H": "false"}}\r\n'):
            for args in (['-y', '--claude'], ['-y', '--global', '--claude']):
                with self.subTest(before=before, args=args):
                    if before is not None:
                        dest.write_bytes(before)
                    result = self.cli(*args)
                    self.assertNotIn(b'SECRET', result.stdout + result.stderr)
                    self.assertEqual(dest.read_bytes() if dest.exists() else None, before)
                    if '--global' in args:
                        self.assertFalse(command.exists())
        settings = json.loads((self.project / '.claude/settings.json').read_bytes())
        self.assertEqual(settings['env']['ENABLE_PROMPT_CACHING_1H'], 'true')

    def test_yes_keeps_claude_where_this_project_has_it(self):
        colon = '\uf03a' if os.name == 'nt' else ':'  # The name releases wrote where a colon cannot exist.
        body = b'# Old\n'
        version = json.loads((self.package / 'package.json').read_bytes())['version']
        stale = {'4.x': {'.claude/skills/devlyn-resolve/stale': body}, '3.x': {f'.claude/skills/devlyn{colon}resolve/SKILL.md': body},
                 '0.x': {'.claude/commands/devlyn.resolve.md': body}, 'none': {'.claude/skills/my-skill/SKILL.md': body},
                 # 4.0.1 put optional skills into .claude/skills without the Claude target.
                 'addons': {f'.claude/skills/{name}/SKILL.md': body for name in
                            ['devlyn-reap', 'devlyn-pencil-pull', *(f'devlyn{c}reap' for c in ('\uf03a', colon))]}}
        for case, planted in stale.items():
            with self.subTest(case=case):
                self.project = self.case / f'project-{case}'
                for path, data in planted.items():
                    (self.project / path).parent.mkdir(parents=True, exist_ok=True); (self.project / path).write_bytes(data)
                self.cli('-y')
                claude = case == '0.x'
                self.assertEqual(self.markers(self.project), {'.agents', '.claude'} if claude else {'.agents'})
                self.assertFalse((self.project / 'CLAUDE.md').exists())
                self.assertFalse((self.project / 'AGENTS.md').exists())
                for path, data in planted.items():
                    preserved = case == 'none' or (case == 'addons' and all(c not in path for c in (':', '\uf03a')))
                    self.assertEqual((self.project / path).exists() and (self.project / path).read_bytes() == data, preserved)
                if claude:
                    marker = json.loads((self.project / '.claude/skills/.devlyn-install.json').read_bytes())
                    self.assertEqual(marker['version'], version)
                    self.assertTrue((self.project / '.claude/skills/devlyn-ideate/SKILL.md').is_file())

    def test_install_and_update_leave_instruction_files_byte_identical(self):
        # Prediction: principles reach sessions from the release, so no install writes or reads a project copy, and an
        # old span alone is no install evidence: `-y` does not add the Claude target for it.
        body = 'Project-specific instructions outside this managed block take precedence over these defaults.\n\n# Old\n'
        block = (f'<!-- devlyn:instructions:begin sha256={hashlib.sha256(body.encode()).hexdigest()} -->\n'
                 f'{body}<!-- devlyn:instructions:end -->\n').encode()
        files = {'AGENTS.md': b'\xef\xbb\xbf# Team\r\n\r\n' + block + b'tail', 'CLAUDE.md': b'@AGENTS.md\n'}
        for name, data in files.items():
            (self.project / name).write_bytes(data)
        self.cli('-y')
        self.assertEqual(self.markers(self.project), {'.agents'})
        for args in (('-y', '--claude'), ('update',)):
            self.cli(*args)
            for name, data in files.items():
                self.assertEqual((self.project / name).read_bytes(), data, args)
        self.assertFalse((self.project / '.devlyn/instructions').exists())

    def test_project_install_refuses_the_home_folder(self):
        # There .claude/settings.json would apply to every project.
        link = self.case / 'home-link'
        if os.name == 'nt':
            run(['cmd.exe', '/d', '/c', 'mklink', '/J', link, self.project])
        else:
            link.symlink_to(self.project, target_is_directory=True)
        for home in (self.project, link):
            for args in (['-y'], ['-y', '--claude']):
                with self.subTest(home=home, args=args):
                    self.env['DEVLYN_TEST_HOME'] = str(home)
                    result = self.cli(*args, code=1)
                    self.assertIn(b'This project is your home folder, so its .claude/settings.json', result.stderr)
                    self.assertNotIn(b'    at ', result.stderr)
                    self.assertEqual(list(self.project.iterdir()), [])

    def test_claude_project_settings_merge_and_reinstall(self):
        # A new install adds only what the drain host needs — one-hour foreground Bash calls and one-hour prompt
        # caching — as new text laid out like its neighbours; every other byte stays, and a rerun changes none.
        dest = self.project / '.claude/settings.json'; dest.parent.mkdir()
        added = (b'"ENABLE_PROMPT_CACHING_1H": "true"', b'"BASH_MAX_TIMEOUT_MS": "3600000"')
        for before, after in (
                (None, b'{\n  "env": {\n    %s,\n    %s\n  }\n}\n' % added),
                # A byte order mark, CRLF, an escape and an owner integer above 2^53.
                (b'\xef\xbb\xbf{\r\n    "big": 12345678901234567890,\r\n    "env": {\r\n        "TEAM_VAR": "\\u00e9"\r\n    }\r\n}\r\n',
                 b'\xef\xbb\xbf{\r\n    "big": 12345678901234567890,\r\n    "env": {\r\n        "TEAM_VAR": "\\u00e9",\r\n'
                 b'        %s,\r\n        %s\r\n    }\r\n}\r\n' % added),
                # Tabs, no env, a repeated owner key and no final newline.
                (b'{\n\t"custom": {\n\t\t"keep": [1, 2]\n\t},\n\t"custom": 3\n}',
                 b'{\n\t"custom": {\n\t\t"keep": [1, 2]\n\t},\n\t"custom": 3,\n\t"env": {\n\t\t%s,\n\t\t%s\n\t}\n}' % added),
                (b'{\n  "env": {}\n}\n', b'{\n  "env": {\n    %s,\n    %s\n  }\n}\n' % added),
                (b'{"env": {"TEAM_VAR": "keep", "BASH_MAX_TIMEOUT_MS": "owner-value"}}',
                 b'{"env": {"TEAM_VAR": "keep", "BASH_MAX_TIMEOUT_MS": "owner-value", %s}}' % added[0]),
                (b'{"env": {"BASH_MAX_TIMEOUT_MS": "600000", "ENABLE_PROMPT_CACHING_1H": false}}', None),
                (b'{"custom": true, "env": {"ENABLE_PROMPT_CACHING_1H": "", "BASH_MAX_TIMEOUT_MS": "7200000"}}', None)):
            with self.subTest(before=before):
                dest.unlink(missing_ok=True)
                if before is not None:
                    dest.write_bytes(before)
                result = self.invoke('installClaudeCore();')
                self.assertEqual(dest.read_bytes(), after or before)
                self.assertNotIn(b'Retired devlyn settings', result.stdout)
                self.invoke('installClaudeCore();')
                self.assertEqual(dest.read_bytes(), after or before)
        self.assertFalse((self.home / '.claude').exists())

    def test_claude_settings_are_read_before_any_claude_write(self):
        # Settings the install cannot merge (or edit in one place, or write back byte for byte) leave the Claude
        # target as it was, with a clear message; a leading BOM, which Claude Code accepts, merges and stays.
        claude = self.project / '.claude'
        hook = claude / 'skills/_shared/resolve-stop-hook.py'
        self.seed_4_1(claude / 'skills')
        (self.project / 'CLAUDE.md').write_bytes(b'# Team rules\n\nUse pnpm.\n')
        settings = claude / 'settings.json'
        retired = {'type': 'command', 'command': 'python3 "$CLAUDE_PROJECT_DIR/.claude/skills/_shared/resolve-stop-hook.py"'}
        def tree():
            return {p: p.read_bytes() if p.is_file() else None for p in [self.project / 'CLAUDE.md', *claude.rglob('*')]}
        for invalid in (b'{"hooks": {"Stop": []},}\n', b'\xef\xbb\xbf[]', b'{"env": "x"}', b'{"env": {"A": "1"}, "env": {}}',
                        b'{"custom": "\xff"}'):
            with self.subTest(invalid=invalid):
                settings.write_bytes(invalid)
                before = tree()
                result = self.cli('-y', '--claude', code=1)
                self.assertIn(b'Cannot merge .claude/settings.json', result.stderr)
                self.assertNotIn(b'    at ', result.stderr)
                self.assertEqual(tree(), before)
        settings.write_bytes(b'\xef\xbb\xbf' + json.dumps({'custom': 1, 'hooks': {'Stop': [{'hooks': [retired]}]}}).encode())
        self.cli('-y', '--claude')
        # The install adds the keys; its cleanup removes the retired hook and the containers that removal emptied.
        self.assertEqual(settings.read_bytes(), b'\xef\xbb\xbf{"custom": 1, "env": {"ENABLE_PROMPT_CACHING_1H": "true", '
                                                b'"BASH_MAX_TIMEOUT_MS": "3600000"}}')
        self.assertFalse(hook.exists())

    def test_claude_install_ships_no_unreferenced_commit_conventions(self):
        # The managed block no longer points to commit conventions, so a new install adds none;
        # a copy an earlier release installed is the user's now and stays as it is.
        self.invoke('installClaudeCore();')
        conventions = self.project / '.claude/commit-conventions.md'
        self.assertFalse(conventions.exists())
        conventions.write_bytes(b'team conventions\n')
        self.invoke('installClaudeCore();')
        self.assertEqual(conventions.read_bytes(), b'team conventions\n')

    def test_claude_install_ships_no_templates(self):
        # The spec and prompt templates are no longer shipped (owner, 2026-10-07): a new install adds
        # none and `list` shows none; a copy an earlier release installed is the user's now and stays.
        self.invoke('installClaudeCore();')
        self.assertFalse((self.project / '.claude/templates').exists())
        self.assertNotIn(b'Templates', self.cli('list').stdout)
        kept = self.project / '.claude/templates/template-feature.spec.md'
        kept.parent.mkdir(parents=True)
        kept.write_bytes(b'team template\n')
        self.invoke('installClaudeCore();')
        self.assertEqual(kept.read_bytes(), b'team template\n')

    def test_agents_command_is_removed_with_replacement(self):
        (self.project / 'keep.txt').write_bytes(b'project user bytes\r\n')
        keep = self.home / '.codex/skills/user-skill/keep'
        keep.parent.mkdir(parents=True); keep.write_bytes(b'user bytes\x00')
        before = {p: p.read_bytes() if p.is_file() else None for p in self.case.rglob('*')}
        for args in (['agents'], ['agents', 'codex'], ['agents', 'all']):
            with self.subTest(args=args):
                result = self.cli(*args, code=1)
                self.assertIn(b'npx devlyn-cli -y [--claude] [--global]', result.stderr)
                self.assertEqual({p: p.read_bytes() if p.is_file() else None for p in self.case.rglob('*')}, before)

    def test_noninteractive_targets_and_scopes(self):
        project_files = {'.agents', '.gitignore'}
        cases = [(['-y'], project_files, set()), ([], project_files, set()), (['--yes'], project_files, set()),
                 (['-y', '--claude'], project_files | {'.claude'}, set()),
                 (['-y', '--global'], set(), {'.agents', '.codex'}),
                 (['init', '-y', '--global', '--claude'], set(), {'.agents', '.codex', '.claude'})]
        for index, (args, files, home) in enumerate(cases):
            with self.subTest(args=args):
                self.project = self.case / f'project-{index}'; self.project.mkdir()
                self.home = self.case / f'home-{index}'; self.home.mkdir()
                self.env['DEVLYN_TEST_HOME'] = str(self.home)
                result = self.cli(*args)
                self.assertEqual(result.stdout.count(b'in a terminal, start with: npx devlyn-cli run'), 0 if os.name == 'nt' else 1)
                if '--claude' not in args:
                    where = '~/.claude/skills' if '--global' in args else '.claude/'
                    self.assertIn(f'{where} for Claude Code: add --claude'.encode(), result.stdout)
                self.assertEqual({p.name for p in self.project.iterdir()}, files)
                self.assertEqual(self.markers(self.project), files & {'.agents', '.claude'})
                self.assertEqual({p.name for p in self.home.iterdir()}, home)
                self.assertEqual(self.markers(self.home), home)
                if files:
                    ignored = (self.project / '.gitignore').read_text(encoding='utf-8').splitlines()
                    self.assertEqual(ignored[1:], ['.devlyn/'])
        self.cli('-y', '--bogus', code=1)
        self.cli('agents-all', code=1)

    def test_windows_install_points_only_to_the_app(self):
        # `devlyn run` does not start on native Windows, so the line after an install there names only the app.
        result = self.invoke("Object.defineProperty(process, 'platform', { value: 'win32' }); install(['agents'], false);")
        self.assertIn(b'The Devlyn app gives every session the principles.', result.stdout)
        self.assertNotIn(b'devlyn-cli run', result.stdout)

    def test_project_upgrade_removes_only_selected_marker_ignore_lines(self):
        agents = b'.agents/skills/.devlyn-install.json'
        claude = b'.claude/skills/.devlyn-install.json'
        before = (b'# User rules\r\nnode_modules/\r\n\r\n# devlyn-cli pipeline state\r\n.devlyn/\r\n'
                  + b'  ' + agents + b' \r\n' + claude + b'\r\n'
                  + b'# Custom header: preserve me\r\n' + agents + b'\r\n'
                  + b'/' + agents + b'\r\n!' + claude + b'\r\n'
                  + claude + b'.backup\r\n# ' + agents + b'\r\nkeep-last')
        for targets in (['agents'], ['claude'], ['agents', 'claude']):
            with self.subTest(targets=targets):
                self.project = self.case / ('upgrade-' + '-'.join(targets)); self.project.mkdir()
                for target in targets:
                    self.seed_4_1(self.project / f'.{target}/skills')
                ignore = self.project / '.gitignore'; ignore.write_bytes(before)
                selected = {f'.{target}/skills/.devlyn-install.json'.encode() for target in targets}
                expected = b''.join(line for line in before.splitlines(keepends=True) if line.removesuffix(b'\n').removesuffix(b'\r') not in selected)
                self.invoke(f'install({json.dumps(targets)}, false);')
                self.assertEqual(ignore.read_bytes(), expected)
                self.invoke(f'install({json.dumps(targets)}, false);')
                self.assertEqual(ignore.read_bytes(), expected)

    def test_project_marker_migration_removes_only_emptied_managed_headers(self):
        marker = b'.agents/skills/.devlyn-install.json'
        header = b'# devlyn-cli pipeline state\r\n'
        before = (b'.devlyn/\r\n' + header + marker + b'\r\n# Custom header\r\ncache/\r\n'
                  + header + marker + b'\r\n\r\nelsewhere/\r\n'
                  + header + marker + b'\r\nkeep/\r\n'
                  + header + marker)
        expected = (b'.devlyn/\r\n# Custom header\r\ncache/\r\n\r\nelsewhere/\r\n'
                    + header + b'keep/\r\n')
        ignore = self.project / '.gitignore'; ignore.write_bytes(before)
        self.cli('-y')
        self.assertEqual(ignore.read_bytes(), expected)

    @unittest.skipIf(os.name == 'nt', 'creating a symlink needs a privilege on native Windows')
    def test_project_gitignore_links_refuse_before_any_mutation(self):
        shared = self.case / 'shared-ignore'
        shared.write_bytes(b'.devlyn/\n.agents/skills/.devlyn-install.json\n')
        ignore = self.project / '.gitignore'
        for target in (shared, self.case / 'missing-ignore'):
            with self.subTest(target=target):
                ignore.symlink_to(target)
                try:
                    before = self.snapshot()
                    result = self.cli('-y', '--claude', code=1)
                    self.assertIn(b'.gitignore', result.stderr)
                    self.assertIn(b'not a regular file', result.stderr)
                    self.assertEqual(self.snapshot(), before)
                finally:
                    ignore.unlink()

    def test_project_gitignore_directory_refuses_before_any_mutation(self):
        (self.project / '.gitignore').mkdir()
        before = self.snapshot()
        result = self.cli('-y', code=1)
        self.assertIn(b'.gitignore', result.stderr)
        self.assertIn(b'not a regular file', result.stderr)
        self.assertEqual(self.snapshot(), before)

    def test_project_gitignore_hardlinks_refuse_when_write_needed(self):
        shared = self.case / 'shared-ignore'
        ignore = self.project / '.gitignore'
        for content in (b'.devlyn/\n.agents/skills/.devlyn-install.json\n', b'cache/\n'):
            with self.subTest(content=content):
                shared.write_bytes(content)
                os.link(shared, ignore)
                try:
                    self.assertEqual(ignore.stat().st_nlink, 2)
                    before = self.snapshot()
                    result = self.cli('-y', '--claude', code=1)
                    self.assertIn(b'.gitignore', result.stderr)
                    self.assertIn(b'links are refused', result.stderr)
                    self.assertEqual(self.snapshot(), before)
                    self.assertEqual(ignore.stat().st_ino, shared.stat().st_ino)
                    self.assertEqual(ignore.stat().st_nlink, 2)
                finally:
                    ignore.unlink()

    def test_project_gitignore_hardlinks_refuse_even_without_rule_changes(self):
        shared = self.case / 'shared-ignore'
        shared.write_bytes(b'.devlyn/\ncache/\n')
        ignore = self.project / '.gitignore'
        os.link(shared, ignore)
        self.assertEqual(ignore.stat().st_nlink, 2)
        before = self.snapshot()
        result = self.cli('-y', '--claude', code=1)
        self.assertIn(b'.gitignore', result.stderr)
        self.assertIn(b'links are refused', result.stderr)
        self.assertEqual(self.snapshot(), before)
        self.assertEqual(ignore.stat().st_ino, shared.stat().st_ino)
        self.assertEqual(ignore.stat().st_nlink, 2)

    def test_project_marker_migration_preserves_invalid_utf8_and_line_endings(self):
        marker = b'.agents/skills/.devlyn-install.json'
        header = b'# devlyn-cli pipeline state'
        for eol in (b'\n', b'\r\n'):
            for add_runtime_rule in (False, True):
                with self.subTest(eol=eol, add_runtime_rule=add_runtime_rule):
                    prefix = b'' if add_runtime_rule else b'.devlyn/' + eol
                    user_rules = b'caf\xe9/' + eol + marker + b'\xe9' + eol + b'keep-last\xe9'
                    before = prefix + header + eol + marker + eol + eol + user_rules
                    expected = prefix + eol + user_rules
                    if add_runtime_rule:
                        expected += eol + eol + header + eol + b'.devlyn/' + eol
                    ignore = self.project / '.gitignore'; ignore.write_bytes(before)
                    self.cli('-y')
                    self.assertEqual(ignore.read_bytes(), expected)
                    self.cli('-y')
                    self.assertEqual(ignore.read_bytes(), expected)

    def test_project_gitignore_preserves_pattern_whitespace(self):
        before = (b'  .devlyn/\r\n# devlyn-cli pipeline state\r\n'
                  b'  .agents/skills/.devlyn-install.json\r\n'
                  b'.agents/skills/.devlyn-install.json \r\n')
        ignore = self.project / '.gitignore'; ignore.write_bytes(before)
        self.cli('-y')
        self.assertEqual(ignore.read_bytes(), before + b'.devlyn/\r\n')

    def commit_install_fixture(self):
        run(['git', '-c', 'core.autocrlf=false', 'add', '--', '.'], cwd=self.project)
        run(['git', '-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.test',
             '-c', 'commit.gpgsign=false', 'commit', '-qm', 'installer fixture'], cwd=self.project)

    def assert_install_notice(self, result, ignored=0, rule=None):
        raw = result.stdout.decode('utf-8')
        output = re.sub(r'\x1b\[[0-9;]*m', '', raw)
        self.assertEqual(result.returncode, 0)
        for line in output.splitlines():
            if 'Retired devlyn settings' not in line:
                self.assertNotIn('commit', line.lower())
        self.assertNotIn('git add', output.lower())
        self.assertNotIn('Optional —', output)
        if not ignored:
            self.assertNotIn('Git ignores', output)
            return
        notice = f'\x1b[2mGit ignores {ignored} installed file{"" if ignored == 1 else "s"} (example rule: {rule}).\x1b[0m'
        self.assertEqual([line for line in raw.splitlines() if 'Git ignores' in line], [notice])
        version = json.loads((self.package / 'package.json').read_bytes())['version']
        self.assertGreater(raw.index(notice), raw.index(f'✅ devlyn {version} installed'))

    def test_project_install_notice_unrelated_skill_changes_are_quiet(self):
        run(['git', 'init', '-q', self.project])
        self.invoke("install(['agents', 'claude'], false, ['devlyn-reap']);")
        for target in ('agents', 'claude'):
            personal = self.project / f'.{target}/skills/personal/SKILL.md'
            personal.parent.mkdir()
            personal.write_bytes(b'personal skill\n')
        self.commit_install_fixture()
        for target in ('agents', 'claude'):
            root = self.project / f'.{target}/skills'
            (root / 'personal/SKILL.md').write_bytes(b'edited personal skill\n')
            (root / 'devlyn-reap/SKILL.md').write_bytes(b'edited optional skill\n')
            (root / '.devlyn-install.json.backup').write_bytes(b'untracked user backup\n')
        before = self.snapshot()
        self.assert_install_notice(self.cli('-y', '--claude'))
        self.assertEqual(self.snapshot(), before)

    def test_project_install_notice_retired_skill_folders(self):
        run(['git', 'init', '-q', self.project])
        for target in ('agents', 'claude'):
            self.seed_4_1(self.project / f'.{target}/skills')
        self.commit_install_fixture()
        result = self.cli('-y', '--claude')
        retired = [f'.{target}/skills/devlyn-{name}' for target in ('agents', 'claude')
                   for name in ('resolve', 'design-ui', 'queue')]
        self.assert_install_notice(result)
        for name in retired:
            self.assertFalse((self.project / name).exists())

    def test_project_install_notice_renamed_skill_folders(self):
        run(['git', 'init', '-q', self.project])
        self.cli('-y', '--claude')
        renamed = []
        for target in ('agents', 'claude'):
            for colon in (['\uf03a'] if os.name == 'nt' else [':', '\uf03a']):
                for name, source in [('engines', self.package / 'config/skills'),
                                     ('reap', self.package / 'optional-skills')]:
                    old = f'.{target}/skills/devlyn{colon}{name}'
                    shutil.copytree(source / f'devlyn-{name}', self.project / old)
                    renamed.append(old)
        self.commit_install_fixture()
        result = self.cli('-y', '--claude')
        self.assert_install_notice(result)
        for name in renamed:
            self.assertFalse((self.project / name).exists())

    def test_project_install_notice_fresh_install(self):
        run(['git', 'init', '-q', self.project])
        (self.project / 'unrelated.txt').write_text('user content', encoding='utf-8')
        result = self.cli('-y', '--claude')
        self.assert_install_notice(result)
        self.assertEqual(run(['git', 'ls-files'], cwd=self.project).stdout, b'')
        self.assertEqual((self.project / 'unrelated.txt').read_bytes(), b'user content')

    def test_project_install_notice_committed_rerun(self):
        run(['git', 'init', '-q', self.project])
        self.assert_install_notice(self.cli('-y', '--claude'))
        self.commit_install_fixture()
        self.assert_install_notice(self.cli('-y', '--claude'))
        self.assertEqual(run(['git', 'status', '--porcelain'], cwd=self.project).stdout, b'')

    def test_project_install_notice_update(self):
        run(['git', 'init', '-q', self.project])
        self.cli('-y', '--claude')
        self.commit_install_fixture()
        self.assert_install_notice(self.cli('update'))
        self.assertEqual(run(['git', 'status', '--porcelain'], cwd=self.project).stdout, b'')

    def test_project_install_notice_cleanup_only_update(self):
        run(['git', 'init', '-q', self.project])
        for global_install in (False, True):
            with self.subTest(global_install=global_install):
                if global_install:
                    self.cli('-y', '--global')
                retired = self.project / '.agents/skills/devlyn-review'
                retired.mkdir(parents=True)
                (retired / 'SKILL.md').write_bytes(b'old devlyn skill')
                result = self.cli('update')
                self.assert_install_notice(result)
                self.assertIn(f'✕ {os.path.relpath(retired, self.project)} (removed)'.encode(), result.stdout)
                self.assertFalse(retired.exists())
                self.assertEqual(self.markers(self.project), set())

    def test_project_install_notice_ignored_install(self):
        run(['git', 'init', '-q', self.project])
        (self.project / '.gitignore').write_text('.agents/\nAGENTS.md\n.devlyn/\n', encoding='utf-8')
        self.commit_install_fixture()
        self.assert_install_notice(self.cli('-y'))
        # Removing the ignore rules makes the same install visible to Git.
        (self.project / '.gitignore').write_text('.devlyn/\n', encoding='utf-8')
        self.assert_install_notice(self.cli('-y'))

    def test_project_install_notice_partially_ignored_scripts(self):
        run(['git', 'init', '-q', self.project])
        (self.project / '.gitignore').write_text('# project scripts\n' * 12 + '**/scripts/queue.py\n', encoding='utf-8')
        result = self.cli('-y')
        self.assert_install_notice(result, ignored=1, rule='.gitignore:13: **/scripts/queue.py')
        self.assertEqual(run(['git', 'ls-files'], cwd=self.project).stdout, b'')

    def test_project_install_notice_wholly_ignored_skill_folders(self):
        run(['git', 'init', '-q', self.project])
        (self.project / '.gitignore').write_text('.agents/skills/devlyn-*\n', encoding='utf-8')
        result = self.cli('-y')
        self.assert_install_notice(result)

    def test_project_install_notice_ignored_scripts_after_incomplete_commit(self):
        run(['git', 'init', '-q', self.project])
        (self.project / '.gitignore').write_text('scripts/\n', encoding='utf-8')
        self.cli('-y')
        self.commit_install_fixture()
        index = self.project / '.git/index'
        before = index.read_bytes()
        self.assert_install_notice(self.cli('-y'), ignored=2, rule='.gitignore:1: scripts/')
        self.assertEqual(index.read_bytes(), before)
        self.assertEqual(run(['git', 'status', '--porcelain'], cwd=self.project).stdout, b'')

    def test_project_install_notice_force_added_scripts_are_quiet(self):
        run(['git', 'init', '-q', self.project])
        (self.project / '.gitignore').write_text('scripts/\n', encoding='utf-8')
        self.cli('-y')
        ignored = [f'.agents/skills/devlyn-ideate/scripts/{name}.py' for name in ('queue', 'acceptance')]
        run(['git', 'add', '-f', '--', *ignored], cwd=self.project)
        self.assert_install_notice(self.cli('-y'))
        self.commit_install_fixture()
        self.assert_install_notice(self.cli('-y'))

    def test_project_install_notice_ignored_cache_is_not_installed(self):
        run(['git', 'init', '-q', self.project])
        (self.project / '.gitignore').write_text('scripts/\n', encoding='utf-8')
        # A runtime cache appears after copying, before the advisory runs. It was not installed.
        cache = '.agents/skills/devlyn-ideate/scripts/__pycache__/queue.cpython-312.pyc'
        result = self.invoke(f"""
const notice = noticeIgnoredInstallFiles;
noticeIgnoredInstallFiles = (...args) => {{
  fs.mkdirSync(path.dirname({json.dumps(cache)}), {{ recursive: true }});
  fs.writeFileSync({json.dumps(cache)}, 'runtime cache');
  notice(...args);
}};
install(['agents'], false);
""")
        self.assert_install_notice(result, ignored=2, rule='.gitignore:1: scripts/')
        self.assertNotIn(cache.encode(), result.stdout)
        self.assertEqual((self.project / cache).read_bytes(), b'runtime cache')

    def test_project_install_notice_ignored_optional_files_and_each_target(self):
        run(['git', 'init', '-q', self.project])
        (self.project / '.gitignore').write_text('scripts/\n.claude/skills/devlyn-*\n', encoding='utf-8')
        result = self.invoke("install(['agents', 'claude'], false, ['polar-billing-setup']);")
        self.assert_install_notice(result, ignored=4, rule='.gitignore:1: scripts/')

    def test_project_install_notice_non_git(self):
        (self.project / '.gitignore').write_text('scripts/\n', encoding='utf-8')
        self.assert_install_notice(self.cli('-y', '--claude'))
        run(['git', 'init', '-q', self.project])
        self.assert_install_notice(self.cli('-y', '--claude'), ignored=4, rule='.gitignore:1: scripts/')

    def test_project_install_notice_global(self):
        run(['git', 'init', '-q', self.project])
        run(['git', 'init', '-q', self.home])
        for base in (self.project, self.home):
            (base / '.gitignore').write_text('scripts/\n', encoding='utf-8')
        self.assert_install_notice(self.cli('-y', '--global', '--claude'))
        self.assert_install_notice(self.cli('-y', '--claude'), ignored=4, rule='.gitignore:1: scripts/')

    def test_project_install_notice_nested_repo_and_git_environment(self):
        run(['git', 'init', '-q', self.case])
        (self.project / '.gitignore').write_text('scripts/\n', encoding='utf-8')
        self.env.update(GIT_DIR=str(self.home / 'missing.git'), GIT_WORK_TREE=str(self.home),
                        GIT_INDEX_FILE=str(self.home / 'missing-index'), GIT_COMMON_DIR=str(self.home),
                        GIT_LITERAL_PATHSPECS='1', GIT_GLOB_PATHSPECS='1', GIT_NOGLOB_PATHSPECS='1',
                        GIT_ICASE_PATHSPECS='1', GIT_CEILING_DIRECTORIES=str(self.project))
        result = self.cli('-y')
        self.assert_install_notice(result, ignored=2, rule='project/.gitignore:1: scripts/')

    def test_project_install_notice_settings_migration(self):
        run(['git', 'init', '-q', self.project])
        self.cli('-y', '--claude')
        (self.project / '.claude/settings.json').write_text('{}\n', encoding='utf-8')
        self.commit_install_fixture()
        self.assert_install_notice(self.cli('-y', '--claude'))

    def test_project_install_notice_optional_skill_after_committed_install(self):
        run(['git', 'init', '-q', self.project])
        self.cli('-y')
        self.commit_install_fixture()
        result = self.interact([['\r'], ['\r'], [' ', '\r']])
        self.assertTrue((self.project / '.agents/skills/asset-creator/SKILL.md').is_file())
        self.assert_install_notice(result)

    def test_project_install_notice_git_unavailable_or_query_fails(self):
        run(['git', 'init', '-q', self.project])
        (self.project / '.gitignore').write_text('scripts/\n', encoding='utf-8')
        preload = self.preload.read_bytes()
        try:
            for failure in ['missing', 'check-ignore', 'ignore-rule', 'none']:
                with self.subTest(failure=failure):
                    self.preload.write_bytes(preload + f"""
const cp = require('child_process');
const spawn = cp.spawnSync;
cp.spawnSync = (file, args, options) => {{
  if (file === 'git' && {json.dumps(failure)} === 'missing') return {{ error: {{ code: 'ENOENT' }} }};
  if (file === 'git' && args.includes('check-ignore')) {{
    if (options.env.GIT_OPTIONAL_LOCKS !== '0') throw new Error('advisory must disable optional Git locks');
    if ({json.dumps(failure)} === 'check-ignore' || ({json.dumps(failure)} === 'ignore-rule' && args.includes('-v'))) {{
      return {{ status: 128, stderr: 'check-ignore failed' }};
    }}
  }}
  return spawn(file, args, options);
}};
""".encode())
                    result = self.cli('-y')
                    self.assert_install_notice(result, ignored=2 if failure == 'none' else 0,
                                               rule='.gitignore:1: scripts/')
                    self.assertIn(b' installed', result.stdout)
                    self.assertEqual(result.stderr, b'')
        finally:
            self.preload.write_bytes(preload)

    def test_fresh_project_markers_are_unignored_and_committed_reinstall_is_identical(self):
        run(['git', 'init', '-q', self.project])
        self.cli('-y', '--claude')
        markers = [f'.{target}/skills/.devlyn-install.json' for target in ('agents', 'claude')]
        before = {name: (self.project / name).read_bytes() for name in markers}
        for name in markers:
            run(['git', 'check-ignore', name], cwd=self.project, code=1)
            marker = json.loads(before[name])
            self.assertEqual(set(marker), {'schemaVersion', 'package', 'version', 'skills'})
            self.assertEqual(marker['version'], json.loads((self.package / 'package.json').read_bytes())['version'])
            self.assertEqual(set(marker['skills']), {'devlyn-ideate', 'devlyn-engines', '_shared'})
        run(['git', 'check-ignore', '.devlyn/probe'], cwd=self.project)
        run(['git', '-c', 'core.autocrlf=false', 'add', '.gitignore', '.agents/skills', '.claude/skills'], cwd=self.project)
        run(['git', '-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.test',
             '-c', 'commit.gpgsign=false', 'commit', '-qm', 'installed skills and markers'], cwd=self.project)
        self.cli('-y', '--claude')
        for name in markers:
            self.assertEqual((self.project / name).read_bytes(), before[name])
            self.assertEqual(run(['git', 'show', f'HEAD:{name}'], cwd=self.project).stdout, before[name])
        run(['git', 'diff', '--exit-code', 'HEAD', '--', *markers], cwd=self.project)

    def test_project_marker_migration_preserves_broader_user_patterns(self):
        for index, pattern in enumerate((b'.claude/', b'*.json')):
            with self.subTest(pattern=pattern):
                self.project = self.case / f'broad-{index}'; self.project.mkdir()
                run(['git', 'init', '-q', self.project])
                ignore = self.project / '.gitignore'
                before = b'# My patterns\r\n' + pattern + b'\r\n'
                ignore.write_bytes(before + b'.claude/skills/.devlyn-install.json\r\n')
                self.cli('-y', '--claude')
                self.assertEqual(ignore.read_bytes(), before + b'\r\n# devlyn-cli pipeline state\r\n.devlyn/\r\n')
                run(['git', 'check-ignore', '.claude/skills/.devlyn-install.json'], cwd=self.project)
                run(['git', 'check-ignore', '.agents/skills/.devlyn-install.json'], cwd=self.project,
                    code=0 if pattern == b'*.json' else 1)
                run(['git', 'check-ignore', '.devlyn/probe'], cwd=self.project)

    def test_interactive_what_and_where(self):
        up, down, enter, space = '\x1b[A', '\x1b[B', '\r', ' '
        mcp = b'Playwright MCP for browser testing'
        # Defaults on an empty project: AGENTS.md only, this project; MCP servers are Claude's.
        # Up wraps to the last addon, which shows its description.
        result = self.interact([[enter], [enter], [up, enter]])
        self.assertNotIn(mcp, result.stdout)
        self.assertEqual({p.name for p in self.project.iterdir()}, {'.agents', '.gitignore'})
        self.assertEqual(self.markers(self.project), {'.agents'})
        # A project with devlyn Claude skills preselects Claude Code; an optional skill goes to both roots.
        (self.project / '.claude/skills').mkdir(parents=True)
        (self.project / '.claude/skills/.devlyn-install.json').write_text(
            '{"schemaVersion": 1, "package": "devlyn-cli", "version": "4.0.1"}', encoding='utf-8')
        result = self.interact([[enter], [enter], [up, down, space, enter]])
        self.assertIn(mcp, result.stdout)
        self.assertEqual(self.markers(self.project), {'.agents', '.claude'})
        self.assertFalse((self.project / 'CLAUDE.md').exists())
        for root in ('.agents', '.claude'):
            self.assertTrue((self.project / root / 'skills/asset-creator/SKILL.md').is_file())
        self.assertEqual(self.markers(self.home), set())
        # Space toggles, arrows move: CLAUDE.md only, globally — skills only, no settings.
        self.project = self.case / 'claude-global'; self.project.mkdir()
        self.interact([[space, down, space, enter], [down, enter], [enter]])
        self.assertEqual(list(self.project.iterdir()), [])
        self.assertEqual({p.name for p in self.home.iterdir()}, {'.claude'})
        self.assertEqual({p.name for p in (self.home / '.claude').iterdir()}, {'skills'})
        self.assertEqual(self.markers(self.home), {'.claude'})
        # Nothing selected installs nothing.
        self.project = self.case / 'nothing'; self.project.mkdir()
        result = self.interact([[space, enter]])
        self.assertIn(b'Nothing selected', result.stdout)
        self.assertEqual(list(self.project.iterdir()), [])
        # --claude and --global preselect both steps.
        self.interact([[enter], [enter], [enter]], '{ claude: true, global: true }')
        self.assertEqual(list(self.project.iterdir()), [])
        self.assertEqual(self.markers(self.home), {'.agents', '.codex', '.claude'})
        # --global alone preselects CLAUDE.md where ~/.claude/skills has devlyn, as -y --global does.
        marker = self.home / '.claude/skills/.devlyn-install.json'
        marker.write_text('{"schemaVersion": 1, "package": "devlyn-cli", "version": "4.0.1"}', encoding='utf-8')
        self.interact([[enter], [enter], [enter]], '{ global: true }')
        self.assertEqual(list(self.project.iterdir()), [])
        self.assertEqual(json.loads(marker.read_bytes())['version'], json.loads((self.package / 'package.json').read_bytes())['version'])

    def test_global_drift_notice_names_roots_it_does_not_install(self):
        roots = {'.agents': '4.0.1', '.codex': '3.3.1', '.claude': '4.1.0', '.grok': '4.0.0'}
        for root, version in roots.items():
            (self.home / root / 'skills/user-skill').mkdir(parents=True)
            (self.home / root / 'skills/user-skill/keep').write_bytes(b'mine')
            (self.home / root / 'skills/.devlyn-install.json').write_text(
                json.dumps({'schemaVersion': 1, 'package': 'devlyn-cli', 'version': version}), encoding='utf-8')
        before = {p: p.read_bytes() if p.is_file() else None for p in self.home.rglob('*')}

        def notices(result):
            return [line for line in result.stdout.decode('utf-8').splitlines() if 'Global devlyn' in line]

        def line(root, advice='refresh it with --global, or delete it'):
            return f"Global devlyn {roots[root]} in {Path('~', root, 'skills')} — {advice}."

        result = self.cli('-y')
        self.assertEqual(notices(result), [f'\x1b[33m{line(root)}\x1b[0m' for root in ('.agents', '.codex', '.claude')])
        self.assertEqual({p: p.read_bytes() if p.is_file() else None for p in self.home.rglob('*')}, before)
        # --global refreshes every user root it installs, Claude's too once it has a marker there.
        result = self.cli('-y', '--global')
        self.assertEqual(notices(result), [])
        self.assertEqual(notices(self.cli('-y')), [])
        version = json.loads((self.package / 'package.json').read_bytes())['version']
        for root in ('.agents', '.codex', '.claude'):
            self.assertEqual(json.loads((self.home / root / 'skills/.devlyn-install.json').read_bytes())['version'], version)
            self.assertEqual((self.home / root / 'skills/user-skill/keep').read_bytes(), b'mine')
        grok = self.home / '.grok'
        self.assertEqual({p: p.read_bytes() if p.is_file() else None for p in grok.rglob('*')},
                         {p: data for p, data in before.items() if grok in p.parents and p.name != '.devlyn-install.json'})

    def test_update_refreshes_existing_installs_and_preserves_user_bytes(self):
        self.cli('-y', '--claude'); self.cli('-y', '--global', '--claude')
        version = json.loads((self.package / 'package.json').read_bytes())['version']
        for root in self.roots():
            marker = root / '.devlyn-install.json'
            data = json.loads(marker.read_bytes()); data['version'] = '4.2.14'
            marker.write_text(json.dumps(data), encoding='utf-8')
            (root / 'user-skill').mkdir(); (root / 'user-skill/keep').write_bytes(b'mine\r\n')
        instructions = {name: b'# Team rules\r\n\r\nKeep this tail.\r\n' for name in ('AGENTS.md', 'CLAUDE.md')}
        for name, data in instructions.items():
            (self.project / name).write_bytes(data)
        result = self.cli('update')
        self.assertNotIn(b'Global devlyn', result.stdout)
        self.assertEqual(result.stdout.count(b'Installing devlyn skills to'), 5)
        self.assertIn(f'✅ devlyn {version} installed'.encode(), result.stdout)
        self.assertFalse(list(self.home.rglob('.devlyn-install.lock')))
        for root in self.roots():
            self.assertEqual(json.loads((root / '.devlyn-install.json').read_bytes())['version'], version)
            self.assertEqual((root / 'user-skill/keep').read_bytes(), b'mine\r\n')
        for name, data in instructions.items():
            self.assertEqual((self.project / name).read_bytes(), data)
        for name in ('.codex', '.claude'):
            shutil.rmtree(self.home / name / 'skills')
        self.cli('update')
        for name in ('.codex', '.claude'):
            self.assertFalse((self.home / name / 'skills').exists())

    def test_update_only_user_roots_leaves_project_empty(self):
        self.cli('-y', '--global')
        # A core skill directory counts without a marker; _shared alone does not.
        (self.home / '.agents/skills/.devlyn-install.json').unlink()
        shared = self.home / '.claude/skills/_shared'
        shared.mkdir(parents=True); (shared / 'keep').write_bytes(b'other tool')
        grok = self.home / '.grok/skills'
        grok.mkdir(parents=True)
        version = json.loads((self.package / 'package.json').read_bytes())['version']
        (grok / '.devlyn-install.json').write_text(json.dumps({'version': version}), encoding='utf-8')
        before = {p: p.read_bytes() for p in (shared / 'keep', grok / '.devlyn-install.json')}
        result = self.cli('update')
        self.assertEqual(list(self.project.iterdir()), [])
        self.assertEqual(self.markers(self.home), {'.agents', '.codex', '.grok'})
        self.assertNotIn(b'delete it', result.stdout)
        for p, data in before.items():
            self.assertEqual(p.read_bytes(), data)

    def test_update_claude_only_project_stays_claude_only(self):
        self.invoke("install(['claude'], false);")
        marker = self.project / '.claude/skills/.devlyn-install.json'
        data = json.loads(marker.read_bytes()); data['version'] = '4.2.14'
        marker.write_text(json.dumps(data), encoding='utf-8')
        self.cli('update')
        self.assertFalse((self.project / '.agents').exists())
        self.assertFalse((self.project / 'AGENTS.md').exists())
        self.assertEqual(list(self.home.iterdir()), [])
        self.assertEqual(json.loads(marker.read_bytes())['version'],
                         json.loads((self.package / 'package.json').read_bytes())['version'])

    def test_update_in_home_skips_project_install(self):
        self.cli('-y', '--global', '--claude')
        self.project = self.home
        before = self.snapshot()
        self.cli('update')
        self.assertEqual(self.snapshot(), before)

    def test_update_refuses_newer_versions_in_every_scope(self):
        self.cli('-y', '--claude'); self.cli('-y', '--global', '--claude')
        malformed = (None, 'malformed', '4.2.15-rc..1', '4.2.15-01', '04.2.15')
        # The next minor's pre-release and build are newer than any release of this one.
        major, minor = map(int, json.loads((self.package / 'package.json').read_bytes())['version'].split('.')[:2])
        newer = f'{major}.{minor + 1}.0'
        for root in self.roots():
            for version in (newer + '-beta.1', newer + '+build', '99.0.0', *malformed):
                with self.subTest(root=root, version=version):
                    marker = root / '.devlyn-install.json'
                    original = marker.read_bytes()
                    data = json.loads(original)
                    if version is None:
                        del data['version']
                    else:
                        data['version'] = version
                    marker.write_text(json.dumps(data), encoding='utf-8')
                    before = self.snapshot()
                    result = self.cli('update', code=1)
                    self.assertIn(str(root).encode(), result.stderr)
                    self.assertIn(b'nothing was changed', result.stderr)
                    if version in malformed:
                        self.assertIn(b'missing or malformed marker version', result.stderr)
                    else:
                        self.assertIn(version.encode(), result.stderr)
                        self.assertIn(b'npx devlyn-cli@latest update', result.stderr)
                    self.assertEqual(self.snapshot(), before)
                    marker.write_bytes(original)

    def test_update_accepts_older_prerelease_and_build_versions(self):
        self.cli('-y', '--global')
        current = json.loads((self.package / 'package.json').read_bytes())['version']
        for version in (current + '-rc.1', current + '+build', '4.0.1'):
            with self.subTest(version=version):
                for root in (self.home / '.agents/skills', self.home / '.codex/skills'):
                    marker = root / '.devlyn-install.json'
                    data = json.loads(marker.read_bytes()); data['version'] = version
                    marker.write_text(json.dumps(data), encoding='utf-8')
                self.cli('update')
                self.assertEqual(json.loads(marker.read_bytes())['version'], current)
                self.assertFalse(list(self.home.rglob('.devlyn-install.lock')))

    def test_user_root_locks_refuse_update_and_global_install(self):
        self.cli('-y', '--claude'); self.cli('-y', '--global', '--claude')
        for name in ('.agents', '.codex', '.claude'):
            lock = self.home / name / 'skills/.devlyn-install.lock'
            lock.write_text('{"pid": 12345, "token": "foreign"}', encoding='utf-8')
            for args in (('update',), ('-y', '--global', '--claude')):
                with self.subTest(root=name, args=args):
                    before = self.snapshot()
                    result = self.cli(*args, code=1)
                    self.assertIn(f'Another devlyn-cli is changing {lock.parent} (pid 12345).'.encode(), result.stderr)
                    self.assertIn(f'delete {lock} and run again.'.encode(), result.stderr)
                    self.assertEqual(self.snapshot(), before)
            lock.unlink()

    def test_lock_only_root_is_discovered_and_new_global_roots_are_cleaned_on_refusal(self):
        lock = self.home / '.claude/skills/.devlyn-install.lock'
        lock.parent.mkdir(parents=True)
        lock.write_text('{"pid": 12345, "token": "foreign"}', encoding='utf-8')
        for args in (('update',), ('-y', '--global', '--claude')):
            with self.subTest(args=args):
                before = self.snapshot()
                result = self.cli(*args, code=1)
                self.assertIn(str(lock).encode(), result.stderr)
                self.assertEqual(self.snapshot(), before)

    def test_global_locks_ignore_namespaced_mkdir_result(self):
        for refused in (False, True):
            with self.subTest(refused=refused):
                self.home = self.case / f'home-{refused}'; self.home.mkdir()
                self.env['DEVLYN_TEST_HOME'] = str(self.home)
                if refused:
                    lock = self.home / '.codex/skills/.devlyn-install.lock'
                    lock.parent.mkdir(parents=True)
                    lock.write_text('{"pid": 12345, "token": "foreign"}', encoding='utf-8')
                before = self.snapshot()
                result = self.invoke(r"""
const mkdir = fs.mkdirSync;
fs.mkdirSync = (dir, options) => {
  const first = mkdir(dir, options);
  return options?.recursive && typeof first === 'string' ? '\\\\?\\' + first : first;
};
install(['agents'], true);
""", code=1 if refused else 0)
                if refused:
                    self.assertIn(b'Another devlyn-cli is changing', result.stderr)
                    self.assertEqual(self.snapshot(), before)
                else:
                    for name in ('.agents', '.codex'):
                        self.assertTrue((self.home / name / 'skills/devlyn-ideate/SKILL.md').is_file())
                    self.assertFalse(list(self.home.rglob('.devlyn-install.lock')))

    def test_global_lock_lifetime_includes_preflight_and_optional_writes(self):
        # A second process must refuse even while the first writer has no marker or skills yet.
        self.invoke(f"""
const assert = require('assert');
const roots = [...skillRoots('agents', true), ...skillRoots('claude', true)];
const check = () => {{
  for (const root of roots) {{
    const lock = path.join(root, DEVLYN_INSTALL_LOCK);
    const owner = JSON.parse(fs.readFileSync(lock, 'utf8'));
    assert.equal(owner.pid, process.pid);
    assert.match(owner.token, /^[0-9a-f]+$/);
    if (process.platform !== 'win32') assert.equal(fs.statSync(lock).mode & 0o777, 0o600);
  }}
  for (const args of [['update'], ['-y', '--global', '--claude']]) {{
    const result = spawnSync(process.execPath,
      ['--require', {json.dumps(str(self.preload))}, __filename, ...args], {{ encoding: 'utf8' }});
    assert.equal(result.status, 1, result.stderr);
    assert.match(result.stderr, /Another devlyn-cli is changing/);
  }}
}};
const preflight = preflightSkills;
preflightSkills = (...args) => {{ check(); return preflight(...args); }};
const optional = installLocalSkill;
installLocalSkill = (...args) => {{ check(); return optional(...args); }};
install(['agents', 'claude'], true, ['devlyn-reap']);
""")
        self.assertFalse(list(self.home.rglob('.devlyn-install.lock')))
        for name in ('.agents', '.codex', '.claude'):
            root = self.home / name / 'skills'
            self.assertTrue((root / 'devlyn-reap/SKILL.md').is_file())
            self.assertNotIn('.devlyn-install.lock', json.loads((root / '.devlyn-install.json').read_bytes())['skills'])
        self.assertNotIn(b'.devlyn-install.lock', self.cli('list').stdout)

    def test_user_locks_release_on_write_failure_and_preserve_replacement_token(self):
        self.cli('-y', '--global')
        for command in ('update()', "install(['agents'], true)"):
            with self.subTest(command=command):
                before = self.snapshot()
                result = self.invoke("installCoreSkills = () => { throw new Error('injected write failure'); }; "
                                     + command + ';', code=1)
                self.assertIn(b'injected write failure', result.stderr)
                self.assertEqual(self.snapshot(), before)
        self.invoke("withUserSkillLocks([skillRoots('agents', true)[0]], () => { "
                    "fs.writeFileSync(path.join(skillRoots('agents', true)[0], DEVLYN_INSTALL_LOCK), "
                    "JSON.stringify({ pid: 12345, token: 'replacement' })); });")
        lock = self.home / '.agents/skills/.devlyn-install.lock'
        self.assertEqual(json.loads(lock.read_bytes())['token'], 'replacement')

    def test_update_discovers_markerless_historical_skills(self):
        names = ['devlyn\uf03aideate', 'devlyn-resolve']
        if os.name != 'nt':
            names.append('devlyn:ideate')
        for name in names:
            with self.subTest(name=name):
                root = self.home / '.agents/skills'
                old = self.seed_pre_4_1(root, '4.0.1', 'devlyn-resolve') if name == 'devlyn-resolve' else root / name
                if name != 'devlyn-resolve':
                    shutil.copytree(self.package / 'config/skills/devlyn-ideate', old)
                self.cli('update')
                self.assertFalse(old.exists())
                self.assertTrue((root / 'devlyn-ideate/SKILL.md').is_file())
                self.assertEqual(list(self.project.iterdir()), [])
                self.assertFalse((self.home / '.codex').exists())
                shutil.rmtree(self.home / '.agents')

    def test_update_skips_marker_shared_and_optional_only_roots(self):
        self.cli('-y')
        for name, entry in (('.agents', '.devlyn-install.json'), ('.codex', '_shared'), ('.claude', 'devlyn-reap')):
            root = self.home / name / 'skills'; root.mkdir(parents=True)
            if entry.endswith('.json'):
                (root / entry).write_bytes(b'{"version":"99.0.0"}')
            else:
                (root / entry).mkdir(); (root / entry / 'keep').write_bytes(b'other tool')
        before = self.snapshot()
        self.cli('update')
        self.assertEqual(self.snapshot(), before)

    def test_update_skips_regular_file_user_root(self):
        self.cli('-y')
        root = self.home / '.agents/skills'; root.parent.mkdir()
        root.write_bytes(b'not a directory')
        result = self.cli('update')
        self.assertIn(b'Installing devlyn skills to', result.stdout)
        self.assertEqual(root.read_bytes(), b'not a directory')

    @unittest.skipIf(os.name == 'nt', 'creating a symlink needs a privilege on native Windows')
    def test_update_reports_linked_roots_and_updates_real_install(self):
        self.cli('-y')
        current = json.loads((self.package / 'package.json').read_bytes())['version']
        project_marker = self.project / '.agents/skills/.devlyn-install.json'
        target = self.case / 'linked-install'; target.mkdir()
        shutil.copytree(self.package / 'config/skills', target / 'skills')
        (target / 'skills/.devlyn-install.json').write_bytes(b'{"version":"4.2.14"}')
        for root in (self.home / '.agents/skills', self.home / '.codex/skills',
                     self.home / '.claude/skills', self.project / '.claude/skills'):
            for parent in (False, True):
                with self.subTest(root=root, parent=parent):
                    link = root.parent if parent else root
                    link.parent.mkdir(parents=True, exist_ok=True)
                    link.symlink_to(target if parent else target / 'skills', target_is_directory=True)
                    data = json.loads(project_marker.read_bytes()); data['version'] = '4.2.14'
                    project_marker.write_text(json.dumps(data), encoding='utf-8')
                    before = self.snapshot()
                    result = self.cli('update')
                    notice = (f'Not updated: {root} is a link — devlyn-cli does not write through links. '
                              'Update the folder it points to, or replace the link with a folder.').encode()
                    self.assertEqual(result.stdout.count(notice), 1)
                    self.assertIn(b'\x1b[33m' + notice, result.stdout)
                    self.assertLess(result.stdout.index(notice), result.stdout.index(b'Installing devlyn skills to'))
                    self.assertEqual(json.loads(project_marker.read_bytes())['version'], current)
                    after = self.snapshot()
                    self.assertEqual({k: v for k, v in before.items() if k.startswith('linked-install/')},
                                     {k: v for k, v in after.items() if k.startswith('linked-install/')})
                    self.assertTrue(link.is_symlink())
                    link.unlink()
                    if not parent:
                        link.parent.rmdir()

    @unittest.skipIf(os.name == 'nt', 'creating a symlink needs a privilege on native Windows')
    def test_update_with_only_linked_roots_refuses_without_writes(self):
        target = self.case / 'linked-install'; (target / 'skills').mkdir(parents=True)
        for root in self.roots():
            for parent in (False, True):
                with self.subTest(root=root, parent=parent):
                    entry = target / 'skills' / ('devlyn-ideate' if parent else '.devlyn-install.json')
                    if parent:
                        entry.mkdir()
                    else:
                        entry.write_bytes(b'{"version":"4.2.14"}')
                    link = root.parent if parent else root
                    link.parent.mkdir(parents=True, exist_ok=True)
                    link.symlink_to(target if parent else target / 'skills', target_is_directory=True)
                    before = self.snapshot()
                    result = self.cli('update', code=1)
                    notice = (f'Not updated: {root} is a link — devlyn-cli does not write through links. '
                              'Update the folder it points to, or replace the link with a folder.').encode()
                    self.assertEqual(result.stdout.count(notice), 1)
                    self.assertIn(b'No devlyn install here to update', result.stderr)
                    self.assertIn(notice, result.stderr)
                    self.assertEqual(self.snapshot(), before)
                    link.unlink()
                    if not parent:
                        link.parent.rmdir()
                    if parent:
                        entry.rmdir()
                    else:
                        entry.unlink()

    def test_update_discovery_errors_name_the_root(self):
        result = self.invoke("const stat = fs.lstatSync; fs.lstatSync = (file, ...args) => { "
                             "if (file === skillRoots('agents', true)[0]) throw Object.assign(new Error('denied'), { code: 'EACCES' }); "
                             "return stat(file, ...args); }; update();", code=1)
        self.assertIn(f'Cannot inspect {self.home / ".agents/skills"}'.encode(), result.stderr)
        self.assertIn(b'Check its permissions and run again.', result.stderr)

    def test_project_install_notice_after_update_and_drift_notice(self):
        run(['git', 'init', '-q', self.project])
        self.cli('-y'); self.cli('-y', '--global')
        grok = self.home / '.grok/skills'; grok.mkdir(parents=True)
        (grok / '.devlyn-install.json').write_bytes(b'{"version":"4.0.1"}')
        for command in ('update();', "install(['agents'], false);"):
            with self.subTest(command=command):
                result = self.invoke(command)
                self.assert_install_notice(result)
                self.assertNotIn(b'delete it', result.stdout)

    def test_update_preflights_all_scopes_before_writing(self):
        self.cli('-y', '--claude'); self.cli('-y', '--global', '--claude')
        for root in self.roots():
            marker = root / '.devlyn-install.json'
            data = json.loads(marker.read_bytes()); data['version'] = '4.2.14'
            marker.write_text(json.dumps(data), encoding='utf-8')
        for root in (self.home / '.agents/skills', self.project / '.claude/skills'):
            with self.subTest(root=root):
                skill = root / 'devlyn-ideate/SKILL.md'
                original = skill.read_bytes(); skill.write_bytes(original + b'edited\n')
                self.assert_install_refused('update', paths=[skill.parent])
                skill.write_bytes(original)
        ignore = self.project / '.gitignore'
        ignore.unlink(); ignore.mkdir()
        before = self.snapshot()
        result = self.cli('update', code=1)
        self.assertIn(str(ignore).encode(), result.stderr)
        self.assertEqual(self.snapshot(), before)

    def test_update_without_install_or_with_arguments_writes_nothing(self):
        before = self.snapshot()
        result = self.cli('update', code=1)
        self.assertIn(b'No devlyn install here to update. Run npx devlyn-cli to install.', result.stderr)
        self.assertEqual(self.snapshot(), before)
        for extra in ('extra', '-y', '--global', '--help'):
            result = self.cli('update', extra, code=1)
            self.assertIn(f'Unknown command: {extra}'.encode(), result.stdout)
            self.assertIn(b'Usage:', result.stdout)
            self.assertEqual(self.snapshot(), before)

    def test_pack_install_reinstall_optional_is_byte_identical(self):
        install = ("const roots = [...install(['agents', 'claude'], false), ...install(['agents', 'claude'], true)];"
                   " installLocalSkill('devlyn-reap', roots);")
        name, optional = 'devlyn-ideate', 'devlyn-reap'
        core = self.package / 'config/skills'
        sources = {skill.name: core for skill in core.iterdir()
                   if (skill / 'SKILL.md').is_file() or skill.name == '_shared'}
        sources[optional] = self.package / 'optional-skills'

        def assert_package_bytes():
            # Installed skills are the package bytes: no install location is written into them,
            # so a committed or copied skill tree works wherever it is checked out.
            for root in self.roots():
                for skill, source in sources.items():
                    for file in (source / skill).rglob('*'):
                        if file.is_file() and '__pycache__' not in file.parts:
                            installed = root / skill / file.relative_to(source / skill)
                            self.assertEqual(installed.read_bytes(), file.read_bytes(), installed)

        self.invoke(install)
        assert_package_bytes()
        # Every target in both scopes writes exactly these roots, with the core skills and the opted-in one.
        self.assertEqual({p.parent for base in (self.project, self.home)
                          for p in base.glob('.*/skills/.devlyn-install.json')}, set(self.roots()))
        for root in self.roots():
            self.assertEqual({p.name for p in root.iterdir()},
                             {'devlyn-ideate', 'devlyn-engines', '_shared', optional, '.devlyn-install.json'}, root)
        before = self.snapshot()
        self.invoke(install)
        self.assertEqual(self.snapshot(), before)

    def snapshot(self):
        return {str(p.relative_to(self.case)): ('link', os.readlink(p)) if p.is_symlink()
                else ('file', p.read_bytes()) if p.is_file() else ('directory',)
                for p in self.case.rglob('*')}

    def seed_4_1(self, root):
        # Exact files from published devlyn-cli@4.1.0, not fabricated old skill names.
        # Original npm tarball sha1: 398ff07d3d689b56cc22e18ac50260bc6e4e9e85.
        root.mkdir(parents=True, exist_ok=True)
        fixture = Path(__file__).parent / 'fixtures/installer-4.1.0.tar.gz'
        with tarfile.open(fixture) as archive:
            archive.extractall(root, filter='data')
        (root / '.devlyn-install.json').write_text(
            json.dumps({'schemaVersion': 1, 'package': 'devlyn-cli', 'version': '4.1.0'}), encoding='utf-8')

    def assert_install_refused(self, *flags, paths=(), reason=None):
        before = self.snapshot()
        result = self.cli(*flags, code=1)
        error = result.stderr.decode('utf-8')
        self.assertIn('Installation refused; nothing was changed', error)
        self.assertIn('Move these out of the install path', error)
        self.assertNotIn('committing', error)
        for path in paths:
            self.assertIn(str(path), error)
        if reason:
            self.assertIn(reason, error)
        self.assertEqual(self.snapshot(), before)
        return result

    def evaluator_block(self):
        raw = (Path(__file__).parent / 'fixtures/instructions/evaluator-0.5.7.md').read_bytes()
        return b'\n\n---\n\n# Devlyn Agent Instructions\n\n' + raw + b'\n'

    def test_cleanup_instruction_owner_bytes_every_target(self):
        names = ['GEMINI.md', '.cursorrules', '.windsurfrules', '.github/copilot-instructions.md']
        for name in names + ['CLAUDE.md', 'AGENTS.md']:
            file = self.project / name; file.parent.mkdir(parents=True, exist_ok=True)
            file.write_bytes(SHORT_PAYLOAD + self.evaluator_block() + SHORT_PAYLOAD)
        self.cli('-y', '--claude')
        for name in ['CLAUDE.md', 'AGENTS.md']:
            self.assertEqual((self.project / name).read_bytes(), SHORT_PAYLOAD + self.evaluator_block() + SHORT_PAYLOAD)
        for name in names:
            data = (self.project / name).read_bytes()
            outside = re.sub(rb'<!-- devlyn:instructions:begin[^\n]*\n.*?<!-- devlyn:instructions:end -->\r?\n', b'', data, flags=re.S)
            self.assertEqual(outside, SHORT_PAYLOAD * 2)
            self.assertNotIn(b'devlyn:instructions:begin', data)
            backup = list((self.project / '.devlyn/instructions').glob('*.backup'))
            self.assertTrue(any(p.read_bytes() == SHORT_PAYLOAD + self.evaluator_block() + SHORT_PAYLOAD for p in backup))

        # These bytes are recognized project evidence, never evidence of a home-level install.
        block = (Path(__file__).parent / 'fixtures/instructions/agents-4.1.0.md').read_bytes()
        paragraph = b'# Project Instructions\n\n' + block.split(b'# Project Instructions\n\n', 1)[1].split(b'\n\n', 1)[0] + b'\n\n'
        global_files = {}
        for name in names + ['CLAUDE.md', 'AGENTS.md', '.claude/CLAUDE.md', '.codex/AGENTS.md']:
            global_files[name] = SHORT_PAYLOAD + paragraph + block + self.evaluator_block() + SHORT_PAYLOAD
        raw = self.evaluator_block().split(b'# Devlyn Agent Instructions\n\n', 1)[1][:-1]
        for folder in ['.claude/agents', '.cursor/rules', '.github/copilot/agents', '.windsurf/rules']:
            global_files[folder + '/evaluator.md'] = raw
        for name in ['prompt-templates.md', 'template-feature.spec.md', 'template-product-spec.md']:
            global_files['.claude/templates/' + name] = (Path(__file__).parent / 'fixtures/cleanup' / name).read_bytes()
        for name, data in global_files.items():
            file = self.home / name; file.parent.mkdir(parents=True, exist_ok=True); file.write_bytes(data)
        for args in [('update',), ('-y', '--global')]:
            self.cli(*args)
            for name, data in global_files.items():
                self.assertEqual((self.home / name).read_bytes(), data, (args, name))
            self.assertFalse((self.home / '.devlyn/instructions').exists())

    def test_cleanup_instruction_empty_edited_and_example(self):
        for name, value in [('GEMINI.md', self.evaluator_block()),
                            ('.cursorrules', self.evaluator_block() + b'owner tail'),
                            ('.windsurfrules', self.evaluator_block().replace(b'evaluator', b'owner-evaluator', 1)),
                            ('.github/copilot-instructions.md', b'```markdown\n' + self.evaluator_block() + b'```\n')]:
            file = self.project / name; file.parent.mkdir(parents=True, exist_ok=True); file.write_bytes(value)
        edited = (self.project / '.windsurfrules').read_bytes()
        example = (self.project / '.github/copilot-instructions.md').read_bytes()
        self.cli('-y')
        self.assertFalse((self.project / 'GEMINI.md').exists())
        self.assertEqual((self.project / '.cursorrules').read_bytes(), b'owner tail')
        self.assertEqual((self.project / '.windsurfrules').read_bytes(), edited)
        self.assertEqual((self.project / '.github/copilot-instructions.md').read_bytes(), example)

    def test_cleanup_generic_files_and_skills_preserve_edits(self):
        raw = self.evaluator_block().split(b'# Devlyn Agent Instructions\n\n', 1)[1][:-1]
        for folder in ['.claude/agents', '.cursor/rules', '.github/copilot/agents', '.windsurf/rules']:
            root = self.project / folder; root.mkdir(parents=True)
            (root / 'evaluator.md').write_bytes(raw.replace(b'\n', b'\r\n'))
            (root / 'owner.md').write_bytes(SHORT_PAYLOAD)
        edited = self.project / '.cursor/rules/evaluator.md'; edited.write_bytes(raw + SHORT_PAYLOAD)
        self.cli('-y')
        self.assertEqual(edited.read_bytes(), raw + SHORT_PAYLOAD)
        for folder in ['.claude/agents', '.cursor/rules', '.github/copilot/agents', '.windsurf/rules']:
            root = self.project / folder
            self.assertEqual((root / 'owner.md').read_bytes(), SHORT_PAYLOAD)
            if folder != '.cursor/rules': self.assertFalse((root / 'evaluator.md').exists())
        # Arbitrary/edited generic skills are never removed or named.
        generic = self.home / '.agents/skills/code-review-standards'; generic.mkdir(parents=True)
        (generic / 'SKILL.md').write_bytes(SHORT_PAYLOAD)
        result = self.cli('-y', '--global')
        self.assertEqual((generic / 'SKILL.md').read_bytes(), SHORT_PAYLOAD)
        self.assertNotIn(str(generic).encode(), result.stdout)

    def test_cleanup_scope_and_clean_only_roots(self):
        roots = self.roots() + [self.home / '.grok/skills']
        for root in roots:
            folder = root / 'devlyn-review'; folder.mkdir(parents=True)
            (folder / 'SKILL.md').write_bytes(b'old')
            foreign = root / 'foreign'; foreign.mkdir(); (foreign / 'keep').write_bytes(SHORT_PAYLOAD)
        self.cli('-y')
        self.assertFalse((self.project / '.claude/skills/devlyn-review').exists())
        self.assertFalse((self.project / '.claude/skills/.devlyn-install.json').exists())
        for root in roots[2:]: self.assertTrue((root / 'devlyn-review').exists())
        self.cli('update')
        for root in roots:
            self.assertFalse((root / 'devlyn-review').exists())
            self.assertEqual((root / 'foreign/keep').read_bytes(), SHORT_PAYLOAD)
        for root in roots[1:]: self.assertFalse((root / '.devlyn-install.json').exists())
        folder = self.project / '.claude/skills/devlyn-clean'; folder.mkdir()
        self.cli('-y', '--global')
        self.assertTrue(folder.exists())
        # update from HOME cleans global roots only and never treats HOME as a project.
        self.project = self.home
        self.cli('update')
        self.assertFalse((self.home / 'AGENTS.md').exists())

    def test_cleanup_retired_root_marker_evidence_and_stale_lock(self):
        root = self.home / '.grok/skills'; root.mkdir(parents=True)
        for name in ['devlyn-custom-retired', 'generic-shipped', 'generic-edited', 'foreign']:
            folder = root / name; folder.mkdir(); (folder / 'file').write_bytes(SHORT_PAYLOAD)
        self.invoke(f"""
const root = {json.dumps(str(root))};
fs.writeFileSync(path.join(root, DEVLYN_INSTALL_MARKER), JSON.stringify({{
  package: PKG.name, schemaVersion: 1, version: '4.0.1', skills: {{
    'devlyn-custom-retired': 'not verified',
    'generic-shipped': fingerprint(path.join(root, 'generic-shipped')),
    'generic-edited': 'old hash'
  }}
}}));
fs.writeFileSync(path.join(root, DEVLYN_INSTALL_LOCK), JSON.stringify({{pid: 2147483647, token: 'old'}}));
""")
        def tree():
            return {p.relative_to(root): p.read_bytes() if p.is_file() else None for p in root.rglob('*')}
        before = tree()
        result = self.cli('-y', '--global')
        self.assertEqual(result.stdout.count(f'Cannot clean up {root}:'.encode()), 1)
        self.assertEqual(tree(), before)
        (root / '.devlyn-install.lock').unlink()
        self.cli('-y', '--global')
        self.assertEqual({p.name for p in root.iterdir()}, {'generic-edited', 'foreign'})
        for name in ['generic-edited', 'foreign']:
            self.assertEqual((root / name / 'file').read_bytes(), SHORT_PAYLOAD)

    def test_cleanup_failure_warns_once_and_succeeds(self):
        root = self.project / '.agents/skills/devlyn-review'; root.mkdir(parents=True)
        (root / 'SKILL.md').write_bytes(b'old')
        result = self.invoke(f"""
const rm = fs.rmSync;
fs.rmSync = (file, ...args) => {{
  if (file === {json.dumps(str(root))}) throw Object.assign(new Error('fixture deletion denied'), {{code: 'EACCES'}});
  return rm(file, ...args);
}};
install(['agents'], false);
""")
        self.assertEqual(result.stdout.count(b'fixture deletion denied'), 1)
        self.assertIn(str(root).encode(), result.stdout)
        self.assertTrue(root.exists())
        self.assertTrue((root.parent / '.devlyn-install.json').exists())

    def test_cleanup_linked_roots_and_generic_links_preserved(self):
        outside = self.case / 'outside'; outside.mkdir()
        (outside / 'devlyn-review').mkdir(); (outside / 'devlyn-review/keep').write_bytes(SHORT_PAYLOAD)
        agent = self.home / '.grok'; agent.mkdir()
        run(['node', '-e', "require('fs').symlinkSync(process.argv[1], process.argv[2], 'junction')", outside, agent / 'skills'])
        self.cli('-y', '--global')
        self.assertEqual((outside / 'devlyn-review/keep').read_bytes(), SHORT_PAYLOAD)
        self.assertEqual({p.name for p in outside.iterdir()}, {'devlyn-review'})

    def test_cleanup_hardlinked_settings_and_marker_preserve_other_names(self):
        settings = self.home / '.claude/settings.json'; settings.parent.mkdir()
        owner = self.case / 'owner-settings.json'
        raw = b'{"env":{"CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS":"1","OWNER":"keep"}}'
        owner.write_bytes(raw); os.link(owner, settings)
        root = self.home / '.claude/skills'; root.mkdir()
        old = root / 'devlyn-review'; old.mkdir(); (old / 'SKILL.md').write_bytes(b'old')
        other = self.case / 'owner-marker.json'
        marker_raw = b'{"package":"devlyn-cli","schemaVersion":1,"version":"4.0.1","skills":{"devlyn-review":"old"}}'
        other.write_bytes(marker_raw); os.link(other, root / '.devlyn-install.json')
        self.invoke("cleanupScope(os.homedir(), true);")
        self.assertEqual(owner.read_bytes(), raw)
        self.assertEqual(other.read_bytes(), marker_raw)
        self.assertEqual(settings.read_bytes(), raw)
        self.assertEqual(json.loads((root / '.devlyn-install.json').read_bytes())['skills'], {})

    def test_cleanup_failed_retired_root_preserves_evidence_for_retry(self):
        root = self.home / '.grok/skills'; root.mkdir(parents=True)
        old = root / 'generic-old'; old.mkdir(); (old / 'file').write_bytes(SHORT_PAYLOAD)
        self.invoke(f"""
const root = {json.dumps(str(root))};
const old = path.join(root, 'generic-old');
fs.writeFileSync(path.join(root, DEVLYN_INSTALL_MARKER), JSON.stringify({{package: PKG.name,
  schemaVersion: 1, version: '4.0.1', skills: {{'generic-old': fingerprint(old)}}}}));
const rm = fs.rmSync;
fs.rmSync = (file, ...args) => {{ if (file === old) throw new Error('fixture denied'); return rm(file, ...args); }};
update();
""")
        self.assertTrue((root / '.devlyn-install.json').exists())
        self.cli('update')
        self.assertFalse(old.exists())
        self.assertFalse((root / '.devlyn-install.json').exists())

    def test_cleanup_foreign_marker_does_not_block_exact_names(self):
        root = self.home / '.grok/skills'; root.mkdir(parents=True)
        for raw in [b'null', b'{}', b'{']:
            marker = root / '.devlyn-install.json'; marker.write_bytes(raw)
            old = root / 'devlyn-review'; old.mkdir()
            self.cli('update')
            self.assertFalse(old.exists())
            self.assertEqual(marker.read_bytes(), raw)

    def test_cleanup_renamed_optional_preserves_foreign_new_name(self):
        root = self.project / '.agents/skills'; root.mkdir(parents=True)
        old = root / ('devlyn\uf03areap' if os.name == 'nt' else 'devlyn:reap'); old.mkdir()
        (old / 'SKILL.md').write_bytes(b'edited old copy')
        new = root / 'devlyn-reap'; new.mkdir(); (new / 'SKILL.md').write_bytes(SHORT_PAYLOAD)
        self.cli('-y')
        self.assertFalse(old.exists())
        self.assertEqual((new / 'SKILL.md').read_bytes(), SHORT_PAYLOAD)

    def test_cleanup_markerless_grok_shared_requires_shipped_tree(self):
        root = self.home / '.grok/skills'
        for name in ['_shared', '_Shared']:
            with self.subTest(name=name):
                self.seed_4_1(root)
                for entry in root.iterdir():
                    if entry.name != '_shared':
                        shutil.rmtree(entry) if entry.is_dir() else entry.unlink()
                folder = root / name
                if name != '_shared': (root / '_shared').rename(folder)
                (folder / 'owner-file').write_bytes(SHORT_PAYLOAD)
                self.cli('-y', '--global')
                self.assertEqual((folder / 'owner-file').read_bytes(), SHORT_PAYLOAD)
                (folder / 'owner-file').unlink()
                self.cli('-y', '--global')
                self.assertFalse(folder.exists())
                self.assertFalse((root / '.devlyn-install.json').exists())

    def test_cleanup_instruction_delete_failure_warns_and_succeeds(self):
        file = self.project / 'GEMINI.md'; file.write_bytes(self.evaluator_block())
        result = self.invoke(f"""
const unlink = fs.unlinkSync;
fs.unlinkSync = (file, ...args) => {{
  if (file === {json.dumps(str(file))}) throw new Error('fixture instruction deletion denied');
  return unlink(file, ...args);
}};
update();
""")
        self.assertEqual(result.stdout.count(b'fixture instruction deletion denied'), 1)
        self.assertEqual(file.read_bytes(), self.evaluator_block())
        self.assertEqual(self.markers(self.project), set())

    def test_cleanup_settings_only_exact_retired_values(self):
        data = {'env': {'CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS': '1', 'OWNER': 'yes',
                        'BASH_MAX_TIMEOUT_MS': '600000', 'ENABLE_PROMPT_CACHING_1H': False},
                'permissions': {'allow': ['Write(.devlyn/**)', 'Edit(.devlyn/**)', 'Bash(git add *)',
                    'Bash(git commit *)', 'Bash(git diff *)', 'Bash(git status *)', 'Bash(git log *)', 'owner']},
                'hooks': {'Stop': [{'hooks': [{'type': 'command', 'command': 'owner hook'}]}]}}
        raw = (json.dumps(data, indent=4) + '\n\n').encode()
        paths = [base / '.claude/settings.json' for base in [self.project, self.home]]
        for settings in paths:
            settings.parent.mkdir(); settings.write_bytes(raw)
        for args in [('-y', '--claude'), ('update',), ('-y', '--global', '--claude')]:
            self.cli(*args)
            for settings in paths:
                self.assertEqual(settings.read_bytes(), raw)

    def test_cleanup_bom_settings_only_exact_retired_hook(self):
        retired = {'type': 'command', 'command': 'python3 "$CLAUDE_PROJECT_DIR/.claude/skills/_shared/resolve-stop-hook.py"'}
        owner = {'type': 'command', 'command': SHORT_PAYLOAD.decode('utf-8')}
        data = {'big': 12345678901234567890, 'env': {'CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS': '1', 'OWNER': SHORT_PAYLOAD.decode('utf-8')},
                'permissions': {'allow': ['Write(.devlyn/**)', 'Bash(git add *)', 'owner']},
                'hooks': {'Stop': [{'hooks': [retired, owner]}]}}
        # A byte order mark, CRLF, an owner integer above 2^53: only the retired hook's bytes go.
        dump = lambda value: b'\xef\xbb\xbf' + json.dumps(value, ensure_ascii=False, indent=4).replace('\n', '\r\n').encode('utf-8') + b'\r\n\r\n'
        raw, expected = dump(data), dump({**data, 'hooks': {'Stop': [{'hooks': [owner]}]}})
        paths = [base / '.claude/settings.json' for base in [self.project, self.home]]
        for args in [('update',), ('-y', '--global')]:
            with self.subTest(args=args):
                for settings in paths:
                    settings.parent.mkdir(exist_ok=True); settings.write_bytes(raw)
                self.cli(*args)
                for settings in paths if args == ('update',) else paths[1:]:
                    self.assertEqual(settings.read_bytes(), expected)
                if args == ('update',):
                    self.assertEqual(self.markers(self.project), set())
                    self.assertEqual(self.markers(self.home), set())
                else:
                    self.assertEqual(paths[0].read_bytes(), raw)
        # A file that held nothing but the retired hook stays with its other bytes: only the reviewed cleanup,
        # which records the file first, deletes it.
        only = json.dumps({'hooks': {'Stop': [{'hooks': [retired]}]}}, indent=4).encode()
        for bom in [b'', b'\xef\xbb\xbf']:
            for eol in [b'\n', b'\r\n']:
                with self.subTest(bom=bom, eol=eol):
                    for settings in paths:
                        settings.write_bytes(bom + only.replace(b'\n', eol) + eol)
                    self.cli('update')
                    for settings in paths:
                        self.assertEqual(settings.read_bytes(), bom + b'{' + eol + b'    ' + eol + b'}' + eol)

    def test_cleanup_historical_optional_and_third_party_skills_survive(self):
        fixtures = Path(__file__).parent / 'fixtures/cleanup'
        copies = {'prompt-engineering': (fixtures / 'prompt-engineering-2.5.3.md').read_bytes(),
                  'web-design-guidelines': (fixtures / 'web-design-guidelines-0.0.1.md').read_bytes()}
        for root in self.roots() + [self.home / '.grok/skills']:
            for name, raw in copies.items():
                folder = root / name; folder.mkdir(parents=True); (folder / 'SKILL.md').write_bytes(raw)
        self.cli('-y', '--claude'); self.cli('update'); self.cli('-y', '--global', '--claude')
        for root in self.roots() + [self.home / '.grok/skills']:
            for name, raw in copies.items():
                self.assertEqual((root / name / 'SKILL.md').read_bytes(), raw)

    def test_cleanup_mixed_case_generic_requires_shipped_bytes(self):
        raw = (Path(__file__).parent / 'fixtures/cleanup/workflow-routing-1.15.0.md').read_bytes()
        for root in [self.project / '.claude/skills', self.home / '.grok/skills']:
            folder = root / 'Workflow-Routing'; folder.mkdir(parents=True)
            (folder / 'SKILL.md').write_bytes(raw + SHORT_PAYLOAD)
            self.invoke('cleanupScope(projectDir(), false); cleanupScope(os.homedir(), true);')
            self.assertEqual((folder / 'SKILL.md').read_bytes(), raw + SHORT_PAYLOAD)
            (folder / 'SKILL.md').write_bytes(raw.replace(b'\n', b'\r\n'))
            self.invoke('cleanupScope(projectDir(), false); cleanupScope(os.homedir(), true);')
            self.assertFalse(folder.exists())

    def test_cleanup_only_lock_prevents_marker_overwrite_race(self):
        root = self.home / '.claude/skills'; root.mkdir(parents=True)
        (root / 'devlyn-review').mkdir()
        marker = root / '.devlyn-install.json'
        marker.write_text(json.dumps({'package': 'devlyn-cli', 'schemaVersion': 1, 'version': '4.0.1',
                                     'skills': {'devlyn-review': 'old'}}))
        self.invoke(f"""
const assert = require('assert/strict');
const root = {json.dumps(str(root))}, marker = path.join(root, DEVLYN_INSTALL_MARKER);
const lock = path.join(root, DEVLYN_INSTALL_LOCK), read = fs.readFileSync;
let raced = false;
fs.readFileSync = (file, ...args) => {{
  const bytes = read(file, ...args);
  if (file === marker && !raced) {{
    raced = true;
    // A competing installer attempts its normal exclusive lock after cleanup reads old evidence.
    try {{
      const fd = fs.openSync(lock, 'wx');
      fs.writeFileSync(fd, JSON.stringify({{pid: process.pid, token: 'competitor'}})); fs.closeSync(fd);
      fs.writeFileSync(marker, JSON.stringify({{package: PKG.name, schemaVersion: 1,
        version: PKG.version, skills: {{'devlyn-ideate': 'new'}}}}));
      assert.fail('competing installer acquired lock while cleanup held old marker evidence');
    }} catch (error) {{ if (error.code !== 'EEXIST') throw error; }}
  }}
  return bytes;
}};
cleanupScope(os.homedir(), true);
assert.equal(raced, true);
assert.equal(fs.existsSync(lock), false);
assert.deepEqual(JSON.parse(read(marker)).skills, {{}});
""")
        # A pre-existing lock (even with our PID) is not a lock owned by this invocation.
        for root in [self.home / '.claude/skills', self.home / '.grok/skills']:
            root.mkdir(parents=True, exist_ok=True)
            (root / 'devlyn-review').mkdir()
            result = self.invoke(f"""
const root = {json.dumps(str(root))};
fs.writeFileSync(path.join(root, DEVLYN_INSTALL_LOCK), JSON.stringify({{pid: process.pid, token: 'other'}}));
cleanupScope(os.homedir(), true);
""")
            self.assertEqual(result.stdout.count(f'Cannot clean up {root}:'.encode()), 1)
            self.assertTrue((root / 'devlyn-review').exists())
            self.assertTrue((root / '.devlyn-install.lock').exists())
            (root / '.devlyn-install.lock').unlink()

    def test_cleanup_existing_only_keeps_recreated_root(self):
        root = self.home / '.grok/skills'; root.mkdir(parents=True)
        self.invoke(f"""
const assert = require('assert/strict');
const root = {json.dumps(str(root))};
const lstat = fs.lstatSync, open = fs.openSync, mkdir = fs.mkdirSync, rmdir = fs.rmdirSync;
let inspections = 0, recreated = false;
fs.lstatSync = (file, ...args) => {{
  const stat = lstat(file, ...args);
  if (file === root && ++inspections === 2) rmdir(root);
  return stat;
}};
fs.openSync = (file, ...args) => {{
  if (file === path.join(root, DEVLYN_INSTALL_LOCK)) {{ mkdir(root); recreated = true; }}
  return open(file, ...args);
}};
fs.mkdirSync = () => assert.fail('existingOnly must not create directories');
withUserSkillLocks([root], () => {{}}, {{existingOnly: true}});
assert.equal(recreated, true);
assert.equal(fs.existsSync(root), true);
assert.deepEqual(fs.readdirSync(root), []);
""")

    def test_deprecated_mixed_verified_and_unknown(self):
        for root in self.roots():
            self.seed_4_1(root)
            for name in ('devlyn-discover-product', 'devlyn-implement-ui', 'devlyn-review',
                         'devlyn-team-design-ui', 'devlyn-team-review', 'devlyn-resolve'):
                folder = root / name; folder.mkdir(exist_ok=True)
                (folder / 'SKILL.md').write_bytes(b'unverified field case')
            foreign = root / 'owner-skill'; foreign.mkdir(); (foreign / 'keep').write_bytes(SHORT_PAYLOAD)
        run(['git', 'init', '-q', self.project])
        run(['git', '-C', self.project, 'add', '.agents', '.claude'])
        result = self.cli('update')
        self.assertNotIn(b'Left in place', result.stdout)
        for root in self.roots():
            self.assertEqual({p.name for p in root.iterdir()},
                             {'devlyn-ideate', 'devlyn-engines', '_shared', '.devlyn-install.json', 'owner-skill'})
            self.assertEqual((root / 'owner-skill/keep').read_bytes(), SHORT_PAYLOAD)
        self.assert_install_notice(result)
        for name in ['.agents/skills/devlyn-review', '.claude/skills/devlyn-review']:
            self.assertIn(f'✕ {name.replace("/", os.sep)} (removed)'.encode(), result.stdout)

    def test_deprecated_only_discovery(self):
        roots = [self.home / '.agents/skills', self.home / '.codex/skills', self.project / '.claude/skills']
        for root in roots:
            folder = root / 'devlyn-review'; folder.mkdir(parents=True)
            (folder / 'SKILL.md').write_bytes(b'unverified')
        self.cli('update')
        for root in roots:
            self.assertEqual(list(root.iterdir()), [])
        self.assertEqual(self.markers(self.home), set())
        self.assertFalse((self.project / 'CLAUDE.md').exists())
        self.assertFalse((self.project / '.claude/settings.json').exists())

    def test_deprecated_discovery_leaves_invalid_markers_to_preflight(self):
        for scope in ('user', 'project-claude'):
            for kind in ('malformed', 'wrong-package', 'wrong-schema', 'directory', 'symlink'):
                with self.subTest(scope=scope, marker=kind):
                    self.project = self.case / f'{scope}-{kind}'; self.project.mkdir()
                    self.home = self.case / f'{scope}-{kind}-home'; self.home.mkdir()
                    self.env['DEVLYN_TEST_HOME'] = str(self.home)
                    root = (self.home / '.agents/skills' if scope == 'user'
                            else self.project / '.claude/skills')
                    foreign = root / 'devlyn-review'; foreign.mkdir(parents=True)
                    (foreign / 'SKILL.md').write_bytes(b'foreign review')
                    # Marker + shared selects the user root without short-circuiting on a current skill.
                    shutil.copytree(self.package / 'config/skills/_shared', root / '_shared')
                    marker = root / '.devlyn-install.json'
                    if kind == 'directory':
                        marker.mkdir()
                    elif kind == 'symlink':
                        target = self.case / f'{scope}-marker-target'
                        target.write_bytes(b'{}')
                        try:
                            marker.symlink_to(target)
                        except OSError as error:
                            if os.name != 'nt' or error.winerror != 1314:
                                raise
                            print('SKIP marker symlink: Windows privilege unavailable', flush=True)
                            continue
                    else:
                        marker.write_bytes({'malformed': b'{', 'wrong-package': b'{}',
                                            'wrong-schema': b'{"package":"devlyn-cli","schemaVersion":2}'}[kind])
                    # Exercise discovery even when readdir yields the deprecated name first.
                    self.invoke(f"""
const readdir = fs.readdirSync;
fs.readdirSync = (dir, ...args) => {{
  const names = readdir(dir, ...args);
  return dir === {json.dumps(str(root))} ? names.sort((a, b) => b.localeCompare(a)) : names;
}};
readInstallManifest = () => {{ throw new Error('discovery read the install marker'); }};
if (!{'hasDevlynInstall(' + json.dumps(str(root)) + ')' if scope == 'user' else 'hasDevlynClaude(false)'}) {{
  throw new Error('selected root was not discovered');
}}
""")
                    flags = ('-y', '--global') if scope == 'user' else ('-y',)
                    for command in (('update',), flags):
                        with self.subTest(command=command):
                            result = self.assert_install_refused(*command, paths=[marker])
                            output = result.stdout + result.stderr
                            self.assertNotIn(b'Cannot inspect', output)
                            self.assertNotRegex(output, rb'(?m)^\s+at ')

    def test_deprecated_case_insensitive_discovery(self):
        for colon in (['-', '\uf03a'] if os.name == 'nt' else ['-', ':', '\uf03a']):
            root = self.home / '.agents/skills'; root.mkdir(parents=True, exist_ok=True)
            folder = root / f'DeVlYn{colon}Review'; folder.mkdir()
            (folder / 'SKILL.md').write_bytes(b'unverified')
            self.cli('update')
            self.assertFalse(folder.exists())
            self.assertFalse((root / '.devlyn-install.json').exists())

    def test_deprecated_removal_plan_boundary(self):
        self.cli('-y')
        root = self.project / '.agents/skills'
        retired = root / 'devlyn-review'; retired.mkdir(); (retired / 'SKILL.md').write_bytes(b'old')
        active = root / 'devlyn-ideate/SKILL.md'; active.write_bytes(b'owner edit')
        self.assert_install_refused('-y', paths=[active.parent])
        self.assertEqual((retired / 'SKILL.md').read_bytes(), b'old')
        # A later copy failure must also leave cleanup-only paths intact.
        active.write_bytes((self.package / 'config/skills/devlyn-ideate/SKILL.md').read_bytes())
        result = self.invoke("fs.copyFileSync = () => { throw new Error('injected copy failure'); }; install(['agents'], false);", code=None)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual((retired / 'SKILL.md').read_bytes(), b'old')

    def test_deprecated_unverifiable_paths_are_removed(self):
        root = self.project / '.agents/skills'; root.mkdir(parents=True)
        unreadable = root / 'devlyn-review'; unreadable.mkdir()
        (unreadable / 'SKILL.md').write_bytes(b'cannot fingerprint')
        regular = root / 'devlyn-clean'; regular.write_bytes(b'ordinary file')
        target = self.case / 'elsewhere'; target.mkdir()
        (target / 'SKILL.md').write_bytes(b'linked content')
        link = root / 'devlyn-resolve'
        run(['node', '-e', "require('fs').symlinkSync(process.argv[1], process.argv[2], 'junction')", target, link])
        retained = [unreadable, regular, link]
        if os.name != 'nt':
            fifo = root / 'devlyn-implement-ui'; os.mkfifo(fifo)
            retained.append(fifo)
        result = self.invoke(f"""
const readdir = fs.readdirSync;
fs.readdirSync = (dir, ...args) => {{
  if (dir === {json.dumps(str(unreadable))}) throw Object.assign(new Error('denied'), {{ code: 'EACCES' }});
  return readdir(dir, ...args);
}};
install(['agents'], false);
""")
        for folder in retained:
            self.assertFalse(os.path.lexists(folder))
        self.assertEqual((target / 'SKILL.md').read_bytes(), b'linked content')
        marker = json.loads((root / '.devlyn-install.json').read_bytes())
        self.assertFalse(set(marker['skills']) & {folder.name for folder in retained})

    def test_tracked_pristine_retired_skill_is_removed(self):
        root = self.project / '.claude/skills'
        self.seed_4_1(root)
        run(['git', 'init', '-q', self.project])
        run(['git', '-C', self.project, 'add', '.claude/skills/devlyn-resolve'])
        run(['git', '-C', self.project, '-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.test',
             '-c', 'commit.gpgsign=false', 'commit', '-qm', 'tracked retired skill'])
        self.cli('-y', '--claude')
        self.assertFalse((root / 'devlyn-resolve').exists())
        # Git still holds the retired copy.
        self.assertTrue(run(['git', '-C', self.project, 'show', 'HEAD:.claude/skills/devlyn-resolve/SKILL.md']).stdout)

    def test_tracked_current_copy_reinstalls_and_adds_optional_skill(self):
        self.cli('-y', '--claude')
        run(['git', 'init', '-q', self.project])
        run(['git', '-C', self.project, 'add', '.agents/skills', '.claude/skills'])
        run(['git', '-C', self.project, '-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.test',
             '-c', 'commit.gpgsign=false', 'commit', '-qm', 'installed skills'])
        before = self.snapshot()
        self.cli('-y', '--claude')
        self.assertEqual(self.snapshot(), before)
        self.invoke("const roots = install(['agents', 'claude'], false, ['devlyn-reap']);"
                    " installLocalSkill('devlyn-reap', roots);")
        for target in ('.agents', '.claude'):
            self.assertTrue((self.project / target / 'skills/devlyn-reap/SKILL.md').is_file())

    def test_tracked_pristine_upgrade_with_optional_addon(self):
        # Cleanup deletes tracked retired copies; the addon must not be re-checked against them.
        root = self.project / '.claude/skills'
        self.seed_4_1(root)
        run(['git', 'init', '-q', self.project])
        run(['git', '-C', self.project, 'add', '.claude/skills'])
        run(['git', '-C', self.project, '-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.test',
             '-c', 'commit.gpgsign=false', 'commit', '-qm', 'tracked 4.1.0 install'])
        self.invoke("const roots = install(['claude'], false, ['devlyn-reap']);"
                    " installLocalSkill('devlyn-reap', roots);")
        self.assertFalse((root / 'devlyn-resolve').exists())
        self.assertTrue((root / 'devlyn-reap/SKILL.md').is_file())

    def test_retired_commands_and_linked_command_root(self):
        commands = self.project / '.claude/commands'; commands.mkdir(parents=True)
        mine = commands / 'devlyn.resolve.md'; mine.write_bytes(b'edited')
        (commands / 'mine.md').write_bytes(SHORT_PAYLOAD)
        self.cli('-y')
        self.assertFalse(mine.exists())
        self.assertEqual((commands / 'mine.md').read_bytes(), SHORT_PAYLOAD)
        elsewhere = self.case / 'global-commands'; commands.rename(elsewhere)
        (elsewhere / 'devlyn.resolve.md').write_bytes(b'target bytes')
        run(['node', '-e', "require('fs').symlinkSync(process.argv[1], process.argv[2], 'junction')", elsewhere, commands])
        self.cli('-y', '--claude')
        self.assertEqual((elsewhere / 'devlyn.resolve.md').read_bytes(), b'target bytes')

    def test_tracked_modified_or_missing_skill_refuses(self):
        root = self.project / '.claude/skills'
        self.seed_4_1(root)
        run(['git', 'init', '-q', self.project])
        for name in ('devlyn-resolve', 'devlyn-ideate'):
            run(['git', '-C', self.project, 'add', f'.claude/skills/{name}'])
            index = (self.project / '.git/index').read_bytes()
            skill = root / name / 'SKILL.md'
            skill.write_bytes(skill.read_bytes() + b'\nUser change\n')
            for state in ('edited', 'partial', 'missing'):
                with self.subTest(name=name, state=state):
                    if state == 'partial':
                        skill.unlink()
                    elif state == 'missing':
                        shutil.rmtree(skill.parent)
                    if name == 'devlyn-ideate':
                        self.assert_install_refused('-y', '--claude', paths=[skill.parent], reason='git-tracked')
                    else:
                        before = {p.relative_to(skill.parent): p.read_bytes() for p in skill.parent.rglob('*') if p.is_file()}
                        self.cli('-y', '--claude')
                        self.assertFalse(skill.parent.exists())
                    self.assertEqual((self.project / '.git/index').read_bytes(), index)
                    if name == 'devlyn-resolve' and state != 'missing':
                        skill.parent.mkdir(exist_ok=True); skill.write_bytes(b'edited')

    def test_crlf_checkout_and_os_metadata_still_match_shipped_copies(self):
        # Git for Windows checks text out with CRLF; Finder and Explorer drop metadata files.
        root = self.project / '.claude/skills'
        self.seed_4_1(root)
        for file in root.rglob('*'):
            if file.is_file() and file.name != '.devlyn-install.json':
                file.write_bytes(file.read_bytes().replace(b'\n', b'\r\n'))
        for skill in ('devlyn-resolve', 'devlyn-ideate', '_shared'):
            (root / skill / '.DS_Store').write_bytes(b'\0\0\0\1Bud1')
        (root / 'devlyn-ideate/Thumbs.db').write_bytes(b'\xd0\xcf\x11\xe0')
        self.cli('-y', '--claude')
        self.assertFalse((root / 'devlyn-resolve').exists())
        source = (self.package / 'config/skills/devlyn-ideate/SKILL.md').read_bytes()
        self.assertEqual((root / 'devlyn-ideate/SKILL.md').read_bytes(), source)
        # Line endings never hide an edit, nor does a folder named like OS metadata.
        hidden = root / 'devlyn-ideate/.DS_Store/private-notes.txt'
        hidden.parent.mkdir(); hidden.write_bytes(b'mine')
        self.assert_install_refused('-y', '--claude', paths=[hidden.parent.parent], reason='modified contents')
        shutil.rmtree(hidden.parent)
        skill = root / 'devlyn-ideate/SKILL.md'
        skill.write_bytes(source.replace(b'\n', b'\r\n') + b'User change\r\n')
        self.assert_install_refused('-y', '--claude', paths=[skill.parent], reason='modified contents')

    def test_install_without_git_still_checks_fingerprints(self):
        bins = self.case / 'no-git'; bins.mkdir()
        self.env['PATH'] = str(bins)
        node = shutil.which('node')
        command = [node, '--require', self.preload, self.package / 'bin/devlyn.js', '-y', '--claude']
        self.assertIsNone(shutil.which('git', path=self.env['PATH']))
        run(command, cwd=self.project, env=self.env)
        skill = self.project / '.claude/skills/devlyn-ideate/SKILL.md'
        self.assertTrue(skill.is_file())
        skill.write_bytes(skill.read_bytes() + b'\nUser change\n')
        before = self.snapshot()
        result = run(command, cwd=self.project, env=self.env, code=1)
        self.assertIn(b'modified contents (install manifest fingerprint mismatch)', result.stderr)
        self.assertEqual(self.snapshot(), before)

    def test_tracked_skill_and_root_casing_cannot_bypass_preflight(self):
        self.cli('-y')
        run(['git', 'init', '-q', self.project])
        original = self.project / '.agents/skills/devlyn-ideate'
        (original / 'SKILL.md').write_bytes(b'User change')
        renamed = original.with_name('Devlyn-Ideate')
        original.rename(original.with_name('case-stage'))
        original.with_name('case-stage').rename(renamed)
        run(['git', '-C', self.project, 'add', '.agents/skills/Devlyn-Ideate'])
        self.assert_install_refused('-y', paths=[original], reason='git-tracked')
        (self.project / '.agents').rename(self.project / 'root-stage')
        (self.project / 'root-stage').rename(self.project / '.AGENTS')
        run(['git', '-C', self.project, 'add', '-A'])
        self.assert_install_refused('-y', paths=[original], reason='git-tracked')

    def test_git_environment_cannot_hide_tracked_skills(self):
        self.cli('-y')
        run(['git', 'init', '-q', self.project])
        run(['git', '-C', self.project, 'add', '.agents/skills/devlyn-ideate'])
        (self.project / '.agents/skills/devlyn-ideate/SKILL.md').write_bytes(b'User change')
        for setting in ('GIT_LITERAL_PATHSPECS', 'GIT_GLOB_PATHSPECS', 'GIT_NOGLOB_PATHSPECS', 'GIT_ICASE_PATHSPECS'):
            with self.subTest(setting=setting):
                self.env[setting] = '1'
                self.assert_install_refused('-y', paths=[self.project / '.agents/skills/devlyn-ideate'], reason='git-tracked')
                del self.env[setting]

    def test_noninteractive_install_never_loads_inquirer(self):
        loader = self.case / 'deny-inquirer.mjs'
        loader.write_text("export function resolve(name, context, next) { "
                          "if (name.startsWith('@inquirer/')) throw new Error('unexpected menu import'); "
                          "return next(name, context); }\n", encoding='utf-8')
        for flags in (['--help'], ['-y', '--claude']):
            # A file URL: Node reads a bare Windows path (C:\...) as a "c:" URL scheme.
            run(['node', '--loader', loader.as_uri(), '--require', self.preload,
                 self.package / 'bin/devlyn.js', *flags], cwd=self.project, env=self.env)

    def test_modified_core_and_unknown_retired_skills_refuse(self):
        self.cli('-y', '--claude')
        root = self.project / '.claude/skills'
        edited = root / 'devlyn-ideate/SKILL.md'
        edited.write_bytes(edited.read_bytes() + b'\nMy local change\n')
        old = root / ('devlyn\uf03aresolve' if os.name == 'nt' else 'devlyn:resolve')
        old.mkdir(); (old / 'SKILL.md').write_bytes(b'unknown provenance')
        result = self.assert_install_refused('-y', '--claude', paths=[edited.parent], reason='modified contents')
        self.assertNotIn(str(old).encode(), result.stderr)

    def test_extra_ignored_and_hidden_shared_files_refuse(self):
        self.cli('-y', '--claude')
        run(['git', 'init', '-q', self.project])
        (self.project / '.gitignore').write_text('.claude/\n', encoding='utf-8')
        root = self.project / '.claude/skills/_shared'
        (root / '.private-notes').write_bytes(b'keep this too')
        (root / 'extra.py').write_bytes(b'print("user code")')
        self.assert_install_refused('-y', '--claude', paths=[root])

    def test_foreign_install_marker_refuses_without_changes(self):
        marker = self.project / '.claude/skills/.devlyn-install.json'
        marker.parent.mkdir(parents=True)
        for value in ({'package': 'someone-else', 'schemaVersion': 1},
                      {'package': 'devlyn-cli', 'schemaVersion': 2},
                      None, [], 'foreign', 1, True):
            with self.subTest(marker=value):
                marker.write_text(json.dumps(value), encoding='utf-8')
                self.assert_install_refused('-y', '--claude', paths=[marker],
                                            reason=f'{marker}: not a devlyn-cli install marker')

    def test_stale_install_marker_temp_is_preserved(self):
        result = self.invoke("""
const markerPath = path.join(process.cwd(), DEVLYN_INSTALL_MARKER);
const tempPath = `${markerPath}.${process.pid}.tmp`;
fs.writeFileSync(tempPath, 'keep stale temp bytes');
console.log(tempPath);
writeInstallMarker(process.cwd(), [], {});
""", code=1)
        self.assertIn(b'EEXIST', result.stderr)
        temp = Path(result.stdout.decode('utf-8').strip())
        self.assertTrue(temp.is_file())
        self.assertEqual(temp.read_bytes(), b'keep stale temp bytes')

    def test_second_target_conflict_preserves_every_target_before_upgrade(self):
        for root in (self.project / '.agents/skills', self.project / '.claude/skills'):
            self.seed_4_1(root)
        bad = self.project / '.claude/skills/devlyn-ideate'
        (bad / 'SKILL.md').write_bytes(b'locally edited old core')
        (self.project / 'AGENTS.md').write_bytes(b'# My instructions\n')
        (self.project / '.claude/settings.json').write_bytes(b'{"env": {}}\n')
        self.assert_install_refused('-y', '--claude', paths=[bad])

    def test_global_second_target_and_tracked_dotfiles_refuse(self):
        for root in (self.home / '.agents/skills', self.home / '.codex/skills', self.home / '.claude/skills'):
            self.seed_4_1(root)
        bad = self.home / '.codex/skills/_shared'
        (bad / 'my-notes').write_bytes(b'my data')
        self.assert_install_refused('-y', '--global', '--claude', paths=[bad])
        run(['git', 'init', '-q', self.home])
        run(['git', '-C', self.home, 'add', '.claude/skills/devlyn-resolve', '.codex/skills/_shared'])
        (self.home / '.claude/skills/devlyn-resolve/SKILL.md').write_bytes(b'User change')
        self.assert_install_refused('-y', '--global', '--claude',
                                    paths=[bad], reason='git-tracked')

    def test_pristine_4_1_upgrade_and_manifest_based_reinstall(self):
        for root in self.roots():
            self.seed_4_1(root)
        self.cli('-y', '--claude'); self.cli('-y', '--global', '--claude')
        for root in self.roots():
            self.assertFalse(any((root / name).exists() for name in ('devlyn-resolve', 'devlyn-queue', 'devlyn-design-ui')))
            marker = json.loads((root / '.devlyn-install.json').read_bytes())
            self.assertEqual(set(marker['skills']), {'_shared', 'devlyn-ideate', 'devlyn-engines'})
        before = self.snapshot()
        self.cli('-y', '--claude'); self.cli('-y', '--global', '--claude')
        self.assertEqual(self.snapshot(), before)
        # Simulate a later package changing its core: the prior install manifest remains evidence.
        run(['git', 'init', '-q', self.project])
        run(['git', '-C', self.project, 'add', '.agents/skills', '.claude/skills'])
        copy = self.case / 'next-package'; shutil.copytree(self.package, copy)
        history = copy / 'bin/skill-history.json'
        history.write_text('{"skills": {}}', encoding='utf-8')
        source = copy / 'config/skills/devlyn-ideate/SKILL.md'
        source.write_bytes(source.read_bytes() + b'\nNew package defaults\n')
        self.invoke("install(['agents', 'claude'], false);", package=copy)
        self.assertEqual((self.project / '.agents/skills/devlyn-ideate/SKILL.md').read_bytes(), source.read_bytes())

    def test_history_allows_manifestless_upgrade_after_package_changes(self):
        # History proves published copies, not the current unreleased tree under test.
        for target in ('.agents', '.claude'):
            self.seed_4_1(self.project / target / 'skills')
            (self.project / target / 'skills/.devlyn-install.json').unlink()
        run(['git', 'init', '-q', self.project])
        run(['git', '-C', self.project, 'add', '.agents/skills', '.claude/skills'])
        copy = self.case / 'next-package'; shutil.copytree(self.package, copy)
        for name in ('_shared', 'devlyn-ideate', 'devlyn-engines'):
            (copy / 'config/skills' / name / 'new-default').write_bytes(b'New package default')
        self.invoke("install(['agents', 'claude'], false);", package=copy)
        for target in ('.agents', '.claude'):
            for name in ('_shared', 'devlyn-ideate', 'devlyn-engines'):
                self.assertEqual((self.project / target / 'skills' / name / 'new-default').read_bytes(),
                                 b'New package default')

    def test_unknown_provenance_retired_is_removed(self):
        root = self.project / '.agents/skills/devlyn-design-ui'
        root.mkdir(parents=True)
        (root / 'SKILL.md').write_bytes(b'Unknown copy')
        copy = self.case / 'no-history-package'; shutil.copytree(self.package, copy)
        (copy / 'bin/skill-history.json').write_text('{"skills": {}}', encoding='utf-8')
        result = self.invoke("install(['agents'], false);", package=copy)
        self.assertIn(b'devlyn-design-ui (removed)', result.stdout)
        self.assertFalse(root.exists())

    def seed_pre_4_1(self, root, version, name, *, stamped=False):
        # Exact published skill bytes; archive paths use Windows-safe logical names.
        fixture = Path(__file__).parent / 'fixtures/installer-pre-4.1.tar.gz'
        dest = root / name
        dest.mkdir(parents=True)
        prefix = f'{version}/{name}/'
        with tarfile.open(fixture) as archive:
            for member in archive.getmembers():
                if member.name.startswith(prefix):
                    file = dest / member.name[len(prefix):]
                    file.parent.mkdir(parents=True, exist_ok=True)
                    file.write_bytes(archive.extractfile(member).read())
        if stamped:
            # Another machine, with every character shellDoubleQuoteDefault escaped.
            foreign = '/Users/other machine/a\\b $cash "quote" `tick` }/.claude/skills/' + name
            escaped = ''.join('\\' + char if char in '\\$"`}' else char for char in foreign)
            sentinel = b'${CLAUDE_SKILL_DIR:-__DEVLYN_SKILL_DIR__}'
            replacement = ('${CLAUDE_SKILL_DIR:-' + escaped + '}').encode()
            changed = 0
            for file in dest.rglob('*.md'):
                data = file.read_bytes()
                changed += data.count(sentinel)
                file.write_bytes(data.replace(sentinel, replacement))
            self.assertGreater(changed, 0)
        return dest

    def test_committed_unedited_4_0_1_resolve_upgrades(self):
        # Prediction: a committed published 4.0.1 tree is removed, never refused as edited.
        root = self.project / '.agents/skills'
        old = self.seed_pre_4_1(root, '4.0.1', 'devlyn-resolve')
        run(['git', 'init', '-q', self.project])
        run(['git', '-C', self.project, 'add', '.agents/skills'])
        run(['git', '-C', self.project, '-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.test',
             '-c', 'commit.gpgsign=false', 'commit', '-qm', 'published 4.0.1 resolve'])
        self.cli('-y')
        self.assertFalse(old.exists())
        self.assertTrue((root / 'devlyn-ideate/SKILL.md').is_file())

    def test_committed_foreign_stamped_3_x_copy_upgrades(self):
        # Prediction: escaping and the original machine's path do not change ownership.
        root = self.project / '.agents/skills'
        old = self.seed_pre_4_1(root, '3.3.1', 'devlyn-engines', stamped=True)
        old.rename(old.with_name('devlyn\uf03aengines'))
        run(['git', 'init', '-q', self.project])
        run(['git', '-C', self.project, 'add', '.agents/skills'])
        run(['git', '-C', self.project, '-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.test',
             '-c', 'commit.gpgsign=false', 'commit', '-qm', 'foreign stamped 3.3.1 engines'])
        self.cli('-y')
        self.assertFalse(old.with_name('devlyn\uf03aengines').exists())
        self.assertEqual((root / 'devlyn-engines/SKILL.md').read_bytes(),
                         (self.package / 'config/skills/devlyn-engines/SKILL.md').read_bytes())

    def test_bytecode_caches_upgrade_and_are_removed(self):
        # Prediction: generated bytecode is ignored for ownership and never survives replacement.
        self.cli('-y')
        root = self.project / '.agents/skills'
        for name in ('_shared', 'devlyn-ideate', 'devlyn-engines'):
            cache = root / name / '__pycache__/x.pyc'
            cache.parent.mkdir(); cache.write_bytes(b'generated bytecode')
        self.cli('-y')
        self.assertEqual(list(root.rglob('__pycache__')), [])
        self.assertEqual(list(root.rglob('*.pyc')), [])

    def test_cache_user_content_and_standalone_bytecode_stay_refused(self):
        # Prediction: tracked and untracked user content cannot hide behind cache names.
        for tracked in (False, True):
            for index, relative in enumerate(('__pycache__/notes.md', '__pycache__/nested', 'standalone.pyc')):
                with self.subTest(tracked=tracked, relative=relative):
                    self.project = self.case / f'cache-{tracked}-{index}'; self.project.mkdir()
                    self.cli('-y')
                    skill = self.project / '.agents/skills/devlyn-engines'
                    file = skill / relative; file.parent.mkdir(exist_ok=True)
                    if file.parent.name == '__pycache__':
                        (file.parent / 'generated.pyc').write_bytes(b'generated bytecode')
                    if relative.endswith('/nested'):
                        file.mkdir()
                    else:
                        file.write_bytes(b'user content')
                    if tracked:
                        run(['git', 'init', '-q', self.project])
                        run(['git', '-C', self.project, 'add', '.agents/skills'])
                    self.assert_install_refused('-y', paths=[skill], reason='modified contents')

    def test_functional_stamp_edits_stay_refused(self):
        old = self.seed_pre_4_1(self.project / '.agents/skills', '3.3.1', 'devlyn-engines')
        file = old / 'SKILL.md'; original = file.read_bytes()
        sentinel = b'${CLAUDE_SKILL_DIR:-__DEVLYN_SKILL_DIR__}'
        self.assertIn(sentinel, original)
        for default in ('$(cat ~/.custom-skill-location)', '/tmp/$(whoami)', '/tmp/$HOME',
                        '/tmp/`whoami`', '/tmp/"quoted"', r'/tmp/\q', 'relative/path', '',
                        'C:relative', r'\rooted', '/tmp/line\nbreak'):
            with self.subTest(default=default):
                file.write_bytes(original.replace(sentinel, ('${CLAUDE_SKILL_DIR:-' + default + '}').encode()))
                self.assert_install_refused('-y', paths=[old], reason='fingerprint mismatch with known shipped copies')

    def test_stamp_normalization_only_changes_historical_markdown_defaults(self):
        # Non-Markdown files and the bare sentinel guard were never stamped.
        self.invoke(r'''
const assert = require('node:assert/strict');
const sentinel = '${CLAUDE_SKILL_DIR:-__DEVLYN_SKILL_DIR__}';
const guard = 'test "$DEVLYN_SKILL_DIR" = "__DEVLYN_SKILL_DIR__"';
const md = path.join(projectDir(), 'probe.md');
const py = path.join(projectDir(), 'probe.py');
for (const file of [md, py]) fs.writeFileSync(file, sentinel + '\n' + guard);
const original = contentHash(md);
for (const absolute of ['/tmp/한글/a\\b $cash "quote" `tick` }', 'C:\\Users\\other machine\\skill', '\\\\server\\share\\skill']) {
  const escaped = absolute.replace(/[\\$"`}]/g, '\\$&');
  const stamped = '${CLAUDE_SKILL_DIR:-' + escaped + '}';
  fs.writeFileSync(md, stamped + '\n' + guard);
  assert.equal(contentHash(md), original, absolute);
  fs.writeFileSync(py, stamped + '\n' + guard);
  assert.notEqual(contentHash(py), original, 'non-Markdown edits are content');
  fs.writeFileSync(md, stamped + '\n' + guard.replace('__DEVLYN_SKILL_DIR__', absolute));
  assert.notEqual(contentHash(md), original, 'guard edits are content');
}
''')

    def test_release_driver_copies_and_identifies_all_installer_fixtures(self):
        if PACKAGE_ROOT is not None:
            self.skipTest('workflow source is checked in the source suite')
        # Execute the workflow's real copy/list block, then run both archives' consumers relocated.
        workflow = (ROOT / '.github/workflows/portability.yml').read_text(encoding='utf-8')
        start = workflow.index("          test = driver / 'test-windows-portability.py'")
        end = workflow.index('          for copied in driver_files:', start)
        driver = self.case / 'driver'; driver.mkdir()
        scope = {'driver': driver, 'shutil': shutil, 'check_source': lambda: None}
        with contextlib.chdir(ROOT):
            exec(compile(textwrap.dedent(workflow[start:end]), str(ROOT / '.github/workflows/portability.yml'), 'exec'), scope)
        expected = [Path('test-windows-portability.py'), Path('test-ideate-loop.py'),
                    *sorted(p.relative_to(ROOT / 'scripts') for p in (ROOT / 'scripts/fixtures').rglob('*') if p.is_file())]
        for relative in expected:
            with self.subTest(relative=relative):
                copied = driver / relative
                self.assertEqual(copied.read_bytes(), (ROOT / 'scripts' / relative).read_bytes())
                self.assertIn(copied, scope['driver_files'])
        run([sys.executable, driver / 'test-windows-portability.py', '--package-root', self.package,
             'PackageTests.test_committed_unedited_4_0_1_resolve_upgrades',
             'PackageTests.test_tracked_pristine_retired_skill_is_removed'], timeout=90)

    def test_edited_stamped_copy_stays_refused(self):
        old = self.seed_pre_4_1(self.project / '.agents/skills', '3.3.1', 'devlyn-engines', stamped=True)
        self.invoke("preflightSkills(skillRoots('agents', false));")
        file = old / 'SKILL.md'
        file.write_bytes(file.read_bytes() + b'\nUser edit\n')
        self.assert_install_refused('-y', paths=[old], reason='fingerprint mismatch with known shipped copies')

    def test_added_non_cache_file_stays_refused(self):
        old = self.seed_pre_4_1(self.project / '.agents/skills', '3.3.1', 'devlyn-engines', stamped=True)
        self.invoke("preflightSkills(skillRoots('agents', false));")
        (old / '.private-notes').write_bytes(b'user content')
        self.assert_install_refused('-y', paths=[old], reason='fingerprint mismatch with known shipped copies')

    def test_stamped_legacy_spellings_upgrade_globally(self):
        root = self.home / '.agents/skills'
        old = self.seed_pre_4_1(root, '3.3.1', 'devlyn-engines', stamped=True)
        shutil.copytree(old, root / 'devlyn\uf03aengines')
        if os.name != 'nt':
            shutil.copytree(old, root / 'devlyn:engines')
        self.cli('-y', '--global')
        self.assertEqual({p.name for p in root.iterdir()},
                         {'_shared', 'devlyn-ideate', 'devlyn-engines', '.devlyn-install.json'})
        self.assertEqual((root / 'devlyn-engines/SKILL.md').read_bytes(),
                         (self.package / 'config/skills/devlyn-engines/SKILL.md').read_bytes())

    def test_raw_manifest_still_matches_after_normalization(self):
        self.cli('-y')
        root = self.project / '.agents/skills'
        # The original 4.2.1-4.2.5 fingerprint algorithm, before stamps/cache normalization.
        result = self.invoke(r"""
function rawFingerprint(dir) {
  const entries = [];
  function visit(full, relative) {
    if (fs.lstatSync(full).isDirectory()) {
      entries.push([relative, 'directory']);
      for (const name of fs.readdirSync(full).sort()) visit(path.join(full, name), relative ? `${relative}/${name}` : name);
    } else {
      const bytes = fs.readFileSync(full).toString('latin1').replace(/\r\n/g, '\n');
      entries.push([relative, 'file', crypto.createHash('sha256').update(bytes, 'latin1').digest('hex')]);
    }
  }
  visit(dir, '');
  return crypto.createHash('sha256').update(JSON.stringify(entries)).digest('hex');
}
console.log(JSON.stringify(Object.fromEntries(DEVLYN_CORE_SKILLS.map((name) =>
  [name, rawFingerprint(path.join(skillRoots('agents', false)[0], name))]))));
""")
        marker_path = root / '.devlyn-install.json'
        marker = json.loads(marker_path.read_bytes())
        self.assertEqual(marker['skills'], json.loads(result.stdout))
        marker['version'] = '4.2.5'
        marker_path.write_text(json.dumps(marker), encoding='utf-8')
        for name in marker['skills']:
            cache = root / name / '__pycache__/x.pyc'
            cache.parent.mkdir(); cache.write_bytes(b'generated bytecode')
        copy = self.case / 'next-package'; shutil.copytree(self.package, copy)
        (copy / 'bin/skill-history.json').write_text('{"skills": {}}', encoding='utf-8')
        for name in marker['skills']:
            (copy / 'config/skills' / name / 'new-default').write_bytes(b'next defaults')
        self.invoke("install(['agents'], false);", package=copy)
        self.assertEqual(list(root.rglob('__pycache__')), [])
        for name in marker['skills']:
            self.assertEqual((root / name / 'new-default').read_bytes(), b'next defaults')

    def test_cache_names_do_not_hide_non_cache_types(self):
        self.cli('-y')
        root = self.project / '.agents/skills/devlyn-engines'
        (root / '__pycache__').write_bytes(b'user file')
        self.assert_install_refused('-y', paths=[root], reason='modified contents')
        (root / '__pycache__').unlink()
        (root / 'user.pyc').mkdir()
        self.assert_install_refused('-y', paths=[root], reason='modified contents')

    @unittest.skipIf(os.name == 'nt', 'creating a symlink needs a privilege on native Windows')
    def test_bytecode_cache_links_and_special_files_stay_refused(self):
        self.cli('-y')
        root = self.project / '.agents/skills/devlyn-engines'
        outside = self.case / 'outside'; outside.write_bytes(b'keep')
        link = root / 'linked.pyc'; link.symlink_to(outside)
        self.assert_install_refused('-y', paths=[root], reason='link or special file')
        link.unlink()
        cache = root / '__pycache__'; cache.mkdir()
        link = cache / 'linked.pyc'; link.symlink_to(outside)
        self.assert_install_refused('-y', paths=[root], reason='link or special file')
        link.unlink()
        os.mkfifo(cache / 'pipe.pyc')
        self.assert_install_refused('-y', paths=[root], reason='link or special file')

    def test_missing_manifest_current_copy_passes_but_old_modified_copy_refuses(self):
        self.cli('-y')
        root = self.project / '.agents/skills'
        (root / '.devlyn-install.json').unlink()
        self.cli('-y')
        (root / '.devlyn-install.json').unlink()
        (root / 'devlyn-engines/SKILL.md').write_bytes(b'unknown old install')
        self.assert_install_refused('-y', paths=[root / 'devlyn-engines'])

    @unittest.skipIf(os.name == 'nt', 'creating a symlink needs a privilege on native Windows')
    def test_symlink_and_nested_added_file_preserved(self):
        self.cli('-y')
        root = self.project / '.agents/skills'
        outside = self.case / 'outside'; outside.mkdir(); (outside / 'mine').write_bytes(b'keep')
        (root / '_shared/user-link').symlink_to(outside, target_is_directory=True)
        self.assert_install_refused('-y', paths=[root / '_shared'], reason='link or special file')

    def test_optional_conflict_refuses_before_core_or_instructions_change(self):
        root = self.project / '.agents/skills'
        self.seed_4_1(root)
        optional = root / 'devlyn-reap'; optional.mkdir(); (optional / 'SKILL.md').write_bytes(b'my optional edits')
        before = self.snapshot()
        # First local addon is asset-creator; ten moves reaches devlyn-reap.
        result = self.interact([['\r'], ['\r'], [*(['j'] * 10), ' ', '\r']], code=None)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(str(optional).encode(), result.stderr)
        self.assertEqual(self.snapshot(), before)

    def managed(self, template=b'# Old\n'):
        body = b'Project-specific instructions outside this managed block take precedence over these defaults.\n\n' + template
        return b'<!-- devlyn:instructions:begin sha256=' + hashlib.sha256(body).hexdigest().encode() + b' -->\n' + body + b'<!-- devlyn:instructions:end -->\n'

    def test_instruction_removal_leaves_exactly_the_owner_bytes(self):
        # Prediction: for every historical block, either line ending, only the block goes.
        prefix, suffix = b'# Team rules\n\nUse pnpm.\n\n', b'\n# Local tail\n\nKeep me.\n'
        for name, version in (('AGENTS.md', '4.0.1'), ('AGENTS.md', '4.1.0'), ('AGENTS.md', '9ecbe51c'), ('AGENTS.md', 'd2d34e3e'),
                              ('AGENTS.md', '415e2d14'), ('CLAUDE.md', '4.1.0'), ('CLAUDE.md', '9ecbe51c'), ('CLAUDE.md', 'd2d34e3e'),
                              ('CLAUDE.md', '415e2d14')):
            dest = self.project / name
            block = (Path(__file__).resolve().parent / f'fixtures/instructions/{name[:-3].lower()}-{version}.md').read_bytes()
            for eol in (b'\n', b'\r\n'):
                with self.subTest(name=name, version=version, eol=eol):
                    dest.write_bytes((prefix + block + suffix).replace(b'\n', eol))
                    self.invoke(f"removeInstructions('{name}');")
                    self.assertEqual(dest.read_bytes(), (prefix + suffix).replace(b'\n', eol))
                    self.invoke(f"removeInstructions('{name}');")
                    self.assertEqual(dest.read_bytes(), (prefix + suffix).replace(b'\n', eol))
        dest = self.project / 'AGENTS.md'
        dest.write_bytes(b'\xef\xbb\xbf' + self.managed().replace(b'\n', b'\r\n') + b'\r\n# Keep\r\n')
        removed = self.invoke("removeInstructions('AGENTS.md');").stdout
        self.assertIn(b'Removed Devlyn defaults from AGENTS.md; project-specific instructions preserved', removed)
        self.assertEqual(dest.read_bytes(), b'\xef\xbb\xbf\r\n# Keep\r\n')

    def test_instruction_removal_of_an_unmarked_template_inside_owner_text(self):
        copy = self.case / 'legacy-package'; shutil.copytree(self.package, copy)
        manifest_path = copy / 'bin/instruction-templates.json'
        manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
        old = '# Codex Project Instructions\n\ndevlyn-cli installs old defaults.\n한글 😀\n'
        manifest['AGENTS.md'].append({'length': len(old.encode('utf-16-le')) // 2,
                                      'sha256': hashlib.sha256(old.encode()).hexdigest()})
        manifest_path.write_text(json.dumps(manifest), encoding='utf-8')
        for eol in ('\n', '\r\n'):
            with self.subTest(eol=eol):
                prefix, suffix = '﻿# My project\n\n', '\n# Keep\ncustom rule\n'
                dest = self.project / 'AGENTS.md'; dest.write_bytes((prefix + old + suffix).replace('\n', eol).encode())
                self.invoke("removeInstructions('AGENTS.md');", package=copy)
                self.assertEqual(dest.read_bytes(), (prefix + suffix).replace('\n', eol).encode())

    def test_instruction_removal_deletes_only_a_file_left_empty(self):
        dest = self.project / 'AGENTS.md'
        for before in (self.managed(), b'\xef\xbb\xbf' + self.managed(), (self.package / 'AGENTS.md').read_bytes()):
            with self.subTest(before=before[:24]):
                dest.write_bytes(before)
                self.assertIn(b'AGENTS.md (removed)', self.invoke("removeInstructions('AGENTS.md');").stdout)
                self.assertFalse(dest.exists())

    def test_instruction_removal_write_failure_keeps_original_and_exact_backup(self):
        run(['git', 'init', '-q', self.project])
        before = b'# Custom project rules\r\n\r\n' + self.managed()
        dest = self.project / 'AGENTS.md'; dest.write_bytes(before)
        result = self.invoke("fs.renameSync = () => { throw new Error('injected rename failure'); }; removeInstructions('AGENTS.md');", code=None)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(b'injected rename failure', result.stderr)
        self.assertEqual(dest.read_bytes(), before)
        self.assertFalse(list(self.project.glob('AGENTS.md.*.tmp')))
        backup, = (self.project / '.devlyn/instructions').glob('AGENTS.md*.backup')
        self.assertEqual(backup.read_bytes(), before)
        run(['git', 'check-ignore', str(backup)], cwd=self.project)
        backup.write_bytes(b'different recovery data')
        result = self.invoke("removeInstructions('AGENTS.md');", code=None)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(b'Instruction recovery file differs', result.stderr)
        self.assertEqual(dest.read_bytes(), before)
        self.assertEqual(backup.read_bytes(), b'different recovery data')

    @unittest.skipIf(os.name == 'nt', 'POSIX group permission bits are not supported on Windows')
    def test_instruction_removal_preserves_permissions_despite_umask(self):
        dest = self.project / 'AGENTS.md'; dest.write_bytes(b'# Shared project rules\n\n' + self.managed())
        dest.chmod(0o664)
        self.invoke("process.umask(0o022); removeInstructions('AGENTS.md');")
        self.assertEqual(dest.read_bytes(), b'# Shared project rules\n\n')
        self.assertEqual(dest.stat().st_mode & 0o777, 0o664)

    def test_instruction_text_that_is_not_a_proven_copy_is_preserved(self):
        examples = [b'# Devlyn Agent Instructions\nOld block\n# User addition\nKeep me\n',
                    b'# Codex Project Instructions\n\ndevlyn-cli installs edited defaults.\n']
        stock = (self.package / 'AGENTS.md').read_bytes()
        examples += [b'# Team rules\n\n```markdown\n' + stock + b'```\n',
                     b'# Team rules\n\n<!--\n' + stock + b'-->\n',
                     b'# Team rules\n\n<details>\n<summary>Example</summary>\n\n' + stock + b'\n</details>\n',
                     b'# Team rules\n\n```markdown\n' + self.managed() + b'```\n',
                     b'# Team rules\n\n<!--\n' + self.managed() + b'-->\n',
                     b'<details><summary>Example</summary>\n\n' + self.managed() + b'\n</details>\n',
                     b'\xef\xbb\xbf```markdown\n' + self.managed() + b'```\n',
                     b'<details\n open>\n\n' + self.managed() + b'\n</details>\n',
                     b'<div></div><details>\n\n' + self.managed() + b'\n</details>\n',
                     b'```Use `npm install` for setup.```\n\n```\n' + self.managed() + b'```\n',
                     b'<![CDATA[\n' + self.managed() + b']]>\n',
                     b'<pre>\n\n' + self.managed() + b'</pre>\n',
                     b'<details>\n<summary>Example</summary>\n<!-- </details> -->\n\n' + self.managed() + b'\n</details>\n',
                     re.sub(rb'^(# [^\n]+\n\n).*?\n\n', rb'\1Our project owns these instructions.\n\n', stock, count=1, flags=re.S)]
        dest = self.project / 'AGENTS.md'
        for before in examples:
            with self.subTest(before=before):
                dest.write_bytes(before)
                self.invoke("removeInstructions('AGENTS.md');")
                self.assertEqual(dest.read_bytes(), before)

    def test_instruction_removal_is_not_stopped_by_closed_or_stray_markup_around_a_block(self):
        dest = self.project / 'AGENTS.md'
        section = b'<details>\nNotes\n</details>\n\n'
        prefix = b'<img src="logo.png">\n\nRun `make <target>` on <branch>.\n\n' + section
        for suffix in (b'\n' + section, b'\n<kbd>K</kbd>\n', b'\n</details>\n'):
            with self.subTest(suffix=suffix):
                dest.write_bytes(prefix + self.managed() + suffix)
                self.invoke("removeInstructions('AGENTS.md');")
                self.assertEqual(dest.read_bytes(), prefix + suffix)

    def test_instruction_markers_that_do_not_add_up_stay_as_they_are(self):
        dest = self.project / 'AGENTS.md'
        begin, rest = self.managed().split(b'\n', 1)
        for before in (self.managed() + self.managed(), begin + b'\n', rest,
                       self.managed().replace(b'# Old', b'# Edited')):
            with self.subTest(before=before[:24]):
                dest.write_bytes(before)
                self.invoke("removeInstructions('AGENTS.md');")
                self.assertEqual(dest.read_bytes(), before)

    def test_instruction_link_is_preserved(self):
        shared = self.case / 'shared.md'; shared.write_bytes(self.managed())
        dest = self.project / 'AGENTS.md'; dest.symlink_to(shared)
        result = self.invoke("removeInstructions('AGENTS.md');", code=None)
        self.assertNotEqual(result.returncode, 0)
        self.assertTrue(dest.is_symlink())
        self.assertEqual(shared.read_bytes(), self.managed())

    def test_instruction_recovery_path_that_is_not_a_real_directory_stops_the_removal(self):
        for component in ('.devlyn', '.devlyn/instructions'):
            for kind in ('link', 'file'):
                with self.subTest(component=component, kind=kind):
                    with tempfile.TemporaryDirectory(dir=self.case) as temp:
                        base = Path(temp); project = base / 'project'; project.mkdir()
                        entry = project / component; entry.parent.mkdir(exist_ok=True)
                        if kind == 'link':
                            (base / 'target').mkdir(); entry.symlink_to(base / 'target', target_is_directory=True)
                        else:
                            entry.write_bytes(b'keep obstruction')
                        dest = project / 'AGENTS.md'; before = b'# Custom\n\n' + self.managed(); dest.write_bytes(before)
                        result = self.invoke(f'process.chdir({json.dumps(str(project))}); removeInstructions("AGENTS.md");', code=None)
                        self.assertNotEqual(result.returncode, 0)
                        self.assertIn(str(entry).encode('utf-8'), result.stderr)
                        self.assertEqual(dest.read_bytes(), before)

    def test_queue_add_captures_literal_rows_under_the_common_gitdir_lock(self):
        helper = self.package / 'config/skills/devlyn-ideate/scripts/queue.py'
        loop = runpy.run_path(str(helper))
        env = dict(self.env, GIT_AUTHOR_NAME='Fixture', GIT_AUTHOR_EMAIL='fixture@example.invalid',
                   GIT_COMMITTER_NAME='Fixture', GIT_COMMITTER_EMAIL='fixture@example.invalid')
        run(['git', 'init', '-q', '--initial-branch=main', self.project], env=env)
        run(['git', '-C', self.project, 'commit', '-q', '--allow-empty', '-m', 'base'], env=env)
        title = 'Keep "quotes", $HOME, `ticks` and 한글'
        meta = loop['write_package'](self.project, 'loop', [('t1', [], title, [{'argv': [sys.executable, '-c', 'pass'], 'contract_refs': ['R1']}])])
        captured = lambda name: run(['git', '-C', self.project, 'cat-file', 'blob', f'refs/devlyn/captures/{name}:docs/specs/{name}/queue.md'],
                                    env=env, code=None)
        add = lambda code=0: run([sys.executable, helper, 'add', meta], cwd=self.project, env=env, code=code)
        add()
        self.assertEqual(captured('loop').stdout, loop['row_line']('loop.t1', title).encode('utf-8') + b'\n')
        commit = run(['git', '-C', self.project, 'rev-parse', 'refs/devlyn/captures/loop'], env=env).stdout
        add()  # The package's recorded add is reported again, so a retried add succeeds; nothing is written.
        self.assertEqual(run(['git', '-C', self.project, 'rev-parse', 'refs/devlyn/captures/loop'], env=env).stdout, commit)
        # The helper writes only while it holds <common Gitdir>/devlyn-loops/queue.lock, so concurrent adds serialize.
        second = loop['write_package'](self.project, 'next', [('t1', [], 'Next', [{'argv': [sys.executable, '-c', 'pass'], 'contract_refs': ['R1']}])])
        lock = self.project / '.git/devlyn-loops/queue.lock'
        with runpy.run_path(str(self.package / 'config/skills/_shared/platform-support.py'))['file_lock'](lock, blocking=True):
            proc = subprocess.Popen([sys.executable, str(helper), 'add', str(second)], cwd=self.project, env=env,
                                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            time.sleep(1.5)
            self.assertIsNone(proc.poll())
            self.assertNotEqual(captured('next').returncode, 0)
        self.assertEqual(proc.wait(timeout=20), 0)
        self.assertEqual(captured('next').stdout, loop['row_line']('next.t1', 'Next').encode('utf-8') + b'\n')

    def test_retired_skill_name_is_removed_only_as_shipped(self):
        # 0.2.0-1.15.0 shipped workflow-routing; a folder of that name the user wrote stays.
        mine = self.project / '.claude/skills/workflow-routing'
        mine.mkdir(parents=True); (mine / 'SKILL.md').write_text('---\nname: workflow-routing\n---\nmine\n', encoding='utf-8')
        self.invoke("install(['claude'], false);")
        self.assertEqual((mine / 'SKILL.md').read_text(encoding='utf-8'), '---\nname: workflow-routing\n---\nmine\n')
        # A shipped copy with an extra dotfile or a folder named like OS metadata stays; only
        # the exact single-file copy goes, beside at most a Finder or Explorer metadata file.
        shipped = b'---\nname: workflow-routing\n---\nshipped\n'
        (mine / 'SKILL.md').write_bytes(shipped.replace(b'\n', b'\r\n'))
        for extra in ('.notes', '.DS_Store/notes'):
            (mine / extra).parent.mkdir(exist_ok=True); (mine / extra).write_bytes(b'x')
            self.invoke("RETIRED_SKILL_MD_SHA256['workflow-routing'] = new Set(["
                        f"'{hashlib.sha256(shipped).hexdigest()}']); install(['claude'], false);")
            self.assertTrue((mine / extra).exists())
            (mine / extra).unlink()
            if (mine / '.DS_Store').is_dir():
                (mine / '.DS_Store').rmdir()
        (mine / '.DS_Store').write_bytes(b'x')
        self.invoke("RETIRED_SKILL_MD_SHA256['workflow-routing'] = new Set(["
                    f"'{hashlib.sha256(shipped).hexdigest()}']); install(['claude'], false);")
        self.assertFalse(mine.exists())

    def test_opted_in_and_own_standards_skills_survive_updates(self):
        # 3.3.0 made the standards skills optional addons; only an unedited default copy goes.
        optional = (self.package / 'optional-skills/root-cause-analysis/SKILL.md').read_bytes()
        mine = b'---\nname: code-review-standards\ndescription: mine\n---\n'
        roots = [self.project / '.agents/skills', self.project / '.claude/skills', self.home / '.claude/skills']
        for root in roots:
            for name, data in (('root-cause-analysis', optional), ('code-review-standards', mine)):
                (root / name).mkdir(parents=True); (root / name / 'SKILL.md').write_bytes(data)
        self.cli('-y', '--claude'); self.cli('-y', '--global', '--claude')
        for root in roots:
            self.assertEqual((root / 'root-cause-analysis/SKILL.md').read_bytes(), optional)
            self.assertEqual((root / 'code-review-standards/SKILL.md').read_bytes(), mine)

    def test_incomplete_source_has_no_marker(self):
        copy = self.case / 'broken'; shutil.copytree(self.package, copy)
        (copy / 'config/skills/devlyn-ideate/SKILL.md').unlink()
        stale = self.home / '.agents/skills/.devlyn-install.json'
        stale.parent.mkdir(parents=True)
        stale.write_text('{"schemaVersion": 1, "package": "devlyn-cli", "version": "stale"}', encoding='utf-8')
        result = self.invoke("install(['agents'], true);", package=copy, code=None)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(b'Incomplete devlyn skill install', result.stderr)
        self.assertEqual(self.markers(self.home), set())

    def test_failed_core_copy_keeps_the_previous_copy_for_a_plain_rerun(self):
        # A core skill is copied and checked aside before it replaces the previous copy, so a copy that fails midway
        # leaves that copy, still provably shipped, and a plain rerun installs.
        root = self.project / '.agents/skills'
        self.seed_4_1(root)
        tree = lambda folder: {p.relative_to(folder): p.read_bytes() if p.is_file() else None for p in folder.rglob('*')}
        previous = tree(root / '_shared')
        result = self.invoke("""
const copy = fs.copyFileSync;
let shared = 0;
fs.copyFileSync = (from, to, ...rest) => {
  if (from.includes(path.join('skills', '_shared') + path.sep) && ++shared === 3) throw new Error('injected copy failure');
  return copy(from, to, ...rest);
};
install(['agents'], false);
""", code=None)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(b'injected copy failure', result.stderr)
        self.assertEqual(tree(root / '_shared'), previous)
        self.assertEqual(list(root.glob('.devlyn-skill-*')), [])
        self.assertFalse((root / '.devlyn-install.json').exists())
        self.cli('-y')
        self.assertEqual(tree(root / '_shared'), tree(self.package / 'config/skills/_shared'))
        self.assertTrue((root / '.devlyn-install.json').is_file())

    def test_unknown_pre_4_names_removed_in_every_selected_root(self):
        spellings = ['\uf03a'] if os.name == 'nt' else [':', '\uf03a']
        for root in self.roots():
            for name in ('resolve', 'ideate', 'engines', 'pencil-pull', 'reap'):
                for colon in spellings:
                    old = root / f'devlyn{colon}{name}'; old.mkdir(parents=True)
                    (old / 'SKILL.md').write_text(f'---\nname: devlyn:{name}\n---\n', encoding='utf-8')
        for args in (('-y', '--claude'), ('-y', '--global', '--claude')):
            selected = self.roots()[2:] if '--global' in args else self.roots()[:2]
            self.cli(*args)
            for root in selected:
                for name in ('resolve', 'ideate', 'engines', 'pencil-pull', 'reap'):
                    for colon in spellings:
                        self.assertFalse((root / f'devlyn{colon}{name}').exists())

    def test_upgrade_removes_retired_resolve_design_ui_and_queue(self):
        # Core skills through 4.1.0, `devlyn:<name>` before 4.0.0 (npm extracts ':' as U+F03A on
        # Windows): each root an install writes loses every spelling, another root keeps them.
        spellings = ['-', '\uf03a'] if os.name == 'nt' else ['-', ':', '\uf03a']
        other = self.home / '.grok/skills'
        for root in [*self.roots(), other]:
            (root / 'my-skill').mkdir(parents=True); (root / 'my-skill/keep').write_bytes(b'mine')
            self.seed_4_1(root)
            for skill in ('resolve', 'design-ui', 'queue'):
                for c in spellings:
                    if c != '-':
                        shutil.copytree(root / f'devlyn-{skill}', root / f'devlyn{c}{skill}')
        snapshot = lambda base: {p: p.read_bytes() if p.is_file() else None for p in base.rglob('*')}
        kept = snapshot(other)
        install = lambda: (self.cli('-y', '--claude'), self.cli('-y', '--global', '--claude'))
        install()
        for root in self.roots():
            self.assertEqual({p.name for p in root.iterdir() if p.name.startswith('devlyn')},
                             {'devlyn-ideate', 'devlyn-engines'}, root)
            self.assertEqual((root / 'my-skill/keep').read_bytes(), b'mine')
            self.assertTrue((root / '.devlyn-install.json').is_file())
        self.assertEqual({p.name for p in other.iterdir()}, {'my-skill'})
        self.assertEqual((other / 'my-skill/keep').read_bytes(), b'mine')
        # Upgrading again changes nothing.
        before = snapshot(self.case)
        install()
        self.assertEqual(snapshot(self.case), before)

    @unittest.skipIf(os.name == 'nt', 'creating a symlink needs a privilege on native Windows')
    def test_upgrade_leaves_a_linked_optional_skill_alone(self):
        root = self.project / '.claude/skills'; root.mkdir(parents=True)
        mine = self.case / 'dotfiles/pencil'; mine.mkdir(parents=True)
        legacy = (self.package / 'optional-skills/devlyn-pencil-pull/SKILL.md').read_bytes().split(b'\n', 5)[5]
        (mine / 'SKILL.md').write_bytes(legacy); (mine / 'notes.md').write_bytes(b'notes')
        (root / 'devlyn-pencil-pull').symlink_to(mine, target_is_directory=True)
        self.invoke("installClaudeCore();")
        self.assertTrue((root / 'devlyn-pencil-pull').is_symlink())
        self.assertEqual({p.name: p.read_bytes() for p in mine.iterdir()}, {'SKILL.md': legacy, 'notes.md': b'notes'})

    def test_interrupted_upgrade_keeps_optional_skill_without_marker(self):
        copy = self.case / 'broken'; shutil.copytree(self.package, copy)
        (copy / 'optional-skills/devlyn-pencil-pull/SKILL.md').unlink()
        root = self.project / '.claude/skills'
        colon = '\uf03a' if os.name == 'nt' else ':'
        old, old_core = root / f'devlyn{colon}pencil-pull', root / f'devlyn{colon}ideate'
        for folder in (old, old_core):
            folder.mkdir(parents=True); (folder / 'keep').write_bytes(b'old')
        result = self.invoke("install(['claude'], false);", package=copy, code=None)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(b'Incomplete devlyn skill install', result.stderr)
        self.assertEqual((old / 'keep').read_bytes(), b'old')
        # Old names go only after the new core skills are in place.
        self.assertTrue((root / 'devlyn-ideate/SKILL.md').is_file())
        self.assertFalse((root / '.devlyn-install.json').exists())
        self.invoke("install(['claude'], false);")
        self.assertFalse(old.exists() or old_core.exists())
        self.assertTrue((root / 'devlyn-pencil-pull/SKILL.md').is_file())
        self.assertTrue((root / '.devlyn-install.json').is_file())

    def test_failed_refresh_keeps_a_0_6_copy(self):
        # A 0.6.x copy is identified by its SKILL.md; a refresh that fails leaves it for the retry.
        legacy = (self.package / 'optional-skills/devlyn-pencil-push/SKILL.md').read_bytes().split(b'\n', 5)[5]
        copy = self.case / 'broken'; shutil.copytree(self.package, copy)
        (copy / 'optional-skills/devlyn-pencil-push/SKILL.md').unlink()
        push = self.project / '.claude/skills/devlyn-pencil-push'
        push.mkdir(parents=True); (push / 'SKILL.md').write_bytes(legacy)
        cache = push / '__pycache__'; cache.mkdir(); (cache / 'x.pyc').write_bytes(b'generated bytecode')
        result = self.invoke("installClaudeCore();", package=copy, code=None)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual((push / 'SKILL.md').read_bytes(), legacy)
        self.invoke("installClaudeCore();")
        self.assertIn(b'name: devlyn-pencil-push', (push / 'SKILL.md').read_bytes())
        self.assertEqual(sorted(p.name for p in push.iterdir()), ['SKILL.md'])
        # Cache cleanup must precede the swap: on failure the legacy hash still selects a retry.
        (push / 'SKILL.md').write_bytes(legacy)
        cache.mkdir(); (cache / 'x.pyc').write_bytes(b'generated bytecode')
        result = self.invoke("const remove = fs.rmSync; fs.rmSync = (file, options) => { "
                             "if (path.basename(file) === '__pycache__') throw new Error('injected cache cleanup'); "
                             "return remove(file, options); }; installClaudeCore();", code=None)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual((push / 'SKILL.md').read_bytes(), legacy)
        self.invoke("installClaudeCore();")
        self.assertEqual(sorted(p.name for p in push.iterdir()), ['SKILL.md'])
        # A Windows checkout with core.autocrlf holds the same copy with CRLF; a failed swap
        # leaves no staged file behind.
        (push / 'SKILL.md').write_bytes(legacy.replace(b'\n', b'\r\n'))
        result = self.invoke("const rename = fs.renameSync; fs.renameSync = (from, to) => { "
                             "if (String(to).endsWith('SKILL.md')) throw new Error('injected'); return rename(from, to); }; "
                             "installClaudeCore();", code=None)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(sorted(p.name for p in push.iterdir()), ['SKILL.md'])
        self.invoke("installClaudeCore();")
        self.assertIn(b'name: devlyn-pencil-push', (push / 'SKILL.md').read_bytes())

    def test_role_configuration_filesystem_errors(self):
        import errno
        import io
        module = runpy.run_path(str(self.package / 'config/skills/_shared/role-config.py'))
        folder = self.project / '.devlyn'; folder.mkdir()
        path = folder / 'engines.json'
        actions = (lambda: module['read_config'](path, optional=True),
                   lambda: module['read_config'](path),
                   lambda: module['resolve'](self.project, 'codex', available=lambda _: True),
                   lambda: module['select'](self.project, 'codex', available=lambda _: True),
                   lambda: module['edit'](self.project, 'codex'),
                   lambda: module['edit'](self.project, None))
        def blocked():
            for index, action in enumerate(actions):
                with self.subTest(action=index):
                    with self.assertRaisesRegex(ValueError, 'BLOCKED:invalid-engine-config') as caught:
                        action()
                    self.assertIn(str(path), str(caught.exception))
        path.mkdir(); (path / 'keep').write_bytes(b'keep')
        blocked(); self.assertEqual((path / 'keep').read_bytes(), b'keep')
        (path / 'keep').unlink(); path.rmdir(); folder.rmdir(); folder.write_bytes(b'keep')
        blocked(); self.assertEqual(folder.read_bytes(), b'keep')
        folder.unlink(); folder.mkdir(); path.write_bytes(b'{"executor":"codex"}')
        for number in (errno.EACCES, errno.EIO):
            with self.subTest(errno=number):
                def inject(original):
                    def access(candidate, *args, **kwargs):
                        if isinstance(candidate, (str, bytes, os.PathLike)) and os.fsdecode(candidate) == str(path):
                            raise OSError(number, 'injected configuration read failure', str(path))
                        return original(candidate, *args, **kwargs)
                    return access
                with contextlib.ExitStack() as patches:
                    for owner, attribute in ((os, 'stat'), (os, 'lstat'), (io, 'open')):
                        patches.enter_context(patch.object(owner, attribute, inject(getattr(owner, attribute))))
                    blocked()
                self.assertEqual(path.read_bytes(), b'{"executor":"codex"}')
        self.assertEqual(sorted(p.name for p in folder.iterdir()), ['engines.json'])

    def test_role_configuration_missing_error_checks_ancestors(self):
        module = runpy.run_path(str(self.package / 'config/skills/_shared/role-config.py'))
        for nested in (False, True):
            with self.subTest(nested=nested):
                parent = self.project / ('file-' + str(nested)); parent.write_bytes(b'keep')
                path = parent / ('missing/engines.json' if nested else 'engines.json')
                def missing(original):
                    def access(candidate, *args, **kwargs):
                        if candidate == path or (nested and candidate == path.parent):
                            raise FileNotFoundError(2, 'Windows missing-path classification', str(candidate))
                        return original(candidate, *args, **kwargs)
                    return access
                with patch.object(Path, 'lstat', missing(Path.lstat)), patch.object(Path, 'stat', missing(Path.stat)):
                    with self.assertRaisesRegex(ValueError, 'BLOCKED:invalid-engine-config') as caught:
                        module['read_config'](path, optional=True)
                    self.assertIn(str(path), str(caught.exception))
                self.assertEqual(parent.read_bytes(), b'keep')
        absent = self.project / 'absent/nested/engines.json'
        self.assertEqual(module['read_config'](absent, optional=True),
                         ({}, {'path': str(absent.absolute()), 'sha256': None}))
        with patch.object(Path, 'stat', side_effect=PermissionError('ancestor access denied')):
            with self.assertRaisesRegex(ValueError, 'BLOCKED:invalid-engine-config'):
                module['read_config'](absent, optional=True)

    @unittest.skipIf(os.name == 'nt', 'symlink creation requires native Windows privileges')
    def test_role_configuration_links_preserve_entries_and_bindings(self):
        module = runpy.run_path(str(self.package / 'config/skills/_shared/role-config.py'))
        folder = self.project / '.devlyn'; folder.mkdir()
        path = folder / 'engines.json'
        sentinel = self.project / 'keep'; sentinel.write_bytes(b'untouched')
        for target in ('absent.json', 'engines.json'):
            path.symlink_to(target)
            for index, action in enumerate((
                lambda: module['read_config'](path, optional=True),
                lambda: module['read_config'](path),
                lambda: module['resolve'](self.project, 'codex', available=lambda _: True),
                lambda: module['select'](self.project, 'claude', available=lambda _: True),
                lambda: module['edit'](self.project, 'codex'),
                lambda: module['edit'](self.project, None),
            )):
                with self.subTest(target=target, action=index):
                    with self.assertRaisesRegex(ValueError, 'BLOCKED:invalid-engine-config') as caught:
                        action()
                    self.assertIn(str(path), str(caught.exception))
                    self.assertTrue(path.is_symlink()); self.assertEqual(str(path.readlink()), target)
                    self.assertEqual(sentinel.read_bytes(), b'untouched')
                    self.assertEqual(sorted(p.name for p in folder.iterdir()), ['engines.json'])
            path.unlink()
        shared = self.project / 'shared.json'; raw = b'{"executor":"claude","custom":7}\n'
        shared.write_bytes(raw); shared.chmod(0o640); path.symlink_to(shared)
        config, binding = module['read_config'](path, optional=True)
        self.assertEqual(config, {'executor': 'claude', 'custom': 7})
        self.assertEqual(binding, {'path': str(shared.resolve()), 'sha256': hashlib.sha256(raw).hexdigest()})
        module['edit'](self.project, 'codex')
        self.assertFalse(path.is_symlink()); self.assertEqual(shared.read_bytes(), raw)
        self.assertEqual(path.stat().st_mode & 0o777, 0o640)
        self.assertEqual(json.loads(path.read_bytes()), {'executor': 'codex', 'custom': 7})
        self.assertEqual(sorted(p.name for p in folder.iterdir()), ['engines.json'])
    def test_executor_pin_status_select_and_clear(self):
        # The executor is the one engine setting. A pin binds; keys earlier releases wrote for the
        # retired pipeline roles stay as written and are reported inactive; an unavailable pin is
        # reported by status and stops dispatch selection.
        script = self.package / 'config/skills/_shared/role-config.py'
        engines = self.project / '.devlyn/engines.json'; engines.parent.mkdir()
        bins = self.case / 'bin'; bins.mkdir()
        for name in ('codex', 'claude'):
            launcher = bins / (name + ('.cmd' if os.name == 'nt' else ''))
            launcher.write_text('@echo off\r\n' if os.name == 'nt' else '#!/bin/sh\n', encoding='utf-8'); launcher.chmod(0o755)

        def role(*args, path=None, code=0):
            env = dict(self.env, PATH=str(path or self.case / 'no-binaries'))
            result = run([sys.executable, script, '--workdir', self.project, '--default-engine', 'claude', *args], env=env, code=code)
            return json.loads(result.stdout) if code == 0 else result.stderr.decode('utf-8')

        legacy = b'{"executor":"codex","pair_judge_priority":["claude"],"roles":{"worker":{"engine":"claude","model":"x"}},"custom":7}\n'
        engines.write_bytes(legacy)
        status = role(path=bins)
        self.assertEqual(status['executor'], {'engine': 'codex', 'source': 'engines.json', 'availability': 'CLI-present/auth-unchecked'})
        self.assertEqual(status['inactive'], ['pair_judge_priority', 'roles'])
        self.assertEqual(role('--select', path=bins)['executor']['engine'], 'codex')
        self.assertEqual(engines.read_bytes(), legacy)
        # Unavailable: status reports it; dispatch selection fails visibly and substitutes nothing.
        self.assertEqual(role()['executor']['availability'], 'CLI-unavailable')
        error = role('--select', code=1)
        self.assertTrue(error.startswith('BLOCKED:codex-unavailable:'), error)
        self.assertNotIn('Traceback', error)
        # A worker profile is never an executor pin; the invoking CLI is reported, never blocked.
        engines.write_bytes(b'{"roles":{"worker":{"engine":"codex"}}}')
        self.assertEqual(role('--select')['executor'], {'engine': 'claude', 'source': 'default', 'availability': 'CLI-unavailable'})
        # Pins are validated before any byte changes; clear keeps unrelated keys and drops the inactive ones.
        engines.write_bytes(legacy)
        self.assertIn('BLOCKED:invalid-engine-config: no adapter for grok', role('--set-executor', 'grok', code=1))
        self.assertEqual(engines.read_bytes(), legacy)
        role('--set-executor', 'claude', path=bins)
        self.assertEqual(json.loads(engines.read_bytes()), {**json.loads(legacy), 'executor': 'claude'})
        role('--clear')
        self.assertEqual(json.loads(engines.read_bytes()), {'custom': 7})
        engines.write_bytes(b'{"executor":"codex"}')
        role('--clear')
        self.assertFalse(engines.exists())

    def test_executor_clear_reports_the_host_default_on_every_host(self):
        script = self.package / 'config/skills/_shared/role-config.py'
        engines = self.project / '.devlyn/engines.json'; engines.parent.mkdir()
        for host in ('pi', 'grok', 'claude', 'codex', 'omp'):
            for keep in ({}, {'custom': 7}):
                with self.subTest(host=host, keep=keep):
                    engines.write_text(json.dumps({'executor': 'codex', 'roles': {}, 'pair_judge_priority': [], **keep}), encoding='utf-8')
                    argv = [sys.executable, script, '--workdir', self.project, '--default-engine', host]
                    env = dict(self.env, PATH=str(self.case / 'no-binaries'))
                    cleared = run([*argv, '--clear'], env=env, code=None)
                    self.assertEqual(json.loads(engines.read_bytes()) if engines.exists() else {}, keep)
                    self.assertEqual(engines.exists(), bool(keep))
                    self.assertEqual(cleared.returncode, 0, cleared.stderr.decode('utf-8'))
                    status = json.loads(cleared.stdout)
                    self.assertEqual(status['executor'], {'engine': host, 'source': 'default', 'availability': 'CLI-unavailable'})
                    self.assertEqual(status['inactive'], [])
                    self.assertEqual(json.loads(run(argv, env=env).stdout), status)
                    if host in ('pi', 'grok'):
                        blocked = run([*argv, '--select'], env=env, code=1)
                        self.assertIn(f'no adapter for {host}'.encode(), blocked.stderr)

    def test_upgrade_from_4_1_0_and_main_retires_resolve(self):
        # A 4.1.0 or main (9ecbe51c) install: resolve as a core skill, beside leftovers under its 3.x
        # name and npm's U+F03A extraction alias; resolve-only helpers in _shared; the retired Stop
        # hook among the user's own hooks; and instruction blocks between project rules. Main's
        # 415e2d14 blocks (delivery only on a ship request, no cleanup sentence) take the same upgrade.
        spellings = ['-', '\uf03a'] if os.name == 'nt' else ['-', ':', '\uf03a']
        managed = {'type': 'command', 'command': 'python3 "$CLAUDE_PROJECT_DIR/.claude/skills/_shared/resolve-stop-hook.py"', 'timeout': 30}
        mine = {'type': 'command', 'command': 'echo keep'}
        allow = ['Write(.devlyn/**)', 'Edit(.devlyn/**)', 'Bash(git add *)', 'Bash(git commit *)',
                 'Bash(git diff *)', 'Bash(git status *)', 'Bash(git log *)']
        old_settings = {
            'env': {'ENABLE_PROMPT_CACHING_1H': 'true', 'CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS': '1', 'BASH_MAX_TIMEOUT_MS': '3600000'},
            'permissions': {'allow': [*allow, 'Bash(npm test)']},
            'hooks': {'Stop': [{'hooks': [managed, mine]}, {'hooks': [managed]}, {'matcher': '*', 'hooks': [managed]}],
                      'PreToolUse': [{'hooks': [managed]}]}}
        prefix, suffix = b'# Team rules\n\nUse pnpm.\n\n', b'\n# Local tail\n\nKeep me.\n'
        fixtures = Path(__file__).resolve().parent / 'fixtures/instructions'
        shipped = {p.name for p in (self.package / 'config/skills/_shared').iterdir() if p.name != '__pycache__'}
        for version in ('4.1.0', '9ecbe51c', '415e2d14'):
            with self.subTest(version=version):
                self.project = self.case / f'project-{version}'; self.project.mkdir()
                self.home = self.case / f'home-{version}'; self.home.mkdir()
                self.env['DEVLYN_TEST_HOME'] = str(self.home)
                other = self.home / '.grok/skills'
                for root in [*self.roots(), other]:
                    (root / 'my-skill').mkdir(parents=True); (root / 'my-skill/keep').write_bytes(b'mine')
                    self.seed_4_1(root)
                    for c in spellings:
                        if c != '-':
                            shutil.copytree(root / 'devlyn-resolve', root / f'devlyn{c}resolve')
                settings = self.project / '.claude/settings.json'
                settings.write_text(json.dumps(old_settings), encoding='utf-8')
                global_settings = self.home / '.claude/settings.json'
                global_settings.write_bytes(settings.read_bytes())
                for name in ('AGENTS.md', 'CLAUDE.md'):
                    block = (fixtures / f'{name[:-3].lower()}-{version}.md').read_bytes()
                    self.assertIn(b'asks to ship' if version == '415e2d14' else b'devlyn-resolve', block)
                    (self.project / name).write_bytes(prefix + block + suffix)
                result = self.cli('-y')
                self.cli('-y', '--global', '--claude')
                for root in self.roots():
                    self.assertEqual({p.name for p in root.iterdir() if p.name.startswith('devlyn')}, {'devlyn-ideate', 'devlyn-engines'}, root)
                    self.assertEqual({p.name for p in (root / '_shared').iterdir()}, shipped, root)
                    self.assertEqual((root / 'my-skill/keep').read_bytes(), b'mine')
                self.assertEqual({p.name for p in other.iterdir()}, {'my-skill'})
                upgraded = json.loads(settings.read_bytes())
                self.assertEqual(global_settings.read_bytes(), settings.read_bytes())
                self.assertEqual(upgraded['env'], old_settings['env'])
                self.assertEqual(upgraded['permissions'], old_settings['permissions'])
                self.assertEqual(upgraded['hooks'], {'Stop': [{'hooks': [mine]}, {'matcher': '*', 'hooks': []}],
                                                     'PreToolUse': [{'hooks': [managed]}]})
                notices = [line for line in result.stdout.decode('utf-8').splitlines() if 'Retired devlyn settings' in line]
                self.assertEqual(len(notices), 1)
                self.assertIn('CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS', notices[0])
                for rule in allow: self.assertIn(rule, notices[0])

                # The project's old principles stay for the one reviewed cleanup; upgrading never rewrites them.
                for name in ('AGENTS.md', 'CLAUDE.md'):
                    data = (self.project / name).read_bytes()
                    self.assertTrue(data.startswith(prefix)); self.assertTrue(data.endswith(suffix))
                # Upgrading again changes nothing.
                tree = {p: p.read_bytes() if p.is_file() else None for base in (self.project, self.home) for p in base.rglob('*')}
                self.cli('-y'); self.cli('-y', '--global', '--claude')
                self.assertEqual({p: p.read_bytes() if p.is_file() else None for base in (self.project, self.home) for p in base.rglob('*')}, tree)


class ProcessTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='devlyn-native-')
        self.addCleanup(self.temp.cleanup)
        self.work = Path(self.temp.name).resolve()
        self.shared = (PACKAGE_ROOT or ROOT) / 'config/skills/_shared'

    def test_utf8_imports_and_cli_with_utf8_mode_disabled(self):
        program = r'''
import codecs, io, json, locale, os, pathlib, runpy, sys
shared, work = map(pathlib.Path, sys.argv[1:])
with io.TextIOWrapper(io.BytesIO()) as default_text:
    default_encoding = default_text.encoding
print(json.dumps({'platform':sys.platform,'utf8_mode':sys.flags.utf8_mode,
                  'locale':locale.getencoding(),'default_textio':default_encoding,
                  'stdin':sys.stdin.encoding,'stdout':sys.stdout.encoding,'stderr':sys.stderr.encoding}), flush=True)
assert sys.flags.utf8_mode == 0
if sys.platform == 'win32':
    assert codecs.lookup(locale.getencoding()).name != 'utf-8', locale.getencoding()
    assert codecs.lookup(default_encoding).name == codecs.lookup(locale.getencoding()).name
payload = '한국어 — “판정” …'
role = runpy.run_path(shared / 'role-config.py')
assert role['adapter']('codex').encode('utf-8') == (shared / 'adapters/codex.adapter.md').read_bytes()
completion = runpy.run_path(shared / 'task-complete.py')
p = work / '한국어.json'
completion['atomic_json'](p, {'message':payload})
assert completion['read_json'](p)['message'] == payload
contract = runpy.run_path(shared / 'expected-contract.py')
assert runpy.run_path(shared / 'warm-build-dirs.py')['warm'](work, work, work) == []
assert contract['loads_strict_json'](p.read_text(encoding='utf-8'))['message'] == payload
storage = runpy.run_path(shared / 'storage-client.py')
wire = storage['encode_request']({'op':'locate', 'parent':str(work), 'entry':payload})
assert json.loads(wire)['request']['entry'] == payload
os.environ['HOME'] = os.environ['USERPROFILE'] = str(work)
assert storage['enrollment']()['mode'] == 'standalone'
assert not (work / '.devlyn').exists()
# Explicit cp949 streams are distinct from the observed native ANSI default.
sys.stdout.reconfigure(encoding='cp949', errors='strict')
sys.stderr.reconfigure(encoding='cp949', errors='strict')
print(json.dumps({'stream_fixture':'cp949','stdout':sys.stdout.encoding,'stderr':sys.stderr.encoding}), flush=True)
runpy.run_path(shared / 'platform-support.py')['configure_utf8']()
print(payload)
print(payload, file=sys.stderr)
'''
        result = run([sys.executable, '-X', 'utf8=0', '-c', program, self.shared, self.work])
        observed = json.loads(result.stdout.splitlines()[0]); print('observed encoding ' + json.dumps(observed), flush=True)
        print('explicit cp949 streams ' + result.stdout.splitlines()[1].decode('ascii'), flush=True)
        if os.name != 'nt': print('SKIP native Windows ANSI defaults; cp949 streams and UTF8-disabled imports exercised', flush=True)
        self.assertIn('한국어 — “판정” …'.encode(), result.stdout)
        self.assertIn('한국어 — “판정” …'.encode(), result.stderr)
        env = environment(); env.update(PYTHONUTF8='0', DEVLYN_CODEX_PROMPT_FILE=str(self.work / '없는 파일'))
        error = run([sys.executable, '-X', 'utf8=0', self.shared / 'invocation-receipt.py', 'dispatch', '--binary', sys.executable,
                     '--timeout', '5', '--heartbeat', '0', '--', '-'], env=env, code=2)
        self.assertIn('없는 파일'.encode(), error.stderr)

    def test_completion_native_locks(self):
        repo = self.work / 'repo'; repo.mkdir()
        ready = self.work / 'ready'
        complete = helper('task-complete')
        branch = 'task/native-lock'; ident = hashlib.sha256(branch.encode()).hexdigest()[:24]
        receipt = self.work / 'common/devlyn-completion' / ident / 'receipt.json'; receipt.parent.mkdir(parents=True)
        complete['atomic_json'](receipt, {'common_gitdir': str(self.work / 'common'), 'id': ident,
                                        'branch': branch, 'base': 'main', 'allocation': 'owned'})
        holder = "import pathlib,runpy,sys,time; m=runpy.run_path(sys.argv[1]);\nwith m['locked_receipt'](pathlib.Path(sys.argv[2])):\n pathlib.Path(sys.argv[3]).touch(); time.sleep(20)"
        proc = subprocess.Popen([sys.executable, '-c', holder, str(self.shared / 'task-complete.py'), str(receipt), str(ready)], env=environment(), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        contender = None
        try:
            wait_for(ready.exists)
            acquired = self.work / 'acquired'
            contender = subprocess.Popen([sys.executable, '-c', holder.replace('time.sleep(20)', 'pass'), str(self.shared / 'task-complete.py'), str(receipt), str(acquired)], env=environment(), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            time.sleep(0.2); self.assertIsNone(contender.poll()); self.assertFalse(acquired.exists())
            proc.kill(); proc.communicate(timeout=5)
            out, err = contender.communicate(timeout=5)
            self.assertEqual((contender.returncode, out, err), (0, b'', b'')); self.assertTrue(acquired.exists())
        finally:
            for child in (proc, contender):
                if child is not None and child.poll() is None:
                    child.kill(); child.communicate(timeout=5)
        with self.assertRaises(RuntimeError):
            with complete['locked_receipt'](receipt):
                raise RuntimeError('release on exception')
        with complete['locked_receipt'](receipt):
            pass
        (receipt.parent / 'lock').unlink(); (receipt.parent / 'lock').mkdir()
        with self.assertRaisesRegex(complete['CompletionError'], 'lock unavailable'):
            with complete['locked_receipt'](receipt):
                self.fail('unavailable lock admitted')
        if os.name == 'nt':
            with self.assertRaisesRegex(complete['CompletionError'], 'unsupported.*retain workspace'):
                complete['stopped_writers'](repo)


@unittest.skipUnless(os.name == 'nt', 'native Windows job ownership and DWORD exit codes')
class NativeOwnershipTests(unittest.TestCase):
    def setUp(self):
        import ctypes
        from ctypes import wintypes
        self.ctypes = ctypes
        self.kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        for name, args, result in (
            ('OpenProcess', [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD], wintypes.HANDLE),
            ('WaitForSingleObject', [wintypes.HANDLE, wintypes.DWORD], wintypes.DWORD),
            ('TerminateProcess', [wintypes.HANDLE, wintypes.UINT], wintypes.BOOL),
            ('CloseHandle', [wintypes.HANDLE], wintypes.BOOL),
            ('GetHandleInformation', [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)], wintypes.BOOL),
            ('CreateEventW', [ctypes.c_void_p, wintypes.BOOL, wintypes.BOOL, wintypes.LPCWSTR], wintypes.HANDLE),
            ('SetEvent', [wintypes.HANDLE], wintypes.BOOL),
            ('QueryInformationJobObject', [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD, ctypes.c_void_p], wintypes.BOOL),
        ):
            function = getattr(self.kernel, name); function.argtypes = args; function.restype = result
        self.temp = tempfile.TemporaryDirectory(prefix='devlyn-job-')
        self.addCleanup(self.temp.cleanup)
        self.work = Path(self.temp.name)
        self.shared = (PACKAGE_ROOT or ROOT) / 'config/skills/_shared'
        self.platform = helper('platform-support')
        self.scope = self.platform['run_process'].__globals__
        self.handles = {}
        self.addCleanup(self.reap_fixture)
        owner = self
        class ObservedLaunch(subprocess.Popen):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                owner.retain(self.pid)
        observer = patch.object(subprocess, 'Popen', ObservedLaunch)
        observer.start(); self.addCleanup(observer.stop)
        self.release = self.work / 'release'
        self.ticks = self.work / 'ticks'
        self.leader = self.work / 'leader.pid'
        leaf = self.work / 'leaf.py'
        leaf.write_text("import os,pathlib,sys,time\np=pathlib.Path(sys.argv[1]); p.with_suffix('.pid').write_text(str(os.getpid()),encoding='utf-8')\nwhile True:\n p.write_bytes(str(time.monotonic_ns()).encode()); time.sleep(.02)\n", encoding='utf-8')
        target = self.work / 'target.py'
        target.write_text("import subprocess,sys,os,pathlib,time,ctypes\nsubprocess.Popen([sys.executable,sys.argv[1],sys.argv[2]])\npathlib.Path(sys.argv[3]).write_text(str(os.getpid()),encoding='utf-8')\ndeadline=time.monotonic()+15\nwhile not pathlib.Path(sys.argv[4]).exists():\n if time.monotonic()>deadline: raise RuntimeError('fixture release timeout')\n time.sleep(.01)\nexit=ctypes.windll.kernel32.ExitProcess; exit.argtypes=[ctypes.c_uint]; exit.restype=None; exit(int(sys.argv[5]))\n", encoding='utf-8')
        self.command = [sys.executable, str(target), str(leaf), str(self.ticks), str(self.leader), str(self.release), '19']

    def retain(self, pid):
        if pid not in self.handles:
            handle = self.kernel.OpenProcess(0x100001 | 0x1000, False, pid)
            if not handle:
                raise self.ctypes.WinError(self.ctypes.get_last_error())
            self.handles[pid] = handle
        return self.handles[pid]

    def alive(self, handle):
        result = self.kernel.WaitForSingleObject(handle, 0)
        self.assertIn(result, (0, 258))
        return result == 258

    def observe_tree(self):
        wait_for(lambda: self.leader.exists() and self.ticks.exists() and self.ticks.with_suffix('.pid').exists())
        leader = self.retain(int(self.leader.read_text(encoding='utf-8')))
        descendant = self.retain(int(self.ticks.with_suffix('.pid').read_text(encoding='utf-8')))
        self.assertTrue(self.alive(leader)); self.assertTrue(self.alive(descendant))
        before = self.ticks.read_bytes()
        wait_for(lambda: self.ticks.read_bytes() != before)
        return leader, descendant

    def assert_ceased(self, handle):
        self.assertFalse(self.alive(handle), 'owned process survived product teardown')

    def assert_all_ceased(self):
        for handle in self.handles.values():
            self.assert_ceased(handle)

    def reap_fixture(self):
        # Retained handles reap failed fixtures; this runs AFTER product assertions.
        self.release.touch()
        for handle in self.handles.values():
            try:
                if self.alive(handle):
                    if not self.kernel.TerminateProcess(handle, 1):
                        raise self.ctypes.WinError(self.ctypes.get_last_error())
                    self.assertEqual(self.kernel.WaitForSingleObject(handle, 5000), 0)
            finally:
                self.assertTrue(self.kernel.CloseHandle(handle))

    @contextlib.contextmanager
    def trace_job_handles(self):
        kernel = self.scope['_kernel']
        create, opened, close, wait = (getattr(kernel, name) for name in
                                     ('CreateJobObjectW', 'OpenProcess', 'CloseHandle', 'WaitForSingleObject'))
        trace = {'jobs': [], 'opened': [], 'closed': [], 'waited': []}
        live = set()

        def created(*args):
            handle = create(*args); trace['jobs'].append(handle)
            live.add(handle)
            return handle

        def retained(access, inherit, pid):
            handle = opened(access, inherit, pid); trace['opened'].append((pid, handle))
            live.add(handle)
            return handle

        def closed(handle):
            result = close(handle)
            value = getattr(handle, 'value', handle)
            if value in live:
                live.remove(value); trace['closed'].append(value)
            flags = self.ctypes.c_ulong()
            self.assertFalse(self.kernel.GetHandleInformation(value, self.ctypes.byref(flags)))
            self.assertEqual(self.ctypes.get_last_error(), 6)
            return result

        def waited(handle, milliseconds):
            trace['waited'].append((handle, milliseconds))
            return wait(handle, milliseconds)

        with patch.object(kernel, 'CreateJobObjectW', created), patch.object(kernel, 'OpenProcess', retained), \
                patch.object(kernel, 'CloseHandle', closed), patch.object(kernel, 'WaitForSingleObject', waited):
            try:
                yield trace
            finally:
                # Failure cleanup is after the test's product assertions, never their oracle.
                for handle in live:
                    close(handle)

    def assert_job_handles_closed(self, trace):
        for handle in trace['jobs'] + [handle for _, handle in trace['opened']]:
            self.assertEqual(trace['closed'].count(handle), 1, trace)

    def pid_array(self, buffer):
        count = self.ctypes.cast(buffer, self.ctypes.POINTER(self.ctypes.c_ulong))[1]
        return (self.ctypes.c_size_t * count).from_address(self.ctypes.cast(buffer, self.ctypes.c_void_p).value + 8)

    def job_pids(self, job):
        buffer = self.ctypes.create_string_buffer(8 + 64 * self.ctypes.sizeof(self.ctypes.c_size_t))
        self.assertTrue(self.kernel.QueryInformationJobObject(job, 3, buffer, len(buffer), None))
        return list(self.pid_array(buffer))

    def gated_job(self):
        work = Path(tempfile.mkdtemp(prefix='gated-', dir=self.work))
        prefix = 'Local\\devlyn-' + self.work.name + '-' + work.name + '-'
        gates = {}
        for name in ('ready', 'a_exit', 'spawn', 'c_ready', 'attempted', 'finish'):
            handle = self.kernel.CreateEventW(None, True, False, prefix + name)
            self.assertTrue(handle)
            self.addCleanup(lambda handle=handle: self.assertTrue(self.kernel.CloseHandle(handle)))
            gates[name] = handle
        script = work / 'gated.py'
        script.write_text(r'''
import ctypes, pathlib, subprocess, sys
from ctypes import wintypes
k = ctypes.WinDLL('kernel32', use_last_error=True)
k.OpenEventW.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.LPCWSTR]
k.OpenEventW.restype = wintypes.HANDLE
k.SetEvent.argtypes = [wintypes.HANDLE]
k.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
k.WaitForSingleObject.restype = wintypes.DWORD
k.CloseHandle.argtypes = [wintypes.HANDLE]
prefix, role = sys.argv[1:]
work = pathlib.Path(__file__).parent
def gate(name, signal=False):
    handle = k.OpenEventW(0x100002, False, prefix + name)
    if not handle: raise ctypes.WinError(ctypes.get_last_error())
    try:
        if signal:
            if not k.SetEvent(handle): raise ctypes.WinError(ctypes.get_last_error())
        elif k.WaitForSingleObject(handle, 15000) != 0:
            raise RuntimeError('native fixture gate timed out: ' + name)
    finally:
        if not k.CloseHandle(handle): raise ctypes.WinError(ctypes.get_last_error())
if role == 'A':
    gate('a_exit')
elif role == 'C':
    (work / 'C.executed').touch()
    gate('c_ready', True)
    gate('finish')
else:
    a = subprocess.Popen([sys.executable, __file__, prefix, 'A'])
    (work / 'A.pid').write_text(str(a.pid), encoding='utf-8')
    gate('ready', True)
    gate('spawn')
    try:
        c = subprocess.Popen([sys.executable, __file__, prefix, 'C'])
    except OSError as exc:
        outcome = str(exc.winerror)
    else:
        (work / 'C.pid').write_text(str(c.pid), encoding='utf-8')
        gate('c_ready')
        outcome = 'admitted'
    (work / 'outcome').write_text(outcome, encoding='utf-8')
    gate('attempted', True)
    gate('finish')
''', encoding='utf-8')
        job = self.scope['_WindowsJob']()
        job.start([sys.executable, str(script), prefix, 'B'], subprocess.DEVNULL)
        self.assertEqual(self.kernel.WaitForSingleObject(gates['ready'], 8000), 0)
        a = self.retain(int((work / 'A.pid').read_text(encoding='utf-8')))
        b = self.retain(job.target_pid)
        self.assertTrue(self.alive(a)); self.assertTrue(self.alive(b))
        return job, gates, work, a, b

    def test_child_after_initial_observation_is_captured_and_pid_buffer_grows(self):
        kernel = self.scope['_kernel']
        with self.trace_job_handles() as trace:
            job, gates, work, a, b = self.gated_job()
            set_limit, query = kernel.SetInformationJobObject, kernel.QueryInformationJobObject
            initial, growth = [], []

            def before_barrier(handle, kind, info, size):
                self.assert_ceased(self.handles[job.child.pid])
                # Signaled bootstrap handles can precede removal from the job PID list.
                wait_for(lambda: job.child.pid not in self.job_pids(handle))
                initial.extend(self.job_pids(handle))
                self.assertEqual(set(initial), {job.target_pid, int((work / 'A.pid').read_text(encoding='utf-8'))})
                self.assertTrue(self.kernel.SetEvent(gates['spawn']))
                self.assertEqual(self.kernel.WaitForSingleObject(gates['attempted'], 8000), 0)
                self.assertEqual((work / 'outcome').read_text(encoding='utf-8'), 'admitted')
                c_pid = int((work / 'C.pid').read_text(encoding='utf-8'))
                self.assertNotIn(c_pid, initial); self.assertTrue(self.alive(self.retain(c_pid)))
                return set_limit(handle, kind, info, size)

            def collect(*args):
                self.assertEqual(args[1], 3, 'pre-kill member PIDs, not accounting')
                try:
                    return query(*args)
                except OSError as exc:
                    growth.append(exc.winerror)
                    raise

            with patch.object(kernel, 'SetInformationJobObject', before_barrier), \
                    patch.object(kernel, 'QueryInformationJobObject', collect):
                job.terminate()
            self.assertEqual(growth, [234])
            self.assertEqual({pid for pid, _ in trace['opened']},
                             {*initial, int((work / 'C.pid').read_text(encoding='utf-8'))})
            self.assertEqual({h for h, _ in trace['waited']}, {h for _, h in trace['opened']})
            self.assert_all_ceased(); self.assert_job_handles_closed(trace)
            print('native initial observation -> admitted C -> zero barrier -> ERROR_MORE_DATA -> capture/wait all', flush=True)

    def test_zero_barrier_rejects_freed_slot_and_current_count_control_admits(self):
        kernel = self.scope['_kernel']
        for control in (False, True):
            with self.subTest(current_count_control=control), self.trace_job_handles() as trace:
                job, gates, work, a, b = self.gated_job()
                set_limit, terminate = kernel.SetInformationJobObject, kernel.TerminateJobObject
                boundaries = []

                def barrier(handle, kind, info, size):
                    limits = self.ctypes.cast(info, self.ctypes.POINTER(self.scope['_ExtendedLimits'])).contents
                    self.assertEqual(limits.BasicLimitInformation.ActiveProcessLimit, 0)
                    self.assertEqual(limits.BasicLimitInformation.LimitFlags, 0x2008)
                    self.assert_ceased(self.handles[job.child.pid])
                    # Establish the exact starting members before testing admission limits.
                    wait_for(lambda: job.child.pid not in self.job_pids(handle))
                    self.assertEqual(set(self.job_pids(handle)), {job.target_pid, int((work / 'A.pid').read_text(encoding='utf-8'))})
                    if control:
                        limits.BasicLimitInformation.ActiveProcessLimit = 2
                    result = set_limit(handle, kind, info, size)
                    readback = self.scope['_ExtendedLimits']()
                    self.assertTrue(self.kernel.QueryInformationJobObject(handle, 9, self.ctypes.byref(readback), size, None))
                    self.assertEqual(readback.BasicLimitInformation.LimitFlags, 0x2008)
                    self.assertEqual(readback.BasicLimitInformation.ActiveProcessLimit, 2 if control else 0)
                    self.assertTrue(self.kernel.SetEvent(gates['a_exit']))
                    self.assertEqual(self.kernel.WaitForSingleObject(a, 8000), 0)
                    wait_for(lambda: int((work / 'A.pid').read_text(encoding='utf-8')) not in self.job_pids(handle))
                    self.assertTrue(self.alive(b))
                    self.assertTrue(self.kernel.SetEvent(gates['spawn']))
                    self.assertEqual(self.kernel.WaitForSingleObject(gates['attempted'], 8000), 0)
                    self.assertEqual((work / 'outcome').read_text(encoding='utf-8'), 'admitted' if control else '1816')
                    self.assertEqual((work / 'C.executed').exists(), control)
                    if control:
                        self.assertTrue(self.alive(self.retain(int((work / 'C.pid').read_text(encoding='utf-8')))))
                    boundaries.append('A exited -> B attempted C')
                    return result

                def kill(handle, code):
                    self.assertEqual(boundaries, ['A exited -> B attempted C'])
                    if not control:
                        self.assertEqual([pid for pid, _ in trace['opened']], [job.target_pid])
                    return terminate(handle, code)

                with patch.object(kernel, 'SetInformationJobObject', barrier), patch.object(kernel, 'TerminateJobObject', kill):
                    job.terminate()
                self.assert_all_ceased(); self.assert_job_handles_closed(trace)
                print(f'native current-count-control={control}: barrier -> A exit -> C outcome=' +
                      (work / 'outcome').read_text(encoding='utf-8') + ' -> retained members ceased', flush=True)

    def test_natural_exit_after_enumeration_before_capture(self):
        kernel = self.scope['_kernel']
        with self.trace_job_handles() as trace:
            job = self.scope['_WindowsJob'](); job.start(self.command, subprocess.DEVNULL)
            leader, descendant = self.observe_tree()
            leader_pid = job.target_pid
            query = kernel.QueryInformationJobObject
            collected = []

            def exit_after_list(*args):
                result = query(*args)
                self.assertEqual(args[1], 3)
                self.assertIn(leader_pid, self.pid_array(args[2]))
                self.release.touch()
                self.assertEqual(self.kernel.WaitForSingleObject(leader, 8000), 0)
                self.assertTrue(self.alive(descendant))
                collected.append('enumerated -> natural leader exit -> live descendant')
                return result

            with patch.object(kernel, 'QueryInformationJobObject', exit_after_list):
                job.terminate()
            self.assertEqual(len(collected), 1)
            self.assertIn(int(self.ticks.with_suffix('.pid').read_text(encoding='utf-8')),
                          [pid for pid, h in trace['opened'] if h in {w for w, _ in trace['waited']}])
            self.assert_all_ceased(); self.assert_job_handles_closed(trace)
            print('native enumeration -> natural exit before capture -> live descendant waited; '
                  f'natural leader acquired={leader_pid in [pid for pid, _ in trace["opened"]]}; '
                  'no claim about pre-capture pending I/O or historical process-object finalization', flush=True)

    def test_stale_list_gone_and_different_job_identity(self):
        kernel = self.scope['_kernel']
        unrelated = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(30)'])
        try:
            with self.trace_job_handles() as trace:
                job = self.scope['_WindowsJob'](); job.start(self.command, subprocess.DEVNULL)
                leader, descendant = self.observe_tree()
                gone = subprocess.Popen([sys.executable, '-c', 'pass'])
                self.assertEqual(gone.wait(timeout=5), 0)
                gone._handle.Close()
                self.assertTrue(self.kernel.CloseHandle(self.handles.pop(gone.pid)))

                def gone_pid():
                    process = self.kernel.OpenProcess(0x101000, False, gone.pid)
                    if not process:
                        self.assertEqual(self.ctypes.get_last_error(), 87)
                        return True
                    try:
                        self.assertFalse(self.alive(process), 'gone-PID fixture refers to a live process')
                    finally:
                        self.assertTrue(self.kernel.CloseHandle(process))
                    return False

                wait_for(gone_pid)
                query, identity = kernel.QueryInformationJobObject, kernel.IsProcessInJob
                rejected = []

                def stale_list(handle, kind, buffer, size, needed):
                    result = query(handle, kind, buffer, size, needed)
                    self.assertEqual(kind, 3)
                    pids = [unrelated.pid if pid == job.target_pid else pid for pid in self.pid_array(buffer)] + [gone.pid]
                    header = self.ctypes.cast(buffer, self.ctypes.POINTER(self.ctypes.c_ulong))
                    header[0] = len(pids)
                    if size < 8 + len(pids) * self.ctypes.sizeof(self.ctypes.c_size_t):
                        raise self.ctypes.WinError(234, 'identity-race fixture needs one stale PID slot')
                    header[1] = len(pids)
                    self.pid_array(buffer)[:] = pids
                    return result

                def checked_identity(handle, owned_job, member):
                    result = identity(handle, owned_job, member)
                    if (unrelated.pid, handle) in trace['opened']:
                        self.assertFalse(self.ctypes.cast(member, self.ctypes.POINTER(self.ctypes.c_long))[0])
                        rejected.append(handle)
                    return result

                with patch.object(kernel, 'QueryInformationJobObject', stale_list), \
                        patch.object(kernel, 'IsProcessInJob', checked_identity):
                    job.terminate()
                self.assertEqual(len(rejected), 1)
                self.assertNotIn(rejected[0], [h for h, _ in trace['waited']])
                self.assertNotIn(gone.pid, [pid for pid, _ in trace['opened']])
                self.assertTrue(self.alive(self.handles[unrelated.pid]))
                self.assert_ceased(descendant)
                self.assert_job_handles_closed(trace)
                print('native stale-list fixture: real gone-87 skipped; substituted unrelated identity '
                      'rejected, unwaited and unaffected; this is not observed OS PID recycling', flush=True)
        finally:
            if unrelated.poll() is None:
                unrelated.kill()
            unrelated.wait(timeout=5)

    def test_retained_handles_block_until_signaled_with_one_deadline(self):
        import threading
        from types import SimpleNamespace
        kernel = self.scope['_kernel']
        with self.trace_job_handles() as trace:
            job = self.scope['_WindowsJob'](); job.start(self.command, subprocess.DEVNULL)
            self.observe_tree()
            terminate, wait = kernel.TerminateJobObject, kernel.WaitForSingleObject
            requested, entered, done = threading.Event(), threading.Event(), threading.Event()
            errors = []

            def deferred_termination(handle, code):
                self.assertEqual((handle, code), (job.handle, 1))
                requested.set()
                return 1  # Scoped gate: the main thread makes this real native call below.

            def blocking_wait(handle, milliseconds):
                if not entered.is_set():
                    self.assertTrue(requested.is_set()); self.assertTrue(self.alive(handle))
                    self.assertGreater(milliseconds, 0)
                    entered.set()
                return wait(handle, milliseconds)

            def teardown():
                try:
                    job.terminate()
                except BaseException as exc:
                    errors.append(exc)
                finally:
                    done.set()

            clock = iter((100, 101, 103))  # One 5s deadline, decreasing remaining waits.
            with patch.object(kernel, 'TerminateJobObject', deferred_termination), \
                    patch.object(kernel, 'WaitForSingleObject', blocking_wait), \
                    patch.dict(self.scope, time=SimpleNamespace(monotonic=lambda: next(clock))):
                worker = threading.Thread(target=teardown); worker.start()
                try:
                    self.assertTrue(entered.wait(timeout=5), errors)
                    self.assertFalse(done.is_set(), 'teardown returned while a retained member was live')
                    terminate(job.handle, 1)
                    self.assertTrue(done.wait(timeout=5))
                finally:
                    worker.join(timeout=6)
            self.assertFalse(worker.is_alive()); self.assertEqual(errors, [])
            self.assertEqual([ms for _, ms in trace['waited']], [4000, 2000])
            self.assert_all_ceased(); self.assert_job_handles_closed(trace)
            print('native deferred termination gate: retained handle nonsignaled -> teardown pending -> '
                  'real TerminateJobObject -> signaled; shared deadline waits=4000,2000ms', flush=True)

    def test_collection_wait_and_cleanup_errors_are_visible(self):
        import signal
        from types import SimpleNamespace
        kernel = self.scope['_kernel']
        teardown = self.scope['terminate_tree']
        boundaries = ('SetInformationJobObject', 'QueryInformationJobObject', 'OpenProcess',
                      'IsProcessInJob', 'TerminateJobObject', 'WaitForSingleObject',
                      'deadline', 'interruption', 'CloseHandle')
        for boundary in boundaries:
            with self.subTest(boundary=boundary), self.trace_job_handles() as trace:
                for path in (self.leader, self.ticks, self.ticks.with_suffix('.pid')):
                    path.unlink(missing_ok=True)
                previous = {sig: signal.getsignal(sig) for sig in (signal.SIGINT, signal.SIGTERM)}
                observations, reached = [], []

                def fail_during_teardown(child, job):
                    observations.extend(self.observe_tree())
                    name = 'WaitForSingleObject' if boundary in ('deadline', 'interruption') else boundary
                    actual = getattr(kernel, name)
                    calls = 0

                    def fault(*args):
                        nonlocal calls
                        calls += 1
                        if boundary in ('OpenProcess', 'IsProcessInJob') and calls == 1:
                            return actual(*args)  # Already acquired handles must still close.
                        reached.append(boundary)
                        if boundary == 'OpenProcess':
                            raise self.ctypes.WinError(5, 'OpenProcess: injected access denied after capture')
                        if boundary == 'interruption':
                            raise KeyboardInterrupt('injected retained-wait interruption')
                        if boundary == 'deadline':
                            self.assertEqual(args[1], 0, 'expired remainder must not become INFINITE')
                            return actual(event, args[1])  # Real WAIT_TIMEOUT on a nonsignaled native event.
                        if boundary == 'CloseHandle':
                            actual(*args)  # Release the real resource, then expose a real close failure.
                            return actual(0)
                        return actual(-1 if boundary == 'QueryInformationJobObject' else 0, *args[1:])  # NULL queries the caller's job.

                    with contextlib.ExitStack() as inject:
                        if boundary == 'deadline':
                            event = self.kernel.CreateEventW(None, True, False, None)
                            self.assertTrue(event); inject.callback(lambda: self.assertTrue(self.kernel.CloseHandle(event)))
                            clock = iter((100, 106))
                            inject.enter_context(patch.dict(self.scope, time=SimpleNamespace(monotonic=lambda: next(clock))))
                        inject.enter_context(patch.object(kernel, name, fault))
                        teardown(child, job)

                expected = KeyboardInterrupt if boundary == 'interruption' else OSError
                with patch.dict(self.scope, terminate_tree=fail_during_teardown), self.assertRaises(expected) as failure:
                    self.platform['run_process'](self.command, subprocess.DEVNULL, .05)
                self.assertTrue(reached, boundary)
                self.assertIn('timed out' if boundary == 'deadline' else
                              'interruption' if boundary == 'interruption' else boundary, str(failure.exception))
                self.assertEqual({sig: signal.getsignal(sig) for sig in previous}, previous)
                if boundary not in ('SetInformationJobObject', 'QueryInformationJobObject'):
                    self.assertTrue(trace['opened'], 'failure must exercise retained-handle cleanup')
                self.assert_job_handles_closed(trace)
                # Error is already asserted. Observe last-job-handle kill safety, then fixture cleanup.
                for handle in observations:
                    self.assertEqual(self.kernel.WaitForSingleObject(handle, 5000), 0)
                self.assert_all_ceased()
                print(f'native {boundary}: visible {failure.exception}; acquired handles closed, '
                      'last-handle kill observed, signal handlers restored', flush=True)

    def test_timeout_selected_then_leader_exit(self):
        import contextlib
        import io
        events = []
        messages = io.StringIO()
        teardown = self.scope['terminate_tree']

        def after_timeout(child, job=None):
            events.append('timeout selected')
            leader, descendant = self.observe_tree()
            bootstrap = self.retain(child.pid)
            self.release.touch()
            wait_for(lambda: not self.alive(leader))
            events.append('actual leader exited')
            self.assertEqual(child.wait(timeout=5), 19)
            self.assert_ceased(bootstrap)
            self.assertTrue(self.alive(descendant))
            events.append('descendant live')
            events.append('teardown')
            teardown(child, job) if job is not None else teardown(child)
            self.assert_ceased(descendant)
            events.append('descendant ceased')
            before = self.ticks.read_bytes(); time.sleep(.15)
            self.assertEqual(self.ticks.read_bytes(), before)

        with patch.dict(self.scope, terminate_tree=after_timeout), contextlib.redirect_stderr(messages):
            result = self.platform['run_process'](self.command, subprocess.DEVNULL, 1, heartbeat=1)
        self.assertEqual(result, 124)
        self.assert_all_ceased()
        self.assertIn('codex pid=' + self.leader.read_text(encoding='utf-8'), messages.getvalue())
        self.assertIn('timeout:', messages.getvalue())
        self.assertEqual(events, ['timeout selected', 'actual leader exited', 'descendant live', 'teardown', 'descendant ceased'])
        print('native ownership: ' + ' -> '.join(events) + ' -> result=124', flush=True)

    def test_normal_exit_early_spawn_and_full_exit_code(self):
        import threading
        for code in (0, 7, 0x80000000, 0xC0000005, 0xFFFFFFFF):
            with self.subTest(code=hex(code)):
                self.release.unlink(missing_ok=True)
                for path in (self.leader, self.ticks, self.ticks.with_suffix('.pid')):
                    path.unlink(missing_ok=True)
                observations, errors = [], []

                def release_live_tree():
                    try:
                        observations.extend(self.observe_tree())
                    except BaseException as exc:
                        errors.append(exc)
                    finally:
                        self.release.touch()

                observer = threading.Thread(target=release_live_tree)
                observer.start()
                try:
                    result = self.platform['run_process']([*self.command[:-1], str(code)], subprocess.DEVNULL, 20)
                finally:
                    observer.join(timeout=10)
                self.assertFalse(observer.is_alive()); self.assertEqual(errors, [])
                self.assertEqual(result, code)
                for handle in observations:
                    self.assert_ceased(handle)
                self.assert_all_ceased()
                print(f'native normal leader exit={code} earliest-spawn descendant ceased', flush=True)

    def test_cli_exit_codes_and_transport_completion(self):
        prompt = self.work / 'prompt'; prompt.write_bytes(PAYLOAD + b'\x00\xff')
        target = 'import ctypes,sys; sys.stdout.buffer.write(sys.stdin.buffer.read()); sys.stdout.buffer.flush(); exit=ctypes.windll.kernel32.ExitProcess; exit.argtypes=[ctypes.c_uint]; exit.restype=None; exit(int(sys.argv[-1]))'
        fixture = self.work / 'codex-fixture'; fixture.mkdir()
        (fixture / 'package.json').write_text(json.dumps({'name': 'codex-fixture', 'version': '1.0.0', 'bin': {'codex': 'cli.js'}}), encoding='utf-8')
        (fixture / 'cli.js').write_text('''#!/usr/bin/env node
const a = process.argv.slice(2);
if (a.includes('features')) {
  for (const f of ['apps', 'plugins', 'remote_plugin', 'computer_use', 'browser_use', 'browser_use_external', 'in_app_browser'])
    console.log(f + ' stable ' + !a.some((v, i) => v === '--disable' && a[i + 1] === f));
  process.exit(0);
}
if (a.includes('mcp')) { console.log('[]'); process.exit(0); }
const r = require('child_process').spawnSync(process.env.DEVLYN_TEST_PYTHON,
  ['-c', process.env.DEVLYN_TEST_TARGET, process.env.DEVLYN_TEST_EXIT_CODE], {stdio:'inherit'});
if (r.error) throw r.error;
process.exit(r.status);
''', encoding='utf-8')
        prefix = self.work / 'native-bin'
        npm(['install', '--global', '--prefix', str(prefix), '--offline', '--ignore-scripts',
             '--no-audit', '--no-fund', str(fixture)], self.work)
        binary = str(prefix / 'codex.cmd')
        for code in (0x80000000, 0xC0000005, 0xFFFFFFFF):
            for route in ('monitored-dispatch', 'monitored-bash'):
                with self.subTest(code=hex(code), route=route):
                    carrier = prompt.with_name(prompt.name + '.transport.json')
                    carrier.unlink(missing_ok=True)
                    env = environment()
                    env.update(HOME=str(self.work), USERPROFILE=str(self.work), DEVLYN_TEST_PYTHON=sys.executable,
                               DEVLYN_TEST_TARGET=target, DEVLYN_TEST_EXIT_CODE=str(code))
                    # Native dispatcher used by codex-monitored.sh; preserve real Python CLI finalization.
                    env['DEVLYN_CODEX_PROMPT_FILE'] = str(prompt)
                    command = [sys.executable, self.shared / 'invocation-receipt.py', 'dispatch', '--binary', binary,
                               '--timeout', '10', '--heartbeat', '0', '--', '-']
                    if route == 'monitored-bash':
                        bash = shutil.which('bash')
                        self.assertIsNotNone(bash, 'Git Bash is required for the monitored boundary')
                        # MSYS encodes native statuses into its shell status. Compare the real
                        # direct exec boundary; the native dispatcher/carrier must still retain DWORD.
                        reference = run([bash, '-c', 'exec "$@"', 'fixture', sys.executable, '-c',
                                         target, str(code)], code=None)
                        env.update(CODEX_BIN=binary, CODEX_MONITORED_TIMEOUT_SEC='10',
                                   CODEX_MONITORED_HEARTBEAT='1')
                        with (self.work / 'stdout').open('wb') as out, (self.work / 'stderr').open('wb') as err:
                            result = subprocess.run([bash, str(self.shared / 'codex-monitored.sh'), '-'],
                                                    cwd=self.work, env=env, stdin=subprocess.DEVNULL,
                                                    stdout=out, stderr=err, timeout=20)
                        self.assertEqual(result.returncode, reference.returncode, (self.work / 'stderr').read_bytes())
                        self.assertEqual((self.work / 'stdout').read_bytes(), prompt.read_bytes())
                    else:
                        result = run(command, cwd=self.work, env=env, code=code)
                        self.assertEqual(result.stdout, prompt.read_bytes())
                    record = json.loads(carrier.read_text(encoding='utf-8'))
                    self.assertEqual(record['exit_code'], code)
                    self.assertEqual(record['status'], 'completed')
                    self.assertEqual(record['argv'][0], self.platform['native_argv']([binary])[0])
                    self.assert_all_ceased()
                    print(f'native {route} target/transport exit={code} observed CLI exit={result.returncode} exact stdin', flush=True)

    def test_cached_exit_code_still_requires_native_cessation(self):
        for exits in (True, False):
            with self.subTest(exits=exits):
                release = self.work / ('cached-release-' + str(exits))
                child = subprocess.Popen([sys.executable, '-c',
                                          'import pathlib,sys,time\nwhile not pathlib.Path(sys.argv[1]).exists(): time.sleep(.01)',
                                          str(release)])
                self.assertTrue(self.alive(self.retain(child.pid)))
                # Model kill()'s observed cached-code state with a real unsignaled process.
                child.returncode = 2
                job = self.scope['_WindowsJob']()
                job.child = child
                if exits:
                    release.touch()
                    job.terminate()
                    self.assert_ceased(self.retain(child.pid))
                else:
                    with self.assertRaises(subprocess.TimeoutExpired):
                        job.terminate()
                self.assertTrue(child._handle.closed)

    def test_admission_and_launch_errors_do_not_dispatch(self):
        kernel = self.scope['_kernel']
        for boundary in ('setup', 'enrollment', 'bootstrap launch', 'target launch'):
            with self.subTest(boundary=boundary):
                if boundary == 'setup':
                    actual = kernel.SetInformationJobObject
                    injection = patch.object(kernel, 'SetInformationJobObject',
                                             lambda job, kind, info, size: actual(job, -1, info, size))
                elif boundary == 'enrollment':
                    actual = kernel.DuplicateHandle
                    injection = patch.object(kernel, 'DuplicateHandle',
                                             lambda source, job, target, out, access, inherit, options:
                                             actual(source, job, target, out, 4, inherit, 0))  # QUERY, without ASSIGN_PROCESS.
                elif boundary == 'bootstrap launch':
                    injection = patch.object(sys, 'executable', str(self.work / 'missing-python.exe'))
                else:
                    injection = patch.dict(self.scope)  # Real target CreateProcess failure after enrollment.
                command = [str(self.work / 'missing-target.exe')] if boundary == 'target launch' else self.command
                with injection, self.assertRaises(OSError) as failure:
                    self.platform['run_process'](command, subprocess.DEVNULL, 1)
                self.assertTrue(str(failure.exception))
                self.assertFalse(self.leader.exists()); self.assertFalse(self.ticks.exists())
                self.assert_all_ceased()
                print(f'native {boundary}: visible error={failure.exception}; no target dispatch', flush=True)

    def test_target_cannot_break_away(self):
        target = r'''
import subprocess, sys
try:
    escaped = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(30)'],
                               creationflags=subprocess.CREATE_BREAKAWAY_FROM_JOB)
except OSError as exc:
    assert exc.winerror == 5, exc
else:
    escaped.kill(); escaped.wait()
    raise AssertionError('target escaped the owned job')
'''
        self.assertEqual(self.platform['run_process']([sys.executable, '-c', target], subprocess.DEVNULL, 10), 0)
        self.assert_all_ceased()
        print('native target CREATE_BREAKAWAY_FROM_JOB refused with access denied', flush=True)

    def test_error_after_native_launch_before_authorization(self):
        actual = subprocess.Popen
        owner = self
        for failure in (OSError('fixture after native launch'), KeyboardInterrupt('fixture launch interruption')):
            class InterruptedLaunch(actual):
                def __init__(self, *args, **kwargs):
                    super().__init__(*args, **kwargs)
                    owner.retain(self.pid)
                    raise failure

            with patch.object(subprocess, 'Popen', InterruptedLaunch), self.assertRaises(type(failure)):
                self.platform['run_process'](self.command, subprocess.DEVNULL, 1)
            self.assertFalse(self.leader.exists()); self.assertFalse(self.ticks.exists())
            for handle in self.handles.values():
                self.assert_ceased(handle)
        print('native post-CreateProcess error/interruption: bootstrap reaped, authorization withheld', flush=True)

    def test_signal_before_popen_records_native_handle(self):
        import signal
        reached = []
        class InterruptedCreation(subprocess.Popen):
            def _close_pipe_fds(self, *args):
                super()._close_pipe_fds(*args)
                # CPython calls this after CreateProcess, before assigning _handle/pid.
                reached.append(True)
                signal.raise_signal(signal.SIGINT)

        with patch.object(subprocess, 'Popen', InterruptedCreation), self.assertRaises(SystemExit) as failure:
            self.platform['run_process'](self.command, subprocess.DEVNULL, 1)
        self.assertEqual(reached, [True]); self.assertEqual(failure.exception.code, 130)
        self.assertFalse(self.leader.exists()); self.assertFalse(self.ticks.exists())
        self.assert_all_ceased()
        print('native signal before Popen handle assignment: exit=130, bootstrap reaped, no target dispatch', flush=True)

    def test_error_after_target_launch_before_owner_return(self):
        read = self.scope['_read_control']
        observations = []

        def fail_after_target(fd, count):
            result = read(fd, count)
            if count == 4:
                observations.extend(self.observe_tree())
                raise OSError('fixture after target creation before owner return')
            return result

        with patch.dict(self.scope, _read_control=fail_after_target), self.assertRaisesRegex(OSError, 'fixture after target'):
            self.platform['run_process'](self.command, subprocess.DEVNULL, 1)
        for handle in observations:
            self.assert_ceased(handle)
        self.assert_all_ceased()
        print('native target-launch error: owned leader and descendant ceased', flush=True)

    def test_teardown_error_is_visible_and_last_handle_kills(self):
        kernel = self.scope['_kernel']
        actual = kernel.TerminateJobObject
        observations = []

        def deny_teardown(job, code):
            # The runner has reaped its bootstrap; the target still awaits our barrier.
            observations.extend(self.observe_tree())
            return actual(0, code)  # Real ERROR_INVALID_HANDLE, not a simulated success.

        with patch.object(kernel, 'TerminateJobObject', deny_teardown), self.assertRaisesRegex(OSError, 'TerminateJobObject'):
            self.platform['run_process'](self.command, subprocess.DEVNULL, 1)
        for handle in observations:
            wait_for(lambda: not self.alive(handle))
            self.assert_ceased(handle)
        self.assert_all_ceased()
        print('native teardown error propagated; final job-handle release ceased descendants', flush=True)


class EngineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bash = shutil.which('bash')
        if cls.bash is None:
            raise RuntimeError('Bash unavailable on PATH')
        cls.temp = tempfile.TemporaryDirectory(prefix='devlyn-engines-')
        cls.root = Path(cls.temp.name).resolve()
        cls.prefix = cls.root / 'native 설치'
        engine_source = r"""#!/usr/bin/env node
const fs = require('fs');
const a = process.argv.slice(2);
if (process.env.DEVLYN_TEST_CALLS) fs.appendFileSync(process.env.DEVLYN_TEST_CALLS, JSON.stringify(a) + '\n');
const features = ['apps', 'plugins', 'remote_plugin', 'computer_use', 'browser_use', 'browser_use_external', 'in_app_browser'];
const config = {};
for (let i = 0; i < a.length; i++) {
  if (a[i] === '--') break;
  if (a[i] === '-c') {
    const value = a[++i], split = value.indexOf('=');
    if (value.startsWith('mcp_servers."')) throw new Error('invalid transport');
    config[value.slice(0, split)] = value.slice(split + 1);
  }
}
if (a[0] === 'features' && a[1] === 'list') {
  for (const f of features) console.log(f + ' under development ' + !a.some((v, i) => v === '--disable' && a[i + 1] === f));
  process.exit(0);
}
if (a.includes('mcp')) {
  console.log(JSON.stringify([{name:'node_repl',enabled:config['mcp_servers.node_repl.enabled'] !== 'false'},
                             {name:'pyx-memory',enabled:true}]));
  process.exit(0);
}
if (a.includes('plugin')) {
  console.log(JSON.stringify([{id:'codex@fixture', scope:'synced', enabled:!a.includes('--settings')}]));
  process.exit(0);
}
if (a.includes('--settings')) {
  const p = a[a.indexOf('--settings') + 1];
  fs.writeFileSync(process.env.DEVLYN_TEST_SEEN, JSON.stringify({argv:a, settings:JSON.parse(fs.readFileSync(p)),
    mode:fs.statSync(p).mode & 0o777, env:process.env.ENABLE_CLAUDEAI_MCP_SERVERS}));
  process.exit(0);
}
if (process.env.DEVLYN_TEST_REPLACE_PROMPT) fs.writeFileSync(process.env.DEVLYN_TEST_REPLACE_PROMPT, 'changed after dispatch');
if (process.env.DEVLYN_TEST_LEAF) {
  const cp = require('child_process');
  fs.writeFileSync(process.env.DEVLYN_TEST_NODE_PID, String(process.pid));
  cp.spawn(process.env.DEVLYN_TEST_PYTHON, [process.env.DEVLYN_TEST_LEAF, process.env.DEVLYN_TEST_TICKS], {stdio:'inherit'});
  setTimeout(() => process.exit(0), 30000);
} else {
 const chunks = [];
 process.stdin.on('data', data => chunks.push(data));
 process.stdin.on('end', () => {
  const data = Buffer.concat(chunks);
  fs.writeFileSync(process.env.DEVLYN_TEST_SEEN, JSON.stringify({argv:a, stdin:data.toString('hex')}));
  console.log(JSON.stringify({type:'fixture'}));
 });
}
"""
        folder = cls.root / 'codex'; folder.mkdir()
        (folder / 'package.json').write_text(json.dumps({'name': '@openai/codex', 'version':'1.2.3', 'bin':{'codex':'cli.js', 'claude':'cli.js'}}), encoding='utf-8')
        (folder / 'cli.js').write_text(engine_source, encoding='utf-8'); (folder / 'cli.js').chmod(0o755)
        npm(['install', '--global', '--prefix', str(cls.prefix), '--offline', '--ignore-scripts',
             '--no-audit', '--no-fund', str(folder)], cls.root)
        cls.bins = cls.prefix if os.name == 'nt' else cls.prefix / 'bin'

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def setUp(self):
        self.work = Path(tempfile.mkdtemp(dir=self.root, prefix='work-')).resolve()
        self.shared = (PACKAGE_ROOT or ROOT) / 'config/skills/_shared'
        self.env = environment(); self.env['PATH'] = str(self.bins) + os.pathsep + self.env['PATH']
        self.env.update(CODEX_BIN=str(self.bins / ('codex.cmd' if os.name == 'nt' else 'codex')),
                        HOME=str(self.work), USERPROFILE=str(self.work),
                        CODEX_MONITORED_HEARTBEAT='1', CODEX_MONITORED_TIMEOUT_SEC='10',
                        DEVLYN_TEST_SEEN=str(self.work / 'seen.json'))

    def seen(self):
        return json.loads((self.work / 'seen.json').read_text(encoding='utf-8'))

    def monitor(self, args, stdout=None, code=0):
        stdout = stdout or self.work / 'stdout'
        stderr = self.work / 'stderr'
        with stdout.open('wb') as out, stderr.open('wb') as err:
            result = subprocess.run([self.bash, str(self.shared / 'codex-monitored.sh'), *map(str, args)],
                                    cwd=self.work, env=self.env, stdin=subprocess.DEVNULL,
                                    stdout=out, stderr=err, timeout=20)
        if code is not None:
            self.assertEqual(result.returncode, code, stderr.read_bytes())
        return result.returncode

    def worker(self):
        # A multiline prompt goes as exact file bytes on stdin, with the sole prompt argument `-`.
        prompt = self.work / 'prompt.md'; prompt.write_bytes(PAYLOAD)
        self.env['DEVLYN_CODEX_PROMPT_FILE'] = str(prompt)
        return prompt, ['-C', str(self.work), '-s', 'workspace-write', '-m', 'fixture-model', '--json']

    def guarded(self, args):
        return ['exec', *[part for f in ('apps', 'plugins', 'remote_plugin', 'computer_use', 'browser_use',
                                        'browser_use_external', 'in_app_browser') for part in ('--disable', f)],
                '-c', 'mcp_servers.node_repl.enabled=false', *args]

    def test_claude_native_launch_settings(self):
        helper = runpy.run_path(str(self.shared / 'unattended-tools.py'))
        with patch.dict(os.environ, self.env, clear=True):
            with helper['claude_launch']([str(self.bins / ('claude.cmd' if os.name == 'nt' else 'claude')), '-p', 'hello'], self.work) as (argv, env):
                subprocess.run(helper['PLATFORM']['native_argv'](argv, cwd=self.work), cwd=self.work, env=env, check=True)
                seen = self.seen()
                self.assertEqual(seen['settings'], {'syncClaudeAiPlugins': False, 'disableClaudeAiConnectors': True,
                                                   'env': {'ENABLE_CLAUDEAI_MCP_SERVERS': 'false'},
                                                   'enabledPlugins': {'codex@fixture': False}})
                self.assertIn('--no-chrome', seen['argv'])
                self.assertEqual(seen['env'], 'false')
                if os.name != 'nt':
                    self.assertEqual(seen['mode'], 0o600)

    def test_file_transport_delivers_exact_bytes_once(self):
        self.assertGreaterEqual(len(PAYLOAD), 64 * 1024)
        prompt, args = self.worker()
        self.monitor([*args, '-'])
        self.assertEqual(bytes.fromhex(self.seen()['stdin']), PAYLOAD)
        self.assertEqual(self.seen()['argv'], self.guarded([*args, '-']))
        record = json.loads(prompt.with_name(prompt.name + '.transport.json').read_text(encoding='utf-8'))
        self.assertEqual((record['status'], record['exit_code'], record['command'][1:]), ('completed', 0, self.guarded([*args, '-'])))
        if os.name != 'nt':
            expected = ['/usr/bin/env', 'node', self.env['CODEX_BIN'], *record['command'][1:]] if sys.platform == 'darwin' else record['command']
            self.assertEqual(record['argv'], expected)
        self.assertEqual(record['prompt']['sha256'], hashlib.sha256(PAYLOAD).hexdigest())
        self.assertNotEqual(self.monitor([*args, '-'], code=None), 0)  # A sealed prompt file is delivered once.
        self.env.pop('DEVLYN_CODEX_PROMPT_FILE')
        self.monitor([*args, SHORT_PAYLOAD.decode().rstrip('\n')])
        self.assertEqual(bytes.fromhex(self.seen()['stdin']), b'')

    def test_rejects_competing_and_missing_before_launch(self):
        prompt, args = self.worker()
        carrier = prompt.with_name(prompt.name + '.transport.json')
        calls = self.work / 'calls.jsonl'
        self.env['DEVLYN_TEST_CALLS'] = str(calls)
        for arguments in ([*args, '-', 'competing'], [*args, '-', '-'], [*args, SHORT_PAYLOAD.decode()], [*args, '--unknown', '-']):
            self.assertNotEqual(self.monitor(arguments, code=None), 0)
            self.assertFalse((self.work / 'seen.json').exists()); self.assertFalse(carrier.exists())
            self.assertFalse(calls.exists())
        for source in ('', self.work / '없는 파일', self.work):
            self.env['DEVLYN_CODEX_PROMPT_FILE'] = str(source)
            self.assertNotEqual(self.monitor([*args, '-'], code=None), 0)
            if source:
                self.assertIn(f'DEVLYN_CODEX_PROMPT_FILE is not a readable prompt file: {source}'.encode('utf-8'),
                              (self.work / 'stderr').read_bytes())
            self.assertFalse((self.work / 'seen.json').exists())
            self.assertFalse(calls.exists())

    def test_snapshot_delivers_bytes_even_if_source_changes_after_dispatch(self):
        prompt, args = self.worker()
        self.env['DEVLYN_TEST_REPLACE_PROMPT'] = str(prompt)
        self.monitor([*args, '-'])
        self.assertEqual(bytes.fromhex(self.seen()['stdin']), PAYLOAD)
        self.assertEqual(prompt.read_bytes(), b'changed after dispatch')
        record = json.loads(prompt.with_name(prompt.name + '.transport.json').read_text(encoding='utf-8'))
        self.assertEqual(record['prompt']['sha256'], hashlib.sha256(PAYLOAD).hexdigest())

    def test_native_shim_literal_argv(self):
        argv = ['', '한국어 space', '"quotes"', "'single'", 'a&b|c>sentinel', '%PATH%', '$(touch sentinel)', '^', 'line\nline']
        dispatch = [sys.executable, self.shared / 'invocation-receipt.py', 'dispatch', '--timeout', '10', '--heartbeat', '0']
        for _ in range(2):
            run([*dispatch, '--binary', 'codex', '--', *argv], cwd=self.work, env=self.env)
            self.assertEqual(self.seen()['argv'], self.guarded(argv)); self.assertEqual(bytes.fromhex(self.seen()['stdin']), b'')
        self.assertFalse((self.work / 'sentinel').exists())
        if os.name == 'nt':
            bad = self.work / 'unknown.cmd'; bad.write_text('@echo unsafe\n', encoding='utf-8')
            error = run([*dispatch, '--binary', bad, '--'], code=2)
            self.assertIn(b'unsupported native command shim', error.stderr)
            shim = self.bins / 'codex.cmd'; raw = shim.read_bytes()
            try:
                shim.write_bytes(b'@echo malformed\r\n')
                error = run([*dispatch, '--binary', 'codex', '--'], env=self.env, code=2)
                self.assertIn(b'unsupported native command shim', error.stderr)
            finally:
                shim.write_bytes(raw)
        else:
            print('SKIP Windows .cmd resolution/tamper branch; real POSIX npm argv exercised', flush=True)

    def test_git_bash_timeout_stops_native_node_and_python(self):
        leaf = self.work / 'leaf.py'
        leaf.write_text("import pathlib,sys,time,os\np=pathlib.Path(sys.argv[1]); p.with_suffix('.pid').write_text(str(os.getpid()),encoding='utf-8')\nwhile True:\n p.write_bytes(str(time.monotonic_ns()).encode()); time.sleep(.03)\n", encoding='utf-8')
        ticks = self.work / 'ticks'; node_pid = self.work / 'node.pid'
        self.env.update(DEVLYN_TEST_LEAF=str(leaf), DEVLYN_TEST_PYTHON=sys.executable, DEVLYN_TEST_TICKS=str(ticks),
                        DEVLYN_TEST_NODE_PID=str(node_pid), CODEX_MONITORED_TIMEOUT_SEC='1')
        self.monitor(['-C', str(self.work), '-s', 'read-only', 'timeout fixture'], code=124)
        self.assertTrue(ticks.exists()); self.assertTrue(node_pid.exists())
        before = ticks.read_bytes(); time.sleep(.2); self.assertEqual(ticks.read_bytes(), before)
        for path in (node_pid, ticks.with_suffix('.pid')):
            wait_for(lambda: not process_running(int(path.read_text(encoding='utf-8'))))
        print('monitored native Node/Python pids=' + node_pid.read_text(encoding='utf-8') + '/' + ticks.with_suffix('.pid').read_text(encoding='utf-8'), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--package-root', type=Path)
    args, tests = parser.parse_known_args()
    if args.package_root:
        PACKAGE_ROOT = args.package_root.resolve(strict=True)
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(encoding='utf-8', errors='strict')
    print(json.dumps({'platform': sys.platform, 'utf8_mode': sys.flags.utf8_mode,
                      'locale': locale.getencoding(), 'package_root': str(PACKAGE_ROOT or ROOT)}), flush=True)
    unittest.main(argv=[sys.argv[0], *tests], verbosity=2)
