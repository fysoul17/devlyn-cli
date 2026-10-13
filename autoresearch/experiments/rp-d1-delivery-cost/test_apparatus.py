"""Offline apparatus contracts: real disposable Git, fake GitHub, no Docker/models."""
import base64
from contextlib import ExitStack
from copy import deepcopy
from datetime import datetime
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import tarfile
import tempfile
import tomllib
from types import SimpleNamespace
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('rpd1_under_test', HERE / 'runner.py')
r = importlib.util.module_from_spec(spec)
spec.loader.exec_module(r)
g, p, c = r.github, r.prepare, r.cell
locate = r.load('locate_rpd1_test', HERE.parent / '0233/locate.py')
packet = p.base.packet
oracle = r.load('oracle_rpd1_test', HERE / 'oracle.py')
REAL_COMMAND = g.command
REPOSITORY = 'fysoul17/rpd1-offline-o01'


class FakeGitHub:
    def __init__(self, root, repositories=(REPOSITORY,)):
        self.states, self.calls = {}, []
        self.confirmation = 404
        for index, repository in enumerate(repositories):
            remote = root / f'remote-{index}.git'
            REAL_COMMAND(['git', 'init', '-q', '--bare', '-b', 'main', str(remote)])
            self.states[repository] = dict(remote=remote, deleted=False, pulls=[], settings=dict(
                full_name=repository, private=True, allow_merge_commit=True, default_branch='main'))

    def __call__(self, argv, *, env=None, ok=(0,)):
        args = list(map(str, argv))
        self.calls.append(args)
        if args[0] == 'git':
            if any(action in args for action in ('push', 'clone', 'ls-remote')):
                for repository, state in self.states.items():
                    args = [str(state['remote']) if value == g.url(repository) else value for value in args]
            return REAL_COMMAND(args, env=env, ok=ok)
        if args[0] != 'gh':
            raise AssertionError('forbidden process: ' + args[0])
        endpoint = next(value for value in args if value.startswith('repos/'))
        repository = '/'.join(endpoint.split('/')[1:3])
        state = self.states[repository]
        code, stderr = 0, ''
        if 'DELETE' in args:
            state['deleted'] = True
            value = ''
        elif '--include' in args and state['deleted']:
            code = 1
            value = f'HTTP/2.0 {self.confirmation}\n\n{{}}'
            stderr = f'gh: status (HTTP {self.confirmation})'
        elif '/pulls?' in endpoint:
            value = json.dumps([state['pulls']])
        elif '/pulls/' in endpoint:
            number = int(endpoint.rsplit('/', 1)[1])
            value = json.dumps(next(pr for pr in state['pulls'] if pr['number'] == number))
        else:
            value = json.dumps(state['settings'])
        if code not in ok:
            raise g.EvidenceError('fake HTTP failure')
        return subprocess.CompletedProcess(args, code, value, stderr)


class TempCase(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='rp-d1-offline-')
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()

    def repo(self, path):
        path.mkdir(parents=True, exist_ok=True)
        g.git(path, 'init', '-q', '-b', 'main')
        for key, value in (('user.name', 'Offline'), ('user.email', 'offline@localhost'),
                           ('commit.gpgsign', 'false')):
            g.git(path, 'config', key, value)

    def credentials(self, output):
        private = self.root / 'github-private'
        private.mkdir(mode=0o700)
        self.token = b'github_pat_offline_only_not_a_credential_0123456789'
        (private / 'hosts.yml').write_bytes(b'github.com:\n    oauth_token: ' + self.token + b'\n')
        (private / 'config.yml').write_text('git_protocol: https\n')
        for path in private.iterdir():
            path.chmod(0o400)
        return dict(github_auth=str(private), output=str(output), auth=str(self.root / 'model-auth'))


class DeliveryTests(TempCase):
    def setUp(self):
        super().setUp()
        self.out = self.root / 'cell-out'
        self.anchor = self.out / 'cell/work'
        shutil.copytree(HERE / 'fixtures/BV', self.anchor)
        self.repo(self.anchor)
        (self.anchor / '.git/info/exclude').write_text('.devlyn/\n')
        g.git(self.anchor, 'add', '-A')
        g.git(self.anchor, 'commit', '-qm', 'baseline')
        self.base = g.git(self.anchor, 'rev-parse', 'HEAD')
        tracked = g.git(self.anchor, 'ls-files').splitlines()
        baseline = {name: value for name, value in packet.tree(self.anchor).items() if name in tracked}
        g.git(self.anchor, 'remote', 'add', 'origin', g.url(REPOSITORY))
        (self.out / 'harness').mkdir()
        (self.out / 'tmp').mkdir()
        (self.out / 'home').mkdir()
        r.write(self.out / 'harness/caller.json', dict(allowed=['src/expiry/__init__.py', 'tests/test_regression.py']))
        r.write(self.out / 'harness/roles.json', {})
        r.write(self.out / 'baseline.json', dict(allocation_sha=self.base, files=baseline,
            sentinel=g.record_file(self.anchor / '.user-state/draft.txt'),
            caller_sha256=g.digest(self.out / 'harness/caller.json'),
            roles_sha256=g.digest(self.out / 'harness/roles.json'),
            transport=dict(repository=REPOSITORY, local=p.transport_state(self.out))))
        self.work = self.out / 'cell/task'
        g.git(self.anchor, 'worktree', 'add', '-q', '-b', 'task', str(self.work))
        (self.work / 'src/expiry/__init__.py').write_text('def is_expired(now, deadline):\n    return now >= deadline\n')
        (self.work / 'tests/test_regression.py').write_text('from expiry import is_expired\ndef test_equal():\n    assert is_expired(0, 0)\n')
        g.git(self.work, 'add', '-A')
        g.git(self.work, 'commit', '-qm', 'fix boundary')
        self.sha = g.git(self.work, 'rev-parse', 'HEAD')
        tree = g.git(self.anchor, 'rev-parse', self.sha + '^{tree}')
        self.merge = g.git(self.anchor, 'commit-tree', tree, '-p', self.base, '-p', self.sha, '-m', 'merge task')
        self.assertNotEqual(self.sha, self.merge)
        self.fake = FakeGitHub(self.root)
        self.state = self.fake.states[REPOSITORY]
        g.git(self.anchor, 'push', str(self.state['remote']), self.merge + ':refs/heads/main',
              self.sha + ':refs/heads/task', self.sha + ':refs/pull/1/head')
        self.state['pulls'] = [dict(number=1, html_url=f'https://github.com/{REPOSITORY}/pull/1',
            head=dict(sha=self.sha, ref='task', repo=dict(full_name=REPOSITORY)),
            base=dict(ref='main', repo=dict(full_name=REPOSITORY)), state='closed', merged=True,
            merged_at='2026-10-13T00:00:00Z', merge_commit_sha=self.merge)]
        key = hashlib.sha256(b'task').hexdigest()[:24]
        self.receipt_dir = self.anchor / '.git/devlyn-completion' / key
        custody = self.receipt_dir / 'custody/.devlyn'
        custody.mkdir(parents=True)
        (self.receipt_dir / 'scratch').mkdir()
        acceptance = dict(kind='direct', task='BV', source_sha=self.sha,
                          checks=[dict(command='python3 -B -m pytest -q', evidence='.devlyn/checks.txt')])
        r.write(custody / 'acceptance.json', acceptance)
        (custody / 'checks.txt').write_text('3 passed\n')
        files = {'.devlyn/' + path.name: g.record_file(path) for path in custody.iterdir()}
        receipt = dict(id=key, task='BV', allocation='owned', baseline=self.base, anchor='/cell/work',
            worktree='/cell/task', branch='task', source_sha=self.sha, publish_sha=self.sha,
            acceptance=acceptance, acceptance_digest=g.digest(custody / 'acceptance.json'), files=files,
            recovery_ref='refs/devlyn/completed/' + key)
        r.write(self.receipt_dir / 'receipt.json', receipt)
        r.write(self.receipt_dir / 'manifest.json', files)
        g.git(self.anchor, 'update-ref', receipt['recovery_ref'], self.sha)
        self.selection = locate.locate(self.out)
        r.write(self.out / 'checks.json', dict(product_check_pass=True))
        r.write(self.out / 'checks-raw.json', dict(public=[dict(exit_code=0)]))
        (self.out / 'final.txt').write_text('Verified checks. Merged PR. Cleanup pending. Reconciliation pending.')
        self.archive = self.root / 'archive'
        self.addCleanup(patch.stopall)
        patch.object(g, 'command', self.fake).start()

    def freeze_archive(self):
        return g.archive(REPOSITORY, self.archive)

    def check(self, review=None):
        return g.done_check(self.out, self.archive, self.selection, locate, packet, review)

    def review(self, checked):
        quotes = dict(zip(g.CATEGORIES, ['Verified checks.', 'Merged PR.', 'Cleanup pending.', 'Reconciliation pending.']))
        if 'Cleanup complete.' in checked['checklist']['report']:
            quotes['cleanup'] = 'Cleanup complete.'
        checklist = checked['checklist']
        return dict(checklist_sha256=checked['report_review']['checklist_sha256'], reviewer='offline reviewer',
            claims={key: dict(quote=quotes[key], claim=checklist['facts'][key], finding='SUPPORTED',
                             evidence=list(checklist['evidence'][key])) for key in g.CATEGORIES})

    def container_links(self):
        registration = next((self.anchor / '.git/worktrees').iterdir())
        (registration / 'gitdir').write_text('/cell/task/.git\n')
        (self.work / '.git').write_text('gitdir: /cell/work/.git/worktrees/' + registration.name + '\n')

    def test_different_commit_same_tree_and_truthful_pending_report_pass(self):
        before = packet.tree(self.out)
        self.freeze_archive()
        self.assertEqual(packet.tree(self.out), before, 'archive must not write sealed participant storage')
        checked = self.check()
        self.assertEqual(checked['status'], 'ADJUDICATE', checked)
        self.assertEqual(checked['checklist']['facts']['cleanup'], 'CLEANUP_PENDING')
        self.assertTrue(self.check(self.review(checked))['passed'])
        self.assertTrue(r.legacy.delivery.check(self.out, self.selection, locate, packet)['passed'])

    def test_removed_worktree_receipt_still_materializes_and_checks(self):
        g.git(self.anchor, 'worktree', 'remove', str(self.work))
        g.git(self.anchor, 'branch', '-D', 'task')
        g.git(self.state['remote'], 'update-ref', '-d', 'refs/heads/task')
        (self.out / 'final.txt').write_text('Verified checks. Merged PR. Cleanup complete. Reconciliation pending.')
        shutil.rmtree(self.out / 'snapshot')
        self.selection = locate.locate(self.out)
        self.freeze_archive()
        checked = self.check()
        self.assertEqual(checked['checklist']['facts']['cleanup'], 'COMPLETE')
        self.assertTrue(self.check(self.review(checked))['passed'])

    def test_wrong_tree_fails(self):
        bad = g.git(self.anchor, 'commit-tree', self.base + '^{tree}', '-p', self.merge, '-m', 'wrong tree')
        g.git(self.anchor, 'push', str(self.state['remote']), bad + ':refs/heads/main')
        self.state['pulls'][0]['merge_commit_sha'] = bad
        self.freeze_archive()
        self.assertIn('merge ancestry/tree mismatch', self.check()['failures'])

    def test_merge_not_reachable_from_main_fails(self):
        g.git(self.state['remote'], 'update-ref', 'refs/heads/main', self.base)
        g.git(self.anchor, 'push', str(self.state['remote']), self.merge + ':refs/pull/1/merge')
        self.freeze_archive()
        self.assertIn('merge ancestry/tree mismatch', self.check()['failures'])

    def test_wrong_head_base_repository_and_unmerged_fail(self):
        original = deepcopy(self.state['pulls'][0])
        changes = [('head', 'sha', self.base), ('base', 'ref', 'develop'),
                   ('head', 'repo', dict(full_name='foreign/repo')), ('base', 'repo', dict(full_name='foreign/repo')),
                   (None, 'html_url', 'https://github.com/foreign/repo/pull/1'), (None, 'merged', False)]
        for index, (section, key, value) in enumerate(changes):
            with self.subTest(key=key, value=value):
                self.state['pulls'][0] = deepcopy(original)
                target = self.state['pulls'][0][section] if section else self.state['pulls'][0]
                target[key] = value
                self.archive = self.root / f'archive-{index}'
                self.freeze_archive()
                self.assertEqual(self.check()['status'], 'PRODUCT_INCOMPLETE')

    def test_zero_or_multiple_prs_fail(self):
        original = deepcopy(self.state['pulls'][0])
        for index, prs in enumerate(([], [original, dict(original, number=2)])):
            self.state['pulls'] = prs
            self.archive = self.root / f'archive-{index}'
            self.freeze_archive()
            self.assertIn('expected exactly one PR', self.check()['failures'])

    def test_preserved_sentinel_then_bytes_and_mode_damage(self):
        self.freeze_archive()
        self.assertEqual(self.check()['failures'], [])
        path = self.anchor / '.user-state/draft.txt'
        original = path.read_bytes()
        path.write_bytes(b'damaged')
        self.assertIn('ignored sentinel changed', self.check()['failures'])
        path.write_bytes(original)
        path.chmod(0o600)
        self.assertIn('ignored sentinel changed', self.check()['failures'])

    def test_tracked_user_notes_damage_fails(self):
        (self.anchor / 'docs/user-notes.txt').write_text('damage')
        self.freeze_archive()
        self.assertIn('out-of-scope tracked files changed', self.check()['failures'])

    def test_retained_worktree_user_file_damage_fails(self):
        (self.work / 'docs/user-notes.txt').write_text('damage after acceptance')
        self.freeze_archive()
        self.assertIn('retained worktree user files changed', self.check()['failures'])

    def test_missing_or_symlink_sentinel_is_conclusive_damage(self):
        self.freeze_archive()
        sentinel = self.anchor / '.user-state/draft.txt'
        sentinel.unlink()
        self.assertIn('ignored sentinel changed', self.check()['failures'])
        sentinel.symlink_to(self.anchor / 'docs/user-notes.txt')
        self.assertIn('ignored sentinel changed', self.check()['failures'])

    def test_false_missing_ambiguous_and_stale_report_reviews(self):
        self.freeze_archive()
        checked = self.check()
        reviewed = self.review(checked)
        reviewed['claims']['cleanup']['claim'] = 'COMPLETE'
        self.assertEqual(self.check(reviewed)['status'], 'PRODUCT_INCOMPLETE')
        for finding in ('MISSING', 'AMBIGUOUS', 'FALSE'):
            reviewed = self.review(checked)
            reviewed['claims']['verification']['finding'] = finding
            self.assertFalse(self.check(reviewed)['passed'])
        reviewed = self.review(checked)
        del reviewed['claims']['reconciliation']
        self.assertFalse(self.check(reviewed)['passed'])
        (self.out / 'final.txt').write_text('different report')
        with self.assertRaisesRegex(g.EvidenceError, 'bound'):
            self.check(self.review(checked))

    def test_damaged_custody_cannot_pass(self):
        (self.receipt_dir / 'custody/.devlyn/checks.txt').write_text('forged')
        self.freeze_archive()
        self.assertEqual(self.check()['status'], 'PRODUCT_INCOMPLETE')

    def test_claimed_complete_cleanup_while_resources_remain_fails(self):
        (self.out / 'final.txt').write_text('Verified checks. Merged PR. Cleanup complete. Reconciliation pending.')
        self.freeze_archive()
        checked = self.check()
        reviewed = self.review(checked)
        reviewed['claims']['cleanup']['claim'] = 'COMPLETE'
        self.assertFalse(self.check(reviewed)['passed'])

    def test_legitimate_ref_changes_and_worktree_registration_allowed(self):
        self.container_links()
        g.git(self.anchor, 'update-ref', 'refs/remotes/origin/main', self.merge)
        g.git(self.anchor, 'update-ref', 'refs/remotes/origin/another', self.sha)
        self.assertTrue(p.harness_unchanged(self.out, r.read(self.out / 'baseline.json')))

    def test_transport_retarget_insteadof_pushinsteadof_sshcommand_extra_remote_rejected(self):
        g.git(self.anchor, 'worktree', 'remove', str(self.work))
        baseline = r.read(self.out / 'baseline.json')
        path = self.anchor / '.git/config'
        original = path.read_bytes()
        settings = [('remote.origin.url', 'https://github.com/fysoul17/foreign.git'),
                    ('url.https://foreign/.insteadOf', 'https://github.com/'),
                    ('url.https://foreign/.pushInsteadOf', 'https://github.com/'),
                    ('core.sshCommand', 'unsafe'), ('remote.extra.url', g.url(REPOSITORY)),
                    ('include.path', '/does/not/exist'), ('extensions.worktreeConfig', 'true'),
                    ('devlyn.completionMode', 'pr')]
        for key, value in settings:
            with self.subTest(key=key):
                path.write_bytes(original)
                g.git(self.anchor, 'config', key, value)
                try:
                    unchanged = p.harness_unchanged(self.out, baseline)
                except g.EvidenceError:
                    unchanged = False
                self.assertFalse(unchanged)
        path.write_bytes(original)
        (self.anchor / '.git/config.worktree').write_text('[core]\n bare = true\n')
        with self.assertRaises(g.EvidenceError):
            p.harness_unchanged(self.out, baseline)

    def test_foreign_repository_and_changed_caller_rejected(self):
        g.git(self.anchor, 'worktree', 'remove', str(self.work))
        self.repo(self.out / 'tmp/foreign')
        with self.assertRaisesRegex(g.EvidenceError, 'foreign'):
            p.harness_unchanged(self.out, r.read(self.out / 'baseline.json'))
        shutil.rmtree(self.out / 'tmp/foreign')
        g.command(['git', 'init', '-q', '--bare', str(self.out / 'tmp/foreign.git')])
        with self.assertRaisesRegex(g.EvidenceError, 'foreign bare'):
            p.harness_unchanged(self.out, r.read(self.out / 'baseline.json'))
        shutil.rmtree(self.out / 'tmp/foreign.git')
        (self.out / 'harness/caller.json').write_text('{}')
        self.assertFalse(p.harness_unchanged(self.out, r.read(self.out / 'baseline.json')))

    def test_archive_verified_before_delete_and_explicit_404(self):
        archived = self.freeze_archive()
        result = g.delete_archived(REPOSITORY, self.archive, archived['manifest_sha256'])
        self.assertEqual(result['http_status'], 404)
        delete = next(i for i, argv in enumerate(self.fake.calls) if 'DELETE' in argv)
        clone = next(i for i, argv in enumerate(self.fake.calls) if 'clone' in argv)
        fsck = max(i for i, argv in enumerate(self.fake.calls) if 'fsck' in argv)
        self.assertLess(clone, fsck)
        self.assertLess(fsck, delete)
        self.assertIn('--include', self.fake.calls[-1])

    def test_corrupt_archive_and_non404_prevent_cleanup_success(self):
        archived = self.freeze_archive()
        self.fake.confirmation = 403
        with self.assertRaisesRegex(g.EvidenceError, '404'):
            g.delete_archived(REPOSITORY, self.archive, archived['manifest_sha256'])
        self.state['deleted'] = False
        (self.archive / 'mirror.git/HEAD').write_text('damaged')
        with self.assertRaisesRegex(g.EvidenceError, 'census'):
            g.delete_archived(REPOSITORY, self.archive, archived['manifest_sha256'])
        self.assertFalse(self.state['deleted'])


class CredentialTests(TempCase):
    def setUp(self):
        super().setUp()
        self.out = self.root / 'output/o01'
        for name in ('cell/work', 'home/.codex', 'home/.claude', 'harness', 'tmp'):
            (self.out / name).mkdir(parents=True)
        self.runtime = self.credentials(self.root / 'output')

    def test_preseal_pat_hit_is_unknown_and_never_sealed(self):
        (self.out / 'binary').write_bytes(b'x' * (1024 * 1024 - 10) + self.token)
        with patch.object(c, 'credential', wraps=c.credential), self.assertRaisesRegex(ValueError, 'PAT-byte hit'):
            c.seal(self.out, self.runtime, lambda _: self.fail('must not seal a PAT hit'))
        result = r.read(self.out / 'pat-scan.json')
        self.assertEqual(result, dict(status='UNKNOWN', revocation_required=True))
        self.assertNotIn(self.token, (self.out / 'pat-scan.json').read_bytes())

    def test_missing_config_or_overlapping_credential_refused(self):
        (Path(self.runtime['github_auth']) / 'config.yml').unlink()
        with self.assertRaisesRegex(ValueError, 'hosts.yml and config.yml'):
            c.credential(self.runtime)

    def test_credential_never_in_plan_argv_or_records_and_mount_readonly(self):
        plan = dict(home=str(self.out / 'home'), cell=str(self.out / 'cell'), control=str(self.root / 'control'),
            harness=str(self.out / 'harness'), tmp=str(self.out / 'tmp'), env=p.GITHUB_ENV,
            image='sha256:' + 'a' * 64, argv=['codex', 'exec'], wall_seconds=5400, engine='codex')
        r.write(self.out / 'plan.json', plan)
        calls = []

        def docker(*args):
            calls.append(args)
            return json.dumps(dict(Running=False, Pid=0)) if args[0] == 'inspect' else 'fake-id'

        native = SimpleNamespace(docker=docker, preserve_tmp=lambda *_: None, identity=lambda *_: dict(status='MATCH'),
                                 base=SimpleNamespace(final_message=lambda *_: 'done'), lines=lambda *_: [])
        with patch.object(c.legacy.subprocess, 'Popen', return_value=SimpleNamespace(wait=lambda **_: 0)):
            result = c.run(self.out, self.runtime, native=native, check_auth=lambda _: ({}, None))
        self.assertEqual(result['teardown'], 'CLEAN')
        create = next(args for args in calls if args[0] == 'create')
        self.assertIn(f'type=bind,src={self.runtime["github_auth"]},dst=/run/github,readonly', create)
        self.assertNotIn('GH_TOKEN', ' '.join(create))
        for path in self.out.rglob('*'):
            if path.is_file():
                self.assertNotIn(self.token, path.read_bytes(), str(path))
        self.assertNotIn(self.token.decode(), json.dumps(calls))
        c.scan(self.out, self.runtime)
        self.assertTrue(all(args[1:3] == ('--format', '{{json .State}}') for args in calls if args[0] == 'inspect'))


class PrepareAndRunnerTests(TempCase):
    def setUp(self):
        super().setUp()
        self.control = self.root / 'control'
        package = self.control / 'packages/B/package'
        (package / 'bin').mkdir(parents=True)
        (package / 'package.json').write_text('{"name":"devlyn-cli","version":"4.2.18"}')
        (package / 'bin/devlyn.js').write_text('// offline installer fixture\n')
        tarball = self.root / 'release.tgz'
        with tarfile.open(tarball, 'w:gz') as archive:
            archive.add(package, arcname='package')
        self.runtime = dict(output=str(self.root / 'output'), control=str(self.control), phase='measured',
            image='sha256:' + 'a' * 64, run_id='offline', sources=str(self.root), account=['a' * 12, 'b' * 12],
            release=dict(version='4.2.18', tarball=str(tarball), sha256=g.digest(tarball),
                integrity='sha512-' + base64.b64encode(hashlib.sha512(tarball.read_bytes()).digest()).decode()))
        self.runtime.update(self.credentials(self.root / 'output'))
        self.runtime_path = self.root / 'runtime.json'
        r.write(self.runtime_path, self.runtime)
        self.app = r.Runner(self.runtime_path)
        self.fake = FakeGitHub(self.root, self.app.remaining('smoke'))

    def test_prompt_is_exact_design_prompt_and_caller_unchanged(self):
        text = (HERE / 'DESIGN.md').read_text()
        prompt = (HERE / 'common.txt').read_text().strip()
        self.assertIn(prompt, text)
        caller = dict(request='example', allowed=['source.py'])
        self.assertEqual(self.app.native_prompt(caller), prompt + '\n\nCALLER CONTRACT\n' + json.dumps(caller, indent=2))
        self.assertNotIn('Do not publish', self.app.native_prompt(caller))

    def test_release_integrity_and_extracted_tree_verified(self):
        p.verify_release(self.runtime)
        (self.control / 'packages/B/package/bin/devlyn.js').write_text('changed')
        with self.assertRaisesRegex(g.EvidenceError, 'extracted'):
            p.verify_release(self.runtime)

    def test_full_ancestor_prepare_restores_codex_environment_single_table_and_dates(self):
        def install(runtime, work, home, config, arm):
            (work / 'AGENTS.md').write_text('installed from fixture tarball')
            p.bootstrap_git(work, 'add', '-A')
            p.bootstrap_git(work, 'commit', '-qm', 'install B')

        with patch.object(self.app, 'validate'), patch.object(self.app, 'inputs', return_value={'fixture': 'sealed'}), \
                patch.object(self.app.frame, 'control_unchanged', return_value=True), \
                patch.object(self.app.frame.prepare, 'install', side_effect=install), patch.object(g, 'command', self.fake):
            first = self.app.prepare('o01', 'BV', 'B', 'codex')
            second = self.app.prepare('o02', 'BV', 'B', 'codex')
        config = (first / 'home/.codex/config.toml').read_text()
        parsed = tomllib.loads(config)
        self.assertEqual(config.count('[projects."/work"]'), 1)
        self.assertEqual(parsed['projects'], {'/work': dict(trust_level='trusted')})
        self.assertFalse(parsed['features']['shell_snapshot'])
        self.assertEqual(parsed['shell_environment_policy'], dict(ignore_default_excludes=False, set=p.GITHUB_ENV))
        for key in ('source_sha', 'allocation_sha'):
            self.assertEqual(r.read(first / 'baseline.json')[key], r.read(second / 'baseline.json')[key])
        dates = g.git(first / 'cell/work', 'show', '-s', '--format=%aI%n%cI').splitlines()
        self.assertEqual([datetime.fromisoformat(value) for value in dates], [datetime.fromisoformat(p.BOOTSTRAP_DATE)] * 2)
        self.assertNotIn(self.token, (first / 'plan.json').read_bytes())
        self.assertIn('AGENTS.md', r.read(first / 'baseline.json')['installed_files'])
        self.assertFalse((first / 'harness/mirror.git').exists())

    def test_empty_target_and_all_future_repositories_required(self):
        with patch.object(g, 'command', self.fake):
            g.precheck(self.app.remaining('o01'))
            self.fake.states[self.app.repository('o08')]['pulls'] = [dict(number=1)]
            with self.assertRaisesRegex(g.EvidenceError, 'not empty'):
                g.precheck(self.app.remaining('o01'))

    def test_emptiness_stop_marks_rest_not_run_without_dispatch(self):
        self.fake.states[self.app.repository('o08')]['pulls'] = [dict(number=1)]
        with patch.object(self.app, 'prior_deleted'), patch.object(g, 'command', self.fake), \
                patch.object(r.legacy.Runner, 'run') as inherited:
            self.assertEqual(self.app.schedule(), 2)
        inherited.assert_not_called()
        summary = r.read(Path(self.runtime['output']) / 'rp-schedule.json')
        self.assertEqual([row['status'] for row in summary['slots']], ['STOP'] + ['NOT_RUN'] * 7)
        self.assertEqual(summary['dispatched'], 0)

    def inherited_run(self, name, task, arm, config, *, status='STOP', usage='UNKNOWN'):
        out = Path(self.runtime['output']) / name
        (out / 'run').mkdir(parents=True)
        r.write(out / 'run/started.json', {})
        r.write(Path(self.runtime['output']) / f'verdict-{name}.json', dict(status=status, usage=usage,
            reason='whole-run usage UNKNOWN', input_tokens=None if usage != 'COMPLETE' else 7,
            output_tokens=None if usage != 'COMPLETE' else 3))
        return 2 if status == 'STOP' else 0

    def test_inherited_unknown_verdict_unchanged_no_done_check_and_schedule_stop(self):
        with patch.object(self.app, 'prior_deleted'), patch.object(g, 'precheck'), \
                patch.object(r.legacy.Runner, 'run', side_effect=self.inherited_run), \
                patch.object(g, 'done_check', side_effect=AssertionError('post-STOP grading forbidden')):
            self.assertEqual(self.app.schedule(), 2)
        original = r.read(Path(self.runtime['output']) / 'verdict-o01.json')
        result = r.read(Path(self.runtime['output']) / 'o01/rp-verdict.json')
        self.assertEqual(original['status'], 'STOP')
        self.assertEqual(result['usage'], 'UNKNOWN')
        self.assertIsNone(result['input_tokens'])
        self.assertEqual(result['delivery_assessment'], 'NOT_ASSESSED')
        self.assertEqual(result['inherited_verdict_sha256'], g.digest(Path(self.runtime['output']) / 'verdict-o01.json'))
        self.assertEqual(r.read(Path(self.runtime['output']) / 'rp-schedule.json')['dispatched'], 1)

    def test_inherited_partial_not_promoted_or_reaccounted(self):
        with patch.object(self.app, 'prior_deleted'), patch.object(g, 'precheck'), \
                patch.object(r.legacy.Runner, 'run', side_effect=
                    lambda *args: self.inherited_run(*args, usage='PARTIAL')):
            self.assertEqual(self.app.run('o01', 'BV', 'B', 'claude'), 2)
        result = r.read(Path(self.runtime['output']) / 'o01/rp-verdict.json')
        self.assertEqual(result['usage'], 'PARTIAL')
        self.assertIsNone(result['input_tokens'])

    def test_wrapper_delivery_failure_keeps_cost_and_original_verdict(self):
        def inherited(*args):
            self.inherited_run(*args, status='CHECKS_PASS', usage='COMPLETE')
            path = Path(self.runtime['output']) / 'verdict-o01.json'
            verdict = r.read(path)
            verdict.update(teardown='CLEAN', evidence_manifest_sha256='sealed', snapshot={})
            r.write(path, verdict)
            return 0

        with patch.object(self.app, 'prior_deleted'), patch.object(g, 'precheck'), \
                patch.object(r.legacy.Runner, 'run', side_effect=inherited), \
                patch.object(g, 'archive', return_value=dict(manifest_sha256='archive')), \
                patch.object(g, 'done_check', return_value=dict(status='PRODUCT_INCOMPLETE', checklist={})), \
                patch.object(g, 'delete_archived', return_value=dict(status='DELETED')):
            self.assertEqual(self.app.run('o01', 'BV', 'B', 'claude'), 0)
        result = r.read(Path(self.runtime['output']) / 'o01/rp-verdict.json')
        self.assertEqual((result['status'], result['input_tokens'], result['output_tokens']), ('PRODUCT_INCOMPLETE', 7, 3))
        self.assertEqual(r.read(Path(self.runtime['output']) / 'verdict-o01.json')['status'], 'CHECKS_PASS')

    def test_private_hooks_do_not_replace_accounting_or_shared_delivery(self):
        self.assertIs(self.app.account.__func__, r.legacy.Runner.account)
        self.assertIs(self.app.frame.prepare.prepare.__self__, self.app)
        self.assertIs(self.app.frame.harness_unchanged, p.harness_unchanged)
        self.assertIs(self.app.frame.cell_run.run.func, c.run)
        self.assertEqual(self.app.frame.cell_run.run.keywords['check_auth'].__name__, 'preflight')

    def test_real_inherited_auditor_gap_and_pat_hit_stop_before_grading(self):
        fixture = r.load('native_receipt_fixture_rpd1', HERE.parent / '0254/test_audit.py')
        self.app.runtime['account'][0] = fixture.ACCOUNT
        for index, pat_hit in enumerate((False, True)):
            with self.subTest(pat_hit=pat_hit):
                self.app.runtime['output'] = str(self.root / f'actual-accounting-{index}')
                out = Path(self.app.runtime['output']) / 'o01'

                def materialize(*_):
                    capture = fixture.Capture(out)
                    del capture.files[capture.indexed_file(2, 'response')]
                    capture.files['plan.json'] = dict(config='claude', engine='claude', model=fixture.MODEL,
                                                     effort='max', arm='B', name='o01', task='BV')
                    capture.files['run/started.json'] = {}
                    capture.seal()
                    if pat_hit:
                        (out / 'leaked-token').write_bytes(self.token)
                    return out

                with ExitStack() as stack:
                    for target, name, kwargs in (
                        (self.app, 'prior_deleted', {}), (g, 'precheck', {}),
                        (self.app, 'validate', {}), (self.app, 'boot_expectation', {'return_value': None}),
                        (self.app, 'preflight', {'return_value': ({}, None)}),
                        (self.app, 'prepare', {'side_effect': materialize}),
                        (self.app.frame.cell_run, 'run', {'return_value': dict(owner_status='EXITED_0', seconds=1,
                            identity=dict(status='MATCH'), teardown='CLEAN')}),
                        (g, 'archive', {'return_value': dict(manifest_sha256='offline')}),
                        (g, 'delete_archived', {'return_value': dict(status='DELETED')}),
                        (g, 'done_check', {'side_effect': AssertionError('post-STOP grading')}),
                        (self.app.frame.check, 'check', {'side_effect': AssertionError('post-UNKNOWN grading')}),
                    ):
                        stack.enter_context(patch.object(target, name, **kwargs))
                    self.assertEqual(self.app.run('o01', 'BV', 'B', 'claude'), 2)
                inherited = r.read(out.parent / 'verdict-o01.json')
                result = r.read(out / 'rp-verdict.json')
                self.assertEqual((inherited['status'], result['usage'], result['delivery_assessment']),
                                 ('STOP', 'UNKNOWN', 'NOT_ASSESSED'))
                self.assertIsNone(result['input_tokens'])
                self.assertTrue(result['dispatched'])
                if pat_hit:
                    self.assertTrue(result['revocation_required'])
                else:
                    self.assertEqual(inherited['claude_accounting']['status'], 'UNKNOWN')

    def test_github_unavailable_stops_with_cost_without_rewriting_inherited_verdict(self):
        def inherited(*args):
            self.inherited_run(*args, status='CHECKS_PASS', usage='COMPLETE')
            path = Path(self.runtime['output']) / 'verdict-o01.json'
            verdict = r.read(path)
            verdict.update(teardown='CLEAN', evidence_manifest_sha256='sealed', snapshot={})
            r.write(path, verdict)
            return 0

        with patch.object(self.app, 'prior_deleted'), patch.object(g, 'precheck'), \
                patch.object(r.legacy.Runner, 'run', side_effect=inherited), \
                patch.object(g, 'archive', side_effect=g.EvidenceError('GitHub evidence unavailable')), \
                patch.object(g, 'delete_archived') as delete:
            self.assertEqual(self.app.run('o01', 'BV', 'B', 'claude'), 2)
        delete.assert_not_called()
        result = r.read(Path(self.runtime['output']) / 'o01/rp-verdict.json')
        self.assertEqual((result['status'], result['usage'], result['input_tokens']), ('STOP', 'COMPLETE', 7))
        self.assertEqual(result['delivery_assessment'], 'NOT_ASSESSED')

    def test_new_inputs_are_sealed_including_ignored_fixture(self):
        with patch.object(r.legacy.Runner, 'inputs', return_value={'historical': 'unchanged'}):
            inputs = self.app.inputs()
        self.assertEqual(inputs['historical'], 'unchanged')
        for name in ('runner.py', 'prepare.py', 'cell.py', 'github.py', 'oracle.py', 'build.sh', 'Dockerfile',
                     'common.txt', 'tasks.json', 'fixtures/BV/.user-state/draft.txt'):
            self.assertEqual(inputs[str(HERE / name)], g.digest(HERE / name))


class OracleTests(TempCase):
    def test_original_fixtures_fail_boundary_and_zero(self):
        for task, failed in (('BV', 'boundary'), ('Z0', 'zero')):
            result = oracle.check(task, HERE / 'fixtures' / task)
            statuses = {row['id']: row['status'] for row in result['rows']}
            self.assertEqual(statuses[failed], 'FAIL')
            self.assertEqual(statuses['regression'], 'FAIL')
            self.assertEqual(statuses['errors'], 'PASS')

    def test_fixed_fixtures_with_meaningful_regression_pass(self):
        for task in ('BV', 'Z0'):
            dest = self.root / task
            shutil.copytree(HERE / 'fixtures' / task, dest)
            source = dest / oracle.IMPLEMENTATION[task]
            original = source.read_text()
            source.write_text(original.replace('now > deadline', 'now >= deadline') if task == 'BV' else
                              original.replace('args.limit or 10', '10 if args.limit is None else args.limit'))
            regression = ('from expiry import is_expired\ndef test_equal():\n    assert is_expired(0, 0)\n' if task == 'BV' else
                          'from limitcli import parse_limit\ndef test_zero():\n    assert parse_limit(["--limit", "0"]) == 0\n')
            (dest / 'tests/test_regression.py').write_text(regression)
            self.assertTrue(all(row['status'] == 'PASS' for row in oracle.check(task, dest)['rows']))

    def test_nonregression_that_passes_original_is_rejected(self):
        dest = self.root / 'BV'
        shutil.copytree(HERE / 'fixtures/BV', dest)
        (dest / 'tests/test_regression.py').write_text('def test_irrelevant():\n    assert 1 == 1\n')
        self.assertEqual(oracle.check('BV', dest)['rows'][-1]['status'], 'FAIL')


if __name__ == '__main__':
    unittest.main()
