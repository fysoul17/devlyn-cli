#!/usr/bin/env python3
"""What Devlyn app builds 0.5.29 and later send to a devlyn-cli release, and what they read from its answers.

The app checks a release it installs, plans each engine's activation (for a session it starts, resumes or forks,
and for each engine its harness sheet lists), reads a project's status, and plans the cleanup twice: a count of the
checkout as it is, and the plan the owner reviews. Each test sends what the app sends and asserts only what the app
reads from the last line of stdout: the keys and their JSON types, and the checks the app itself makes on a plan.

An assertion here is loosened or removed only after an app release that no longer depends on it has shipped and the
app's supported range excludes the older builds. Adding a key to an answer never needs a change here.

--package-root exercises an extracted release; otherwise pack this checkout. No engine, model or network.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import runpy
import shutil
import subprocess
import tarfile
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
HELPERS = runpy.run_path(str(ROOT / 'scripts/test-harness-release.py'))
run, environment = HELPERS['run'], HELPERS['environment']
PACKAGE_ROOT = None
NONE = type(None)
# The engine ids the app sends.
APP_ENGINES = ('claude', 'codex', 'grok', 'omp', 'antigravity', 'cursor', 'opencode', 'kimi', 'copilot', 'qwen', 'pi')
PROMPT = {'text': 'Fix the failing test', 'transport': 'argv'}


def data(result):
    """The answer as the app reads it: the last non-empty line of stdout, {ok: true, data: {...}}."""
    try:
        envelope = json.loads([line for line in result.stdout.decode('utf-8').splitlines() if line.strip()][-1])
    except (IndexError, ValueError):
        envelope = None
    if not (isinstance(envelope, dict) and envelope.get('ok') is True and isinstance(envelope.get('data'), dict)):
        raise AssertionError(f'{result.args}: no answer the app reads\n{result.stdout!r}\n{result.stderr!r}')
    return envelope['data']


class AppContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix='devlyn-app-contract-')
        cls.work = Path(cls.temp.name).resolve()
        if PACKAGE_ROOT:
            cls.package = PACKAGE_ROOT
        else:
            npm = Path(shutil.which('npm')).resolve()
            command = [npm] if os.name != 'nt' else [shutil.which('node'), npm.parent / 'node_modules/npm/bin/npm-cli.js']
            packed = run([*command, 'pack', ROOT, '--json', '--pack-destination', cls.work, '--cache', cls.work / 'npm-cache'])
            with tarfile.open(cls.work / json.loads(packed.stdout)[0]['filename']) as archive:
                archive.extractall(cls.work, filter='data')
            cls.package = cls.work / 'package'
        cls.home = cls.work / 'home'
        cls.account = cls.home / '.devlyn/cli-accounts/codex/fixture'
        cls.project = cls.work / 'project'
        cls.run_dir = Path(tempfile.mkdtemp(prefix='run-', dir=cls.work))
        for directory in (cls.home / '.codex', cls.account, cls.project):
            directory.mkdir(parents=True)
        cls.env = environment()
        for key in list(cls.env):
            if key.startswith(('CODEX_', 'CLAUDE_', 'COPILOT_', 'GROK_', 'QWEN_', 'KIMI_', 'OPENCODE_', 'PI_', 'XDG_')):
                del cls.env[key]
        cls.env.update(HOME=str(cls.home), USERPROFILE=str(cls.home), DEVLYN_NODE=shutil.which('node'))
        # A Git project with a committed instruction file, and a copy of a release skill an earlier install left in the
        # home and in the project: the plans name it and the cleanup removes it.
        run(['git', 'init', '-q', cls.project])
        for key, value in (('user.name', 'Fixture'), ('user.email', 'fixture@example.invalid')):
            run(['git', '-C', cls.project, 'config', key, value])
        shutil.copyfile(cls.package / 'harness/AGENTS.md', cls.project / 'AGENTS.md')
        run(['git', '-C', cls.project, 'add', 'AGENTS.md'])
        run(['git', '-C', cls.project, 'commit', '-qm', 'fixture'])
        for root in (cls.home, cls.project):
            shutil.copytree(cls.package / 'config/skills/devlyn-ideate', root / '.agents/skills/devlyn-ideate')
        cls.release = cls.ask('release', '--verify', '--root', cls.package)['release']
        floors = run(['node', '-p', 'JSON.stringify(require(process.argv[1]).ENGINE_CAPABILITIES)',
                      cls.package / 'bin/engines.js'])
        cls.floors = {engine: value['minimum'] for engine, value in json.loads(floors.stdout).items()}
        cls.engines = [*APP_ENGINES, *(engine for engine in cls.floors if engine not in APP_ENGINES)]

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    @classmethod
    def ask(cls, *args, context=None):
        # As the app runs a release: node <release>/bin/devlyn.js <args> --json, an activation context on stdin.
        stdin = {'stdin': subprocess.DEVNULL} if context is None else {'input': json.dumps(context).encode()}
        return data(subprocess.run(['node', str(cls.package / 'bin/devlyn.js'), *map(str, args), '--json'],
                                   capture_output=True, env=cls.env, timeout=120, **stdin))

    def keys(self, value, **types):
        self.assertIsInstance(value, dict)
        for key, expected in types.items():
            self.assertIn(key, value)
            self.assertIsInstance(value[key], expected, key)

    def contexts(self, engine):
        """What the app sends to plan `engine`: from its harness sheet (fresh, with no account home or first
        instruction), and from a session it starts, resumes or forks, with or without a recorded release."""
        owner = str(self.work / 'owner')
        # The engine's effective config as the app builds it: with only the keys it always sends, and with every key.
        minimal, full = {
            'claude': ({'pluginDirs': []}, {'pluginDirs': [], 'appendSystemPrompt': 'Owner text'}),
            'codex': ({}, {'developer_instructions': 'Owner text',
                           'marketplaces': {'owner': {'source_type': 'local', 'source': owner}},
                           'plugins': {'unrelated@owner': {'enabled': True}},
                           'skills': {'config': [{'path': os.path.join(owner, 'SKILL.md'), 'enabled': True}]}}),
            'omp': ({'skills': {}}, {'appendSystemPrompt': 'Owner text', 'skills': {
                'customDirectories': [owner], 'ignoredSkills': [], 'enableSkillCommands': True}}),
            'opencode': ({}, {'inlineConfig': '{}', 'skillsPaths': []}),
            'kimi': ({'ownerAgent': False}, {'ownerAgent': True}),
        }.get(engine, ({}, {}))
        sheet = dict(schemaVersion=1, engine=engine, version=self.floors.get(engine), launchMode='fresh',
                     cwd=str(self.project), runDir=str(self.run_dir), projectChoice='default',
                     committedBlockApplies=False, initialPrompt=None, effectiveConfig=None)
        pane = {**sheet, **({'accountHome': str(self.home / '.codex')} if engine == 'codex' else {})}
        recorded = {'recordedRelease': self.release}
        return {
            'sheet, config unread': sheet,
            'sheet': {**sheet, 'effectiveConfig': minimal},
            'sheet, every config key': {**sheet, 'effectiveConfig': full},
            'sheet, off, version unread': {**sheet, 'projectChoice': 'none', 'version': None, 'effectiveConfig': minimal},
            'start': {**pane, 'initialPrompt': PROMPT, 'committedBlockApplies': True, 'effectiveConfig': full},
            'start, off': {**pane, 'projectChoice': 'none'},
            'resume': {**pane, **recorded, 'launchMode': 'resume', 'initialPrompt': PROMPT, 'effectiveConfig': minimal},
            'fork, version unread': {**pane, **recorded, 'launchMode': 'fork', 'version': None, 'effectiveConfig': full},
            'resume, unrecorded': {**pane, 'launchMode': 'resume', 'effectiveConfig': minimal},
            'fork, unrecorded, off': {**pane, 'launchMode': 'fork', 'projectChoice': 'none', 'initialPrompt': PROMPT},
        }

    def check_plan(self, plan, seen):
        self.keys(plan, release=(dict, NONE), engineArgs=list, envPatch=dict, prompt=(dict, NONE), files=list,
                  machineSync=(dict, NONE), channels=dict)
        if plan['release'] is not None:
            self.keys(plan['release'], package=str, version=str, digest=str, root=str)
            # A Codex session's sync compares it with the release the app checked.
            self.assertEqual(plan['release'], self.release)
            seen.add('release')
        for arg in plan['engineArgs']:
            self.assertIsInstance(arg, str)
            seen.add('engineArgs')
        for value in plan['envPatch'].values():
            self.assertIsInstance(value, (str, NONE))
            seen.add('envPatch')
        if plan['prompt'] is not None:
            self.keys(plan['prompt'], text=str)
            seen.add('prompt')
        for file in plan['files']:
            self.keys(file, relativePath=str, utf8=str, sha256=str)
            # The app writes a file only below the run folder, and only as hashed.
            parts = file['relativePath'].replace('\\', '/').split('/')
            self.assertTrue(parts[0] not in ('', '.') and ':' not in parts[0] and '..' not in parts, file['relativePath'])
            self.assertEqual(file['sha256'], hashlib.sha256(file['utf8'].encode()).hexdigest())
            seen.add('files')
        if plan['machineSync'] is not None:
            self.keys(plan['machineSync'], accountHome=str)
            seen.add('machineSync')
        channels = plan['channels']
        self.keys(channels, overall=str, principles=dict, skills=dict, invocation=(dict, NONE), inheritedDevlyn=list)
        for name in ('principles', 'skills'):
            self.keys(channels[name], state=str, reasons=list)
            for reason in channels[name]['reasons']:
                self.keys(reason, code=str)
                self.assertIsInstance(reason.get('params', {}), dict)
                seen.add('reasons')
        if channels['invocation'] is not None:
            self.keys(channels['invocation'], kind=str, text=str)
            seen.add('invocation')
        for entry in channels['inheritedDevlyn']:
            self.assertIsInstance(entry, str)
            seen.add('inheritedDevlyn')

    def test_release_check(self):
        # The app's check of a release it installs, and of its default at every status read.
        self.keys(self.release, package=str, version=str, digest=str, root=str)

    def test_activation_plans(self):
        seen = set()
        for engine in self.engines:
            plans = {}
            for label, context in self.contexts(engine).items():
                with self.subTest(engine=engine, context=label):
                    plan = self.ask('activation', '--plan', '--release-root', self.release['root'],
                                    '--context-file', '-', context=context)
                    self.check_plan(plan, seen)
                    plans[label] = plan
            # The effective config the app sends is taken: one read as unreadable plans as the failed read does.
            for label in ('sheet', 'sheet, every config key'):
                if {label, 'sheet, config unread'} <= plans.keys():
                    with self.subTest(engine=engine, config=label):
                        self.assertNotEqual(plans[label]['channels'], plans['sheet, config unread']['channels'])
        # The fixture puts every part of a plan the app reads in some answer: no check above passed on empty values.
        self.assertEqual(seen, {'release', 'engineArgs', 'envPatch', 'prompt', 'files', 'machineSync', 'reasons',
                                'invocation', 'inheritedDevlyn'})

    def test_status(self):
        # The harness sheet reads the project's committed instruction files and the programs the harness needs.
        status = self.ask('status', '--project', self.project)
        self.keys(status, instructions=list, requirements=list)
        self.assertTrue(status['instructions'] and status['requirements'], status)
        for instruction in status['instructions']:
            self.keys(instruction, committed=bool, ownership=str, applicableEngines=list)
            for engine in instruction['applicableEngines']:
                self.assertIsInstance(engine, str)
        for requirement in status['requirements']:
            self.keys(requirement, name=str, required=bool, available=bool)

    def items(self, plan):
        self.keys(plan, scopes=list)
        for scope in plan['scopes']:
            self.keys(scope, items=list)
        items = [item for scope in plan['scopes'] for item in scope['items']]
        self.assertTrue(items, plan)
        return items

    def test_cleanup_plans(self):
        command = ('cleanup', '--plan', '--machine', '--project', self.project, '--account-home', self.account)
        # The status read's count: each item's action and path, and a kept item's first reason.
        for item in self.items(self.ask(*command, '--checkout-only')):
            self.keys(item, action=str, path=str)
            if item['action'] == 'skip':
                self.keys(item, reasons=list)
                self.assertTrue(item['reasons'], item)
                self.keys(item['reasons'][0], code=str)
        # The plan the owner reviews: the app keeps it whole for the apply and words each reason with its params.
        review = self.ask(*command)
        self.keys(review, digest=str, version=str)
        for scope in review['scopes']:
            self.keys(scope, id=str, kind=str, root=str, name=(str, NONE))
        reasons = []
        for item in self.items(review):
            self.keys(item, id=str, kind=str, path=str, action=str, route=str, reasons=list)
            reasons += item['reasons']
        self.assertTrue(reasons, review)
        for reason in reasons:
            self.keys(reason, code=str, params=dict)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('--package-root', type=Path)
    args, remaining = parser.parse_known_args()
    if args.package_root:
        PACKAGE_ROOT = args.package_root.resolve()
    unittest.main(argv=[__file__, *remaining])
