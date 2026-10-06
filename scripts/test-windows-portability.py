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
import runpy
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
PACKAGE_ROOT = None
SHORT_PAYLOAD = '한국어 프롬프트 — “정확 바이트” …\r\n마지막\n\n'.encode('utf-8')
PAYLOAD = SHORT_PAYLOAD * 1024
CURRENT_DEFAULTS = b'Without a pin, you are the executor.'


def environment():
    env = {k: v for k, v in os.environ.items() if not k.startswith(('DEVLYN_', 'CODEX_MONITORED_', 'GIT_'))
           and k not in ('CODEX_BLOCKED', 'CODEX_BIN', 'CODEX_REAL_BIN', 'PYTHONUTF8', 'PYTHONIOENCODING')}
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
    return run([*command, *args, '--cache', str(temp / 'npm-cache')], timeout=90)


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
            packed = npm(['pack', str(ROOT), '--ignore-scripts', '--json', '--pack-destination', str(cls.root)], cls.root)
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
        return run(['node', '--require', self.preload, self.invoker,
                    (package or self.package) / 'bin/devlyn.js', body], cwd=self.project, env=self.env, code=code)

    def cli(self, *args, code=0):
        return run(['node', '--require', self.preload, self.package / 'bin/devlyn.js', *args],
                   cwd=self.project, env=self.env, code=code)

    def interact(self, prompts, options='{}', code=0):
        # A terminal that types one list of keys into each prompt as it opens.
        return self.invoke(f"""
const stdin = Object.assign(new (require('events'))(), {{ isTTY: true, setRawMode() {{}}, resume() {{}}, pause() {{}}, setEncoding() {{}} }});
Object.defineProperty(process, 'stdin', {{ value: stdin }});
const prompts = {json.dumps(prompts)};
stdin.on('newListener', (event) => {{
  if (event === 'data') setImmediate(() => prompts.shift().forEach((key) => stdin.emit('data', key)));
}});
init({options});
""", code=code)

    def roots(self):
        return [self.project / '.agents/skills', self.project / '.claude/skills',
                self.home / '.agents/skills', self.home / '.codex/skills', self.home / '.claude/skills']

    def markers(self, base):
        return {p.parent.parent.name for p in base.glob('.*/skills/.devlyn-install.json')}

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
                    self.assertEqual(command.read_bytes(), b'my command\r\n')
        settings = json.loads((self.project / '.claude/settings.json').read_bytes())
        self.assertEqual(settings['env']['ENABLE_PROMPT_CACHING_1H'], 'true')

    def test_project_install_refuses_the_home_folder(self):
        # There CLAUDE.md, AGENTS.md and .claude/settings.json would apply to every project.
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
                    self.assertIn(b'This project is your home folder, so its CLAUDE.md, AGENTS.md', result.stderr)
                    self.assertNotIn(b'    at ', result.stderr)
                    self.assertEqual(list(self.project.iterdir()), [])

    def test_claude_project_settings_merge_and_reinstall(self):
        # A new install sets only what the drain host needs — one-hour foreground Bash calls and
        # one-hour prompt caching — and keeps every other key as it was.
        dest = self.project / '.claude/settings.json'; dest.parent.mkdir()
        for value in (None, {'custom': {'keep': [1, 2]}},
                      {'custom': True, 'env': {'TEAM_VAR': 'keep', 'ENABLE_PROMPT_CACHING_1H': 'false',
                                               'BASH_MAX_TIMEOUT_MS': '7200000'}}):
            with self.subTest(value=value):
                dest.unlink(missing_ok=True)
                if value is not None:
                    dest.write_text(json.dumps(value), encoding='utf-8')
                result = self.invoke('installClaudeCore();')
                settings = json.loads(dest.read_bytes())
                self.assertEqual(settings, {**(value or {}), 'env': {'ENABLE_PROMPT_CACHING_1H': 'true', 'BASH_MAX_TIMEOUT_MS': '3600000',
                                                                     **(value or {}).get('env', {})}})
                self.assertNotIn(b'Retired devlyn settings', result.stdout)
                first = dest.read_bytes()
                self.invoke('installClaudeCore();')
                self.assertEqual(dest.read_bytes(), first)
        self.assertFalse((self.home / '.claude').exists())

    def test_claude_install_ships_no_unreferenced_commit_conventions(self):
        # The managed block no longer points to commit conventions, so a new install adds none;
        # a copy an earlier release installed is the user's now and stays as it is.
        self.invoke('installClaudeCore();')
        conventions = self.project / '.claude/commit-conventions.md'
        self.assertFalse(conventions.exists())
        conventions.write_bytes(b'team conventions\n')
        self.invoke('installClaudeCore();')
        self.assertEqual(conventions.read_bytes(), b'team conventions\n')

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
        project_files = {'AGENTS.md', '.agents', '.gitignore'}
        cases = [(['-y'], project_files, set()), ([], project_files, set()), (['--yes'], project_files, set()),
                 (['-y', '--claude'], project_files | {'CLAUDE.md', '.claude'}, set()),
                 (['-y', '--global'], set(), {'.agents', '.codex'}),
                 (['init', '-y', '--global', '--claude'], set(), {'.agents', '.codex', '.claude'})]
        for index, (args, files, home) in enumerate(cases):
            with self.subTest(args=args):
                self.project = self.case / f'project-{index}'; self.project.mkdir()
                self.home = self.case / f'home-{index}'; self.home.mkdir()
                self.env['DEVLYN_TEST_HOME'] = str(self.home)
                result = self.cli(*args)
                if '--claude' not in args:
                    where = '~/.claude/skills' if '--global' in args else 'CLAUDE.md + .claude/'
                    self.assertIn(f'{where} for Claude Code: add --claude'.encode(), result.stdout)
                self.assertEqual({p.name for p in self.project.iterdir()}, files)
                self.assertEqual(self.markers(self.project), files & {'.agents', '.claude'})
                self.assertEqual({p.name for p in self.home.iterdir()}, home)
                self.assertEqual(self.markers(self.home), home)
                if files:
                    ignored = (self.project / '.gitignore').read_text(encoding='utf-8').splitlines()
                    self.assertEqual(ignored[1:], ['.devlyn/', '.agents/skills/.devlyn-install.json']
                                     + ['.claude/skills/.devlyn-install.json'] * ('CLAUDE.md' in files))
        self.cli('-y', '--bogus', code=1)
        self.cli('agents-all', code=1)

    def test_yes_keeps_claude_where_this_project_has_it(self):
        colon = '' if os.name == 'nt' else ':'
        body = 'Project-specific instructions outside this managed block take precedence over these defaults.\n\n# Old\n'
        block = (f'<!-- devlyn:instructions:begin sha256={hashlib.sha256(body.encode()).hexdigest()} -->\n'
                 f'{body}<!-- devlyn:instructions:end -->\n').encode()
        version = json.loads((self.package / 'package.json').read_bytes())['version']
        legacy = (Path(__file__).resolve().parent / 'fixtures/instructions/legacy-claude.md').read_bytes()
        # A team may commit CLAUDE.md and ignore .claude/: a fresh clone has only the block, or
        # the template a release before managed blocks copied in whole.
        stale = {'4.x': {'.claude/skills/devlyn-resolve/stale': block}, '3.x': {f'.claude/skills/devlyn{colon}resolve/SKILL.md': block},
                 '0.x': {'.claude/commands/devlyn.resolve.md': block}, 'clone': {'CLAUDE.md': block},
                 'template-clone': {'CLAUDE.md': legacy}, 'none': {'.claude/skills/my-skill/SKILL.md': block},
                 # 4.0.1 put optional skills into .claude/skills without the Claude target.
                 'addons': {f'.claude/skills/{name}/SKILL.md': block for name in
                            ['devlyn-reap', 'devlyn-pencil-pull', *(f'devlyn{c}reap' for c in ('\uf03a', colon))]}}
        for case, planted in stale.items():
            with self.subTest(case=case):
                self.project = self.case / f'project-{case}'
                for path, data in planted.items():
                    (self.project / path).parent.mkdir(parents=True, exist_ok=True); (self.project / path).write_bytes(data)
                if case == '4.x':
                    (self.project / '.claude/skills/.devlyn-install.json').write_text('{"version": "4.0.1"}', encoding='utf-8')
                self.cli('-y')
                claude = case not in ('none', 'addons')
                self.assertEqual(self.markers(self.project), {'.agents', '.claude'} if claude else {'.agents'})
                self.assertEqual((self.project / 'CLAUDE.md').exists(), claude)
                self.assertTrue((self.project / 'AGENTS.md').is_file())
                # Removed or refreshed by the Claude update; a user's own skill stays as it was.
                for path, data in planted.items():
                    self.assertEqual((self.project / path).exists() and (self.project / path).read_bytes() == data, not claude)
                if claude:
                    marker = json.loads((self.project / '.claude/skills/.devlyn-install.json').read_bytes())
                    self.assertEqual(marker['version'], version)
                    self.assertTrue((self.project / '.claude/skills/devlyn-ideate/SKILL.md').is_file())
                    self.assertFalse((self.project / '.claude/skills/devlyn-resolve').exists())
        if os.name != 'nt':
            # A CLAUDE.md linked to AGENTS.md is AGENTS.md's; the Claude target refuses links.
            self.project = self.case / 'linked'; self.project.mkdir()
            (self.project / 'AGENTS.md').write_bytes(block); (self.project / 'CLAUDE.md').symlink_to('AGENTS.md')
            self.cli('-y')
            self.assertEqual(self.markers(self.project), {'.agents'})
            self.assertTrue((self.project / 'CLAUDE.md').is_symlink())
            # An AGENTS.md linked to CLAUDE.md gets its block there when the Claude target runs too.
            self.project = self.case / 'agents-linked'; (self.project / '.claude/skills').mkdir(parents=True)
            (self.project / '.claude/skills/.devlyn-install.json').write_text('{"version": "4.0.1"}', encoding='utf-8')
            (self.project / 'CLAUDE.md').write_bytes(block); (self.project / 'AGENTS.md').symlink_to('CLAUDE.md')
            self.cli('-y')
            self.assertEqual(self.markers(self.project), {'.agents', '.claude'})
            self.assertEqual(json.loads((self.project / '.claude/skills/.devlyn-install.json').read_bytes())['version'], version)
            self.assertEqual(os.readlink(self.project / 'AGENTS.md'), 'CLAUDE.md')
            self.assertIn(CURRENT_DEFAULTS, (self.project / 'CLAUDE.md').read_bytes())
            # Without the Claude target the user is told to add it.
            result = self.invoke('installAgentsProject();', code=None)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn(b'--claude', result.stdout + result.stderr)
            # Linked elsewhere, even to another hard link of CLAUDE.md, AGENTS.md is still refused.
            for name in ('shared.md', 'hardlink.md'):
                shared = self.case / name
                os.link(self.project / 'CLAUDE.md', shared) if name == 'hardlink.md' else shared.write_bytes(block)
                (self.project / 'AGENTS.md').unlink(); (self.project / 'AGENTS.md').symlink_to(shared)
                before = shared.read_bytes()
                self.cli('-y', code=1)
                self.assertEqual(shared.read_bytes(), before)
        # Git for Windows without symlinks checks the link out as a file holding its target.
        self.project = self.case / 'agents-placeholder'; (self.project / '.claude/skills').mkdir(parents=True)
        (self.project / '.claude/skills/.devlyn-install.json').write_text('{"version": "4.0.1"}', encoding='utf-8')
        (self.project / 'CLAUDE.md').write_bytes(block); (self.project / 'AGENTS.md').write_bytes(b'CLAUDE.md')
        self.cli('-y')
        self.assertEqual((self.project / 'AGENTS.md').read_bytes(), b'CLAUDE.md')
        self.assertIn(CURRENT_DEFAULTS, (self.project / 'CLAUDE.md').read_bytes())
        self.assertEqual(self.markers(self.project), {'.agents', '.claude'})
        self.assertEqual(self.markers(self.home), set())

    def test_interactive_what_and_where(self):
        down, enter, space = '\x1b[B', '\r', ' '
        mcp = b'Playwright MCP for browser testing'
        # Defaults on an empty project: AGENTS.md only, this project; MCP servers are Claude's.
        result = self.interact([[enter], [enter], [enter]])
        self.assertNotIn(mcp, result.stdout)
        self.assertEqual({p.name for p in self.project.iterdir()}, {'AGENTS.md', '.agents', '.gitignore'})
        self.assertEqual(self.markers(self.project), {'.agents'})
        # A project with devlyn Claude skills preselects CLAUDE.md; an optional skill goes to both roots.
        (self.project / '.claude/skills').mkdir(parents=True)
        (self.project / '.claude/skills/.devlyn-install.json').write_text('{"version": "4.0.1"}', encoding='utf-8')
        result = self.interact([[enter], [enter], [space, enter]])
        self.assertIn(mcp, result.stdout)
        self.assertEqual(self.markers(self.project), {'.agents', '.claude'})
        self.assertTrue((self.project / 'CLAUDE.md').is_file())
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
        marker.write_text('{"version": "4.0.1"}', encoding='utf-8')
        self.interact([[enter], [enter], [enter]], '{ global: true }')
        self.assertEqual(list(self.project.iterdir()), [])
        self.assertEqual(json.loads(marker.read_bytes())['version'], json.loads((self.package / 'package.json').read_bytes())['version'])

    def test_global_drift_notice_names_roots_it_does_not_install(self):
        roots = {'.agents': '4.0.1', '.codex': '3.3.1', '.claude': '4.1.0', '.grok': '4.0.0'}
        for root, version in roots.items():
            (self.home / root / 'skills/user-skill').mkdir(parents=True)
            (self.home / root / 'skills/user-skill/keep').write_bytes(b'mine')
            (self.home / root / 'skills/.devlyn-install.json').write_text(json.dumps({'version': version}), encoding='utf-8')
        before = {p: p.read_bytes() if p.is_file() else None for p in self.home.rglob('*')}

        def notices(result):
            return [line for line in result.stdout.decode('utf-8').splitlines() if 'Global devlyn' in line]

        def line(root, advice='refresh it with --global, or delete it'):
            return f"Global devlyn {roots[root]} in {Path('~', root, 'skills')} — {advice}."

        result = self.cli('-y')
        self.assertEqual(notices(result), [f'\x1b[33m{line(root)}\x1b[0m' for root in ('.agents', '.codex', '.claude')]
                         + [f"\x1b[33m{line('.grok', 'delete it')}\x1b[0m"])
        self.assertEqual({p: p.read_bytes() if p.is_file() else None for p in self.home.rglob('*')}, before)
        # --global refreshes every user root it installs, Claude's too once it has a marker there.
        result = self.cli('-y', '--global')
        self.assertEqual(notices(result), [f"\x1b[33m{line('.grok', 'delete it')}\x1b[0m"])
        version = json.loads((self.package / 'package.json').read_bytes())['version']
        for root in ('.agents', '.codex', '.claude'):
            self.assertEqual(json.loads((self.home / root / 'skills/.devlyn-install.json').read_bytes())['version'], version)
            self.assertEqual((self.home / root / 'skills/user-skill/keep').read_bytes(), b'mine')
        grok = self.home / '.grok'
        self.assertEqual({p: p.read_bytes() if p.is_file() else None for p in grok.rglob('*')},
                         {p: data for p, data in before.items() if grok in p.parents})

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
        # Everything the resolve retirement removed from the package: a copy it still shipped would return on reinstall.
        retired = ['devlyn-resolve', *(f'_shared/{name}' for name in (
            'archive_run.py', 'codex-config.md', 'collect-codex-findings.py', 'finish-gate.py', 'grok-anchor-guard.py',
            'judge-output-parser.py', 'judge-role-evidence.py', 'phase-prompt-render.py', 'process-evidence.py',
            'resolve-bootstrap.py', 'resolve-stop-hook.py', 'run-bounded.py', 'spec-verify-check.py', 'state-phase-write.py',
            'terminal-claim-check.py', 'verify-merge-findings.py', 'adapters/grok.md', 'adapters/README.md'))]
        for root in self.roots():
            for relative in retired:
                (root / relative).parent.mkdir(exist_ok=True); (root / relative).write_bytes(b'from an older release')
            (root / name / 'stale').write_bytes(b'old')
            (root / optional / 'stale').write_bytes(b'old')
            (root / 'user-skill').mkdir(); (root / 'user-skill/keep').write_bytes(b'user')
            old = 'devlyn\uf03aauto-resolve' if os.name == 'nt' else 'devlyn:auto-resolve'
            (root / old).mkdir()
        self.invoke(install)
        assert_package_bytes()
        for root in self.roots():
            self.assertFalse((root / name / 'stale').exists())
            self.assertFalse(any((root / relative).exists() for relative in retired), root)
            self.assertFalse((root / optional / 'stale').exists())
            self.assertEqual((root / 'user-skill/keep').read_bytes(), b'user')
            self.assertFalse((root / old).exists())

    def test_instruction_custom_rules_survive_all_targets_and_reinstall(self):
        custom = b'\xef\xbb\xbf# Team rules\r\nKeep our Korean labels and formatting.\r\n'
        for name in ('AGENTS.md', 'CLAUDE.md'):
            (self.project / name).write_bytes(custom)
        self.invoke("installClaudeCore(); installAgentsProject();")
        installed = {}
        for name in ('AGENTS.md', 'CLAUDE.md'):
            data = (self.project / name).read_bytes()
            self.assertTrue(data.startswith(custom))
            self.assertEqual(data.count(b'devlyn:instructions:begin'), 1)
            self.assertIn(CURRENT_DEFAULTS, data)
            self.assertIn(custom, [p.read_bytes() for p in (self.project / '.devlyn/instructions').glob(name + '*.backup')])
            installed[name] = data
        self.invoke("installClaudeCore(); installAgentsProject();")
        for name, data in installed.items():
            self.assertEqual((self.project / name).read_bytes(), data)

    def test_instruction_future_template_upgrade_preserves_outside_bytes(self):
        copy = self.case / 'next-version'; shutil.copytree(self.package, copy)
        prefix = b'\xef\xbb\xbf'
        suffix = b'\r\n# Local additions\r\nDo not remove these.\r\n'
        self.invoke("updateInstructions('AGENTS.md');")
        dest = self.project / 'AGENTS.md'
        before = prefix + dest.read_bytes().replace(b'\n', b'\r\n') + suffix
        dest.write_bytes(before)
        source = copy / 'AGENTS.md'
        source.write_bytes(source.read_bytes() + b'\nA new managed default for this regression.\n')
        self.invoke("updateInstructions('AGENTS.md');", package=copy)
        after = dest.read_bytes()
        self.assertTrue(after.startswith(prefix)); self.assertTrue(after.endswith(suffix))
        self.assertIn(b'A new managed default for this regression.', after)
        self.assertIn(before, [p.read_bytes() for p in (self.project / '.devlyn/instructions').glob('AGENTS.md*.backup')])
        self.invoke("updateInstructions('AGENTS.md');", package=copy)
        self.assertEqual(dest.read_bytes(), after)

    def test_instruction_legacy_hash_migration_preserves_prefix_suffix(self):
        copy = self.case / 'legacy-package'; shutil.copytree(self.package, copy)
        manifest_path = copy / 'bin/instruction-templates.json'
        manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
        old = '# Codex Project Instructions\n\ndevlyn-cli installs old defaults.\n한글 😀\n'
        manifest['AGENTS.md'].append({'length': len(old.encode('utf-16-le')) // 2,
                                      'sha256': hashlib.sha256(old.encode()).hexdigest()})
        manifest_path.write_text(json.dumps(manifest), encoding='utf-8')
        for eol in ('\n', '\r\n'):
            with self.subTest(eol=eol):
                prefix, suffix = '\ufeff# My project\n\n', '\n# Keep\ncustom rule\n'
                before = (prefix + old + suffix).replace('\n', eol).encode()
                dest = self.project / 'AGENTS.md'; dest.write_bytes(before)
                self.invoke("updateInstructions('AGENTS.md');", package=copy)
                after = dest.read_bytes()
                self.assertTrue(after.startswith(prefix.replace('\n', eol).encode()))
                self.assertTrue(after.endswith(suffix.replace('\n', eol).encode()))
                self.assertNotIn(b'installs old defaults', after)
                self.assertIn(CURRENT_DEFAULTS, after)
                self.invoke("updateInstructions('AGENTS.md');", package=copy)
                self.assertEqual(dest.read_bytes(), after)

    def test_instruction_legacy_preamble_edits_migrate_with_exact_body(self):
        copy = self.case / 'legacy-package'; shutil.copytree(self.package, copy)
        manifest_path = copy / 'bin/instruction-templates.json'
        manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
        header = '# Project Instructions\n\n'
        preamble = header + 'devlyn-cli installs old defaults.\n\n'
        body = '## North Star\n\nThis contract serves one goal: any capable engine, old defaults. 한글 😀\n'
        def signature(text):
            return {'length': len(text.encode('utf-16-le')) // 2,
                    'sha256': hashlib.sha256(text.encode()).hexdigest()}
        for intro in (preamble.replace('old defaults', 'another release'), preamble):
            manifest['CLAUDE.md'].append({**signature(intro + body),
                                          'preamble': intro, 'body': signature(body)})
        manifest_path.write_text(json.dumps(manifest), encoding='utf-8')
        custom = '사용자 규칙: resolve 금지. 배포는 사용자가 진행.\n\n'
        for eol in ('\n', '\r\n'):
            for intro in (header + custom, preamble + custom):
                with self.subTest(eol=eol, intro=intro):
                    prefix, suffix = '\ufeff# Team\n\n', '\n# Local tail\nKeep me.\n'
                    before = (prefix + intro + body + suffix).replace('\n', eol).encode()
                    dest = self.project / 'CLAUDE.md'; dest.write_bytes(before)
                    self.invoke('installClaudeCore();', package=copy)
                    after = dest.read_bytes()
                    kept_intro = custom if intro.startswith(preamble) else intro
                    self.assertTrue(after.startswith((prefix + kept_intro).replace('\n', eol).encode()))
                    self.assertTrue(after.endswith(suffix.replace('\n', eol).encode()))
                    self.assertNotIn(b'old defaults', after)
                    self.assertEqual(after.count(b'devlyn:instructions:begin'), 1)
                    self.assertIn(before, [p.read_bytes() for p in (self.project / '.devlyn/instructions').glob('CLAUDE.md*.backup')])
                    self.invoke('installClaudeCore();', package=copy)
                    self.assertEqual(dest.read_bytes(), after)
        for before in (header + custom + body.replace('old defaults', 'edited body'),
                       preamble + body + header + custom + body,
                       preamble.replace('old defaults.', 'old defaults. Use pnpm.') + body,
                       preamble.rstrip('\n') + '\n' + body,
                       header + custom + body + body):
            dest.write_bytes(before.encode('utf-8'))
            original = dest.read_bytes()
            self.invoke('installClaudeCore();', package=copy)
            after = dest.read_bytes()
            self.assertIn(original, [p.read_bytes() for p in (self.project / '.devlyn/instructions').glob('CLAUDE.md*.backup')])
            self.assertEqual(after.count(b'devlyn:instructions:begin'), 1)
            if custom in before:
                self.assertIn(custom.encode(), after)
            if 'Use pnpm.' in before:
                self.assertIn(b'Use pnpm.', after)
            self.invoke('installClaudeCore();', package=copy)
            self.assertEqual(dest.read_bytes(), after)

    def test_instruction_cli_conflict_guides_merge_and_retry_without_stack(self):
        for name, args in [('CLAUDE.md', ['-y', '--claude']), ('AGENTS.md', ['-y'])]:
            with self.subTest(name=name):
                dest = self.project / name
                original = (b'<!-- devlyn:instructions:begin sha256=' + b'0' * 64 + b' -->\n'
                            + (self.package / name).read_bytes() + b'<!-- broken:end -->\n')
                dest.write_bytes(original)
                argv = ['node', '--require', self.preload, self.package / 'bin/devlyn.js', *args]
                result = run(argv, cwd=self.project, env=self.env, code=1)
                self.assertIn(b'needs merge', result.stderr)
                self.assertIn(b'Original preserved', result.stderr)
                self.assertNotIn(b'    at ', result.stderr)
                self.assertNotIn(b'All done', result.stdout)
                self.assertEqual(dest.read_bytes(), original)
                recovery = self.project / '.devlyn/instructions'
                backup, = recovery.glob(name + '*.backup')
                incoming, = recovery.glob(name + '*.incoming')
                guide, = recovery.glob(name + '*.merge.md')
                self.assertEqual(backup.read_bytes(), original)
                guide_text = guide.read_text(encoding='utf-8')
                self.assertIn(str(backup), guide_text)
                self.assertIn(str(incoming), guide_text)
                self.assertIn('outside', guide_text)
                self.assertIn('npx devlyn-cli', guide_text)
                self.assertIn(str(guide).encode(), result.stderr)
                files = {p.name: p.read_bytes() for p in recovery.iterdir()}
                run(argv, cwd=self.project, env=self.env, code=1)
                self.assertEqual({p.name: p.read_bytes() for p in recovery.iterdir()}, files)
                custom = b'# Project rules\nKeep our custom contract.\n\n'
                dest.write_bytes(custom + incoming.read_bytes())
                run(argv, cwd=self.project, env=self.env)
                self.assertTrue(dest.read_bytes().startswith(custom))

    def test_instruction_conflicts_preserve_original_and_fail_visibly(self):
        self.invoke("updateInstructions('AGENTS.md');")
        dest = self.project / 'AGENTS.md'; good = dest.read_bytes()
        cases = [good.replace(b'devlyn:instructions:end', b'broken:end'), good + good,
                 b'\xffinvalid utf8']
        for before in cases:
            with self.subTest(before=before[:70]):
                dest.write_bytes(before)
                result = self.invoke("installAgentsProject();", code=None)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(dest.read_bytes(), before)
                self.assertFalse((self.project / '.agents').exists())
        self.assertTrue(list((self.project / '.devlyn/instructions').glob('AGENTS.md*.incoming')))
        claude = self.project / 'CLAUDE.md'; claude.write_bytes(good.replace(b'devlyn:instructions:end', b'broken:end'))
        before = claude.read_bytes()
        result = self.invoke('installClaudeCore();', code=None)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(claude.read_bytes(), before)
        self.assertFalse((self.project / '.claude').exists())

    def test_instruction_write_failure_keeps_original_and_exact_backup(self):
        run(['git', 'init', '-q', self.project])
        before = b'# Custom project rules\r\nKeep exact bytes.\r\n'
        dest = self.project / 'AGENTS.md'; dest.write_bytes(before)
        result = self.invoke("fs.renameSync = () => { throw new Error('injected rename failure'); }; updateInstructions('AGENTS.md');", code=None)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(b'injected rename failure', result.stderr)
        self.assertEqual(dest.read_bytes(), before)
        self.assertFalse(list(self.project.glob('AGENTS.md.*.tmp')))
        backup, = (self.project / '.devlyn/instructions').glob('AGENTS.md*.backup')
        self.assertEqual(backup.read_bytes(), before)
        run(['git', 'check-ignore', str(backup)], cwd=self.project)
        backup.write_bytes(b'different recovery data')
        result = self.invoke("updateInstructions('AGENTS.md');", code=None)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(b'Instruction recovery file differs', result.stderr)
        self.assertEqual(dest.read_bytes(), before)
        self.assertEqual(backup.read_bytes(), b'different recovery data')

    def test_instruction_source_templates_are_not_wrapped(self):
        copy = self.case / 'source-package'; shutil.copytree(self.package, copy)
        originals = {name: (copy / name).read_bytes() for name in ('AGENTS.md', 'CLAUDE.md')}
        alias = self.case / 'source-alias'
        run(['node', '-e', "require('fs').symlinkSync(process.argv[1], process.argv[2], 'junction')", copy, alias])
        run(['node', '--preserve-symlinks', '--require', self.preload, self.invoker, alias / 'bin/devlyn.js',
             "updateInstructions('AGENTS.md');"], cwd=copy, env=self.env)
        run(['node', '--require', self.preload, self.invoker, copy / 'bin/devlyn.js',
             "installClaudeCore(); installAgentsProject();"], cwd=copy, env=self.env)
        for name, data in originals.items():
            self.assertEqual((copy / name).read_bytes(), data)
        self.invoke("installClaudeCore(); installAgentsProject();", package=copy)
        self.invoke("installClaudeCore(); installAgentsProject();", package=copy)
        (copy / 'AGENTS.md').write_bytes((self.project / 'AGENTS.md').read_bytes())
        before = (self.project / 'AGENTS.md').read_bytes()
        result = self.invoke("installAgentsProject();", package=copy, code=None)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(b'Packaged instruction template contains managed markers', result.stderr)
        self.assertEqual((self.project / 'AGENTS.md').read_bytes(), before)

    @unittest.skipIf(os.name == 'nt', 'POSIX group permission bits are not supported on Windows')
    def test_instruction_preserves_permissions_despite_umask(self):
        dest = self.project / 'AGENTS.md'; dest.write_bytes(b'# Shared project rules\n')
        dest.chmod(0o664)
        self.invoke("process.umask(0o022); updateInstructions('AGENTS.md');")
        self.assertEqual(dest.stat().st_mode & 0o777, 0o664)

    def test_instruction_edited_unmarked_templates_preserve_edits_and_install(self):
        for name, command in [('AGENTS.md', "installAgentsProject();"), ('CLAUDE.md', 'installClaudeCore();')]:
            with self.subTest(name=name):
                dest = self.project / name
                before = (self.package / name).read_bytes().replace(b'This contract serves one goal:', b'Team changed this body sentence:', 1)
                dest.write_bytes(before)
                self.invoke(command)
                after = dest.read_bytes()
                custom, _ = after.split(b'<!-- devlyn:instructions:begin', 1)
                self.assertIn(b'Team changed this body sentence:', custom)
                self.assertIn(b'## North Star', custom)
                self.assertNotIn(b'## Core principles', custom)
                self.assertIn(before, [p.read_bytes() for p in (self.project / '.devlyn/instructions').glob(name + '*.backup')])
                self.invoke(command)
                self.assertEqual(dest.read_bytes(), after)

    def test_instruction_mixed_legacy_versions_update_without_stale_defaults(self):
        # Historical e2e720573 template + two later stock entry-policy paragraphs:
        # the real combination that failed whole-template signature matching.
        for name, command, fixture in [
                ('AGENTS.md', "updateInstructions('AGENTS.md');", 'mixed-legacy-agents.md'),
                ('AGENTS.md', "updateInstructions('AGENTS.md');", 'legacy-july-agents.md'),
                ('CLAUDE.md', 'installClaudeCore();', 'legacy-claude.md')]:
            original = (Path(__file__).resolve().parent / 'fixtures/instructions' / fixture).read_bytes()
            for eol in (b'\n', b'\r\n'):
                with self.subTest(name=name, fixture=fixture, eol=eol):
                    dest = self.project / name
                    user_rules = b'\xef\xbb\xbf# Local rules\n\nKeep our project workflow.\n\n'.replace(b'\n', eol)
                    before = user_rules + original.replace(b'\n', eol)
                    dest.write_bytes(before)
                    self.invoke(command)
                    after = dest.read_bytes()
                    custom, block = after.split(b'<!-- devlyn:instructions:begin', 1)
                    self.assertEqual(custom.strip(), user_rules.strip())
                    self.assertNotIn(b'engine downgraded:', block)
                    self.assertNotIn(b'Default to direct execution only for clear, local', block)
                    self.assertIn(CURRENT_DEFAULTS, block)
                    self.assertIn(before, [p.read_bytes() for p in (self.project / '.devlyn/instructions').glob(name + '*.backup')])
                    self.invoke(command)
                    self.assertEqual(dest.read_bytes(), after)

    def test_instruction_4_x_blocks_are_replaced_in_place(self):
        # 4.1.0 renamed the AGENTS.md title and intro; design-ui, the queue skill and resolve were
        # retired after it. A 4.0.1, 4.1.0 or main (9ecbe51c, d2d34e3e) block is replaced, never stacked,
        # and an edited one keeps only the edits: its stock paragraphs, the retired ones too, are
        # registered fingerprints.
        prefix, suffix = b'# Team rules\n\nUse pnpm.\n\n', b'\n# Local tail\n\nKeep me.\n'
        for name, version in (('AGENTS.md', '4.0.1'), ('AGENTS.md', '4.1.0'), ('AGENTS.md', '9ecbe51c'), ('AGENTS.md', 'd2d34e3e'),
                              ('CLAUDE.md', '4.1.0'), ('CLAUDE.md', '9ecbe51c'), ('CLAUDE.md', 'd2d34e3e')):
            dest = self.project / name
            block = (Path(__file__).resolve().parent / f'fixtures/instructions/{name[:-3].lower()}-{version}.md').read_bytes()
            for edited in (False, True):
                for eol in (b'\n', b'\r\n'):
                    with self.subTest(name=name, version=version, edited=edited, eol=eol):
                        old = block.replace(b'This contract serves one goal:', b'Team changed this body sentence:') if edited else block
                        dest.write_bytes((prefix + old + suffix).replace(b'\n', eol))
                        self.invoke(f"updateInstructions('{name}');")
                        after = dest.read_bytes()
                        custom, managed = after.split(b'<!-- devlyn:instructions:begin', 1)
                        self.assertEqual(after.count(b'devlyn:instructions:begin'), 1)
                        self.assertTrue(after.endswith(suffix.replace(b'\n', eol)))
                        self.assertIn(b'# Project Instructions' + eol, managed)
                        self.assertIn(CURRENT_DEFAULTS, managed)
                        for stale in (b'Codex CLI reads this file', b'design-ui', b'devlyn-queue', b'references/task-completion.md',
                                      b'outer-loop.md', b'queue drains retain', b'--quick', b'--from-spec', b'per item: spec it',
                                      b'devlyn-resolve', b'VERIFY', b'`/devlyn-'):
                            self.assertNotIn(stale, after)
                        if edited:
                            self.assertTrue(custom.startswith(prefix.replace(b'\n', eol)))
                            self.assertIn(b'Team changed this body sentence:', custom)
                            self.assertNotIn(b'unstructured idea', custom)
                        else:
                            self.assertEqual(custom, prefix.replace(b'\n', eol))
                        self.invoke(f"updateInstructions('{name}');")
                        self.assertEqual(dest.read_bytes(), after)

    def test_instruction_custom_content_survives_legacy_and_edited_managed_blocks(self):
        for name, command in [('AGENTS.md', "updateInstructions('AGENTS.md');"), ('CLAUDE.md', 'installClaudeCore();')]:
            for managed in (False, True):
                with self.subTest(name=name, managed=managed):
                    dest = self.project / name
                    if dest.exists():
                        dest.unlink()
                    self.invoke(command)
                    stock = dest.read_bytes() if managed else (self.package / name).read_bytes()
                    edited = '2. **No overengineering** — Team rule: keep our API stable.\n'.encode()
                    # A changed list item, nested custom section, code fence and comment
                    # must all retain their original bytes and heading ancestry.
                    text = stock.decode('utf-8')
                    old_item = next(line for line in text.splitlines(True) if line.startswith('2. **No overengineering**'))
                    addition = ('\n### 배포 규칙\n\n승인 없이 배포 금지. 😀\n\n'
                                '```md\n# Codex Project Instructions\n\ndevlyn-cli installs examples.\n'
                                '## Core principles\n\nSeven rules govern every change. Cite them by name when a decision touches one.\n```\n\n'
                                '<!-- custom\n\n## Quick Start\n\nKeep this comment.\n-->\n\n').encode()
                    before = text.replace(old_item, edited.decode()).encode().replace(b'## Quick Start\n', addition + b'## Quick Start\n', 1)
                    prefix = b'# Team rules\nUse pnpm.\n\n'
                    suffix = b'\n# Outside\n\n## Core principles\n\nSeven rules govern every change. Cite them by name when a decision touches one.\n'
                    before = (prefix + before + suffix).replace(b'\n', b'\r\n')
                    dest.write_bytes(before)
                    self.invoke(command)
                    after = dest.read_bytes()
                    self.assertTrue(after.startswith(prefix.replace(b'\n', b'\r\n')))
                    self.assertIn(suffix.replace(b'\n', b'\r\n'), after)
                    custom, _ = after.split(b'<!-- devlyn:instructions:begin', 1)
                    self.assertIn(edited.replace(b'\n', b'\r\n'), custom)
                    self.assertIn(addition.replace(b'\n', b'\r\n'), custom)
                    self.assertIn(b'## Core principles\r\n', custom)
                    self.assertNotIn(b'1. **No workaround**', custom)
                    self.assertEqual(after.count(b'devlyn:instructions:begin'), 1)
                    self.invoke(command)
                    self.assertEqual(dest.read_bytes(), after)

    def test_instruction_quoted_and_unknown_legacy_text_is_preserved(self):
        examples = [b'# Codex Project Instructions\n\n```md\ndevlyn-cli installs examples.\n\n## Core principles\n\nSeven rules govern every change. Cite them by name when a decision touches one.\n```\n',
                    b'# Devlyn Agent Instructions\nOld block\n# User addition\nKeep me\n',
                    b'# Codex Project Instructions\n\ndevlyn-cli installs edited defaults.\n',
                    b'# Codex Project Instructions\n\n<!-- devlyn-cli installs examples.\n\n## Core principles\n\nSeven rules govern every change. Cite them by name when a decision touches one.\n-->\n']
        stock = (self.package / 'AGENTS.md').read_bytes()
        examples += [b'# Team rules\n\n```markdown\n' + stock + b'```\n',
                     b'# Team rules\n\n<!--\n' + stock + b'-->\n',
                     b'# Team rules\n\n<details>\n<summary>Example</summary>\n\n' + stock + b'\n</details>\n',
                     b'# Team rules\n\n<details>\n<details>Nested</details>\n\n' + stock + b'\n</details>\n',
                     b'# Team rules\n\n<details>\n<!-- </details> -->\n\n' + stock + b'\n</details>\n',
                     b'# Team rules\n\n<!-- first --> <!-- second\n\n' + stock + b'-->\n']
        dest = self.project / 'AGENTS.md'
        for before in examples:
            with self.subTest(before=before):
                dest.write_bytes(before)
                self.invoke("updateInstructions('AGENTS.md');")
                after = dest.read_bytes()
                self.assertTrue(after.startswith(before))
                self.invoke("updateInstructions('AGENTS.md');")
                self.assertEqual(dest.read_bytes(), after)

    @unittest.skipIf(os.name == 'nt', 'symlink creation requires native Windows privileges')
    def test_instruction_symlink_is_preserved(self):
        shared = self.case / 'shared.md'; shared.write_bytes(b'shared custom rules')
        dest = self.project / 'AGENTS.md'; dest.symlink_to(shared)
        result = self.invoke("installAgentsProject();", code=None)
        self.assertNotEqual(result.returncode, 0)
        self.assertTrue(dest.is_symlink())
        self.assertEqual(shared.read_bytes(), b'shared custom rules')

    @unittest.skipIf(os.name == 'nt', 'symlink creation requires native Windows privileges')
    def test_instruction_recovery_directory_symlinks_are_preserved(self):
        for component in ('.devlyn', '.devlyn/instructions'):
            for kind in ('outside', 'inside', 'dangling'):
                for conflict in (False, True):
                    for name, command in [('AGENTS.md', "installAgentsProject();"), ('CLAUDE.md', 'installClaudeCore();')]:
                        with self.subTest(component=component, kind=kind, conflict=conflict, name=name):
                            with tempfile.TemporaryDirectory(dir=self.case) as temp:
                                base = Path(temp); project = base / 'project'; project.mkdir()
                                target = (project if kind == 'inside' else base) / 'target'
                                if kind != 'dangling':
                                    target.mkdir(); (target / 'keep').write_bytes(b'untouched target')
                                entry = project / component; entry.parent.mkdir(exist_ok=True)
                                entry.symlink_to(target, target_is_directory=True)
                                before = b'<!-- devlyn:instructions:begin broken -->\n' if conflict else b'# Custom rules\r\n'
                                dest = project / name; dest.write_bytes(before)
                                result = self.invoke(f'process.chdir({json.dumps(str(project))}); {command}', code=None)
                                self.assertNotEqual(result.returncode, 0)
                                self.assertIn(str(entry).encode('utf-8'), result.stderr)
                                self.assertIn(b'Move it aside', result.stderr)
                                self.assertEqual(dest.read_bytes(), before)
                                self.assertTrue(entry.is_symlink())
                                self.assertEqual(entry.readlink(), target)
                                if kind == 'dangling':
                                    self.assertFalse(target.exists())
                                else:
                                    self.assertEqual(list(target.iterdir()), [target / 'keep'])
                                    self.assertEqual((target / 'keep').read_bytes(), b'untouched target')
                                self.assertFalse((project / '.claude').exists())
                                self.assertFalse((project / '.agents').exists())

    def test_instruction_recovery_non_directory_and_unused_path(self):
        for component in ('.devlyn', '.devlyn/instructions'):
            with self.subTest(component=component):
                with tempfile.TemporaryDirectory(dir=self.case) as temp:
                    project = Path(temp)
                    entry = project / component; entry.parent.mkdir(exist_ok=True)
                    entry.write_bytes(b'keep obstruction')
                    dest = project / 'AGENTS.md'; dest.write_bytes(b'# Custom rules\n')
                    body = f'process.chdir({json.dumps(str(project))}); updateInstructions("AGENTS.md");'
                    result = self.invoke(body, code=None)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn(str(entry).encode('utf-8'), result.stderr)
                    self.assertEqual(dest.read_bytes(), b'# Custom rules\n')
                    self.assertEqual(entry.read_bytes(), b'keep obstruction')
                    dest.unlink()  # Fresh install and exact repeat do not use recovery.
                    self.invoke(body); installed = dest.read_bytes()
                    self.invoke(body)
                    self.assertEqual(dest.read_bytes(), installed)
                    self.assertEqual(entry.read_bytes(), b'keep obstruction')

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
        self.invoke("installClaudeCore();")
        self.assertEqual((mine / 'SKILL.md').read_text(encoding='utf-8'), '---\nname: workflow-routing\n---\nmine\n')
        # A shipped copy (here: the hash of this text, CRLF on disk, beside a .DS_Store) goes.
        shipped = b'---\nname: workflow-routing\n---\nshipped\n'
        (mine / 'SKILL.md').write_bytes(shipped.replace(b'\n', b'\r\n')); (mine / '.DS_Store').write_bytes(b'x')
        self.invoke("RETIRED_SKILL_MD_SHA256['workflow-routing'] = new Set(["
                    f"'{hashlib.sha256(shipped).hexdigest()}']); installClaudeCore();")
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
        stale.parent.mkdir(parents=True); stale.write_text('{"version": "stale"}', encoding='utf-8')
        result = self.invoke("install(['agents'], true);", package=copy, code=None)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(b'Incomplete devlyn skill install', result.stderr)
        self.assertEqual(self.markers(self.home), set())

    def test_upgrade_retires_pre_4_names_only_where_it_installs(self):
        # Before 4.0.0 each skill was `devlyn:<name>`; npm extracts ':' as U+F03A on Windows.
        spellings = ['\uf03a'] if os.name == 'nt' else [':', '\uf03a']
        core = ['ideate', 'engines']
        claude = self.project / '.claude/skills'
        agents, codex, grok = (self.home / name / 'skills' for name in ('.agents', '.codex', '.grok'))
        planted = {claude: core + ['resolve', 'pencil-pull', 'pencil-push', 'reap'], codex: core + ['resolve', 'pencil-pull'],
                   agents: core + ['resolve'], grok: ['resolve', 'reap']}
        for root, names in planted.items():
            (root / 'my-skill').mkdir(parents=True); (root / 'my-skill/keep').write_bytes(b'mine')
            for name in names:
                for colon in spellings:
                    old = root / f'devlyn{colon}{name}'; old.mkdir()
                    (old / 'SKILL.md').write_text(f'---\nname: devlyn:{name}\n---\n', encoding='utf-8')
        # 0.6.x installed the pencil skills under today's names, as today's SKILL.md minus its
        # 5-line frontmatter; an edited or newer copy under a 4.0 name is the user's own.
        legacy = (self.package / 'optional-skills/devlyn-pencil-push/SKILL.md').read_bytes().split(b'\n', 5)[5]
        (agents / 'devlyn-pencil-push').mkdir(); (agents / 'devlyn-pencil-push/SKILL.md').write_bytes(legacy)
        (codex / 'devlyn-pencil-push').mkdir(); (codex / 'devlyn-pencil-push/SKILL.md').write_bytes(b'mine\n')
        self.invoke("installClaudeCore(); install(['agents'], true);")
        for root, optional in ((claude, {'pencil-pull', 'pencil-push', 'reap'}), (codex, {'pencil-pull'}), (agents, {'pencil-push'})):
            entries = {p.name for p in root.iterdir()}
            self.assertEqual({n for n in entries if n.startswith(('devlyn:', 'devlyn\uf03a'))}, set(), root)
            mine = {'devlyn-pencil-push'} if root == codex else set()
            self.assertEqual({n for n in entries if n.startswith('devlyn-')}, {f'devlyn-{n}' for n in core} | {f'devlyn-{n}' for n in optional} | mine, root)
            for name in core + sorted(optional):
                self.assertIn(f'name: devlyn-{name}\n', (root / f'devlyn-{name}/SKILL.md').read_text(encoding='utf-8'))
            self.assertEqual((root / 'my-skill/keep').read_bytes(), b'mine')
            self.assertTrue((root / '.devlyn-install.json').is_file())
        self.assertEqual((codex / 'devlyn-pencil-push/SKILL.md').read_bytes(), b'mine\n')
        # A root this run does not install into keeps its old skills untouched.
        self.assertEqual({p.name for p in grok.iterdir()}, {'my-skill'} | {f'devlyn{c}{n}' for c in spellings for n in ('resolve', 'reap')})
        # A 4.x reinstall leaves an opted-in optional skill as the user has it, as 3.x did.
        edited = claude / 'devlyn-pencil-pull/SKILL.md'
        edited.write_text(edited.read_text(encoding='utf-8') + 'my rule\n', encoding='utf-8')
        self.invoke("installClaudeCore();")
        self.assertTrue(edited.read_text(encoding='utf-8').endswith('my rule\n'))

    def test_upgrade_removes_retired_resolve_design_ui_and_queue(self):
        # Core skills through 4.1.0, `devlyn:<name>` before 4.0.0 (npm extracts ':' as U+F03A on
        # Windows): each root an install writes loses every spelling, another root keeps them.
        spellings = ['-', '\uf03a'] if os.name == 'nt' else ['-', ':', '\uf03a']
        other = self.home / '.grok/skills'
        for root in [*self.roots(), other]:
            (root / 'my-skill').mkdir(parents=True); (root / 'my-skill/keep').write_bytes(b'mine')
            for name in (f'devlyn{c}{skill}' for c in spellings for skill in ('resolve', 'design-ui', 'queue')):
                (root / name / 'scripts').mkdir(parents=True)
                (root / name / 'SKILL.md').write_text(f'---\nname: {name}\n---\n', encoding='utf-8')
                (root / name / 'scripts/append.py').write_bytes(b'print(1)\n')
        snapshot = lambda base: {p: p.read_bytes() if p.is_file() else None for p in base.rglob('*')}
        kept = snapshot(other)
        install = lambda: (self.cli('-y', '--claude'), self.cli('-y', '--global', '--claude'))
        install()
        for root in self.roots():
            self.assertEqual({p.name for p in root.iterdir() if p.name.startswith('devlyn')},
                             {'devlyn-ideate', 'devlyn-engines'}, root)
            self.assertEqual((root / 'my-skill/keep').read_bytes(), b'mine')
            self.assertTrue((root / '.devlyn-install.json').is_file())
        self.assertEqual(snapshot(other), kept)
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
        result = self.invoke("installClaudeCore();", package=copy, code=None)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(b'Incomplete devlyn skill install', result.stderr)
        self.assertEqual((old / 'keep').read_bytes(), b'old')
        # Old names go only after the new core skills are in place.
        self.assertTrue((root / 'devlyn-ideate/SKILL.md').is_file())
        self.assertFalse((root / '.devlyn-install.json').exists())
        self.invoke("installClaudeCore();")
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
        result = self.invoke("installClaudeCore();", package=copy, code=None)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual((push / 'SKILL.md').read_bytes(), legacy)
        self.invoke("installClaudeCore();")
        self.assertIn(b'name: devlyn-pencil-push', (push / 'SKILL.md').read_bytes())
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

    def test_upgrade_from_4_1_0_and_main_retires_resolve(self):
        # A 4.1.0 or main (9ecbe51c) install: resolve as a core skill, beside leftovers under its 3.x
        # name and npm's U+F03A extraction alias; resolve-only helpers in _shared; the retired Stop
        # hook among the user's own hooks; and instruction blocks between project rules.
        spellings = ['-', '\uf03a'] if os.name == 'nt' else ['-', ':', '\uf03a']
        helpers = ['resolve-stop-hook.py', 'archive_run.py', 'spec-verify-check.py', 'run-bounded.py', 'codex-config.md']
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
        for version in ('4.1.0', '9ecbe51c'):
            with self.subTest(version=version):
                self.project = self.case / f'project-{version}'; self.project.mkdir()
                self.home = self.case / f'home-{version}'; self.home.mkdir()
                self.env['DEVLYN_TEST_HOME'] = str(self.home)
                other = self.home / '.grok/skills'
                for root in [*self.roots(), other]:
                    (root / 'my-skill').mkdir(parents=True); (root / 'my-skill/keep').write_bytes(b'mine')
                    for c in spellings:
                        (root / f'devlyn{c}resolve/references').mkdir(parents=True)
                        (root / f'devlyn{c}resolve/SKILL.md').write_bytes(b'---\nname: devlyn-resolve\n---\n')
                    (root / '_shared').mkdir()
                    for helper in helpers:
                        (root / '_shared' / helper).write_bytes(version.encode())
                    (root / '.devlyn-install.json').write_text(json.dumps({'version': version}), encoding='utf-8')
                settings = self.project / '.claude/settings.json'
                settings.write_text(json.dumps(old_settings), encoding='utf-8')
                for name in ('AGENTS.md', 'CLAUDE.md'):
                    block = (fixtures / f'{name[:-3].lower()}-{version}.md').read_bytes()
                    self.assertIn(b'devlyn-resolve', block)
                    (self.project / name).write_bytes(prefix + block + suffix)
                result = self.cli('-y')
                self.cli('-y', '--global', '--claude')
                for root in self.roots():
                    self.assertEqual({p.name for p in root.iterdir() if p.name.startswith('devlyn')}, {'devlyn-ideate', 'devlyn-engines'}, root)
                    self.assertEqual({p.name for p in (root / '_shared').iterdir()}, shipped, root)
                    self.assertEqual((root / 'my-skill/keep').read_bytes(), b'mine')
                self.assertEqual({p.name for p in other.iterdir()},
                                 {'my-skill', '_shared', '.devlyn-install.json', *(f'devlyn{c}resolve' for c in spellings)})
                upgraded = json.loads(settings.read_bytes())
                self.assertEqual((upgraded['env'], upgraded['permissions']), (old_settings['env'], old_settings['permissions']))
                self.assertEqual(upgraded['hooks'], {'Stop': [{'hooks': [mine]}, {'matcher': '*', 'hooks': []}],
                                                     'PreToolUse': [{'hooks': [managed]}]})
                notices = [line for line in result.stdout.decode('utf-8').splitlines() if 'Retired devlyn settings' in line]
                self.assertEqual(len(notices), 1, notices)
                for setting in ('CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS', *allow):
                    self.assertIn(setting, notices[0])
                for name in ('AGENTS.md', 'CLAUDE.md'):
                    data = (self.project / name).read_bytes()
                    self.assertTrue(data.startswith(prefix)); self.assertTrue(data.endswith(suffix))
                    self.assertEqual(data.count(b'devlyn:instructions:begin'), 1)
                    self.assertIn(CURRENT_DEFAULTS, data); self.assertNotIn(b'devlyn-resolve', data)
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
import codecs, io, json, locale, pathlib, runpy, sys
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
assert role['adapter']('codex').encode('utf-8') == (shared / 'adapters/codex.md').read_bytes()
completion = runpy.run_path(shared / 'task-complete.py')
p = work / '한국어.json'
completion['atomic_json'](p, {'message':payload})
assert completion['read_json'](p)['message'] == payload
contract = runpy.run_path(shared / 'expected-contract.py')
assert contract['loads_strict_json'](p.read_text(encoding='utf-8'))['message'] == payload
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
        for code in (0x80000000, 0xC0000005, 0xFFFFFFFF):
            for route in ('monitored-dispatch', 'monitored-bash'):
                with self.subTest(code=hex(code), route=route):
                    carrier = prompt.with_name(prompt.name + '.transport.json')
                    carrier.unlink(missing_ok=True)
                    env = environment()
                    # Native dispatcher used by codex-monitored.sh; preserve real Python CLI finalization.
                    env['DEVLYN_CODEX_PROMPT_FILE'] = str(prompt)
                    command = [sys.executable, self.shared / 'invocation-receipt.py', 'dispatch', '--binary', sys.executable,
                               '--timeout', '10', '--heartbeat', '0', '--', '-c', target, '-']
                    # Python receives "exec" as a script name from the dispatcher.
                    (self.work / 'exec').write_text(target.replace('int(sys.argv[-1])', str(code)), encoding='utf-8')
                    if route == 'monitored-bash':
                        bash = shutil.which('bash')
                        self.assertIsNotNone(bash, 'Git Bash is required for the monitored boundary')
                        # MSYS encodes native statuses into its shell status. Compare the real
                        # direct exec boundary; the native dispatcher/carrier must still retain DWORD.
                        reference = run([bash, '-c', 'exec "$@"', 'fixture', sys.executable, '-c',
                                         target, str(code)], code=None)
                        env.update(CODEX_BIN=sys.executable, CODEX_MONITORED_TIMEOUT_SEC='10',
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
                    self.assertEqual(record['argv'][0], sys.executable)
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
        (folder / 'package.json').write_text(json.dumps({'name': '@openai/codex', 'version':'1.2.3', 'bin':{'codex':'cli.js'}}), encoding='utf-8')
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

    def test_file_transport_delivers_exact_bytes_once(self):
        self.assertGreaterEqual(len(PAYLOAD), 64 * 1024)
        prompt, args = self.worker()
        self.monitor([*args, '-'])
        self.assertEqual(bytes.fromhex(self.seen()['stdin']), PAYLOAD)
        self.assertEqual(self.seen()['argv'], ['exec', *args, '-'])
        record = json.loads(prompt.with_name(prompt.name + '.transport.json').read_text(encoding='utf-8'))
        self.assertEqual((record['status'], record['exit_code'], record['command'][1:]), ('completed', 0, ['exec', *args, '-']))
        self.assertEqual(record['prompt']['sha256'], hashlib.sha256(PAYLOAD).hexdigest())
        self.assertNotEqual(self.monitor([*args, '-'], code=None), 0)  # A sealed prompt file is delivered once.
        self.env.pop('DEVLYN_CODEX_PROMPT_FILE')
        self.monitor([*args, SHORT_PAYLOAD.decode().rstrip('\n')])
        self.assertEqual(bytes.fromhex(self.seen()['stdin']), b'')

    def test_rejects_competing_and_missing_before_launch(self):
        prompt, args = self.worker()
        carrier = prompt.with_name(prompt.name + '.transport.json')
        for arguments in ([*args, '-', 'competing'], [*args, '-', '-'], [*args, SHORT_PAYLOAD.decode()], [*args, '--unknown', '-']):
            self.assertNotEqual(self.monitor(arguments, code=None), 0)
            self.assertFalse((self.work / 'seen.json').exists()); self.assertFalse(carrier.exists())
        for source in ('', self.work / 'missing', self.work):
            self.env['DEVLYN_CODEX_PROMPT_FILE'] = str(source)
            self.assertNotEqual(self.monitor([*args, '-'], code=None), 0)
            self.assertFalse((self.work / 'seen.json').exists())

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
            self.assertEqual(self.seen()['argv'], ['exec', *argv]); self.assertEqual(bytes.fromhex(self.seen()['stdin']), b'')
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
