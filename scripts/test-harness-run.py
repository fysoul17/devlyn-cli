#!/usr/bin/env python3
"""`devlyn run` against fake engines: exact argv, files, environment, exit status and refusals.
Packs this checkout (or --package-root) and runs it in an isolated HOME; no model calls."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import runpy
import signal
import subprocess
import sys
import tarfile
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
HELPERS = runpy.run_path(str(ROOT / 'scripts/test-harness-release.py'))
run, environment = HELPERS['run'], HELPERS['environment']
PACKAGE_ROOT = None
PREFIX = 'The following Devlyn instructions are defaults for this session.'
FAKE = r'''#!/usr/bin/env python3
import json, os, signal, sys
name, argv = os.path.basename(sys.argv[0]), sys.argv[1:]
if argv == ['--version']:
    said = os.environ.get('FAKE_VERSION')
    print(said if said is not None else {'claude': '2.1.318 (Claude Code)', 'codex': 'codex-cli 0.164.0', 'omp': 'omp/18.14.2'}[name])
    sys.exit(0)
if name == 'omp' and argv[:3] == ['config', 'list', '--json']:
    if os.environ.get('FAKE_OMP_FAIL'):
        print('SECRET-TOKEN in settings', file=sys.stderr)
        sys.exit(1)
    print(json.dumps({'skills.enabled': {'value': True}, 'skills.customDirectories': {'value': ['/owner/skills']},
                      'autoResume': {'value': os.environ.get('FAKE_AUTORESUME') == '1'}}))
    sys.exit(0)
if name == 'codex' and argv[:1] == ['app-server']:
    if os.environ.get('FAKE_HANG'):
        signal.signal(signal.SIGTERM, signal.SIG_IGN)
    for line in sys.stdin:
        message = json.loads(line)
        if message.get('method') == 'initialize':
            print(json.dumps({'id': message['id'], 'result': {}}), flush=True)
        elif message.get('method') == 'config/read':
            if os.environ.get('FAKE_HANG'):
                import time
                time.sleep(60)
            if os.environ.get('FAKE_CONFIG_ERROR'):
                print(json.dumps({'id': message['id'], 'error': {'message': 'bad line: SECRET-TOKEN'}}), flush=True)
                continue
            print(json.dumps({'method': 'note'}), flush=True)
            print(json.dumps({'id': message['id'], 'result': {'config': {'developer_instructions': 'OWNER DEV',
                'plugins': None, 'skills': {'config': None}}}}), flush=True)
    sys.exit(0)
files = {arg: open(arg, encoding='utf-8').read() for arg in argv if os.path.isfile(arg)}
with open(os.environ['FAKE_OUT'], 'w', encoding='utf-8') as out:
    json.dump({'argv': argv, 'cwd': os.getcwd(), 'files': files, 'stdin': sys.stdin.read() if os.environ.get('FAKE_READ_STDIN') else None,
               'env': {key: value for key, value in os.environ.items() if key.startswith('DEVLYN_')}}, out)
print('engine stdout', flush=True)
if os.environ.get('FAKE_SIGNAL'):
    os.kill(os.getpid(), int(os.environ['FAKE_SIGNAL']))
sys.exit(int(os.environ.get('FAKE_EXIT', '0')))
'''


@unittest.skipIf(os.name == 'nt', '`devlyn run` refuses Windows for now')
class RunTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix='devlyn-run-')
        cls.work = Path(cls.temp.name).resolve()
        if PACKAGE_ROOT:
            cls.package = PACKAGE_ROOT
        else:
            packed = run(['npm', 'pack', ROOT, '--json', '--pack-destination', cls.work, '--cache', cls.work / 'npm-cache'])
            with tarfile.open(cls.work / json.loads(packed.stdout)[0]['filename']) as archive:
                archive.extractall(cls.work, filter='data')
            cls.package = cls.work / 'package'
        cls.cli = cls.package / 'bin/devlyn.js'
        verified = run(['node', cls.cli, 'release', '--verify', '--root', cls.package, '--json'])
        cls.release = json.loads(verified.stdout)['data']['release']

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def setUp(self):
        self.case = self.work / self.id().rsplit('.', 1)[-1]
        self.home, self.bin, self.project = self.case / 'home', self.case / 'bin', self.case / 'project'
        for directory in (self.home, self.bin, self.project, self.home / '.codex'):
            directory.mkdir(parents=True)
        run(['git', 'init', '-q', self.project])
        for name in ('claude', 'codex', 'omp'):
            engine = self.bin / name
            engine.write_text(FAKE.replace('/usr/bin/env python3', sys.executable, 1), encoding='utf-8')
            engine.chmod(0o755)
        self.out = self.case / 'launch.json'
        self.env = {**environment(), 'HOME': str(self.home), 'FAKE_OUT': str(self.out),
                    'PATH': f'{self.bin}{os.pathsep}{os.environ["PATH"]}'}
        for key in ('CODEX_HOME', 'CLAUDE_CONFIG_DIR'):
            self.env.pop(key, None)

    def devlyn(self, *args, env=None, stdin=None):
        return subprocess.run(['node', self.cli, 'run', *args], cwd=self.project, env={**self.env, **(env or {})},
                              input=stdin, capture_output=True, text=True, timeout=120)

    def launch(self):
        return json.loads(self.out.read_text(encoding='utf-8'))

    def state(self, **fields):
        harness = self.home / '.devlyn/harness'
        harness.mkdir(parents=True, exist_ok=True)
        (harness / 'state.json').write_text(json.dumps({'schemaVersion': 1, 'revision': 1, 'defaultRelease': None, **fields}), encoding='utf-8')

    def test_omp_gets_the_plan_before_the_owner_args_and_its_exit_code_returns(self):
        # Prediction: plan arguments lead, owner arguments follow untouched, stdout stays the engine's, and exit 7 is 7.
        result = self.devlyn('omp', '-p', '--no-session', '--', '--flag-like prompt', env={'FAKE_EXIT': '7'})
        self.assertEqual(result.returncode, 7, result.stderr)
        self.assertEqual(result.stdout, 'engine stdout\n')
        launch = self.launch()
        self.assertEqual(launch['argv'][0], '--config')
        self.assertEqual(launch['argv'][2], '--append-system-prompt')
        self.assertTrue(launch['argv'][3].startswith(PREFIX))
        self.assertEqual(launch['argv'][4:], ['-p', '--no-session', '--', '--flag-like prompt'])
        overlay = json.loads(launch['files'][launch['argv'][1]])
        self.assertIn('/owner/skills', overlay['skills']['customDirectories'])
        self.assertTrue(overlay['skills']['enabled'])
        self.assertEqual(launch['cwd'], str(self.project.resolve()))
        self.assertTrue(Path(launch['env']['DEVLYN_NODE']).is_absolute())
        self.assertFalse(Path(launch['argv'][1]).exists(), 'the run folder outlives the launch')
        line = result.stderr.strip().splitlines()[-1]
        self.assertIn('omp 18.14.2', line)
        self.assertIn('(package)', line)
        self.assertIn('principles=configured:append-system-prompt', line)

    def test_stdin_reaches_the_engine_unread(self):
        result = self.devlyn('omp', '-p', env={'FAKE_READ_STDIN': '1'}, stdin='piped task')  # no positional
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.launch()['stdin'], 'piped task')

    def test_claude_owner_append_text_is_merged_not_duplicated(self):
        # Prediction: the owner's flag is consumed and its text leads the single merged append file.
        for args in (['--append-system-prompt', 'OWNER TEXT'], ['--append-system-prompt=OWNER TEXT']):
            with self.subTest(args=args):
                result = self.devlyn('claude', *args, '-p', 'a task')
                self.assertEqual(result.returncode, 0, result.stderr)
                argv = self.launch()['argv']
                self.assertNotIn('--append-system-prompt', argv)
                at = argv.index('--append-system-prompt-file')
                merged = self.launch()['files'][argv[at + 1]]
                self.assertIn('OWNER TEXT', merged)
                self.assertIn(PREFIX, merged)
                self.assertEqual(argv[-2:], ['-p', 'a task'])
        owner = self.case / 'owner.txt'
        owner.write_text('FROM A FILE', encoding='utf-8')
        result = self.devlyn('claude', '--append-system-prompt-file', str(owner), '-p', 'a task')
        self.assertEqual(result.returncode, 0, result.stderr)
        argv = self.launch()['argv']
        self.assertEqual(argv.count('--append-system-prompt-file'), 1)
        self.assertIn('FROM A FILE', self.launch()['files'][argv[argv.index('--append-system-prompt-file') + 1]])

    def test_arguments_after_a_literal_separator_are_not_options(self):
        result = self.devlyn('claude', '-p', '--', '--resume')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.launch()['argv'][-3:], ['-p', '--', '--resume'])
        result = self.devlyn('claude', '--model=opus', '-p', 'a task')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.launch()['argv'][-3:], ['--model=opus', '-p', 'a task'])

    def test_codex_overrides_precede_the_subcommand_and_the_projection_is_synced(self):
        result = self.devlyn('codex', 'exec', 'do the task')
        self.assertEqual(result.returncode, 0, result.stderr)
        argv = self.launch()['argv']
        self.assertEqual(argv[-2:], ['exec', 'do the task'])
        settings = [argv[i + 1] for i, arg in enumerate(argv[:-2]) if arg == '-c']
        instructions = next(value for value in settings if value.startswith('developer_instructions='))
        self.assertIn('OWNER DEV', instructions)
        self.assertIn(PREFIX, instructions)
        self.assertTrue(list((self.home / '.codex/plugins/cache').glob('devlyn-harness-v*')), 'no projection')

    def test_every_refusal_starts_no_engine(self):
        # Prediction: each stops before spawn with its own reason, including attached and aliased forms.
        cases = [
            (('grok',), {}, 'run-engine-unsupported'),
            (('claude', '--resume', 'abc'), {}, 'run-argument-unsupported'),
            (('claude', '-r123'), {}, 'run-argument-unsupported'),
            (('claude', '-c'), {}, 'run-argument-unsupported'),
            (('claude', '--fork-session'), {}, 'run-argument-unsupported'),
            (('claude', '--settings', 'x.json'), {}, 'run-argument-unsupported'),
            (('claude', '--append-system-prompt', 'a', '--append-system-prompt', 'b'), {}, 'run-argument-unsupported'),
            (('codex', 'resume'), {}, 'run-continuation-unsupported'),
            (('codex', 'resume', '--last'), {}, 'run-argument-unsupported'),
            (('codex', 'exec', 'resume'), {}, 'run-continuation-unsupported'),
            (('codex', 'e', 'resume'), {}, 'run-continuation-unsupported'),
            (('codex', '-m', 'resume', 'fork'), {}, 'run-continuation-unsupported'),
            (('codex', 'login'), {}, 'run-argument-unsupported'),
            (('codex', '-p', 'work'), {}, 'run-argument-unsupported'),
            (('codex', '-pwork'), {}, 'run-argument-unsupported'),
            (('codex', '-c', 'developer_instructions="x"'), {}, 'run-argument-unsupported'),
            (('codex', '-cdeveloper_instructions="x"', 'exec', 'a task'), {}, 'run-argument-unsupported'),
            (('codex', '--config=plugins.a.enabled=true'), {}, 'run-argument-unsupported'),
            (('codex', '-C', 'sub', 'exec', 'a task'), {}, 'run-argument-unsupported'),
            (('codex', '-c developer_instructions="x"', 'exec', 'a task'), {}, 'run-argument-unsupported'),
            (('codex', 'hello', 'resume', 'abc'), {}, 'run-argument-unsupported'),
            (('codex', 'do the task', 'resume'), {}, 'run-continuation-unsupported'),
            (('claude', '-rmy session', '-p', 'a task'), {}, 'run-argument-unsupported'),
            (('claude', '-wmy tree', '-p', 'a task'), {}, 'run-argument-unsupported'),
            (('claude', 'attach', 'deadbeef'), {}, 'run-argument-unsupported'),
            (('claude', '--', 'update'), {}, 'run-argument-unsupported'),
            (('claude', '--', 'auth', 'status'), {}, 'run-argument-unsupported'),
            (('omp', '--', 'config'), {}, 'run-argument-unsupported'),
            (('claude', '-p', 'hello'), {}, 'run-argument-unsupported'),
            (('omp', 'hello'), {}, 'run-argument-unsupported'),
            (('omp', '--config', 'x.yml'), {}, 'run-argument-unsupported'),
            (('omp', '--cwd=/elsewhere'), {}, 'run-argument-unsupported'),
            (('omp', '-r', 'abc'), {}, 'run-argument-unsupported'),
            (('omp', '--session', 'abc'), {}, 'run-argument-unsupported'),
            (('omp', '--fork', 'abc'), {}, 'run-argument-unsupported'),
            (('omp',), {'FAKE_AUTORESUME': '1'}, 'run-continuation-unsupported'),
            (('omp', '-p', 'a task'), {'FAKE_VERSION': 'omp/1.0.0'}, 'principles-unavailable'),
            (('omp', '-p', 'a task'), {'FAKE_VERSION': 'unknown'}, 'principles-unavailable'),
        ]
        for args, env, code in cases:
            with self.subTest(args=args, env=env):
                self.out.unlink(missing_ok=True)
                result = self.devlyn(*args, env=env)
                self.assertNotEqual(result.returncode, 0, result.stderr)
                self.assertIn(code, result.stderr)
                self.assertFalse(self.out.exists(), 'an engine started')

    def test_a_value_is_never_read_as_an_option(self):
        result = self.devlyn('claude', '--append-system-prompt', '--resume', '--model', '-c', '-p', 'a task')
        self.assertEqual(result.returncode, 0, result.stderr)
        argv = self.launch()['argv']
        self.assertEqual(argv[-4:], ['--model', '-c', '-p', 'a task'])
        self.assertIn('--resume', self.launch()['files'][argv[argv.index('--append-system-prompt-file') + 1]])

    def test_literal_text_after_the_separator_is_a_prompt(self):
        # Prediction: after `--` every word is the task, even one that names a command.
        for args in (('codex', '--', 'resume'), ('codex', 'exec', '--', 'review'), ('claude', '-p', '--', 'attach'), ('omp', '-p', '--', 'hello'),
                     ('claude', '--', 'a multi word task')):
            with self.subTest(args=args):
                result = self.devlyn(*args)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(self.launch()['argv'][-len(args) + 1:], list(args[1:]))

    def test_a_list_option_keeps_all_its_values(self):
        for args, tail in ((('claude', '--allowedTools', 'Read', 'Edit', '-p', '--', 'ping'), ['--allowedTools', 'Read', 'Edit', '-p', '--', 'ping']),
                           (('codex', 'exec', '--image', 'a.png', 'b.png', '--', 'compare them'), ['exec', '--image', 'a.png', 'b.png', '--', 'compare them'])):
            with self.subTest(args=args):
                result = self.devlyn(*args)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(self.launch()['argv'][-len(tail):], tail)

    def test_a_long_omp_append_text_is_text(self):
        # Prediction: text too long for a path is merged, not refused, and never printed.
        text = 'owner rule ' * 40
        result = self.devlyn('omp', '--append-system-prompt', text, '-p', 'a task')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(text.strip(), self.launch()['argv'][3])

    def test_a_plan_that_cannot_deliver_the_principles_starts_no_engine(self):
        # Prediction: the planner refuses NUL in append text as partial; partial principles are not a launch.
        owner = self.case / 'binary.txt'
        owner.write_bytes(b'owner\0text')
        result = self.devlyn('claude', '--append-system-prompt-file', str(owner), '-p', 'a task')
        self.assertNotEqual(result.returncode, 0, result.stderr)
        self.assertIn('principles-unavailable', result.stderr)
        self.assertFalse(self.out.exists())

    def test_omp_owner_append_text_survives_the_plans_explicit_prompt(self):
        # Prediction: an existing file named on the flag, then a discovered APPEND_SYSTEM.md, are merged as text.
        owner = self.project / 'owner.md'
        owner.write_text('FROM NAMED FILE', encoding='utf-8')
        result = self.devlyn('omp', '--append-system-prompt', 'owner.md', '-p', 'a task')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('FROM NAMED FILE', self.launch()['argv'][3])
        (self.project / '.omp').mkdir()
        (self.project / '.omp/APPEND_SYSTEM.md').write_text('FROM PROJECT FILE', encoding='utf-8')
        result = self.devlyn('omp', '-p', 'a task')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('FROM PROJECT FILE', self.launch()['argv'][3])

    def test_failures_never_print_what_the_engine_said(self):
        # Prediction: engine diagnostics can quote settings, so only the reason code reaches stderr.
        for args, env in ((('omp', '-p', 'a task'), {'FAKE_OMP_FAIL': '1'}), (('codex', 'exec', 'a task'), {'FAKE_CONFIG_ERROR': '1'})):
            with self.subTest(args=args):
                result = self.devlyn(*args, env=env)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn('config-unreadable', result.stderr)
                self.assertNotIn('SECRET-TOKEN', result.stderr + result.stdout)
                self.assertFalse(self.out.exists())

    def test_a_hung_codex_helper_cannot_hold_the_launch(self):
        # Prediction: past the read budget the helper is killed, even one ignoring SIGTERM.
        started = time.monotonic()
        result = self.devlyn('codex', 'exec', 'a task', env={'FAKE_HANG': '1'})
        self.assertLess(time.monotonic() - started, 30)
        self.assertIn('config-unreadable', result.stderr)
        self.assertFalse(self.out.exists())

    def test_a_relative_path_entry_resolves_to_one_absolute_program(self):
        result = self.devlyn('omp', '-p', 'a task', env={'PATH': f'../bin{os.pathsep}{os.environ["PATH"]}'})
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_a_recorded_release_that_does_not_verify_stops_the_launch(self):
        # Prediction: a bad record never yields to this package's release.
        harness = self.home / '.devlyn/harness'
        harness.mkdir(parents=True)
        state = harness / 'state.json'
        common = self.project / '.git/devlyn-loops'
        common.mkdir()
        binding = common / 'harness.json'
        def link():
            state.unlink()
            state.symlink_to(self.case / 'gone.json')
        def queue(text):
            state.unlink()
            binding.write_text(text, encoding='utf-8')
        cases = ((lambda: state.write_text('{', encoding='utf-8'), 'config-unreadable'),
                 (lambda: state.write_text('null', encoding='utf-8'), 'state-unreadable'),
                 (link, 'config-unreadable'),
                 (lambda: self.state(defaultRelease={'version': '9.9.9', 'digest': '0' * 64}), 'release-unavailable'),
                 (lambda: queue('null'), 'state-unreadable'),
                 (lambda: binding.write_text(json.dumps({'schemaVersion': 1, 'release': self.release}), encoding='utf-8'), 'state-unreadable'),
                 (lambda: binding.write_text(json.dumps({'schemaVersion': 1, 'release': self.release,
                     'defaults': {'path': 'relative.md', 'sha256': '0' * 64}}), encoding='utf-8'), 'state-unreadable'))
        for setup, code in cases:
            with self.subTest(code=code):
                setup()
                result = self.devlyn('omp', '-p', 'a task')
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(code, result.stderr)
                self.assertFalse(self.out.exists())

    def test_the_app_default_release_is_used_as_recorded(self):
        store = self.home / '.devlyn/harness'
        run(['node', self.cli, 'release', '--materialize', '--source', self.package, '--store', store, '--json'], env=self.env)
        self.state(defaultRelease={'version': self.release['version'], 'digest': self.release['digest']})
        result = self.devlyn('omp', '-p', 'a task')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('(app-default)', result.stderr)
        self.assertEqual(self.launch()['env']['DEVLYN_HARNESS_ROOT'], str((store / 'devlyn-cli' / self.release['version']).resolve()))
        self.state(defaultRelease={'version': self.release['version'], 'digest': 'f' * 64})
        self.out.unlink()
        result = self.devlyn('omp', '-p', 'a task')
        self.assertIn('release-version-conflict', result.stderr)
        self.assertFalse(self.out.exists())

    def test_this_package_is_captured_once_when_no_release_is_recorded(self):
        result = self.devlyn('omp', '-p', 'a task')
        self.assertEqual(result.returncode, 0, result.stderr)
        root = self.home / '.devlyn/cli/releases/devlyn-cli' / self.release['version']
        self.assertEqual(self.launch()['env']['DEVLYN_HARNESS_ROOT'], str(root.resolve()))
        self.assertEqual(self.devlyn('omp', '-p', 'a task').returncode, 0)

    def test_a_harness_turned_off_launches_without_activation_and_says_so(self):
        self.state(machineChoice='none')
        result = self.devlyn('omp', '-p', 'a task', env={'FAKE_EXIT': '3'})
        self.assertEqual(result.returncode, 3, result.stderr)
        self.assertEqual(self.launch()['argv'], ['-p', 'a task'])
        self.assertIn('harness off for this project', result.stderr)
        # Nothing is planned, so the owner's arguments pass through whole.
        result = self.devlyn('claude', '--append-system-prompt', 'OWNER RULES', '--resume', 'abc', '-p', 'a task')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.launch()['argv'], ['--append-system-prompt', 'OWNER RULES', '--resume', 'abc', '-p', 'a task'])

    def test_a_signal_death_is_reproduced_and_the_run_folder_is_removed(self):
        result = self.devlyn('omp', '-p', 'a task', env={'FAKE_SIGNAL': str(int(signal.SIGTERM))})
        self.assertEqual(result.returncode, -signal.SIGTERM, result.stderr)
        self.assertFalse(Path(self.launch()['argv'][1]).exists())

    def test_sigterm_to_the_launcher_reaches_the_engine(self):
        slow = self.bin / 'omp'
        slow.write_text(FAKE.replace('/usr/bin/env python3', sys.executable, 1).replace(
            "print('engine stdout', flush=True)",
            "import time\nsignal.signal(signal.SIGTERM, lambda *_: sys.exit(42))\nprint('ready', flush=True)\ntime.sleep(30)"), encoding='utf-8')
        process = subprocess.Popen(['node', self.cli, 'run', 'omp', '-p', 'a task'], cwd=self.project, env=self.env,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        self.assertEqual(process.stdout.readline(), 'ready\n')
        process.terminate()
        self.assertEqual(process.wait(timeout=30), 42)
        process.stdout.close()
        process.stderr.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--package-root', type=Path)
    known, rest = parser.parse_known_args()
    PACKAGE_ROOT = known.package_root.resolve() if known.package_root else None
    unittest.main(argv=[sys.argv[0], *rest], verbosity=1)
