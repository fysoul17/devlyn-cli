#!/usr/bin/env python3
"""What Devlyn app builds 0.5.29 and later send to a devlyn-cli release, and what they read from its answers.

The app checks a release it installs, plans each engine's activation (for a session it starts, resumes or forks,
and for each engine its harness sheet lists), syncs a Codex account before a session whose plan names it, reads a
project's status and its queue, and plans the cleanup twice: a count of the checkout as it is, and the plan the owner
reviews, which it then applies. Each test sends what the app sends and asserts only what the app reads: the exit
status where it requires 0, and from the last line of stdout the keys and their JSON types, the values it matches
on, and the checks the app itself makes on a plan.

What this suite holds is preserved for the whole of devlyn-cli major 4. Adding a key to an answer never needs a
change here.

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
# The values the app matches on.
STATES = ('configured', 'partial', 'unavailable', 'disabled')
# The fields of the checked release the app keeps, and the only ones it sends back.
RELEASE_FIELDS = ('package', 'version', 'digest', 'root')


def answer(result):
    """The line the app reads: the last non-empty line of stdout, as JSON; None without one."""
    try:
        return json.loads([line for line in result.stdout.decode('utf-8').splitlines() if line.strip()][-1])
    except (IndexError, ValueError):
        return None


def data(result):
    """The answer as the app reads it: {ok: true, data: {...}}."""
    envelope = answer(result)
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
        # As the app's install check runs it: an environment holding only these, and the release as the working folder.
        node = cls.env['DEVLYN_NODE']
        cleared = {'DEVLYN_NODE': node, 'PYTHONDONTWRITEBYTECODE': '1',
                   **{key: os.environ[key] for key in ('SystemRoot', 'WINDIR') if os.name == 'nt' and key in os.environ}}
        cls.verified = subprocess.run([node, cls.package / 'bin/devlyn.js', 'release', '--verify', '--root', cls.package,
                                       '--json'], cwd=cls.package, env=cleared, stdin=subprocess.DEVNULL,
                                      capture_output=True, timeout=120)
        release = data(cls.verified).get('release')
        if not (isinstance(release, dict) and all(isinstance(release.get(key), str) for key in RELEASE_FIELDS)):
            raise AssertionError(f'{cls.verified.args}: no release the app reads\n{cls.verified.stdout!r}')
        cls.release = {key: release[key] for key in RELEASE_FIELDS}
        floors = run(['node', '-p', 'JSON.stringify(require(process.argv[1]).ENGINE_CAPABILITIES)',
                      cls.package / 'bin/engines.js'])
        cls.floors = {engine: value['minimum'] for engine, value in json.loads(floors.stdout).items()}

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    @classmethod
    def cli(cls, *args, context=None):
        # As the app runs a release: node <release>/bin/devlyn.js <args> --json, an activation context on stdin.
        stdin = {'stdin': subprocess.DEVNULL} if context is None else {'input': json.dumps(context).encode()}
        return subprocess.run(['node', str(cls.package / 'bin/devlyn.js'), *map(str, args), '--json'],
                              capture_output=True, env=cls.env, timeout=120, **stdin)

    @classmethod
    def ask(cls, *args, context=None):
        return data(cls.cli(*args, context=context))

    def keys(self, value, **types):
        self.assertIsInstance(value, dict)
        for key, expected in types.items():
            self.assertIn(key, value)
            self.assertIsInstance(value[key], expected, key)

    def count(self, value, name):
        """A count the app reads as an unsigned integer: an int, not a bool, and not negative."""
        self.assertIs(type(value), int, name)
        self.assertGreaterEqual(value, 0, name)

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
        start = {**pane, 'initialPrompt': PROMPT, 'committedBlockApplies': True, 'effectiveConfig': full}
        return {
            'sheet, config unread': sheet,
            'sheet': {**sheet, 'effectiveConfig': minimal},
            'sheet, every config key': {**sheet, 'effectiveConfig': full},
            'sheet, off, version unread': {**sheet, 'projectChoice': 'none', 'version': None, 'effectiveConfig': minimal},
            'start': start,
            # Newer than every version a channel was examined on, so current Antigravity and Cursor plan their
            # run-folder channels. Only a run folder no other user can write gets one: the harness job's TMPDIR=/root
            # and macOS's per-user temp folder qualify, /tmp does not.
            'start, newer version': {**start, 'version': '2099.01.01-0000000' if engine == 'cursor' else '99.0.0'},
            'start, off': {**pane, 'projectChoice': 'none'},
            'resume': {**pane, **recorded, 'launchMode': 'resume', 'initialPrompt': PROMPT, 'effectiveConfig': minimal},
            'fork, version unread': {**pane, **recorded, 'launchMode': 'fork', 'version': None, 'effectiveConfig': full},
            'resume, unrecorded': {**pane, 'launchMode': 'resume', 'effectiveConfig': minimal},
            'fork, unrecorded, off': {**pane, 'launchMode': 'fork', 'projectChoice': 'none', 'initialPrompt': PROMPT},
        }

    def optional(self, value, **types):
        """Keys the app reads with a default equal to the CLI's empty value: typed only when present. The `seen`
        set and the non-empty checks catch a rename."""
        self.assertIsInstance(value, dict)
        for key, expected in types.items():
            if key in value:
                self.assertIsInstance(value[key], expected, key)

    def check_plan(self, plan, seen):
        self.keys(plan, channels=dict)
        self.optional(plan, release=(dict, NONE), engineArgs=list, envPatch=dict, prompt=(dict, NONE), files=list,
                      machineSync=(dict, NONE))
        if plan.get('release') is not None:
            self.keys(plan['release'], package=str, version=str, digest=str, root=str)
            # A Codex session's sync compares these four with the release the app checked; it ignores any other key.
            self.assertEqual({key: plan['release'][key] for key in RELEASE_FIELDS}, self.release)
            seen.add('release')
        for arg in plan.get('engineArgs', []):
            self.assertIsInstance(arg, str)
            seen.add('engineArgs')
        for value in plan.get('envPatch', {}).values():
            self.assertIsInstance(value, (str, NONE))
            seen.add('envPatch')
        if plan.get('prompt') is not None:
            self.keys(plan['prompt'], text=str)
            seen.add('prompt')
        for file in plan.get('files', []):
            self.keys(file, relativePath=str, utf8=str, sha256=str)
            # The app writes a file only below the run folder, and only as hashed.
            parts = file['relativePath'].replace('\\', '/').split('/')
            self.assertTrue(parts[0] not in ('', '.') and ':' not in parts[0] and '..' not in parts, file['relativePath'])
            self.assertEqual(file['sha256'], hashlib.sha256(file['utf8'].encode()).hexdigest())
            seen.add('files')
        if plan.get('machineSync') is not None:
            self.keys(plan['machineSync'], accountHome=str)
            if 'machineSync' not in seen:
                # The app runs it before every Codex session whose plan names it.
                self.ask('machine', 'sync', '--release-root', self.release['root'], '--engine', 'codex',
                         '--account-home', plan['machineSync']['accountHome'])
            seen.add('machineSync')
        channels = plan['channels']
        self.keys(channels, overall=str, principles=dict, skills=dict)
        self.optional(channels, invocation=(dict, NONE), inheritedDevlyn=list)
        self.assertIn(channels['overall'], STATES)
        for name in ('principles', 'skills'):
            self.keys(channels[name], state=str)
            self.optional(channels[name], reasons=list)
            self.assertIn(channels[name]['state'], STATES)
            for reason in channels[name].get('reasons', []):
                self.keys(reason, code=str)
                self.assertIsInstance(reason.get('params', {}), dict)
                seen.add('reasons')
        if channels.get('invocation') is not None:
            self.keys(channels['invocation'], kind=str, text=str)
            self.assertIn(channels['invocation']['kind'], ('slash', 'dollar', 'read-file'))
            seen.add('invocation')
        for entry in channels.get('inheritedDevlyn', []):
            self.assertIsInstance(entry, str)
            seen.add('inheritedDevlyn')

    def test_release_check(self):
        # The app's check of a release it installs, and of its default at every status read; its answer is read above.
        self.assertEqual(self.verified.returncode, 0, self.verified)

    def test_activation_plans(self):
        self.assertLessEqual(set(APP_ENGINES), self.floors.keys(), 'the release no longer knows an engine the app sends')
        seen = set()
        for engine in APP_ENGINES:
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

    def test_activation_refusal(self):
        # The app reads every refusal as {ok: false, error: {code, params?}}.
        context = {**self.contexts('claude')['sheet'], 'schemaVersion': 2}
        refusal = answer(self.cli('activation', '--plan', '--release-root', self.release['root'], '--context-file', '-',
                                  context=context))
        self.keys(refusal, error=dict)
        self.assertIs(refusal.get('ok'), False)
        self.keys(refusal['error'], code=str)
        self.assertIsInstance(refusal['error'].get('params', {}), dict)

    def test_status(self):
        # The harness sheet reads the project's committed instruction files and the programs the harness needs.
        status = self.ask('status', '--project', self.project)
        self.keys(status, instructions=list, requirements=list)
        self.assertTrue(status['instructions'] and status['requirements'], status)
        for instruction in status['instructions']:
            self.keys(instruction, committed=bool, ownership=str, applicableEngines=list)
            # The fixture commits the release's own template: the app applies a committed block only for these two.
            self.assertIn(instruction['ownership'], ('current', 'outdated'))
            for engine in instruction['applicableEngines']:
                self.assertIsInstance(engine, str)
        for requirement in status['requirements']:
            self.keys(requirement, name=str, required=bool, available=bool)

    def test_queue_inspect(self):
        # The queue panel reads a project's queue with the release's queue.py, strictly, and only after exit status 0.
        root = self.release['root']
        result = subprocess.run(['python3', '-B', Path(root) / 'config/skills/devlyn-ideate/scripts/queue.py', 'inspect',
                                 '--json', '--repo', self.project], cwd=self.project, stdin=subprocess.DEVNULL,
                                env={**self.env, 'DEVLYN_HARNESS_ROOT': root}, capture_output=True, timeout=120)
        self.assertEqual(result.returncode, 0, result)
        queue = answer(result)
        self.keys(queue, status=str, counts=dict, blockers=list, delivery=list, cleanup=list)
        self.assertEqual(queue['status'], 'OK', queue)
        counts = queue['counts']
        for key in ('pending', 'active', 'accepted', 'failed', 'blocked'):
            self.count(counts.get(key), key)
        self.count(counts.get('legacyPending', counts.get('legacy_pending')), 'legacyPending')
        self.assertIsInstance(queue.get('next'), (str, NONE))
        for entry in queue['blockers'] + queue['cleanup']:
            self.assertIsInstance(entry, str)
        for entry in queue['delivery']:
            self.keys(entry, identity=str, result=str)
        if queue.get('compatibility') is not None:
            self.keys(queue['compatibility'], compatible=bool)
            self.optional(queue['compatibility'], reasons=list)
            for reason in queue['compatibility'].get('reasons', []):
                self.assertIsInstance(reason, str)

    def items(self, plan):
        self.keys(plan, scopes=list)
        for scope in plan['scopes']:
            self.optional(scope, items=list)
        items = [item for scope in plan['scopes'] for item in scope.get('items', [])]
        self.assertTrue(items, plan)
        for item in items:
            self.keys(item, action=str)
            self.assertIn(item['action'], ('remove', 'edit', 'skip'))
        return items

    def test_cleanup_plans(self):
        command = ('cleanup', '--plan', '--machine', '--project', self.project, '--account-home', self.account)
        # The status read's count: each item's action and path, and a kept item's first reason.
        count = self.items(self.ask(*command, '--checkout-only'))
        for item in count:
            self.keys(item, path=str)
            if item['action'] == 'skip':
                self.keys(item, reasons=list)
                self.assertTrue(item['reasons'], item)
                self.keys(item['reasons'][0], code=str)
        # The release-skill copies the fixture left in the home and the project are counted as copies to clean.
        copies = {str(root / '.agents/skills/devlyn-ideate') for root in (self.home, self.project)}
        self.assertLessEqual(copies, {item['path'] for item in count if item['action'] == 'remove'}, count)
        # The plan the owner reviews: the app keeps it whole for the apply and words each reason with its params.
        review = self.ask(*command)
        self.keys(review, digest=str, version=str)
        for scope in review['scopes']:
            self.keys(scope, id=str, kind=str, root=str)
            self.assertIn(scope['kind'], ('machine', 'project'))
            # The machine scope is labeled by its kind; a project scope by its name.
            if scope['kind'] == 'project':
                self.keys(scope, name=str)
        reasons = []
        for item in self.items(review):
            self.keys(item, id=str, kind=str, path=str, route=str, reasons=list)
            self.assertIn(item['route'], ('local', 'delivery'))
            reasons += item['reasons']
        self.assertTrue(reasons, review)
        for reason in reasons:
            self.keys(reason, code=str, params=dict)

    def test_cleanup_apply(self):
        # The app saves the plan the owner reviewed and applies it with its progress lines. Only an edited copy can be
        # chosen, and the fixture has none, so the app adds no --include.
        review = self.ask('cleanup', '--plan', '--machine', '--project', self.project, '--account-home', self.account)
        # Applied only inside the suite's own home and project.
        paths = [scope['root'] for scope in review['scopes']] + [item['path'] for item in self.items(review)]
        self.assertTrue(all(Path(path).is_relative_to(self.work) for path in paths), paths)
        # The other tests count the copies this removes.
        for root in (self.home, self.project):
            self.addCleanup(shutil.copytree, self.package / 'config/skills/devlyn-ideate',
                            root / '.agents/skills/devlyn-ideate', dirs_exist_ok=True)
        plan_file = self.work / 'cleanup-plan.json'
        plan_file.write_text(json.dumps(review), encoding='utf-8')
        result = self.cli('cleanup', '--apply', '--events', '--plan-file', plan_file, '--digest', review['digest'])
        outcome = data(result)
        self.keys(outcome, state=str, scopes=list)
        self.assertEqual(outcome['state'], 'succeeded', outcome)
        # A line before the answer reaches the app only as JSON naming an event; a scope event carries a record.
        progress = []
        for line in [line for line in result.stdout.decode('utf-8').splitlines() if line.strip()][:-1]:
            try:
                event = json.loads(line)
            except ValueError:
                continue
            if isinstance(event, dict) and event.get('event') == 'scope':
                progress.append(event.get('scope'))
        self.assertTrue(progress and outcome['scopes'], result.stdout)
        ids = {scope['id'] for scope in review['scopes']}
        # Each record moves the row of its plan scope: found by scopeId, counted by state and total, and shown by its
        # kind, a project's name, its delivery and its error.
        for record in progress + outcome['scopes']:
            self.keys(record, scopeId=str, kind=str, total=int, state=str)
            self.optional(record, delivery=(dict, NONE), error=(dict, NONE))
            self.assertIn(record['scopeId'], ids)
            self.assertIn(record['kind'], ('machine', 'project'))
            if record['kind'] == 'project':
                self.keys(record, name=str)
            self.count(record['total'], 'total')
            self.assertIn(record['state'], ('running', 'done', 'failed', 'skipped'))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('--package-root', type=Path)
    args, remaining = parser.parse_known_args()
    if args.package_root:
        PACKAGE_ROOT = args.package_root.resolve()
    unittest.main(argv=[__file__, *remaining])
