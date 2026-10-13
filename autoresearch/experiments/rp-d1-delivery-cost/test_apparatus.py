"""Offline apparatus contracts: real disposable Git, fake GitHub, no Docker/models."""
import base64
from contextlib import ExitStack
from copy import deepcopy
from datetime import datetime
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
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
        if code == 0 and 'DELETE' not in args:
            value = json.dumps(json.loads(value, object_hook=lambda row:
                dict(row, temp_clone_token=f'offline-clone-token-{len(self.calls)}')))
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

    def test_tracked_file_installer_permissions_pass(self):
        (self.anchor / 'docs/user-notes.txt').chmod(0o600)
        self.freeze_archive()
        checked = self.check()
        self.assertEqual(checked['failures'], [])
        self.assertTrue(self.check(self.review(checked))['passed'])

    def test_tracked_file_deletion_and_executable_change_fail(self):
        self.freeze_archive()
        path = self.anchor / 'docs/user-notes.txt'
        g.git(self.anchor, 'config', 'core.filemode', 'false')
        for mode in (0o744, 0o654, 0o645):
            with self.subTest(mode=oct(mode)):
                path.chmod(mode)
                self.assertIn('out-of-scope tracked files changed', self.check()['failures'])
        path.unlink()
        self.assertIn('out-of-scope tracked files changed', self.check()['failures'])

    def test_tracked_file_type_changes_fail(self):
        self.freeze_archive()
        path = self.anchor / 'docs/user-notes.txt'
        path.unlink()
        path.symlink_to(self.work / 'docs/user-notes.txt')
        self.assertIn('out-of-scope tracked files changed', self.check()['failures'])
        path.unlink()
        path.mkdir()
        self.assertIn('out-of-scope tracked files changed', self.check()['failures'])

    def test_index_flags_and_hidden_content_edits_fail(self):
        self.freeze_archive()
        name = 'docs/user-notes.txt'
        path = self.anchor / name
        original = path.read_bytes()
        for flags, tag in ((['--assume-unchanged'], 'h'), (['--skip-worktree'], 'S'),
                           (['--assume-unchanged', '--skip-worktree'], 's')):
            for edited in (False, True):
                with self.subTest(flags=flags, edited=edited):
                    g.git(self.anchor, 'update-index', '--no-assume-unchanged', '--', name)
                    g.git(self.anchor, 'update-index', '--no-skip-worktree', '--', name)
                    path.write_bytes(original)
                    for flag in flags:
                        g.git(self.anchor, 'update-index', flag, '--', name)
                    if edited:
                        path.write_text('hidden damage')
                    self.assertEqual(g.git(self.anchor, 'ls-files', '-v', '--', name), tag + ' ' + name)
                    self.assertEqual(g.git(self.anchor, 'diff', self.base, '--', name), '')
                    checked = self.check()
                    self.assertIn('out-of-scope tracked files changed', checked['failures'])
                    self.assertEqual(checked['checklist']['tracked_damage'], [name])

    def test_index_flag_on_new_out_of_scope_tracked_path_fails(self):
        name = 'docs/new notes\n.txt'
        (self.anchor / name).write_text('new user state')
        g.git(self.anchor, 'add', '--', name)
        g.git(self.anchor, 'update-index', '--assume-unchanged', '--', name)
        self.freeze_archive()
        self.assertEqual(self.check()['checklist']['tracked_damage'], [name])

    def test_index_flags_in_allowed_scope_pass(self):
        name = 'src/expiry/__init__.py'
        g.git(self.anchor, 'update-index', '--assume-unchanged', '--', name)
        g.git(self.anchor, 'update-index', '--skip-worktree', '--', name)
        self.freeze_archive()
        self.assertEqual(self.check()['failures'], [])

    def test_clean_filter_hidden_content_edit_fails(self):
        name = 'docs/user-notes.txt'
        (self.anchor / '.git/info/attributes').write_text(name + ' filter=hide-damage\n')
        g.git(self.anchor, 'config', 'filter.hide-damage.clean', f'git show {self.base}:{name}')
        (self.anchor / name).write_text('damage hidden by clean filter')
        self.assertEqual(g.git(self.anchor, 'diff', self.base, '--', name), '')
        self.freeze_archive()
        checked = self.check()
        self.assertIn('out-of-scope tracked files changed', checked['failures'])
        self.assertEqual(checked['checklist']['tracked_damage'], [name])

    def test_staged_damage_with_restored_working_file_fails(self):
        path = self.anchor / 'docs/user-notes.txt'
        original = path.read_bytes()
        path.write_text('staged damage')
        g.git(self.anchor, 'add', '--', 'docs/user-notes.txt')
        path.write_bytes(original)
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

    def test_changed_caller_rejected(self):
        (self.out / 'harness/caller.json').write_text('{}')
        self.assertFalse(p.harness_unchanged(self.out, r.read(self.out / 'baseline.json')))

    def test_rotating_clone_token_is_discarded_before_comparison_and_archive(self):
        self.state['settings']['parent'] = {'extra': [{'keep': 'settings metadata'}]}
        self.state['pulls'][0]['extra'] = [{'keep': 'pull metadata'}]
        for observe in (g.settings, g.pulls, g.observe):
            with self.subTest(observe=observe.__name__):
                first = observe(REPOSITORY)
                self.assertNotIn('temp_clone_token', json.dumps(first))
                self.assertEqual(first, observe(REPOSITORY))
        archived = self.freeze_archive()
        observed = g.read(self.archive / 'repository.json')
        self.assertNotIn('temp_clone_token', json.dumps(observed))
        self.assertEqual(observed['settings']['parent']['extra'], [{'keep': 'settings metadata'}])
        self.assertEqual(observed['pulls'][0]['extra'], [{'keep': 'pull metadata'}])
        for path in self.archive.rglob('*'):
            if path.is_file():
                self.assertNotIn(b'offline-clone-token-', path.read_bytes(), str(path))
        self.assertEqual(g.delete_archived(REPOSITORY, self.archive, archived['manifest_sha256'])['status'],
                         'DELETED')

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
        with self.assertRaisesRegex(ValueError, 'PAT-byte hit'):
            c.seal(self.out, self.runtime, lambda _: self.fail('must not seal a PAT hit'))
        result = r.read(self.out / 'pat-scan.json')
        self.assertEqual(result, dict(status='UNKNOWN', revocation_required=True))
        self.assertNotIn(self.token, (self.out / 'pat-scan.json').read_bytes())

    def test_unreadable_token_named_directory_records_unknown_without_path(self):
        directory = self.out / self.token.decode()
        directory.mkdir(mode=0)
        self.addCleanup(directory.chmod, 0o700)
        scandir = c.os.scandir

        def unreadable(path):
            if Path(path) == directory:
                raise PermissionError(13, 'Permission denied', str(directory))
            return scandir(path)

        # Inject the OS denial so this also exercises the path when tests run as root.
        with patch.object(c.os, 'scandir', side_effect=unreadable), self.assertRaises(ValueError) as raised:
            c.scan(self.out, self.runtime)
        self.assertEqual(str(raised.exception),
                         'PAT scan failed: UNKNOWN; owner must revoke PAT immediately; schedule stopped')
        self.assertEqual(r.read(self.out / 'pat-scan.json'), dict(status='UNKNOWN', revocation_required=True))
        self.assertNotIn(self.token, (self.out / 'pat-scan.json').read_bytes())
        self.assertNotIn(str(self.out), str(raised.exception))

    def test_nonregular_entry_records_unknown_without_path(self):
        c.os.mkfifo(self.out / self.token.decode())
        with self.assertRaises(ValueError) as raised:
            c.scan(self.out, self.runtime)
        self.assertNotIn(self.token.decode(), str(raised.exception))
        self.assertNotIn(str(self.out), str(raised.exception))
        self.assertEqual(r.read(self.out / 'pat-scan.json'), dict(status='UNKNOWN', revocation_required=True))

    def test_unreachable_git_blob_and_registered_worktree_objects_are_scanned(self):
        anchor = self.out / 'cell/work'
        self.repo(anchor)
        g.git(anchor, 'commit', '-qm', 'initial', '--allow-empty')
        worktree = self.out / 'tmp/task'
        g.git(anchor, 'worktree', 'add', '-q', '-b', 'task', str(worktree))
        registration = next((anchor / '.git/worktrees').iterdir())
        (registration / 'gitdir').write_text('/tmp/task/.git\n')
        (worktree / '.git').write_text('gitdir: /cell/work/.git/worktrees/' + registration.name + '\n')
        g.git(anchor, 'hash-object', '-w', str(Path(self.runtime['github_auth']) / 'hosts.yml'))
        self.assertTrue(all(self.token not in path.read_bytes() for path in self.out.rglob('*') if path.is_file()))
        with patch.object(c.subprocess, 'Popen', wraps=c.subprocess.Popen) as processes, \
                self.assertRaisesRegex(ValueError, 'PAT-byte hit'):
            c.scan(self.out, self.runtime)
        self.assertEqual({call.args[0][2] for call in processes.call_args_list},
                         {str(anchor / '.git'), str(registration)})
        self.assertEqual(r.read(self.out / 'pat-scan.json'), dict(status='UNKNOWN', revocation_required=True))

    def test_arbitrary_bare_git_blob_is_scanned_once_across_overlapping_roots(self):
        bare = self.out / 'tmp/cache.git'
        g.command(['git', 'init', '-q', '--bare', str(bare)])
        g.command(['git', '--git-dir', str(bare), 'hash-object', '-w',
                   str(Path(self.runtime['github_auth']) / 'hosts.yml')])
        self.assertTrue(all(self.token not in path.read_bytes() for path in self.out.rglob('*') if path.is_file()))
        for roots in ([self.out], [bare], [self.out, bare, bare / '..' / bare.name]):
            with self.subTest(roots=roots), \
                    patch.object(c.subprocess, 'Popen', wraps=c.subprocess.Popen) as processes, \
                    self.assertRaisesRegex(ValueError, 'PAT-byte hit'):
                c.scan(self.out, self.runtime, roots=roots)
            self.assertEqual([call.args[0][2] for call in processes.call_args_list], [str(bare)])
            self.assertEqual(r.read(self.out / 'pat-scan.json'), dict(status='UNKNOWN', revocation_required=True))

    def test_git_discovery_does_not_follow_symlinks(self):
        bare = self.root / 'external'
        g.command(['git', 'init', '-q', '--bare', str(bare)])
        g.git(bare, 'hash-object', '-w', str(Path(self.runtime['github_auth']) / 'hosts.yml'))
        (self.out / '.git').symlink_to(bare, target_is_directory=True)
        for linked in ('HEAD', 'objects'):
            candidate = self.out / linked
            candidate.mkdir()
            for name in ('HEAD', 'objects'):
                if name == linked:
                    (candidate / name).symlink_to(bare / name, target_is_directory=name == 'objects')
                elif name == 'HEAD':
                    (candidate / name).write_text('ref: refs/heads/main\n')
                else:
                    (candidate / name).mkdir()
        with patch.object(c.subprocess, 'Popen', wraps=c.subprocess.Popen) as processes:
            c.scan(self.out, self.runtime)
        processes.assert_not_called()
        self.assertFalse((self.out / 'pat-scan.json').exists())

    def test_archive_mirror_blob_is_scanned_without_changing_archive(self):
        archive = self.root / 'archive'
        mirror = archive / 'mirror.git'
        g.command(['git', 'init', '-q', '--bare', str(mirror)])
        g.git(mirror, 'hash-object', '-w', str(Path(self.runtime['github_auth']) / 'hosts.yml'))
        before = g.archive_files(archive)
        self.assertTrue(all(self.token not in path.read_bytes() for path in archive.rglob('*') if path.is_file()))
        with self.assertRaisesRegex(ValueError, 'PAT-byte hit'):
            c.scan(self.out, self.runtime, roots=[archive])
        self.assertEqual(g.archive_files(archive), before)
        self.assertEqual(r.read(self.out / 'pat-scan.json'), dict(status='UNKNOWN', revocation_required=True))

    def test_git_object_read_failure_records_unknown(self):
        self.repo(self.out / 'cell/work')
        obj = self.out / 'cell/work/.git/objects/aa' / ('a' * 38)
        obj.parent.mkdir()
        obj.write_bytes(b'not a Git object')
        with self.assertRaisesRegex(ValueError, 'PAT scan failed'):
            c.scan(self.out, self.runtime)
        self.assertEqual(r.read(self.out / 'pat-scan.json'), dict(status='UNKNOWN', revocation_required=True))

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
        self.runtime = dict(output=str(self.root / 'output'), smoke_output=str(self.root / 'smoke-output'),
            control=str(self.control), phase='measured',
            image='sha256:' + 'a' * 64, run_id='offline', sources=str(self.root), account=['a' * 12, 'b' * 12],
            release=dict(version='4.2.18', tarball=str(tarball), sha256=g.digest(tarball),
                integrity='sha512-' + base64.b64encode(hashlib.sha512(tarball.read_bytes()).digest()).decode()))
        self.runtime.update(self.credentials(self.root / 'output'))
        self.runtime_path = self.root / 'runtime.json'
        r.write(self.runtime_path, self.runtime)
        self.app = r.Runner(self.runtime_path)
        self.fake = FakeGitHub(self.root, self.app.remaining('smoke-claude'))

    def test_smoke_shared_lifecycle_order_receipts_and_separate_outputs(self):
        app = r.Runner(self.runtime_path, phase='smoke')
        output = Path(self.runtime['smoke_output'])
        events = []

        def install(runtime, work, home, config, arm):
            (work / 'AGENTS.md').write_text('installed from fixture tarball')
            p.bootstrap_git(work, 'add', '-A')
            p.bootstrap_git(work, 'commit', '-qm', 'install B')

        def inherited(name, task, arm, config):
            events.append(('prepare', name))
            out = app.prepare(name, task, arm, config)
            caller = r.read(out / 'harness/caller.json')
            self.assertIn('slugify(text)', caller['request'])
            self.assertEqual(caller['allowed'], app.task('SM')['allowed'])
            self.assertEqual(r.read(out / 'baseline.json')['tasks_sha256'], g.digest(HERE / 'smoke-tasks.json'))
            self.assertFalse((out / 'cell/work/src/expiry').exists())
            self.assertFalse((out / 'cell/work/src/limitcli').exists())
            (out / 'run').mkdir()
            r.write(out / 'run/started.json', {})
            c.seal(out, app.runtime, lambda _: ('sealed', []))
            r.write(output / f'verdict-{name}.json', dict(status='CHECKS_PASS', usage='COMPLETE',
                input_tokens=7, output_tokens=3, teardown='CLEAN', evidence_manifest_sha256='sealed', snapshot={}))

        def done(out, *_):
            events.append(('done', out.name))
            return dict(status='ADJUDICATE', checklist={})

        delete_archived = g.delete_archived

        def delete(repository, root, manifest):
            result = delete_archived(repository, root, manifest)
            events.append(('deleted', root.name))
            return result

        with patch.object(app, 'validate'), patch.object(app, 'inputs', return_value={'fixture': 'sealed'}), \
                patch.object(app.frame, 'control_unchanged', return_value=True), \
                patch.object(app.frame.prepare, 'install', side_effect=install), \
                patch.object(r.legacy.Runner, 'run', side_effect=inherited) as launch, \
                patch.object(g, 'command', self.fake), patch.object(c, 'scan', wraps=c.scan) as scan, \
                patch.object(g, 'done_check', side_effect=done), patch.object(g, 'delete_archived', side_effect=delete):
            self.assertEqual(app.schedule(), 0)
            self.assertEqual([call.args for call in launch.call_args_list],
                             [('smoke-claude', 'SM', 'B', 'claude'), ('smoke-codex', 'SM', 'B', 'codex')])
            for name, task, config in r.smoke_slots():
                with self.assertRaisesRegex(ValueError, 'never replay'):
                    app.run(name, task, 'B', config)
            self.assertEqual(launch.call_count, 2)
        self.assertEqual(events, [(action, name) for name in ('smoke-claude', 'smoke-codex')
                                  for action in ('prepare', 'done', 'deleted')])
        self.assertEqual([call.kwargs.get('roots', [call.args[0]]) for call in scan.call_args_list],
                         [roots for name, _, _ in r.smoke_slots() for roots in (
                             [output / name],
                             [output / name, output / 'archives' / name, output / f'verdict-{name}.json'])])
        self.assertFalse(Path(self.runtime['output']).exists())
        summary = r.read(output / 'rp-schedule.json')
        self.assertEqual((summary['phase'], summary['dispatched']), ('smoke', 2))
        for row in summary['slots']:
            self.assertEqual((row['phase'], row['measurement_eligible']), ('smoke', False))
            self.assertEqual((row['input_tokens'], row['output_tokens']), (7, 3))
            self.assertEqual(row['repository_cleanup']['http_status'], 404)
            self.assertEqual(row['repository_cleanup']['status'], 'DELETED')
        self.app.prior_deleted('o01')
        (output / 'smoke-claude/rp-verdict.json').unlink()
        with self.assertRaises(FileNotFoundError):
            self.app.prior_deleted('o01')

    def test_phases_reject_each_others_slots_and_changed_task_manifests(self):
        smoke = r.Runner(self.runtime_path, phase='smoke')
        self.assertEqual([task['id'] for task in smoke.tasks['tasks']], ['SM'])
        self.assertEqual([task['id'] for task in self.app.tasks['tasks']], ['BV', 'Z0'])
        with patch.object(r.legacy.Runner, 'run') as inherited:
            for app, foreign in ((smoke, r.SCHEDULE), (self.app, r.smoke_slots())):
                for name, task, config in foreign:
                    with self.assertRaisesRegex(ValueError, 'unregistered'):
                        app.run(name, task, 'B', config)
                app.tasks['tasks'][0]['request'] = 'changed'
                name, task, config = app.slots()[0]
                with self.assertRaisesRegex(ValueError, 'frozen'):
                    app.run(name, task, 'B', config)
        inherited.assert_not_called()
        self.assertFalse(Path(self.runtime['output']).exists())
        self.assertFalse(Path(self.runtime['smoke_output']).exists())

    def test_output_roots_must_be_disjoint_in_both_phases(self):
        measured = Path(self.runtime['output'])
        alias = self.root / 'alias'
        alias.symlink_to(measured, target_is_directory=True)
        for root in (measured, measured / 'nested', measured.parent, alias):
            r.write(self.runtime_path, dict(self.runtime, smoke_output=str(root)))
            for phase in ('smoke', 'measured'):
                with self.subTest(root=root, phase=phase), self.assertRaisesRegex(ValueError, 'must not overlap'):
                    r.Runner(self.runtime_path, phase=phase)

    def test_o01_refuses_missing_invalid_or_stopped_smoke_receipts(self):
        with patch.object(r.legacy.Runner, 'run') as inherited, patch.object(g, 'precheck') as precheck:
            self.assertEqual(self.app.run('o01', 'BV', 'B', 'claude'), 2)
        inherited.assert_not_called()
        precheck.assert_not_called()
        paths = []
        for name, _, _ in r.smoke_slots():
            path = Path(self.runtime['smoke_output']) / name / 'rp-verdict.json'
            path.parent.mkdir(parents=True)
            paths.append(path)
            r.write(path, dict(status='ADJUDICATE', repository_cleanup=dict(repository=self.app.repository(name),
                status='DELETED', http_status=404, archive_manifest_sha256='archive')))
        self.app.prior_deleted('o01')
        for path in paths:
            original = r.read(path)
            path.unlink()
            with self.assertRaises(FileNotFoundError):
                self.app.prior_deleted('o01')
            for key, value in (('repository', self.app.repository('o01')), ('status', 'PENDING'),
                               ('http_status', 403), ('archive_manifest_sha256', None)):
                record = deepcopy(original)
                record['repository_cleanup'][key] = value
                r.write(path, record)
                with self.assertRaisesRegex(ValueError, 'deletion/404'):
                    self.app.prior_deleted('o01')
            for status in ('STOP', 'UNKNOWN', 'NOT_RUN'):
                r.write(path, dict(original, status=status))
                with self.assertRaisesRegex(ValueError, 'already stopped'):
                    self.app.prior_deleted('o01')
            r.write(path, dict(original, status='PRODUCT_INCOMPLETE'))
            with self.assertRaisesRegex(ValueError, 'working delivery'):
                self.app.prior_deleted('o01')
            r.write(path, original)

    def test_smoke_delivery_failure_keeps_cost_runs_codex_and_blocks_measurement(self):
        app = r.Runner(self.runtime_path, phase='smoke')
        output = Path(self.runtime['smoke_output'])

        def inherited(name, *_):
            (output / name / 'run').mkdir(parents=True)
            r.write(output / name / 'run/started.json', {})
            r.write(output / f'verdict-{name}.json', dict(status='CHECKS_PASS', usage='COMPLETE',
                input_tokens=7, output_tokens=3, teardown='CLEAN', evidence_manifest_sha256='sealed', snapshot={}))

        with patch.object(g, 'precheck'), patch.object(r.legacy.Runner, 'run', side_effect=inherited) as launch, \
                patch.object(g, 'archive', return_value=dict(manifest_sha256='archive')), patch.object(c, 'scan'), \
                patch.object(g, 'done_check', side_effect=[dict(status=status, checklist={})
                    for status in ('PRODUCT_INCOMPLETE', 'ADJUDICATE')]), \
                patch.object(g, 'delete_archived', side_effect=lambda repository, *_: dict(repository=repository,
                    status='DELETED', http_status=404, archive_manifest_sha256='archive')):
            self.assertEqual(app.schedule(), 0)
        self.assertEqual([call.args for call in launch.call_args_list],
                         [('smoke-claude', 'SM', 'B', 'claude'), ('smoke-codex', 'SM', 'B', 'codex')])
        summary = r.read(output / 'rp-schedule.json')
        self.assertEqual([row['status'] for row in summary['slots']], ['PRODUCT_INCOMPLETE', 'ADJUDICATE'])
        for row in summary['slots']:
            self.assertEqual((row['input_tokens'], row['output_tokens']), (7, 3))
            self.assertEqual(row['repository_cleanup']['repository'], app.repository(row['cell']))
            self.assertEqual(row['repository_cleanup']['status'], 'DELETED')
        self.assertEqual((summary['status'], summary['dispatched']), ('RECORDED', 2))
        with self.assertRaisesRegex(ValueError, 'working delivery'):
            self.app.prior_deleted('o01')

    def test_smoke_codex_requires_claude_receipt_and_stop_prevents_replay(self):
        app = r.Runner(self.runtime_path, phase='smoke')
        with self.assertRaises(FileNotFoundError):
            app.prior_deleted('smoke-codex')
        with patch.object(g, 'precheck', side_effect=g.EvidenceError('offline refusal')), \
                patch.object(r.legacy.Runner, 'run') as inherited:
            self.assertEqual(app.schedule(), 2)
            with self.assertRaisesRegex(ValueError, 'never replay'):
                app.run('smoke-codex', 'SM', 'B', 'codex')
        inherited.assert_not_called()
        summary = r.read(Path(self.runtime['smoke_output']) / 'rp-schedule.json')
        self.assertEqual([row['status'] for row in summary['slots']], ['STOP', 'NOT_RUN'])
        self.assertEqual(summary['dispatched'], 0)
        with self.assertRaisesRegex(ValueError, 'already stopped'):
            self.app.prior_deleted('o01')

    def test_smoke_attempt_requires_positive_integer(self):
        for value in (0, -1, True, 2.0, '2', None):
            r.write(self.runtime_path, dict(self.runtime, smoke_attempt=value))
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, 'smoke_attempt'):
                r.Runner(self.runtime_path)
        self.assertEqual(self.app.runtime['smoke_attempt'], 1)

    def test_second_attempt_uses_only_fresh_smoke_repos_and_current_output(self):
        old_output = Path(self.runtime['smoke_output'])
        for name, _, _ in r.smoke_slots():
            path = old_output / name / 'rp-verdict.json'
            path.parent.mkdir(parents=True)
            r.write(path, dict(status='STOP'))
        old_files = {path: path.read_bytes() for path in old_output.rglob('*') if path.is_file()}
        output = self.root / 'stage2/smoke-output'
        r.write(self.runtime_path, dict(self.runtime, smoke_attempt=2, smoke_output=str(output)))
        app = r.Runner(self.runtime_path, phase='smoke')
        expected = ['smoke2-claude', 'smoke2-codex', *[f'o{i:02}' for i in range(1, 9)]]
        repositories = [app.repository(name) for name in expected]
        self.assertEqual(app.remaining('smoke2-claude'), repositories)
        self.assertEqual(app.remaining('smoke2-codex'), repositories[1:])
        self.assertEqual([name for name, _, _ in app.slots()], expected[:2])
        fake_root = self.root / 'attempt2-remotes'
        fake_root.mkdir()
        fake = FakeGitHub(fake_root, repositories)
        with patch.object(g, 'command', fake):
            g.precheck(app.remaining('smoke2-claude'))
            for repository in repositories:
                fake.states[repository]['pulls'] = [dict(number=1)]
                with self.assertRaisesRegex(g.EvidenceError, 'not empty'):
                    g.precheck(app.remaining('smoke2-claude'))
                fake.states[repository]['pulls'] = []
        app.prior_deleted('smoke2-claude')
        measured = r.Runner(self.runtime_path)
        with self.assertRaises(FileNotFoundError):
            measured.prior_deleted('o01')
        for name in expected[:2]:
            path = output / name / 'rp-verdict.json'
            path.parent.mkdir(parents=True)
            r.write(path, dict(status='ADJUDICATE', repository_cleanup=dict(repository=app.repository(name),
                status='DELETED', http_status=404, archive_manifest_sha256='archive')))
        measured.prior_deleted('o01')
        r.write(path, dict(status='STOP'))
        with self.assertRaisesRegex(ValueError, 'already stopped'):
            measured.prior_deleted('o01')
        with self.assertRaisesRegex(ValueError, 'unregistered'):
            app.run('smoke-claude', 'SM', 'B', 'claude')
        for path, raw in old_files.items():
            self.assertEqual(path.read_bytes(), raw)

    def test_smoke_repositories_are_first_in_emptiness_precheck(self):
        expected = ['smoke-claude', 'smoke-codex', *[f'o{i:02}' for i in range(1, 9)]]
        self.assertEqual(self.app.remaining('smoke-claude'), [self.app.repository(name) for name in expected])
        self.assertEqual(self.app.remaining('smoke-codex'), [self.app.repository(name) for name in expected[1:]])
        with patch.object(g, 'command', self.fake):
            g.precheck(self.app.remaining('smoke-claude'))
            for name in expected[:2]:
                state = self.fake.states[self.app.repository(name)]
                state['pulls'] = [dict(number=1)]
                with self.assertRaisesRegex(g.EvidenceError, 'not empty'):
                    g.precheck(self.app.remaining('smoke-claude'))
                state['pulls'] = []

    def test_cli_selects_phase_output_and_schedule(self):
        for phase, slots, key in (('smoke', r.smoke_slots(), 'smoke_output'), ('measured', r.SCHEDULE, 'output')):
            def schedule(app):
                self.assertEqual(app.runtime['phase'], phase)
                self.assertEqual(app.runtime['output'], self.runtime[key])
                self.assertEqual(app.slots(), slots)
                return 2

            with patch.object(sys, 'argv', ['runner.py', str(self.runtime_path), phase]), \
                    patch.object(r.Runner, 'schedule', schedule):
                self.assertEqual(r.main(), 2)

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
        for name in ('public', 'oracle'):
            (self.control / name).mkdir()
        r.write(self.root / 'control.manifest.json', dict(manifests={name: {
            str(path.relative_to(self.control / name)): g.digest(path)
            for path in (self.control / name).rglob('*') if path.is_file()}
            for name in ('public', 'oracle', 'packages')}))
        model_auth = Path(self.runtime['auth'])
        model_auth.mkdir()
        r.write(model_auth / 'manifest.json', {})  # inputs() seals it; prepare does not authenticate.
        run = subprocess.run
        installs = []

        def docker_only(argv, **kwargs):
            if argv[:3] == ['docker', 'image', 'inspect']:
                return subprocess.CompletedProcess(argv, 0, self.runtime['image'] + '\n', '')
            if argv[:2] == ['docker', 'run']:
                installs.append(argv)
                mount = next(value for value in argv if value.startswith('type=bind,src=') and value.endswith(',dst=/work'))
                work = Path(mount.removeprefix('type=bind,src=').removesuffix(',dst=/work'))
                (work / 'AGENTS.md').write_text('installed from fixture tarball')
                return subprocess.CompletedProcess(argv, 0, b'', b'')
            return run(argv, **kwargs)

        with patch.object(subprocess, 'run', side_effect=docker_only), patch.object(g, 'command', self.fake):
            first = self.app.prepare('o01', 'BV', 'B', 'codex')
            second = self.app.prepare('o02', 'BV', 'B', 'codex')
        self.assertEqual(len(installs), 2)
        self.assertTrue(all(argv[-3:] == ['node', '/install/package/bin/devlyn.js', '-y'] for argv in installs))
        config = (first / 'home/.codex/config.toml').read_text()
        parsed = tomllib.loads(config)
        self.assertEqual(config.count('[projects."/cell/work"]'), 1)
        self.assertEqual(parsed['projects'], {'/cell/work': dict(trust_level='trusted')})
        self.assertFalse(parsed['features']['shell_snapshot'])
        self.assertEqual(parsed['shell_environment_policy'], dict(ignore_default_excludes=False, set=p.GITHUB_ENV))
        self.assertEqual(g.git(first / 'cell/work', 'show', '-s', '--format=%s'), 'install B')
        dates = g.git(first / 'cell/work', 'show', '-s', '--format=%aI%n%cI').splitlines()
        self.assertEqual([datetime.fromisoformat(value) for value in dates], [datetime.fromisoformat(p.BOOTSTRAP_DATE)] * 2)
        for key in ('source_sha', 'allocation_sha'):
            self.assertEqual(r.read(first / 'baseline.json')[key], r.read(second / 'baseline.json')[key])
        self.assertNotIn(self.token, (first / 'plan.json').read_bytes())
        self.assertIn('AGENTS.md', r.read(first / 'baseline.json')['installed_files'])
        self.assertFalse((first / 'harness/mirror.git').exists())

    def test_routes_register_only_owner_and_native_children_use_owner(self):
        native = self.app.frame.cell_run.run.keywords['native']
        for config, route in self.app.tasks['routes'].items():
            self.assertEqual(set(route), {'owner'})
            self.assertEqual(route['owner']['engine'], config)
            self.assertEqual(native.evidence.seats(dict(config=config)),
                             dict(owner=route['owner'], child=route['owner']))
        self.assertIs(native.identity, native.legacy.identity)

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

    def test_inherited_preflight_refusal_keeps_fixed_reason(self):
        with patch.object(self.app, 'prior_deleted'), patch.object(g, 'precheck'), \
                patch.object(self.app, 'validate'), patch.object(self.app, 'boot_expectation'), \
                patch.object(self.app, 'preflight', return_value=({}, 'fixed-auth-refused')):
            self.assertEqual(self.app.run('o01', 'BV', 'B', 'claude'), 2)
        output = Path(self.runtime['output'])
        self.assertFalse((output / 'verdict-o01.json').exists())
        result = r.read(output / 'o01/rp-verdict.json')
        self.assertEqual(result['reason'], r.read(output / 'not-dispatched-o01.json')['reason'])
        self.assertEqual(result['reason'], 'fixed-auth-refused')
        self.assertFalse(result['dispatched'])

    def test_measured_claude_without_catalogs_refuses_before_github_mutation(self):
        with patch.object(self.app, 'prior_deleted'), patch.object(self.app, 'validate'), \
                patch.object(g, 'command', self.fake), patch.object(self.app, 'prepare') as prepare, \
                patch.object(self.app.frame.cell_run, 'run') as launch:
            self.assertEqual(self.app.schedule(), 2)
        prepare.assert_not_called()
        launch.assert_not_called()
        result = r.read(Path(self.runtime['output']) / 'o01/rp-verdict.json')
        self.assertEqual(result['reason'], 'measured Claude requires boot_catalogs.claude.B')
        self.assertFalse(result['dispatched'])
        self.assertTrue(self.fake.calls)
        self.assertTrue(all(argv[:2] == ['git', 'ls-remote'] or
                            argv[:2] == ['gh', 'api'] and '--method' not in argv for argv in self.fake.calls))
        self.assertEqual([row['status'] for row in r.read(Path(self.runtime['output']) / 'rp-schedule.json')['slots']],
                         ['STOP'] + ['NOT_RUN'] * 7)

    def test_arbitrary_exception_payload_is_not_a_named_boot_refusal(self):
        with patch.object(self.app, 'prior_deleted'), patch.object(g, 'precheck'), \
                patch.object(r.legacy.Runner, 'run', side_effect=ValueError('private exception payload')):
            self.assertEqual(self.app.run('o01', 'BV', 'B', 'claude'), 2)
        result = r.read(Path(self.runtime['output']) / 'o01/rp-verdict.json')
        self.assertEqual(result['reason'], 'rp-d1 instrumentation failed: ValueError')

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
                patch.object(c, 'scan'), \
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
        for index, fault in enumerate(('accounting', 'hit', 'unreadable')):
            with self.subTest(fault=fault):
                self.app.runtime['output'] = str(self.root / f'actual-accounting-{index}')
                out = Path(self.app.runtime['output']) / 'o01'

                def materialize(*_):
                    capture = fixture.Capture(out)
                    del capture.files[capture.indexed_file(2, 'response')]
                    capture.files['plan.json'] = dict(config='claude', engine='claude', model=fixture.MODEL,
                                                     effort='max', arm='B', name='o01', task='BV')
                    capture.files['run/started.json'] = {}
                    capture.seal()
                    if fault == 'hit':
                        (out / 'leaked-token').write_bytes(self.token)
                    elif fault == 'unreadable':
                        (out / self.token.decode()).mkdir()
                    return out

                scandir = c.os.scandir

                def unreadable(path):
                    if Path(path).name == self.token.decode():
                        raise PermissionError(13, 'Permission denied', str(path))
                    return scandir(path)

                archive_root = Path(self.app.runtime['output']) / 'archives/o01'
                archive_root.mkdir(parents=True)
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
                    stack.enter_context(patch.object(c.os, 'scandir', side_effect=unreadable))
                    self.assertEqual(self.app.run('o01', 'BV', 'B', 'claude'), 2)
                inherited = r.read(out.parent / 'verdict-o01.json')
                result = r.read(out / 'rp-verdict.json')
                self.assertEqual((inherited['status'], result['usage'], result['delivery_assessment']),
                                 ('STOP', 'UNKNOWN', 'NOT_ASSESSED'))
                self.assertIsNone(result['input_tokens'])
                self.assertTrue(result['dispatched'])
                if fault != 'accounting':
                    self.assertEqual(result['status'], 'UNKNOWN')
                    self.assertTrue(result['revocation_required'])
                    for path in (out.parent / 'verdict-o01.json', out / 'rp-verdict.json', out / 'pat-scan.json'):
                        self.assertNotIn(self.token, path.read_bytes())
                        self.assertNotIn(str(out), path.read_text())
                else:
                    self.assertEqual(inherited['claude_accounting']['status'], 'UNKNOWN')

    def test_pat_only_in_archived_pr_body_deletes_repository_and_stops_schedule(self):
        source = self.root / 'seed'
        self.repo(source)
        g.git(source, 'commit', '-qm', 'seed', '--allow-empty')
        sha = g.git(source, 'rev-parse', 'HEAD')
        state = self.fake.states[self.app.repository('o01')]
        g.git(source, 'push', str(state['remote']), 'HEAD:refs/heads/main')
        state['pulls'] = [dict(number=1, body=self.token.decode(), head=dict(sha=sha), merged=False)]

        def inherited(*args):
            self.inherited_run(*args, status='CHECKS_PASS', usage='COMPLETE')
            output = Path(self.runtime['output'])
            c.scan(output / 'o01', self.runtime)
            verdict = r.read(output / 'verdict-o01.json')
            verdict.update(teardown='CLEAN', evidence_manifest_sha256='sealed', snapshot={})
            r.write(output / 'verdict-o01.json', verdict)

        with patch.object(self.app, 'prior_deleted'), patch.object(g, 'precheck'), \
                patch.object(g, 'command', self.fake), \
                patch.object(r.legacy.Runner, 'run', side_effect=inherited), \
                patch.object(g, 'done_check', return_value=dict(status='ADJUDICATE', checklist={})):
            self.assertEqual(self.app.schedule(), 2)
        output = Path(self.runtime['output'])
        result = r.read(output / 'o01/rp-verdict.json')
        self.assertEqual((result['status'], result['usage']), ('UNKNOWN', 'UNKNOWN'))
        self.assertTrue(result['revocation_required'])
        self.assertIsNone(result['input_tokens'])
        self.assertIsNone(result['output_tokens'])
        self.assertEqual(result['repository_cleanup']['status'], 'DELETED')
        self.assertTrue(state['deleted'])
        archive = output / 'archives/o01'
        self.assertEqual(result['repository_cleanup']['archive_manifest_sha256'], g.digest(archive / 'manifest.json'))
        self.assertEqual(r.read(archive / 'repository.json')['pulls'][0]['body'], self.token.decode())
        for path in (output / 'o01/rp-verdict.json', output / 'o01/pat-scan.json', output / 'rp-schedule.json'):
            self.assertNotIn(self.token, path.read_bytes())
        self.assertEqual([row['status'] for row in r.read(output / 'rp-schedule.json')['slots']],
                         ['UNKNOWN'] + ['NOT_RUN'] * 7)

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
        self.assertEqual(result['repository_cleanup']['status'], 'RETAINED')
        self.assertIn('manual cleanup', result['repository_cleanup']['reason'])

    def test_deletion_failure_after_done_check_clears_assessment_and_retains_costs_and_evidence(self):
        for status in ('PASS', 'ADJUDICATE', 'PRODUCT_INCOMPLETE'):
            for error in (g.EvidenceError, OSError):
                with self.subTest(status=status, error=error.__name__):
                    output = self.root / f'{status}-{error.__name__}'
                    self.runtime['output'] = self.app.runtime['output'] = str(output)
                    out, archive = output / 'o01', output / 'archives/o01'
                    done = dict(status=status, checklist={'verification': 'PASS'})
                    evidence = {}

                    def inherited(*args):
                        self.inherited_run(*args, status='CHECKS_PASS', usage='COMPLETE')
                        path = output / 'verdict-o01.json'
                        r.write(path, dict(r.read(path), teardown='CLEAN', evidence_manifest_sha256='sealed',
                                           snapshot={}, owner_seconds=12.5))

                    def freeze_archive(repository, root):
                        root.mkdir(parents=True)
                        r.write(root / 'manifest.json', dict(repository=repository))
                        return dict(manifest_sha256=g.digest(root / 'manifest.json'))

                    def fail_delete(*args):
                        self.assertEqual(r.read(out / 'github-delivery.json'), done)
                        evidence.update({path: path.read_bytes() for path in output.rglob('*') if path.is_file()})
                        raise error('repository deletion failed')

                    with patch.object(self.app, 'prior_deleted'), patch.object(g, 'precheck'), \
                            patch.object(r.legacy.Runner, 'run', side_effect=inherited), \
                            patch.object(g, 'archive', side_effect=freeze_archive), \
                            patch.object(g, 'done_check', return_value=done), \
                            patch.object(g, 'delete_archived', side_effect=fail_delete) as delete:
                        self.assertEqual(self.app.run('o01', 'BV', 'B', 'claude'), 2)
                    delete.assert_called_once_with(self.app.repository('o01'), archive,
                                                   g.digest(archive / 'manifest.json'))
                    result = r.read(out / 'rp-verdict.json')
                    self.assertEqual((result['status'], result['delivery_assessment']), ('STOP', 'NOT_ASSESSED'))
                    self.assertEqual((result['usage'], result['input_tokens'], result['output_tokens']),
                                     ('COMPLETE', 7, 3))
                    self.assertEqual(r.read(output / 'verdict-o01.json')['owner_seconds'], 12.5)
                    self.assertEqual(result['inherited_verdict_sha256'], g.digest(output / 'verdict-o01.json'))
                    self.assertEqual(result['archive'], dict(manifest_sha256=g.digest(archive / 'manifest.json')))
                    self.assertEqual(result['repository_cleanup']['repository'], self.app.repository('o01'))
                    self.assertEqual(result['repository_cleanup']['status'], 'RETAINED')
                    self.assertIn('manual cleanup', result['repository_cleanup']['reason'])
                    self.assertEqual(r.read(out / 'report-checklist.json'), done['checklist'])
                    for path, raw in evidence.items():
                        self.assertEqual(path.read_bytes(), raw, str(path))

    def test_partial_archive_pat_is_scanned_and_repository_retained(self):
        source = self.root / 'seed'
        self.repo(source)
        g.git(source, 'commit', '-qm', 'seed', '--allow-empty')
        state = self.fake.states[self.app.repository('o01')]
        g.git(source, 'push', str(state['remote']), 'HEAD:refs/heads/main')
        state['pulls'] = [dict(number=1, body=self.token.decode(),
                              head=dict(sha=g.git(source, 'rev-parse', 'HEAD')), merged=False)]
        output = Path(self.runtime['output'])
        archive = output / 'archives/o01'

        def inherited(*args):
            self.inherited_run(*args, status='CHECKS_PASS', usage='COMPLETE')
            c.seal(output / 'o01', self.runtime, lambda _: ('sealed', []))
            verdict = r.read(output / 'verdict-o01.json')
            r.write(output / 'verdict-o01.json', dict(verdict, teardown='CLEAN', evidence_manifest_sha256='sealed'))

        write = g.write

        def fail_manifest(path, value):
            if path == archive / 'manifest.json':
                raise OSError(self.token.decode())
            write(path, value)

        with patch.object(self.app, 'prior_deleted'), patch.object(g, 'precheck'), \
                patch.object(r.legacy.Runner, 'run', side_effect=inherited), patch.object(g, 'command', self.fake), \
                patch.object(g, 'write', side_effect=fail_manifest), patch.object(c, 'scan', wraps=c.scan) as scan, \
                patch.object(g, 'done_check') as done, patch.object(g, 'delete_archived') as delete:
            self.assertEqual(self.app.schedule(), 2)
        done.assert_not_called()
        delete.assert_not_called()
        self.assertEqual(scan.call_count, 2, 'pre-seal plus one final scan')
        self.assertIn(archive, scan.call_args.kwargs['roots'])
        self.assertIn(self.token, (archive / 'repository.json').read_bytes())
        self.assertFalse((archive / 'manifest.json').exists())
        self.assertFalse(state['deleted'])
        result = r.read(output / 'o01/rp-verdict.json')
        self.assertEqual((result['status'], result['usage']), ('UNKNOWN', 'UNKNOWN'))
        self.assertTrue(result['revocation_required'])
        self.assertEqual(result['repository_cleanup']['status'], 'RETAINED')
        self.assertIn('manual cleanup', result['repository_cleanup']['reason'])
        self.assertNotIn(self.token, (output / 'o01/rp-verdict.json').read_bytes())
        self.assertNotIn('repository.json', (output / 'o01/rp-verdict.json').read_text())
        self.assertEqual([row['status'] for row in r.read(output / 'rp-schedule.json')['slots']],
                         ['UNKNOWN'] + ['NOT_RUN'] * 7)

    def test_final_scan_catches_real_evaluator_output_after_seal(self):
        output = Path(self.runtime['output'])
        out = output / 'o01'
        hidden = self.control / 'oracle/experiments/rp-d1-delivery-cost'
        hidden.mkdir(parents=True)
        shutil.copyfile(HERE / 'oracle.py', hidden / 'oracle.py')

        def in_image(runtime, work, command):
            argv = ([sys.executable, '-B', '-m', 'pytest', '-q', '-p', 'no:cacheprovider'] if command[0] == 'sh'
                    else [sys.executable, '-B', str(HERE / 'oracle.py'), 'BV', str(work)])
            result = subprocess.run(argv, cwd=work, capture_output=True, text=True,
                                    env=g.git_env() | {'PYTHONPATH': str(work / 'src'),
                                        'PYTHONDONTWRITEBYTECODE': '1', 'PYTEST_DISABLE_PLUGIN_AUTOLOAD': '1'})
            return dict(argv=command, exit_code=result.returncode, timeout=False, stdout=result.stdout, stderr=result.stderr)

        def inherited(*args):
            self.inherited_run(*args, status='CHECKS_PASS', usage='COMPLETE')
            shutil.copytree(HERE / 'fixtures/BV', out / 'snapshot')
            r.write(out / 'baseline.json', dict(task='BV', files=packet.tree(out / 'snapshot')))
            (out / 'snapshot/src/expiry/__init__.py').write_text(
                'import base64\nprint(base64.b64decode(' + repr(base64.b64encode(self.token)) + ').decode())\n'
                'def is_expired(now, deadline):\n    return now >= deadline\n')
            (out / 'snapshot/tests/test_regression.py').write_text(
                'from expiry import is_expired\ndef test_equal():\n    assert is_expired(0, 0)\n')
            c.seal(out, self.runtime, lambda _: ('sealed', []))
            checked = self.app.frame.check.check(out, self.runtime)
            self.assertTrue(checked['product_check_pass'], checked)
            self.assertIn(self.token, (out / 'checks-raw.json').read_bytes())
            verdict = r.read(output / 'verdict-o01.json')
            r.write(output / 'verdict-o01.json', dict(verdict, teardown='CLEAN', evidence_manifest_sha256='sealed', snapshot={}))

        scan = c.scan
        with patch.object(self.app, 'prior_deleted'), patch.object(g, 'precheck'), \
                patch.object(r.legacy.Runner, 'run', side_effect=inherited), \
                patch.object(self.app.frame.check, 'in_image', side_effect=in_image), \
                patch.object(g, 'archive', return_value=dict(manifest_sha256='archive')), \
                patch.object(g, 'done_check', return_value=dict(status='ADJUDICATE', checklist={})), \
                patch.object(g, 'delete_archived', return_value=dict(status='DELETED')) as delete:
            # Keep the real scanner at both boundaries and observe final record ordering.
            def observed_scan(*args, **kwargs):
                if 'roots' in kwargs:
                    self.assertTrue(all((out / name).exists() for name in (
                        'checks-raw.json', 'github-delivery.json', 'report-checklist.json')))
                    self.assertFalse((out / 'rp-verdict.json').exists())
                return scan(*args, **kwargs)
            with patch.object(c, 'scan', side_effect=observed_scan) as scanned:
                self.assertEqual(self.app.schedule(), 2)
        self.assertEqual(scanned.call_count, 2)
        delete.assert_called_once()
        result = r.read(out / 'rp-verdict.json')
        self.assertEqual((result['status'], result['usage'], result['delivery_assessment']),
                         ('UNKNOWN', 'UNKNOWN', 'NOT_ASSESSED'))
        self.assertTrue(result['revocation_required'])
        self.assertNotIn(self.token, (out / 'rp-verdict.json').read_bytes())
        self.assertNotIn('checks-raw.json', (out / 'rp-verdict.json').read_text())
        self.assertEqual([row['status'] for row in r.read(output / 'rp-schedule.json')['slots']],
                         ['UNKNOWN'] + ['NOT_RUN'] * 7)

    def test_final_scan_failure_without_marker_stops_and_requires_revocation(self):
        with patch.object(self.app, 'prior_deleted'), patch.object(g, 'precheck'), \
                patch.object(r.legacy.Runner, 'run', side_effect=self.inherited_run), \
                patch.object(c, 'scan', side_effect=ValueError(self.token.decode())) as scan:
            self.assertEqual(self.app.schedule(), 2)
        scan.assert_called_once()
        out = Path(self.runtime['output']) / 'o01'
        self.assertFalse((out / 'pat-scan.json').exists())
        result = r.read(out / 'rp-verdict.json')
        self.assertTrue(result['revocation_required'])
        self.assertEqual((result['status'], result['usage']), ('UNKNOWN', 'UNKNOWN'))
        self.assertNotIn(self.token, (out / 'rp-verdict.json').read_bytes())

    def test_new_inputs_are_sealed_including_ignored_fixture(self):
        with patch.object(r.legacy.Runner, 'inputs', return_value={'historical': 'unchanged'}):
            inputs = self.app.inputs()
        self.assertEqual(inputs['historical'], 'unchanged')
        for name in ('runner.py', 'prepare.py', 'cell.py', 'github.py', 'oracle.py', 'build.sh', 'Dockerfile', 'stage.py',
                     'common.txt', 'tasks.json', 'smoke-tasks.json', 'summarize.py', 'test_summarize.py',
                     'fixtures/BV/.user-state/draft.txt',
                     'fixtures/SM/.user-state/draft.txt'):
            self.assertEqual(inputs[str(HERE / name)], g.digest(HERE / name))


class OracleTests(TempCase):
    def test_smoke_original_fails_and_correct_fixture_with_public_regression_passes(self):
        original = oracle.check('SM', HERE / 'fixtures/SM')
        self.assertEqual([row['id'] for row in original['rows']], r.read(HERE / 'smoke-tasks.json')['tasks'][0]['oracle'])
        self.assertTrue(all(row['status'] == 'FAIL' for row in original['rows']))
        dest = self.root / 'SM'
        shutil.copytree(HERE / 'fixtures/SM', dest)
        (dest / oracle.IMPLEMENTATION['SM']).write_text(
            'import re\ndef slugify(text):\n'
            '    if not isinstance(text, str):\n        raise TypeError("expected text")\n'
            '    return re.sub(r"[^A-Za-z0-9]+", "-", text).strip("-").lower()\n')
        (dest / 'tests/test_regression.py').write_text(
            'from slugtools import slugify\ndef test_words():\n    assert slugify(" Hello World! ") == "hello-world"\n')
        public = subprocess.run([sys.executable, '-B', '-m', 'pytest', '-q'], cwd=dest,
                                capture_output=True, text=True)
        self.assertEqual(public.returncode, 0, public.stdout + public.stderr)
        self.assertTrue(all(row['status'] == 'PASS' for row in oracle.check('SM', dest)['rows']))

    def test_float_implementation_passes_public_but_datetime_exception_fails_row(self):
        dest = self.root / 'BV'
        shutil.copytree(HERE / 'fixtures/BV', dest)
        (dest / oracle.IMPLEMENTATION['BV']).write_text(
            'def is_expired(now, deadline):\n    return float(now) >= float(deadline)\n')
        public = subprocess.run([sys.executable, '-B', '-m', 'pytest', '-q', '-p', 'no:cacheprovider'],
            cwd=dest, capture_output=True, text=True, env=g.git_env() | {
                'PYTHONPATH': str(dest / 'src'), 'PYTHONDONTWRITEBYTECODE': '1', 'PYTEST_DISABLE_PLUGIN_AUTOLOAD': '1'})
        self.assertEqual(public.returncode, 0, public.stdout + public.stderr)
        result = subprocess.run([sys.executable, '-B', str(HERE / 'oracle.py'), 'BV', str(dest)],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        rows = {row['id']: row for row in json.loads(result.stdout)['rows']}
        self.assertEqual(rows['datetime'], dict(id='datetime', status='FAIL', reason='participant raised during check'))
        self.assertEqual(rows['boundary']['status'], 'PASS')
        self.assertEqual(rows['before-after']['status'], 'PASS')

    def test_unimportable_fixture_stays_unknown(self):
        result = subprocess.run([sys.executable, '-B', str(HERE / 'oracle.py'), 'BV', str(self.root / 'missing')],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(json.loads(result.stdout)['status'], 'UNKNOWN')

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
