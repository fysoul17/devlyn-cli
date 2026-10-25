#!/usr/bin/env python3
"""Model-free activation, projection and native argv fixtures.

--codex-probe additionally runs only `codex debug prompt-input`, in an isolated
HOME/CODEX_HOME below TMPDIR. No model session, login, or persistent registration.
--package-root exercises an extracted release; otherwise pack this checkout.
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
import tomllib
import unittest

ROOT = Path(__file__).resolve().parents[1]
HELPERS = runpy.run_path(str(ROOT / 'scripts/test-harness-release.py'))
run, snapshot, environment = (HELPERS[key] for key in ('run', 'snapshot', 'environment'))
PACKAGE_ROOT = None
CODEX = None
VERSIONS = dict(claude='2.1.307', codex='0.163.0', grok='1.0.62', omp='16.5.0',
                antigravity='1.4.4', cursor='2025.09.12-4852336', opencode='1.19.2',
                kimi='2.3.0', copilot='1.0.98', qwen='0.26.0')


class ActivationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix='devlyn-activation-')
        cls.work = Path(cls.temp.name).resolve()
        if PACKAGE_ROOT:
            cls.package = PACKAGE_ROOT
        else:
            npm = Path(shutil.which('npm')).resolve()
            command = [npm] if os.name != 'nt' else [shutil.which('node'), npm.parent / 'node_modules/npm/bin/npm-cli.js']
            packed = run([*command, 'pack', ROOT, '--json', '--pack-destination', cls.work,
                          '--cache', cls.work / 'npm-cache'])
            with tarfile.open(cls.work / json.loads(packed.stdout)[0]['filename']) as archive:
                archive.extractall(cls.work, filter='data')
            cls.package = cls.work / 'package'
        cls.cli = cls.package / 'bin/devlyn.js'
        result = run(['node', cls.cli, 'release', '--verify', '--root', cls.package, '--json'])
        cls.release = json.loads(result.stdout)['data']['release']
        cls.release_before = snapshot(cls.package)

    @classmethod
    def tearDownClass(cls):
        try:
            assert snapshot(cls.package) == cls.release_before, 'activation mutated the release'
        finally:
            cls.temp.cleanup()

    def setUp(self):
        self.case = self.work / self.id().rsplit('.', 1)[-1]
        self.case.mkdir()
        self.home = self.case / 'home'
        self.account = self.case / 'account with spaces 한글'
        self.project = self.case / 'project'
        self.run_dir = self.case / 'run 한글'
        for directory in (self.home, self.account, self.project, self.run_dir):
            directory.mkdir()
        self.env = environment()
        for key in list(self.env):
            if key.startswith(('CODEX_', 'CLAUDE_', 'COPILOT_', 'GROK_', 'QWEN_', 'KIMI_', 'OPENCODE_', 'PI_', 'XDG_')):
                del self.env[key]
        self.env.update(HOME=str(self.home), USERPROFILE=str(self.home), CODEX_HOME=str(self.account),
                        XDG_CONFIG_HOME=str(self.home / '.config'), XDG_CACHE_HOME=str(self.home / '.cache'),
                        XDG_DATA_HOME=str(self.home / '.local/share'), XDG_STATE_HOME=str(self.home / '.local/state'))
        run(['git', 'init', '-q', self.project], env=self.env)

    def context(self, engine='codex', **changes):
        return dict(schemaVersion=1, engine=engine, version=VERSIONS[engine], launchMode='fresh',
                    cwd=str(self.project), runDir=str(self.run_dir), projectChoice='devlyn',
                    committedBlockApplies=False, initialPrompt=None, accountRef='fixture',
                    effectiveConfig={'ownerAgent': False} if engine == 'kimi' else {}, **changes)

    def plan(self, context, code=0, file=False, release_root=None):
        raw = json.dumps(context, ensure_ascii=False).encode()
        target = '-'
        if file:
            target = self.case / 'context.json'
            target.write_bytes(raw)
        before = snapshot(self.case)
        result = subprocess.run(['node', str(self.cli), 'activation', '--plan', '--release-root', str(release_root or self.package),
                                 '--context-file', str(target), '--json'], input=raw if target == '-' else None,
                                capture_output=True, env=self.env, timeout=30)
        self.assertEqual(result.returncode, code, result.stderr.decode())
        self.assertEqual(snapshot(self.case), before, 'plan wrote files')
        value = json.loads(result.stdout)
        self.assertEqual(value['ok'], code == 0)
        return value['data' if code == 0 else 'error']

    def sync(self, code=0, account=None):
        result = run(['node', self.cli, 'machine', 'sync', '--release-root', self.package,
                      '--engine', 'codex', '--account-home', account or self.account, '--json'], env=self.env, code=code)
        value = json.loads(result.stdout)
        return value['data' if code == 0 else 'error']

    def overrides(self, plan):
        args = plan['engineArgs']
        return {key: value for index, arg in enumerate(args) if arg == '-c'
                for key, value in tomllib.loads(args[index + 1]).items()}

    def test_per_engine_fresh_fixture(self):
        # Prediction: Copilot configures both session channels; other engine defaults stay unchanged.
        flags = dict(claude='--plugin-dir', codex='-c', grok='--rules', omp='--config',
                     kimi='--agent-file', qwen='--append-system-prompt')
        for engine in VERSIONS:
            with self.subTest(engine=engine):
                plan = self.plan(self.context(engine), file=True)
                self.assertEqual(plan['release'], self.release)
                self.assertEqual(plan['channels']['engine'], engine)
                self.assertEqual(plan['channels']['executor']['supported'], engine in ('claude', 'codex'))
                if engine in flags:
                    self.assertIn(flags[engine], plan['engineArgs'])
                if engine in ('cursor', 'antigravity'):
                    self.assertEqual(plan['engineArgs'], [])
                    self.assertEqual(plan['channels']['principles']['reasons'][0]['code'], 'principles-task-only')
                if engine == 'copilot':
                    self.assertEqual(plan['channels']['overall'], 'configured')
                for file in plan['files']:
                    self.assertEqual(file['sha256'], hashlib.sha256(file['utf8'].encode()).hexdigest())
                    self.assertFalse(Path(file['relativePath']).is_absolute())

    def test_per_engine_none_preserves_owner_configuration(self):
        for engine in VERSIONS:
            with self.subTest(engine=engine):
                ctx = self.context(engine)
                ctx['projectChoice'] = 'none'
                plan = self.plan(ctx)
                for key, empty in [('engineArgs', []), ('envPatch', {}), ('files', []), ('machineSync', None), ('release', None), ('prompt', None)]:
                    self.assertEqual(plan[key], empty)
                for name in ('principles', 'skills', 'hide'):
                    self.assertEqual(plan['channels'][name]['state'], 'disabled')
                self.assertEqual(plan['channels']['overall'], 'disabled')

    def test_per_engine_old_and_unknown_generation(self):
        for engine in VERSIONS:
            for version in ('0.0.0', '999.0.0', None):
                with self.subTest(engine=engine, version=version):
                    ctx = self.context(engine)
                    ctx['version'] = version
                    plan = self.plan(ctx)
                    self.assertEqual(plan['channels']['overall'], 'unavailable')
                    self.assertEqual(plan['engineArgs'], [])
                    self.assertEqual(plan['channels']['skills']['reasons'][0]['params']['minimum'], VERSIONS[engine])

    def test_newer_releases_of_the_examined_major_are_taken(self):
        # Prediction: a newer minor or patch (and a newer Cursor build) plans like the examined one; a new major does not.
        newer = dict(claude='2.3.0', codex='0.171.2', grok='1.4.0', omp='16.9.1', antigravity='1.6.0',
                     cursor='2026.01.05-abcdef1', opencode='1.25.0', kimi='2.9.0', copilot='1.2.0', qwen='0.31.0')
        for engine, version in newer.items():
            with self.subTest(engine=engine):
                ctx = self.context(engine)
                ctx['version'] = version
                self.assertNotEqual(self.plan(ctx)['channels']['overall'], 'unavailable')

    def test_per_engine_committed_block_omits_defaults(self):
        for engine in VERSIONS:
            with self.subTest(engine=engine):
                ctx = self.context(engine)
                ctx.update(committedBlockApplies=True, initialPrompt={'text': 'owner task', 'transport': 'argv'})
                plan = self.plan(ctx)
                self.assertNotIn('The following Devlyn instructions are defaults', json.dumps(plan))
                self.assertEqual(plan['channels']['principles']['mechanism'], 'native-project')
                self.assertNotEqual(plan['channels']['skills']['state'], 'disabled')

    def test_per_engine_resume_fork_uses_recorded_binding_even_when_none(self):
        for engine in VERSIONS:
            for mode in ('resume', 'fork'):
                with self.subTest(engine=engine, mode=mode):
                    ctx = self.context(engine)
                    ctx.update(launchMode=mode, recordedRelease=self.release, projectChoice='none')
                    plan = self.plan(ctx)
                    self.assertEqual(plan['release'], self.release)
                    if engine == 'kimi':
                        self.assertEqual(plan['engineArgs'], [])
                        self.assertEqual(plan['channels']['overall'], 'partial')
                    elif engine in ('claude', 'codex'):
                        self.assertEqual(plan['channels']['overall'], 'configured')
                    ctx['recordedRelease'] = None
                    disabled = self.plan(ctx)
                    self.assertEqual(disabled['channels']['overall'], 'disabled')
                    self.assertIsNone(disabled['release'])

    def test_per_engine_legacy_resume_is_never_upgraded(self):
        for engine in VERSIONS:
            with self.subTest(engine=engine):
                ctx = self.context(engine)
                ctx['launchMode'] = 'resume'
                plan = self.plan(ctx)
                self.assertIsNone(plan['release'])
                self.assertEqual(plan['channels']['overall'], 'partial')
                self.assertEqual(plan['envPatch'], {})

    def test_resume_ignores_current_default_root(self):
        ctx = self.context()
        ctx.update(launchMode='resume', recordedRelease=self.release)
        # The current default may even have disappeared; only the recording is read.
        plan = self.plan(ctx, release_root=self.case / 'removed-current-default')
        self.assertEqual(plan['release'], self.release)

    def test_per_engine_malformed_effective_config(self):
        for engine in VERSIONS:
            for config in (None, [], {'unexpected': 'owner'}):
                with self.subTest(engine=engine, config=config):
                    ctx = self.context(engine)
                    ctx['effectiveConfig'] = config
                    plan = self.plan(ctx)
                    self.assertEqual(plan['engineArgs'], [])
                    self.assertEqual(plan['envPatch'], {})
                    self.assertEqual(plan['channels']['skills']['reasons'][0]['code'], 'config-unreadable')

    def test_context_rejects_full_environment_and_bad_inputs(self):
        self.assertEqual(self.plan(self.context(), release_root='relative', code=2)['code'], 'invalid-arguments')
        for patch in ({'env': {'SECRET': 'no'}}, {'cwd': 'relative'}, {'initialPrompt': 'string'},
                      {'engine': 'agy'}, {'schemaVersion': 2}, {'recordedRelease': {'root': '/bad'}}):
            with self.subTest(patch=patch):
                ctx = self.context()
                ctx.update(patch)
                self.assertEqual(self.plan(ctx, code=2)['code'], 'invalid-arguments')
        ctx = self.context()
        ctx.update(launchMode='resume', recordedRelease={**self.release, 'digest': '0' * 64})
        self.assertEqual(self.plan(ctx, code=3)['code'], 'release-version-conflict')

    def test_codex_merges_effective_values_and_toml_round_trip(self):
        ctx = self.context()
        developer = 'Owner "quoted" \\ values\n한글\t\x7f'
        entries = [{'path': str(self.case / 'owner SKILL.md'), 'enabled': False}]
        ctx['effectiveConfig'] = {'developer_instructions': developer, 'skills': {'config': entries},
                                  'marketplaces': {'owner': {'source_type': 'local', 'source': str(self.case)}},
                                  'plugins': {'owner@owner': {'enabled': True}}}
        values = self.overrides(self.plan(ctx))
        self.assertTrue(values['developer_instructions'].startswith(developer + '\n\n'))
        self.assertEqual(values['marketplaces']['owner'], ctx['effectiveConfig']['marketplaces']['owner'])
        self.assertEqual(values['plugins']['owner@owner'], {'enabled': True})
        self.assertNotIn('skills', values)  # no replacement unless hide is needed
        self.assertIn(str(self.package / 'config/skills/_shared'), values['developer_instructions'])

    def test_codex_none_hides_only_fingerprint_proven_skills(self):
        root = self.home / '.agents/skills'
        shutil.copytree(self.package / 'config/skills/devlyn-ideate', root / 'devlyn-ideate')
        shutil.copytree(self.package / 'config/skills/devlyn-engines', root / 'devlyn-engines')
        (root / 'devlyn-engines/owner-content').write_text('keep mine')
        ctx = self.context()
        ctx['projectChoice'] = 'none'
        ctx['effectiveConfig'] = {'skills': {'config': [{'path': str(root / 'owner/SKILL.md'), 'enabled': True}]}}
        plan = self.plan(ctx)
        entries = self.overrides(plan)['skills']['config']
        self.assertEqual(entries, [*ctx['effectiveConfig']['skills']['config'],
                                  {'path': str(root / 'devlyn-ideate/SKILL.md'), 'enabled': False}])
        self.assertEqual(plan['channels']['hide']['state'], 'configured')
        self.assertEqual(plan['channels']['principles']['state'], 'disabled')
        self.assertEqual(plan['envPatch'], {})

    def test_collision_preserves_owner_skills_per_engine(self):
        root = self.case / 'owner-skills'
        skill = root / 'devlyn-ideate'
        skill.mkdir(parents=True)
        (skill / 'SKILL.md').write_text('---\nname: devlyn-ideate\ndescription: owner\n---\nOwner')
        for engine in VERSIONS:
            with self.subTest(engine=engine):
                ctx = self.context(engine)
                ctx['skillRoots'] = [str(root)]
                plan = self.plan(ctx)
                self.assertEqual(plan['channels']['inheritedDevlyn'], [])
                if engine in ('omp', 'copilot'):
                    self.assertEqual(plan['channels']['skills']['state'], 'partial')
                    self.assertEqual(plan['channels']['skills']['reasons'][0]['code'], 'name-collision')
                if engine in ('claude', 'codex'):
                    self.assertEqual(plan['channels']['skills']['state'], 'configured')  # different namespace
                ctx['projectChoice'] = 'none'
                self.assertEqual(self.plan(ctx)['engineArgs'], [])

    def test_codex_market_collision_falls_back_without_overwrite(self):
        ctx = self.context()
        market = 'devlyn-harness-v' + self.release['version'].replace('.', '-')
        ctx['effectiveConfig'] = {'marketplaces': {market: {'source_type': 'local', 'source': '/owner'}}}
        plan = self.plan(ctx)
        self.assertIsNone(plan['machineSync'])
        self.assertEqual(set(self.overrides(plan)), {'developer_instructions'})
        self.assertEqual(plan['channels']['invocation']['kind'], 'read-file')

    def test_claude_plugin_namespace_collision_uses_absolute_invocation(self):
        owner = self.case / 'owner-plugin/.claude-plugin'
        owner.mkdir(parents=True)
        (owner / 'plugin.json').write_text('{"name":"devlyn"}')
        ctx = self.context('claude')
        ctx['effectiveConfig']['pluginDirs'] = [str(owner.parent)]
        plan = self.plan(ctx)
        self.assertNotIn('--plugin-dir', plan['engineArgs'])
        self.assertEqual(plan['channels']['invocation']['kind'], 'read-file')
        self.assertEqual(plan['channels']['skills']['reasons'][0]['code'], 'name-collision')
        ctx['effectiveConfig']['pluginDirs'] = [str(self.package / 'native/claude')]
        plan = self.plan(ctx)
        self.assertNotIn('--plugin-dir', plan['engineArgs'])
        self.assertEqual(plan['channels']['skills']['state'], 'configured')

    def test_append_and_overlay_merges(self):
        for engine, key in [('claude', 'appendSystemPrompt'), ('grok', 'rules'), ('qwen', 'appendSystemPrompt'), ('omp', 'appendSystemPrompt')]:
            with self.subTest(engine=engine):
                ctx = self.context(engine)
                ctx['effectiveConfig'][key] = 'Owner text\n"한글"'
                if engine == 'omp':
                    ctx['effectiveConfig']['skills'] = {'customDirectories': ['/owner one', '/owner two'],
                                                       'ignoredSkills': ['owner-hidden'], 'enableSkillCommands': False}
                plan = self.plan(ctx)
                self.assertIn('Owner text\\n\\"한글\\"', json.dumps(plan, ensure_ascii=False))
                if engine == 'omp':
                    overlay = json.loads(plan['files'][0]['utf8'])
                    self.assertEqual(overlay['skills']['customDirectories'], ['/owner one', '/owner two', str(self.package / 'config/skills')])
                    self.assertEqual(overlay['skills']['ignoredSkills'], ['owner-hidden'])
                    self.assertFalse(overlay['skills']['enableSkillCommands'])

    def test_opencode_preserves_inline_and_rejects_malformed(self):
        ctx = self.context('opencode')
        owner = {'instructions': ['owner.md'], 'skills': {'paths': ['/owner']}, 'permission': {'bash': 'ask'}, 'model': 'owner/model'}
        ctx['effectiveConfig'] = {'inlineConfig': json.dumps(owner)}
        plan = self.plan(ctx)
        merged = json.loads(plan['envPatch']['OPENCODE_CONFIG_CONTENT'])
        self.assertEqual(merged['instructions'][0], 'owner.md')
        self.assertEqual({k: v for k, v in merged.items() if k != 'instructions'}, {k: v for k, v in owner.items() if k != 'instructions'})
        for invalid in ('{', '[]', '{"instructions":null}', '{"instructions":"owner.md"}'):
            ctx['effectiveConfig']['inlineConfig'] = invalid
            plan = self.plan(ctx)
            self.assertEqual(plan['envPatch'], {})
            self.assertEqual(plan['files'], [])

    def test_copilot_instructions_file(self):
        # Prediction: Copilot plans an apply-to-all file with the same defaults/catalog and a verified hash.
        plan = self.plan(self.context('copilot'))
        instructions = self.plan(self.context('opencode'))['files'][0]['utf8']
        content = '---\napplyTo: "**"\n---\n' + instructions
        self.assertEqual(plan['files'], [{'relativePath': 'copilot/devlyn.instructions.md', 'utf8': content,
                                          'sha256': hashlib.sha256(content.encode()).hexdigest()}])
        self.assertEqual(plan['envPatch']['COPILOT_CUSTOM_INSTRUCTIONS_DIRS'], str(self.run_dir / 'copilot'))
        self.assertEqual(plan['channels']['principles'], {
            'state': 'configured', 'mechanism': 'COPILOT_CUSTOM_INSTRUCTIONS_DIRS', 'reasons': []})
        self.assertEqual(plan['channels']['overall'], 'configured')

    def test_copilot_instructions_merge_and_dedupe(self):
        # Prediction: effective instructionsDirs wins over env; null/absent uses env; an existing run dir is unchanged.
        directory = str(self.run_dir / 'copilot')
        self.env['COPILOT_CUSTOM_INSTRUCTIONS_DIRS'] = '/env one,/env two'
        for config, expected in [({}, '/env one,/env two,' + directory),
                                 ({'instructionsDirs': None}, '/env one,/env two,' + directory),
                                 ({'instructionsDirs': ''}, directory),
                                 ({'instructionsDirs': '/owner one,/owner two'}, '/owner one,/owner two,' + directory),
                                 ({'instructionsDirs': '/owner,' + directory + ',/last'}, '/owner,' + directory + ',/last')]:
            with self.subTest(config=config):
                ctx = self.context('copilot')
                ctx['effectiveConfig'] = config
                self.assertEqual(self.plan(ctx)['envPatch']['COPILOT_CUSTOM_INSTRUCTIONS_DIRS'], expected)
        self.env['COPILOT_CUSTOM_INSTRUCTIONS_DIRS'] = '/env,' + directory
        self.assertEqual(self.plan(self.context('copilot'))['envPatch']['COPILOT_CUSTOM_INSTRUCTIONS_DIRS'], '/env,' + directory)

    def test_copilot_instructions_comma_fallback(self):
        # Prediction: a comma in the run path leaves principles unavailable without an instruction file/env patch.
        ctx = self.context('copilot')
        ctx['runDir'] = str(self.case / 'run,comma')
        plan = self.plan(ctx)
        self.assertEqual(plan['files'], [])
        self.assertNotIn('COPILOT_CUSTOM_INSTRUCTIONS_DIRS', plan['envPatch'])
        self.assertEqual(plan['channels']['principles'], {'state': 'unavailable', 'mechanism': None,
            'reasons': [{'code': 'principles-unavailable', 'params': {'detail': 'comma-in-path'}}]})
        self.assertEqual(plan['channels']['skills']['state'], 'configured')

    def test_copilot_instructions_committed_block_wins(self):
        # Prediction: committed principles bypass instruction injection even with a comma or release-local runDir.
        ctx = self.context('copilot')
        ctx['committedBlockApplies'] = True
        ctx['effectiveConfig'] = {'instructionsDirs': '/owner'}
        for directory in (self.run_dir, self.case / 'run,comma', self.package / 'run'):
            with self.subTest(directory=directory):
                ctx['runDir'] = str(directory)
                plan = self.plan(ctx)
                self.assertEqual(plan['files'], [])
                self.assertNotIn('COPILOT_CUSTOM_INSTRUCTIONS_DIRS', plan['envPatch'])
                self.assertEqual(plan['channels']['principles'], {
                    'state': 'configured', 'mechanism': 'native-project', 'reasons': []})
                self.assertEqual(plan['channels']['skills']['state'], 'configured')

    def test_opencode_native_skills_merge(self):
        # Prediction: effective paths survive unchanged, duplicates collapse, inline urls remain, and invocation stays read-file.
        ctx = self.context('opencode')
        owner = {'instructions': ['owner.md'], 'skills': {'paths': ['/stale-inline'], 'urls': ['https://example.com/skills']},
                 'permission': {'bash': 'ask'}}
        for paths in ([], ['relative/skills', '/owner skills', 'relative/skills']):
            with self.subTest(paths=paths):
                ctx['effectiveConfig'] = {'inlineConfig': json.dumps(owner), 'skillsPaths': paths}
                plan = self.plan(ctx)
                merged = json.loads(plan['envPatch']['OPENCODE_CONFIG_CONTENT'])
                self.assertEqual(merged['skills'], {'paths': list(dict.fromkeys([*paths, str(self.package / 'config/skills')])),
                                                   'urls': owner['skills']['urls']})
                self.assertEqual(merged['instructions'], ['owner.md', str(self.run_dir / 'devlyn-instructions.md')])
                self.assertEqual(merged['permission'], owner['permission'])
                self.assertEqual(plan['channels']['skills'], {'state': 'configured', 'mechanism': 'skills.paths', 'reasons': []})
                self.assertEqual(plan['channels']['overall'], 'configured')
                self.assertEqual(plan['channels']['invocation'], {
                    'kind': 'read-file', 'text': 'Read ' + str(self.package / 'config/skills/devlyn-ideate/SKILL.md')})
                self.assertNotIn('OPENCODE_CONFIG_DIR', plan['envPatch'])

    def test_opencode_native_skills_release_path_once(self):
        # Prediction: an already-selected release root is deduplicated, not treated as a competing skill source.
        ctx = self.context('opencode')
        root = str(self.package / 'config/skills')
        ctx['effectiveConfig'] = {'skillsPaths': [root, root]}
        plan = self.plan(ctx)
        self.assertEqual(json.loads(plan['envPatch']['OPENCODE_CONFIG_CONTENT'])['skills']['paths'], [root])
        self.assertEqual(plan['channels']['overall'], 'configured')

    def test_opencode_native_skills_unknown_paths_keep_catalog(self):
        # Prediction: absent/null effective paths preserve inline skills and the original partial catalog behavior.
        ctx = self.context('opencode')
        owner = {'skills': {'paths': ['relative/skills'], 'urls': ['https://example.com/skills']}}
        for extra in ({}, {'skillsPaths': None}):
            with self.subTest(extra=extra):
                ctx['effectiveConfig'] = {'inlineConfig': json.dumps(owner), **extra}
                plan = self.plan(ctx)
                self.assertEqual(json.loads(plan['envPatch']['OPENCODE_CONFIG_CONTENT'])['skills'], owner['skills'])
                self.assertEqual(plan['channels']['skills'], {'state': 'partial', 'mechanism': 'absolute-catalog',
                    'reasons': [{'code': 'skills-catalog', 'params': {}}]})
                self.assertEqual(plan['channels']['invocation']['kind'], 'read-file')
                self.assertEqual(plan['channels']['principles']['state'], 'configured')

    def test_opencode_known_selection_none_reports_inherited(self):
        # Prediction: disabling activation still reports effective release skills that cannot be selectively hidden.
        ctx = self.context('opencode')
        root = self.package / 'config/skills'
        ctx['effectiveConfig'] = {'skillsPaths': [str(root)]}
        for changes in ({'projectChoice': 'none'}, {'launchMode': 'resume', 'recordedRelease': None}):
            with self.subTest(changes=changes):
                plan = self.plan({**ctx, **changes})
                self.assertEqual(plan['channels']['inheritedDevlyn'],
                                 [str(root / name / 'SKILL.md') for name in ('devlyn-ideate', 'devlyn-engines')])
                self.assertEqual(plan['channels']['hide']['state'], 'partial')
                self.assertEqual(plan['envPatch'], {})
                self.assertEqual(plan['files'], [])

    def test_opencode_malformed_inline_skills(self):
        # Prediction: malformed inline skills fail closed before an effective-path overlay could mask them.
        ctx = self.context('opencode')
        for skills in (None, [], 'owner', True):
            with self.subTest(skills=skills):
                ctx['effectiveConfig'] = {'skillsPaths': [], 'inlineConfig': json.dumps({'skills': skills})}
                plan = self.plan(ctx)
                self.assertEqual(plan['envPatch'], {})
                self.assertEqual(plan['files'], [])
                for channel in ('principles', 'skills'):
                    self.assertEqual(plan['channels'][channel], {'state': 'partial', 'mechanism': None,
                        'reasons': [{'code': 'config-unreadable', 'params': {'field': 'inlineConfig.skills'}}]})

    def test_opencode_native_skills_collision_keeps_catalog(self):
        # Prediction: collisions in effective paths (relative to cwd) or supplied roots prevent the native overlay.
        root = self.project / 'owner-skills'
        skill = root / 'devlyn-ideate'
        skill.mkdir(parents=True)
        (skill / 'SKILL.md').write_text('---\nname: devlyn-ideate\ndescription: owner\n---\nOwner')
        for effective_path in (str(root), 'owner-skills', None):
            with self.subTest(effective_path=effective_path):
                ctx = self.context('opencode')
                owner = {'skills': {'paths': ['/inline-owner'], 'urls': ['https://example.com/skills']}}
                ctx['effectiveConfig'] = {'inlineConfig': json.dumps(owner),
                                          'skillsPaths': [effective_path] if effective_path else []}
                if effective_path is None:
                    ctx['skillRoots'] = [str(root)]
                plan = self.plan(ctx)
                self.assertEqual(json.loads(plan['envPatch']['OPENCODE_CONFIG_CONTENT'])['skills'], owner['skills'])
                self.assertEqual(plan['channels']['skills'], {'state': 'partial', 'mechanism': 'absolute-catalog',
                    'reasons': [{'code': 'name-collision', 'params': {'name': 'devlyn-ideate', 'path': str(skill / 'SKILL.md')}},
                                {'code': 'skills-catalog', 'params': {}}]})
                self.assertEqual(plan['channels']['invocation']['kind'], 'read-file')

    @unittest.skipIf(os.name == 'nt', 'symlink fixture needs POSIX privileges')
    def test_opencode_native_skills_inspection_error_keeps_catalog(self):
        # Prediction: an uninspectable effective skill source reports its error and prevents the native overlay.
        root = self.project / 'owner-skills'
        root.mkdir()
        (root / 'devlyn-ideate').symlink_to(self.case / 'missing', target_is_directory=True)
        ctx = self.context('opencode')
        ctx['effectiveConfig'] = {'skillsPaths': ['owner-skills']}
        plan = self.plan(ctx)
        self.assertNotIn('skills', json.loads(plan['envPatch']['OPENCODE_CONFIG_CONTENT']))
        self.assertEqual(plan['channels']['skills']['state'], 'partial')
        self.assertEqual([r['code'] for r in plan['channels']['skills']['reasons']],
                         ['name-collision', 'config-unreadable', 'skills-catalog'])

    def test_session_channel_effective_config_validation(self):
        # Prediction: invalid types/NULs fail closed instead of injecting either session channel.
        for engine, key, values in [('copilot', 'instructionsDirs', [[], {}, 1, 'bad\0path']),
                                    ('opencode', 'skillsPaths', ['', {}, 1, [None], ['bad\0path']])]:
            for value in values:
                with self.subTest(engine=engine, value=value):
                    ctx = self.context(engine)
                    ctx['effectiveConfig'] = {key: value}
                    plan = self.plan(ctx)
                    self.assertEqual(plan['envPatch'], {})
                    self.assertEqual(plan['files'], [])
                    self.assertEqual(plan['channels']['skills']['reasons'],
                                     [{'code': 'config-unreadable', 'params': {'field': 'effectiveConfig'}}])

    def test_copilot_append_and_kimi_wrapper(self):
        ctx = self.context('copilot')
        ctx['effectiveConfig'] = {'skillsDirs': '/owner one,/owner two'}
        plan = self.plan(ctx)
        self.assertEqual(plan['envPatch']['COPILOT_SKILLS_DIRS'], '/owner one,/owner two,' + str(self.package / 'config/skills'))
        ctx = self.context('kimi')
        plan = self.plan(ctx)
        self.assertTrue(plan['files'][0]['utf8'].startswith('${base_prompt}\n\n'))
        ctx['effectiveConfig']['ownerAgent'] = True
        plan = self.plan(ctx)
        self.assertEqual(plan['files'], [])
        self.assertEqual(plan['engineArgs'], [])

    def test_initial_task_is_preserved_and_never_synthesized(self):
        for engine in ('antigravity', 'cursor'):
            ctx = self.context(engine)
            self.assertIsNone(self.plan(ctx)['prompt'])
            for transport in ('argv', 'stdin'):
                task = 'Task "quotes" \\ 한국어\n끝'
                ctx['initialPrompt'] = {'text': task, 'transport': transport}
                plan = self.plan(ctx)
                self.assertTrue(plan['prompt']['text'].endswith('\n\n' + task))
                self.assertEqual(plan['prompt']['transport'], transport)
                self.assertEqual(plan['channels']['overall'], 'partial')

    def test_projection_regular_idempotent_and_marker(self):
        original = self.account / 'config.toml'
        original.write_text('# owner\n[features]\nowner = true\n')
        first = self.sync()
        before = snapshot(self.account)
        second = self.sync()
        self.assertTrue(first['created'])
        self.assertFalse(second['created'])
        self.assertEqual(snapshot(self.account), before)
        root = Path(first['projectionRoot'])
        self.assertFalse(root.is_symlink())
        self.assertFalse(any(p.is_symlink() for p in root.rglob('*')))
        marker = root / '.devlyn-harness-projection.json'
        self.assertEqual(json.loads(marker.read_bytes()), {'schemaVersion': 1, 'release': self.release, 'source': 'native/codex/plugins/devlyn'})
        self.assertEqual(first['markerSha256'], hashlib.sha256(marker.read_bytes()).hexdigest())

    def test_runtime_paths_cannot_write_inside_release(self):
        ctx = self.context('claude')
        ctx['runDir'] = str(self.package / 'new-run')
        self.assertEqual(self.plan(ctx, code=2)['code'], 'invalid-arguments')
        self.assertEqual(self.sync(code=2, account=self.package)['code'], 'invalid-arguments')

    def test_projection_conflict_preserves_bytes_and_plan_falls_back(self):
        root = Path(self.sync()['projectionRoot'])
        (root / 'skills/devlyn-ideate/SKILL.md').write_text('owner change')
        before = snapshot(self.account)
        self.assertEqual(self.sync(code=3)['code'], 'name-collision')
        self.assertEqual(snapshot(self.account), before)
        plan = self.plan(self.context())
        self.assertIsNone(plan['machineSync'])
        self.assertEqual(plan['channels']['skills']['state'], 'partial')

    def test_projection_extra_file_empty_directory_and_marker_conflict(self):
        root = Path(self.sync()['projectionRoot'])
        for name, is_dir in [('owner.txt', False), ('empty-owner-dir', True), ('.devlyn-harness-projection.json', False)]:
            with self.subTest(name=name):
                file = root / name
                previous = file.read_bytes() if file.exists() else None
                file.mkdir() if is_dir else file.write_text('owner content')
                before = snapshot(self.account)
                self.assertEqual(self.sync(code=3)['code'], 'name-collision')
                self.assertEqual(snapshot(self.account), before)
                if previous is not None:
                    file.write_bytes(previous)
                elif is_dir:
                    file.rmdir()
                else:
                    file.unlink()

    @unittest.skipIf(os.name == 'nt', 'symlink fixture needs POSIX privileges; Windows argv is separate')
    def test_projection_rejects_link_and_hardlink(self):
        root = Path(self.sync()['projectionRoot'])
        moved = self.case / 'projection'
        root.rename(moved)
        root.symlink_to(moved, target_is_directory=True)
        self.assertEqual(self.sync(code=3)['code'], 'name-collision')
        root.unlink()
        moved.rename(root)
        marker = root / '.devlyn-harness-projection.json'
        os.link(marker, self.case / 'hardlink')
        self.assertEqual(self.sync(code=3)['code'], 'name-collision')

    def test_account_home_matches_finalized_environment(self):
        ctx = self.context()
        ctx['accountHome'] = str(self.home)
        self.assertEqual(self.plan(ctx, code=2)['code'], 'config-unreadable')
        ctx['accountHome'] = str(self.account)
        self.assertEqual(self.plan(ctx)['machineSync']['accountHome'], str(self.account))
        if os.name != 'nt':
            alias = self.case / 'account-parent-alias'
            alias.symlink_to(self.case, target_is_directory=True)
            ctx['accountHome'] = str(alias / self.account.name)
            self.assertEqual(self.plan(ctx)['machineSync']['accountHome'], ctx['accountHome'])

    def test_none_hides_only_verified_registered_plugin(self):
        self.sync()
        market = 'devlyn-harness-v' + self.release['version'].replace('.', '-')
        key = 'devlyn@' + market
        ctx = self.context()
        ctx['projectChoice'] = 'none'
        ctx['effectiveConfig'] = {'marketplaces': {market: {'source_type': 'local', 'source': str(self.package / 'native/codex')}},
                                  'plugins': {key: {'enabled': True}, 'owner@elsewhere': {'enabled': True}}}
        plan = self.plan(ctx)
        self.assertEqual(self.overrides(plan)['plugins'], {key: {'enabled': False}, 'owner@elsewhere': {'enabled': True}})
        self.assertIn(key, plan['channels']['inheritedDevlyn'])
        ctx['projectChoice'] = 'devlyn'
        self.assertTrue(self.overrides(self.plan(ctx))['plugins'][key]['enabled'])
        ctx['projectChoice'] = 'none'
        root = Path(self.sync()['projectionRoot'])
        (root / '.devlyn-harness-projection.json').unlink()
        self.assertEqual(self.plan(ctx)['engineArgs'], [], 'name alone must never authorize suppression')

    def test_projection_occupied_publication_lock_is_visible(self):
        market = 'devlyn-harness-v' + self.release['version'].replace('.', '-')
        parent = self.account / 'plugins/cache' / market / 'devlyn'
        parent.mkdir(parents=True)
        lock = parent / ('.' + self.release['version'] + '.lock')
        lock.write_text('owner or interrupted publisher')
        before = snapshot(self.account)
        self.assertEqual(self.sync(code=3)['code'], 'name-collision')
        self.assertEqual(snapshot(self.account), before)

    def test_discovery_stops_at_repository_boundary(self):
        root = self.case / '.agents/skills'
        shutil.copytree(self.package / 'config/skills/devlyn-ideate', root / 'devlyn-ideate')
        ctx = self.context()
        ctx['projectChoice'] = 'none'
        self.assertEqual(self.plan(ctx)['engineArgs'], [])
        ctx['skillRoots'] = [str(root)]
        self.assertIn('skills', self.overrides(self.plan(ctx)))

    def test_status_uses_same_engine_status_without_writes(self):
        ctx = self.context()
        expected = self.plan(ctx)['channels']
        file = self.case / 'status-context.json'
        file.write_text(json.dumps(ctx))
        before = snapshot(self.case)
        result = run(['node', self.cli, 'status', '--project', self.project, '--engine', 'codex', '--context-file', file, '--json'], env=self.env)
        self.assertEqual(json.loads(result.stdout)['data']['engines'], [expected])
        self.assertEqual(snapshot(self.case), before)
        result = run(['node', self.cli, 'status', '--project', self.project, '--engine', 'claude', '--context-file', file, '--json'], env=self.env, code=2)
        self.assertEqual(json.loads(result.stdout)['error']['code'], 'invalid-arguments')

    def test_windows_argv_and_toml_fixture(self):
        values = ['C:\\Users\\한 글\\release', '\\\\server\\share name\\run', 'quotes " and apostrophe \'',
                  'trailing\\', 'line\n두', '$HOME `not executed` $(not executed)']
        script = '''const path = require('path');
const {toml, skillCatalog} = require(process.argv[1]);
const {projectionPath} = require(process.argv[2]);
const values = JSON.parse(process.argv[3]);
process.stdout.write(JSON.stringify({values, toml: toml(values),
 catalog: skillCatalog({root:values[0]}, path.win32),
 projection: projectionPath({version:'4.2.25'},values[1],path.win32)}));'''
        result = run(['node', '-e', script, self.package / 'bin/harness-activation.js', self.package / 'bin/codex-projection.js', json.dumps(values)], env=self.env)
        data = json.loads(result.stdout)
        self.assertEqual(data['values'], values)
        self.assertEqual(tomllib.loads('value=' + data['toml'])['value'], values)
        self.assertIn(values[0] + '\\config\\skills\\_shared', data['catalog'])
        self.assertTrue(data['projection'].startswith(values[1] + '\\plugins\\cache\\'))

    def test_omp_adapter_is_explicitly_ineligible(self):
        adapter = (self.package / 'config/skills/_shared/adapters/omp.md').read_text()
        self.assertIn('\nexecutor: no\n', adapter)

    def test_codex_native_inactive_selected_inactive(self):
        if not CODEX:
            self.skipTest('opt in with --codex-probe; no model calls')
        version = run([CODEX, '--version'], env=self.env).stdout.decode().strip()
        self.assertEqual(version, 'codex-cli 0.163.0', 'native probe is qualified for the examined generation')
        # Same structure as astra-lab/engine-native/probe-codex-final.py.
        market = self.case / 'owner-market'
        (market / '.agents/plugins').mkdir(parents=True)
        (market / '.agents/plugins/marketplace.json').write_text(json.dumps({'name': 'owner', 'plugins': [
            {'name': 'unrelated', 'source': {'source': 'local', 'path': './plugins/unrelated'}}]}))
        plugin = market / 'plugins/unrelated'
        (plugin / '.codex-plugin').mkdir(parents=True)
        (plugin / '.codex-plugin/plugin.json').write_text(json.dumps({'name': 'unrelated', 'version': '0.0.1', 'skills': './skills/'}))
        skill = plugin / 'skills/owner-skill'
        skill.mkdir(parents=True)
        (skill / 'SKILL.md').write_text('---\nname: owner-skill\ndescription: OWNER_PLUGIN_MARKER\n---\nOwner\n')
        shutil.copytree(plugin, self.account / 'plugins/cache/owner/unrelated/0.0.1')
        config = self.account / 'config.toml'
        config.write_text('developer_instructions="OWNER_DEVELOPER_MARKER"\n[marketplaces.owner]\nsource_type="local"\nsource='
                          + json.dumps(str(market)) + '\n[plugins."unrelated@owner"]\nenabled=true\n')
        original = config.read_bytes()
        self.sync()
        ctx = self.context()
        ctx['effectiveConfig'] = {'developer_instructions': 'OWNER_DEVELOPER_MARKER',
                                  'marketplaces': {'owner': {'source_type': 'local', 'source': str(market)}},
                                  'plugins': {'unrelated@owner': {'enabled': True}}}
        selected = self.plan(ctx)
        ctx['projectChoice'] = 'none'
        inactive = self.plan(ctx)
        for label, plan, expected in [('inactive-before', inactive, False), ('selected', selected, True), ('inactive-after', inactive, False)]:
            env = {**self.env, **plan['envPatch']}
            result = run([CODEX, 'debug', 'prompt-input', *plan['engineArgs'], 'model-free inspection'], cwd=self.project, env=env)
            rendered = result.stdout.decode()
            (self.case / (label + '.json')).write_bytes(result.stdout)
            self.assertIn('OWNER_PLUGIN_MARKER', rendered)
            self.assertIn('OWNER_DEVELOPER_MARKER', rendered)
            self.assertEqual('devlyn:devlyn-ideate' in rendered, expected)
            self.assertEqual('The following Devlyn instructions are defaults' in rendered, expected)
            self.assertEqual(config.read_bytes(), original)
            print(f'Codex {label}: managed={expected}, owner plugin=true, owner developer=true, config unchanged=true', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('--package-root', type=Path)
    parser.add_argument('--codex-probe', action='store_true')
    args, remaining = parser.parse_known_args()
    if args.package_root:
        PACKAGE_ROOT = args.package_root.resolve()
    if args.codex_probe:
        CODEX = shutil.which('codex')
        if not CODEX:
            parser.error('--codex-probe requires codex on PATH')
    unittest.main(argv=[__file__, *remaining])
