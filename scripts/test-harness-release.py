#!/usr/bin/env python3
"""Model-free release/inspection fixtures, including real npm pack → extract → verify.

Use TMPDIR for fixture output. --package-root exercises an already extracted package.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import runpy
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import tempfile
import unittest
from types import SimpleNamespace
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
PACKAGE_ROOT = None
NODE = shutil.which('node')
PREFIX = ('The following Devlyn instructions are defaults for this session. Applicable explicit user instructions '
          'and native owner/project instructions take precedence over these defaults. This delegation applies only '
          'to the Devlyn defaults below; it does not change other engine instructions or permissions.\n\n')


def environment():
    env = {k: v for k, v in os.environ.items() if not k.startswith(('GIT_', 'DEVLYN_'))}
    env.update(GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM='1', PYTHONDONTWRITEBYTECODE='1')
    return env


def run(argv, *, cwd=None, env=None, code=0):
    result = subprocess.run([str(arg) for arg in argv], cwd=cwd, env=env or environment(),
                            stdin=subprocess.DEVNULL, capture_output=True, timeout=120)
    if code is not None:
        assert result.returncode == code, (argv, result.returncode, result.stdout, result.stderr)
    return result


def snapshot(root):
    result = {}
    for file in sorted(root.rglob('*')):
        info = file.lstat()
        value = (info.st_mode, info.st_size, info.st_mtime_ns)
        if file.is_symlink():
            value += (os.readlink(file),)
        elif file.is_file():
            value += (hashlib.sha256(file.read_bytes()).hexdigest(),)
        result[str(file.relative_to(root))] = value
    return result


def resign(root):
    file = root / 'release.json'
    manifest = json.loads(file.read_bytes())
    manifest.pop('digest')
    digest = hashlib.sha256(json.dumps(manifest, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()).hexdigest()
    manifest['digest'] = {'algorithm': 'sha256', 'value': digest}
    file.write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    return manifest


class ReleaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix='devlyn-harness-')
        cls.work = Path(cls.temp.name).resolve()
        if PACKAGE_ROOT:
            cls.package = PACKAGE_ROOT
        else:
            npm = Path(shutil.which('npm')).resolve()
            command = [npm] if os.name != 'nt' else [shutil.which('node'), npm.parent / 'node_modules/npm/bin/npm-cli.js']
            packed = run([*command, 'pack', ROOT, '--json', '--pack-destination', cls.work,
                          '--cache', os.environ.get('npm_config_cache', str(cls.work / 'npm-cache'))])
            tarball = cls.work / json.loads(packed.stdout)[0]['filename']
            # postpack leaves the source checkout as it was: no release.json makes its skills read as a release.
            for generated in ('release.json', 'harness', 'native'):
                assert not (Path(ROOT) / generated).exists(), generated
            with tarfile.open(tarball) as archive:
                for member in archive.getmembers():
                    assert member.name.startswith('package/') and '..' not in Path(member.name).parts
                    assert member.isfile() or member.isdir(), member.name
                archive.extractall(cls.work, filter='data')
            cls.package = cls.work / 'package'
        checked = run(['node', cls.package / 'bin/devlyn.js', 'release', '--verify', '--root', cls.package, '--json'])
        cls.release = json.loads(checked.stdout)['data']['release']
        print(f"extracted release verified: {cls.release['version']} {cls.release['digest']}", flush=True)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def setUp(self):
        self.case = Path(tempfile.mkdtemp(prefix='case-', dir=self.work))

    def cli(self, *args, code=0, package=None, env=None):
        result = run([NODE, (package or self.package) / 'bin/devlyn.js', *args, '--json'], env=env, code=code)
        lines = result.stdout.splitlines()
        self.assertEqual(len(lines), 1, result.stdout)
        envelope = json.loads(lines[0])
        self.assertEqual(envelope['schemaVersion'], 1)
        self.assertEqual(envelope['ok'], result.returncode == 0)
        if result.returncode:
            self.assertTrue(result.stderr)
            self.assertIsInstance(envelope['error']['params'], dict)
        return envelope.get('data', envelope.get('error'))

    def copy(self):
        target = self.case / 'copy'
        shutil.copytree(self.package, target)
        return target

    def change_manifest(self, root, change):
        file = root / 'release.json'
        manifest = json.loads(file.read_bytes())
        change(manifest)
        file.write_text(json.dumps(manifest), encoding='utf-8')
        resign(root)

    def init_repo(self, root):
        root.mkdir()
        run(['git', 'init', '-q', root])
        run(['git', '-C', root, 'config', 'user.name', 'Fixture'])
        run(['git', '-C', root, 'config', 'user.email', 'fixture@example.invalid'])
        return root

    def commit(self, root):
        run(['git', '-C', root, 'add', '.'])
        run(['git', '-C', root, 'commit', '-qm', 'fixture'])

    def test_managed_node_verifies_release_without_path_node(self):
        # Prediction: DEVLYN_NODE runs the real verifier with no Node on PATH, including paths with spaces.
        node = self.case / "managed node" / Path(NODE).name
        node.parent.mkdir()
        shutil.copy2(NODE, node)
        script = "import runpy,sys; print(runpy.run_path(sys.argv[1])['verify_release'](sys.argv[2])['release']['digest'])"
        env = {**environment(), "PATH": str(self.case), "DEVLYN_NODE": str(node)}
        result = run([sys.executable, '-c', script, self.package / 'config/skills/_shared/harness-store.py', self.package], env=env)
        self.assertEqual(result.stdout.decode().strip(), self.release['digest'])

    def test_invalid_managed_node_is_explicit_and_never_falls_back(self):
        # Prediction: relative, empty, missing, directory and non-executable overrides are visible errors,
        # even when PATH contains a working Node.
        file = self.case / 'not-executable'
        file.write_text('not a program')
        values = ['', 'node', str(self.case / 'missing'), str(self.case)]
        if os.name != 'nt':
            values.append(str(file))
        script = "import runpy,sys; runpy.run_path(sys.argv[1])['verify_release'](sys.argv[2])"
        for value in values:
            with self.subTest(value=value):
                result = run([sys.executable, '-c', script, self.package / 'config/skills/_shared/harness-store.py', self.package],
                             env={**environment(), 'DEVLYN_NODE': value}, code=None)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(b'DEVLYN_NODE must be an absolute path to an executable file', result.stderr)

    def test_project_and_engine_commands_keep_the_sessions_node(self):
        # Prediction: DEVLYN_NODE runs devlyn-cli's own scripts only; a project's node command and an npm .cmd shim
        # resolve Node as the platform does, so the app's choice never changes what a project check runs on.
        platform = runpy.run_path(str(self.package / 'config/skills/_shared/platform-support.py'))
        resolve = platform['native_argv']
        env = {**environment(), 'DEVLYN_NODE': NODE}
        with mock.patch.dict(os.environ, env, clear=True):
            if os.name != 'nt':  # Windows resolves the PATH executable itself.
                self.assertEqual(resolve(['node', '-v']), ['node', '-v'])
            shim = self.case / 'npm.cmd'
            shim.write_text('SET "NODE_EXE=%~dp0\\node.exe"\n'
                            'SET "NPM_CLI_JS=%~dp0\\npm-cli.js"\n'
                            '"%NODE_EXE%" "%NPM_CLI_JS%" %*\n')
            (self.case / 'npm-cli.js').write_text('// npm fixture')
            (self.case / 'node.exe').write_text('adjacent Node')
            simulated = SimpleNamespace(name='nt', environ=os.environ)
            with mock.patch.dict(resolve.__globals__, os=simulated), mock.patch('shutil.which', return_value=str(shim)):
                self.assertEqual(resolve(['npm', 'test']),
                                 [str(self.case / 'node.exe'), str(self.case / 'npm-cli.js'), 'test'])

    def test_derivation_and_native_manifests(self):
        template = (self.package / 'CLAUDE.md').read_text(encoding='utf-8')
        self.assertEqual(template, (self.package / 'AGENTS.md').read_text(encoding='utf-8'))
        self.assertNotIn('<!-- devlyn:instructions:begin', template)
        body = 'Project-specific instructions outside this managed block take precedence over these defaults.\n\n' + template.rstrip('\n') + '\n'
        digest = hashlib.sha256(body.encode()).hexdigest()
        self.assertEqual((self.package / 'config/skills/_shared/runtime-principles.md').read_bytes(), (PREFIX + template).encode())
        memory = f'<!-- devlyn:instructions:begin sha256={digest} -->\n{body}<!-- devlyn:instructions:end -->\n'
        for name in ['CLAUDE.md', 'AGENTS.md']:
            self.assertEqual((self.package / 'harness' / name).read_bytes(), memory.encode())
        for native in ['native/claude', 'native/codex/plugins/devlyn']:
            for file in (self.package / 'config/skills').rglob('*'):
                if file.is_file():
                    mirror = self.package / native / 'skills' / file.relative_to(self.package / 'config/skills')
                    self.assertEqual(file.read_bytes(), mirror.read_bytes())
                    self.assertEqual(bool(file.stat().st_mode & 0o111), bool(mirror.stat().st_mode & 0o111))
        for file in ['native/claude/.claude-plugin/plugin.json', 'native/codex/plugins/devlyn/.codex-plugin/plugin.json']:
            plugin = json.loads((self.package / file).read_bytes())
            self.assertEqual((plugin['name'], plugin['version']), ('devlyn', self.release['version']))
        market = json.loads((self.package / 'native/codex/.agents/plugins/marketplace.json').read_bytes())
        self.assertEqual(market['name'], 'devlyn-harness-v' + self.release['version'].replace('.', '-'))

    def test_digest_covers_every_file_and_mode(self):
        manifest = json.loads((self.package / 'release.json').read_bytes())
        files = {f['path']: f for f in manifest['files']}
        self.assertTrue(any(p.startswith('node_modules/') for p in files))
        self.assertEqual(set(files), {str(f.relative_to(self.package)).replace(os.sep, '/') for f in self.package.rglob('*') if f.is_file()} - {'release.json'})
        for name, entry in files.items():
            self.assertEqual(entry['sha256'], hashlib.sha256((self.package / name).read_bytes()).hexdigest())
        root = self.copy()
        self.assertEqual(resign(root)['digest'], manifest['digest'])
        self.cli('release', '--verify', '--root', root)

    def test_invalid_arguments_and_schema(self):
        for args in [('release',), ('release', '--verify'), ('release', '--build', '--verify'),
                     ('release', '--build', '--root', str(self.case)), ('release', '--verify', '--root', 'relative'),
                     ('status',), ('status', '--project', str(self.case), '--engine', 'made-up')]:
            with self.subTest(args=args):
                self.assertEqual(self.cli(*args, code=2)['code'], 'invalid-arguments')
        root = self.copy()
        self.change_manifest(root, lambda m: m.update(schemaVersion=2))
        self.assertEqual(self.cli('release', '--verify', '--root', root, code=3)['code'], 'release-schema')

    def test_corruption_missing_extra_and_modes(self):
        root = self.copy()
        file = root / 'bin/instructions.js'
        original = file.read_bytes()
        file.write_bytes(original + b'\n')
        self.assertEqual(self.cli('release', '--verify', '--root', root, code=1)['code'], 'release-file-digest-mismatch')
        file.unlink()
        self.assertEqual(self.cli('release', '--verify', '--root', root, code=1)['code'], 'release-file-list-mismatch')
        file.write_bytes(original)
        file.chmod((self.package / 'bin/instructions.js').stat().st_mode)
        extra = root / 'unexpected'
        extra.write_bytes(b'extra')
        self.assertEqual(self.cli('release', '--verify', '--root', root, code=1)['code'], 'release-file-list-mismatch')
        extra.unlink()
        if os.name != 'nt':
            file.chmod(file.stat().st_mode ^ 0o111)
            self.assertEqual(self.cli('release', '--verify', '--root', root, code=1)['code'], 'release-mode-mismatch')

    def test_unsafe_paths_duplicates_and_case_collisions(self):
        root = self.copy()
        original = (root / 'release.json').read_bytes()
        for unsafe in ['../escape', '/absolute', 'C:/escape', 'C:escape', '\\\\host\\share', '//host/share',
                       'bin\\escape', 'bin/../escape', 'bin//escape', 'bin/./escape', 'bin/name.',
                       'bin/name ', 'bin/CON', 'bin/nul.txt', 'bin/a:stream', 'bin/a\x00b']:
            with self.subTest(path=unsafe):
                (root / 'release.json').write_bytes(original)
                self.change_manifest(root, lambda m: m['files'][0].update(path=unsafe))
                self.assertEqual(self.cli('release', '--verify', '--root', root, code=1)['code'], 'release-unsafe-path')
        for added, expected in [('AGENTS.md', 'release-duplicate-path'), ('agents.md', 'release-case-collision'),
                                ('BIN/extra', 'release-case-collision'), ('bin/devlyn.js/extra', 'release-path-conflict')]:
            (root / 'release.json').write_bytes(original)
            self.change_manifest(root, lambda m: m['files'].append(dict(m['files'][0], path=added)))
            self.assertEqual(self.cli('release', '--verify', '--root', root, code=1)['code'], expected)
        for first, second in [('bin/Straße', 'bin/STRASSE'), ('bin/café', 'bin/cafe\u0301')]:
            (root / 'release.json').write_bytes(original)
            self.change_manifest(root, lambda m: m['files'].extend([dict(m['files'][0], path=p) for p in [first, second]]))
            self.assertEqual(self.cli('release', '--verify', '--root', root, code=1)['code'], 'release-case-collision')

    def test_build_rejects_divergent_templates_and_links_before_generation(self):
        root = self.copy()
        before = snapshot(root / 'native')
        agents = root / 'AGENTS.md'
        original = agents.read_bytes()
        agents.write_bytes(original + b'changed\n')
        self.assertEqual(self.cli('release', '--build', package=root, code=1)['code'], 'release-template-mismatch')
        self.assertEqual(snapshot(root / 'native'), before)
        agents.write_bytes(original)
        if os.name != 'nt':
            link = root / 'bin/hidden-by-npm.js'
            link.symlink_to(root / 'bin/devlyn.js')
            self.assertEqual(self.cli('release', '--build', package=root, code=1)['code'], 'release-unsafe-entry')
            self.assertEqual(snapshot(root / 'native'), before)

    def test_resigned_mirror_tampering_still_fails_derivation(self):
        root = self.copy()
        name = 'native/claude/skills/_shared/runtime-principles.md'
        file = root / name
        file.write_bytes(file.read_bytes().replace(b'## Quick Start', b'## Removed Quick Start'))
        def alter(m):
            next(f for f in m['files'] if f['path'] == name)['sha256'] = hashlib.sha256(file.read_bytes()).hexdigest()
        self.change_manifest(root, alter)
        self.assertEqual(self.cli('release', '--verify', '--root', root, code=1)['code'], 'release-generated-mismatch')

    @unittest.skipIf(os.name == 'nt', 'POSIX links/FIFO; native Windows qualification is separate')
    def test_links_hardlinks_special_files_and_linked_roots(self):
        root = self.copy()
        file = root / 'bin/instructions.js'
        original = file.read_bytes()
        outside = self.case / 'outside'
        outside.write_bytes(original)
        before = snapshot(self.case)
        file.unlink()
        file.symlink_to(outside)
        self.assertEqual(self.cli('release', '--verify', '--root', root, code=1)['code'], 'release-unsafe-entry')
        file.unlink()
        os.link(outside, file)
        self.assertEqual(self.cli('release', '--verify', '--root', root, code=1)['code'], 'release-unsafe-entry')
        file.unlink()
        os.mkfifo(file)
        self.assertEqual(self.cli('release', '--verify', '--root', root, code=1)['code'], 'release-unsafe-entry')
        file.unlink()
        file.write_bytes(original)
        linked = self.case / 'linked'
        linked.symlink_to(root, target_is_directory=True)
        self.assertEqual(self.cli('release', '--verify', '--root', linked, code=1)['code'], 'release-unsafe-entry')
        store_link = self.case / 'store-link'
        store_link.symlink_to(root, target_is_directory=True)
        self.assertEqual(self.cli('release', '--materialize', '--source', self.package, '--store', store_link / 'child', code=1)['code'], 'release-unsafe-entry')
        self.assertEqual(snapshot(self.case)['outside'], before['outside'])

    def test_materialize_idempotent_and_same_version_conflict(self):
        store = self.case / 'store'
        first = self.cli('release', '--materialize', '--source', self.package, '--store', store)
        self.assertTrue(first['created'])
        self.assertEqual(Path(first['release']['root']), store / 'devlyn-cli' / self.release['version'])
        before = snapshot(store)
        second = self.cli('release', '--materialize', '--source', self.package, '--store', store)
        self.assertFalse(second['created'])
        self.assertEqual(snapshot(store), before)
        root = self.copy()
        changed = root / 'bin/devlyn.js'
        changed.write_bytes(changed.read_bytes() + b'\n// different payload\n')
        def alter(m):
            next(f for f in m['files'] if f['path'] == 'bin/devlyn.js')['sha256'] = hashlib.sha256(changed.read_bytes()).hexdigest()
        self.change_manifest(root, alter)
        self.cli('release', '--verify', '--root', root)
        self.assertEqual(self.cli('release', '--materialize', '--source', root, '--store', store, code=3)['code'], 'release-version-conflict')
        self.assertEqual(snapshot(store), before)

    def test_npm_installed_source_captures_only_release_payload(self):
        tarball = self.case / 'installed-source.tgz'
        with tarfile.open(tarball, 'w:gz') as archive:
            archive.add(self.package, arcname='package')
        npm = Path(shutil.which('npm')).resolve()
        command = [npm] if os.name != 'nt' else [NODE, npm.parent / 'node_modules/npm/bin/npm-cli.js']
        run([*command, 'install', '--prefix', self.case / 'install', '--offline', '--ignore-scripts', '--no-audit', '--no-fund',
             '--cache', os.environ.get('npm_config_cache', str(self.case / 'cache')), tarball])
        source = self.case / 'install/node_modules/devlyn-cli'
        self.assertTrue((source / 'node_modules/.bin/marked').exists())
        before = snapshot(source)
        result = self.cli('release', '--materialize', '--source', source, '--store', self.case / 'store')
        captured = Path(result['release']['root'])
        self.assertFalse((captured / 'node_modules/.bin').exists())
        self.cli('release', '--verify', '--root', captured)
        self.assertEqual(result['release']['digest'], self.release['digest'])
        self.cli('status', '--project', self.case, package=source)
        self.assertEqual(snapshot(source), before)
        (source / 'node_modules/.bin/unlisted').write_text('not npm scaffolding', encoding='utf-8')
        self.assertEqual(self.cli('release', '--materialize', '--source', source, '--store', self.case / 'other', code=1)['code'], 'release-file-list-mismatch')

    def test_materialize_failures_never_publish_partial_release(self):
        # Inject real IO failures at copying and rename; assertions observe the public destination.
        script = self.case / 'failure.cjs'
        script.write_text("""const assert = require('assert/strict'), fs = require('fs'), path = require('path');
const [pkg, store, phase] = process.argv.slice(2);
const release = require(path.join(pkg, 'bin/release.js'));
const mkdir = fs.mkdtempSync, write = fs.writeFileSync;
let staging;
fs.mkdtempSync = (...args) => { staging = mkdir(...args); return staging; };
fs.writeFileSync = (file, ...args) => {
  if (phase === 'copy' && staging && file.startsWith(staging)) throw Object.assign(new Error('injected write failure'), {code:'EIO'});
  return write(file, ...args);
};
fs.renameSync = (...args) => { assert.equal(fs.existsSync(args[1]), false); throw Object.assign(new Error('injected rename failure'), {code:'EIO'}); };
assert.throws(() => release.materializeRelease(pkg, store), /injected/);
assert.deepEqual(fs.readdirSync(path.join(store, 'devlyn-cli')), []);
""", encoding='utf-8')
        for phase in ['copy', 'rename']:
            run(['node', script, self.package, self.case / phase, phase])

    def test_concurrent_materialize(self):
        argv = ['node', str(self.package / 'bin/devlyn.js'), 'release', '--materialize', '--source', str(self.package),
                '--store', str(self.case / 'store'), '--json']
        workers = [subprocess.Popen(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=environment()) for _ in range(3)]
        results = []
        for worker in workers:
            stdout, stderr = worker.communicate(timeout=60)
            self.assertEqual(worker.returncode, 0, (stdout, stderr))
            results.append(json.loads(stdout)['data'])
        self.assertEqual(sum(r['created'] for r in results), 1)
        self.assertEqual(len({r['release']['digest'] for r in results}), 1)
        self.assertEqual(os.listdir(self.case / 'store/devlyn-cli'), [self.release['version']])

    def test_status_is_pure_including_home_release_queue_and_git(self):
        repo = self.init_repo(self.case / 'repo')
        (repo / 'AGENTS.md').write_bytes((self.package / 'harness/AGENTS.md').read_bytes())
        (repo / 'CLAUDE.md').write_text('@AGENTS.md\n', encoding='utf-8')
        self.commit(repo)
        queue = repo / '.git/devlyn-loops'
        queue.mkdir()
        (queue / 'queue.md').write_text('legacy unfinished queue\n', encoding='utf-8')
        (queue / 'harness.json').write_text('{invalid', encoding='utf-8')
        home = self.case / 'home'
        home.mkdir()
        env = environment()
        env.update(HOME=str(home), USERPROFILE=str(home), CODEX_HOME=str(home / '.codex'), CLAUDE_CONFIG_DIR=str(home / '.claude'))
        before = snapshot(self.case), snapshot(self.package)
        data = self.cli('status', '--project', repo, '--engine', 'codex', env=env)
        self.assertEqual((snapshot(self.case), snapshot(self.package)), before)
        self.assertEqual(data['repository']['root'], str(repo))
        self.assertFalse(data['repository']['sourceRepository'])
        agents = next(i for i in data['instructions'] if i['path'].endswith('AGENTS.md'))
        self.assertEqual((agents['ownership'], agents['committed'], agents['applicability']), ('current', True, 'unknown'))
        self.assertEqual(agents['applicableEngines'], [])
        self.assertNotIn('queue', data)
        self.assertNotIn('engines', data)
        self.assertEqual({r['name'] for r in data['requirements']}, {'node', 'python', 'git', 'git-bash', 'gh'})

    def test_status_source_repository_and_linked_worktree_identity(self):
        repo = self.init_repo(self.case / 'repo')
        (repo / 'package.json').write_text('{"name":"devlyn-cli"}', encoding='utf-8')
        (repo / 'bin').mkdir()
        (repo / 'bin/devlyn.js').write_text('// source', encoding='utf-8')
        self.commit(repo)
        worktree = self.case / 'worktree'
        run(['git', '-C', repo, 'worktree', 'add', '-qb', 'fixture', worktree])
        (worktree / 'package.json').unlink()
        first = self.cli('status', '--project', repo)
        second = self.cli('status', '--project', worktree)
        self.assertTrue(first['repository']['sourceRepository'])
        self.assertTrue(second['repository']['sourceRepository'])
        self.assertEqual(first['repository']['commonGitDir'], second['repository']['commonGitDir'])

    def test_instruction_ownership_and_uncommitted_edits(self):
        repo = self.init_repo(self.case / 'repo')
        agents = repo / 'AGENTS.md'
        original = (self.package / 'harness/AGENTS.md').read_bytes()
        agents.write_bytes(b'\xef\xbb\xbf' + original.replace(b'\n', b'\r\n'))
        self.commit(repo)
        data = self.cli('status', '--project', repo)['instructions'][0]
        self.assertEqual((data['ownership'], data['committed']), ('current', True))
        for content, expected in [(original + b'local edit\n', 'current'),
                                  (original.replace(b'Without a pin', b'With a pin'), 'modified'),
                                  (original + original, 'modified'), (b'# Owner rules\n', 'unowned'),
                                  (b'```md\n' + original + b'```\n', 'unowned')]:
            agents.write_bytes(content)
            data = self.cli('status', '--project', repo)['instructions'][0]
            self.assertEqual((data['ownership'], data['committed']), (expected, False))

    def test_committed_compares_raw_instruction_bytes(self):
        repo = self.init_repo(self.case / 'repo')
        agents = repo / 'AGENTS.md'
        for content in [b'# Owner rules\n\xff\x80\n', b'\xef\xbb\xbf# Owner rules\r\n']:
            with self.subTest(content=content):
                agents.write_bytes(content)
                self.commit(repo)
                data = self.cli('status', '--project', repo)
                self.assertTrue(data['instructions'][0]['committed'])
                if b'\xff' in content:
                    self.assertEqual(data['ownership'][0]['reasons'][0]['code'], 'instruction-encoding')
                agents.write_bytes(content + b'\x81')
                self.assertFalse(self.cli('status', '--project', repo)['instructions'][0]['committed'])

    def test_status_engine_ids_use_app_inventory(self):
        repo = self.init_repo(self.case / 'repo')
        self.cli('status', '--project', repo, '--engine', 'antigravity')
        self.assertEqual(self.cli('status', '--project', repo, '--engine', 'agy', code=2)['code'], 'invalid-arguments')

    def test_missing_requirements_are_visible_without_git(self):
        env = environment()
        empty = self.case / 'empty-path'
        empty.mkdir()
        env['PATH'] = str(empty)
        before = snapshot(self.case)
        result = self.cli('status', '--project', self.case, env=env)
        self.assertIsNone(result['repository'])
        for requirement in result['requirements']:
            if requirement['name'] != 'node':
                self.assertFalse(requirement['available'])
                self.assertTrue(requirement['reasons'])
        self.assertEqual(snapshot(self.case), before)

    def test_skill_ownership_summary_and_links(self):
        repo = self.init_repo(self.case / 'repo')
        skill = repo / '.agents/skills/devlyn-ideate'
        shutil.copytree(self.package / 'config/skills/devlyn-ideate', skill)
        data = self.cli('status', '--project', repo)
        self.assertEqual(data['ownership'][0]['proof'], 'current')
        (skill / 'owner-content').write_text('mine', encoding='utf-8')
        data = self.cli('status', '--project', repo)
        self.assertEqual(data['ownership'][0]['proof'], 'none')
        if os.name != 'nt':
            shutil.rmtree(repo / '.agents')
            (repo / '.agents').symlink_to(self.package, target_is_directory=True)
            before = snapshot(self.package)
            data = self.cli('status', '--project', repo)
            self.assertEqual(data['ownership'][0]['proof'], 'none')
            self.assertTrue(data['ownership'][0]['reasons'])
            self.assertEqual(snapshot(self.package), before)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('--package-root', type=Path)
    args, remaining = parser.parse_known_args()
    if args.package_root:
        PACKAGE_ROOT = args.package_root.resolve()
    unittest.main(argv=[__file__, *remaining])
