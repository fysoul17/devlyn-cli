"""Offline tests for 0265's schedule and two-lane driver. driver.py runs from a temp copy beside the fake
fixtures/driver/run_cell.py, so no Docker, keychain, network or model is touched."""
import contextlib
import datetime
import importlib.util
import inspect
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import threading
import time
import unittest
from unittest import mock
import urllib.error

HERE = Path(__file__).resolve().parent


def load(name, path):
    spec = importlib.util.spec_from_file_location('test_0265_driver_' + name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


generate = load('generate_cells', HERE / 'generate_cells.py')
_COPY = tempfile.TemporaryDirectory()  # driver.py loads run_cell from its own folder
shutil.copyfile(HERE / 'driver.py', Path(_COPY.name) / 'driver.py')
shutil.copyfile(HERE / 'fixtures/driver/run_cell.py', Path(_COPY.name) / 'run_cell.py')
driver = load('driver', Path(_COPY.name) / 'driver.py')

CELLS = driver.rows([str(HERE / 'cells.tsv')])
WINDOWS = {name: {'used': 0, 'resets': '2026-11-12T00:00:00+00:00'} for name in ('seven_day', 'five_hour')}
GIB = 2**30


def runtime(root, lane):
    """One lane's runtime file; every lane shares output, renewal lock and check lock (common brief)."""
    path = root / f'runtime-{lane or "smoke"}.json'
    path.write_text(json.dumps(dict(
        output=str(root / 'output'), lane=lane, auth=str(root / f'auth-{lane or "smoke"}'),
        renewal_lock=str(root / 'renewal.lock'), check_lock=str(root / 'check.lock'),
        caps={'seven_day': 95, 'five_hour': 95}, image='sha256:test', image_tarball=str(root / 'image.tar'),
        renewal_command=['claude', '-p', '--tools', '', '--strict-mcp-config', '--mcp-config', '{"mcpServers":{}}',
                         'ok'])))
    return path


def lane(root, name, slots=()):
    return driver.Driver(runtime(root, name), list(slots))


def events(root, name):
    log = root / 'output' / f'driver-{name}.log'
    return [json.loads(line) for line in log.read_text().splitlines()] if log.exists() else []


def seal(root, status='PASS'):
    (root / 'instructions.seal.json').write_text(json.dumps({'qualification': {'status': status}}))


def host(free=None):
    """The local holds pass: host disk at the floor exactly, the image present and the cell disk check passing."""
    stack = contextlib.ExitStack()
    stack.enter_context(mock.patch.object(driver.shutil, 'disk_usage', return_value=mock.Mock(
        free=driver.cell.HEADROOM_BYTES if free is None else free)))
    stack.enter_context(mock.patch.object(driver.Driver, 'image', return_value=True))
    stack.enter_context(mock.patch.object(driver.Driver, 'cell_disk', return_value=True))
    return stack


def snapshot(seconds, account=('account', 'org')):
    return {'expires': time.time() + seconds, 'account': list(account), 'access_token': 'fake'}


def row(name):
    return next(r for r in CELLS if r[0].startswith(name))


COMPLETE = dict(status='COMPLETE', scope_violations=[], teardown='CLEAN', identity={'status': 'MATCH'},
                owner_status='EXITED_0')
LAUNCH = dict(status='STOP', reason='B launch fault: run-package-missing', teardown='CLEAN',
              identity={'status': 'UNKNOWN'}, owner_status='EXITED_1')
MEMORY = dict(status='STOP', reason='memory kill: OOMKilled=True exit_code=137 owner EXITED_NONZERO', teardown='CLEAN',
              identity={'status': 'MATCH'}, owner_status='EXITED_NONZERO')
ACCOUNT = dict(status='STOP', reason='shared account fault during execution: codex authentication', teardown='CLEAN',
               identity={'status': 'UNVERIFIED'}, owner_status='EXITED_NONZERO')  # a refresh_token_reused at the start


def cells(output, outcomes):
    """A fake run_cell.run writing the next verdict listed for the slot; returns (fake, called slot names)."""
    called = []

    def run(_runtime, name, *_args, **_kwargs):
        called.append(name)
        verdict = outcomes[name].pop(0)
        (output / name).mkdir()
        (output / f'verdict-{name}.json').write_text(json.dumps(dict(verdict, cell=name)))
        return 2 if verdict['status'] == 'STOP' else 0
    return run, called


class Schedule(unittest.TestCase):
    def test_160_unique_slots_and_committed_files(self):
        written = generate.generate()
        self.assertEqual({name: len(rows) for name, rows in written.items()}, {'cells.tsv': 160, 'smoke.tsv': 4})
        self.assertEqual(written['smoke.tsv'], [('smoke-claude-A', 'SMOKE', 'A', 'claude'),
                                               ('smoke-claude-B', 'SMOKE', 'B', 'claude'),
                                               ('smoke-codex-A', 'SMOKE', 'A', 'codex'),
                                               ('smoke-codex-B', 'SMOKE', 'B', 'codex')])
        for name, rows in written.items():
            self.assertEqual(generate.render(rows), (HERE / name).read_text())
            self.assertTrue(all(len(line.split('\t')) == len(rows[0])
                                for line in (HERE / name).read_text().splitlines()))
        measured = written['cells.tsv']
        self.assertEqual(len({r[0] for r in measured}), 160)
        self.assertEqual(len({r[1:] for r in measured}), 160)
        for i, (name, task, arm, config, replicate) in enumerate(measured, 1):
            self.assertEqual(name, f'c{i:03d}-{task}-{config}-{arm}-r{replicate}')
        self.assertEqual(driver.rows([str(HERE / 'cells.tsv')]), [list(map(str, r)) for r in measured])

    def test_each_config_runs_core_then_screen(self):
        measured = generate.generate()['cells.tsv']
        for config in ('claude', 'codex'):
            own = [r for r in measured if r[3] == config]
            self.assertEqual(len(own), 80)
            self.assertEqual([(r[1], r[4]) for r in own[:32]],
                             [(task, rep) for rep in range(1, 9) for task in ('B5', 'F10') for _ in 'AB'])
            self.assertEqual([(r[1], r[4]) for r in own[32:]],
                             [(task, rep) for rep in range(1, 9) for task in ('D3', 'D4', 'F11') for _ in 'AB'])
        self.assertEqual({r[3] for r in measured[:80]}, {'claude'})

    def test_blocks_alternate_ab_and_ba(self):
        measured = generate.generate()['cells.tsv']
        for i in range(0, 160, 2):
            block = measured[i:i + 2]
            self.assertEqual({(r[1], r[3], r[4]) for r in block}, {(block[0][1], block[0][3], block[0][4])})
            self.assertEqual(''.join(r[2] for r in block), 'AB' if block[0][4] % 2 else 'BA')
        for task in ('B5', 'F10', 'D3', 'D4', 'F11'):
            for config in ('claude', 'codex'):
                for arm in 'AB':
                    self.assertEqual(sorted(r[4] for r in measured if r[1:4] == (task, arm, config)),
                                     list(range(1, 9)))


class LaneControls(unittest.TestCase):
    def test_lane_filter(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            claude, codex, smoke = (lane(root, name, CELLS) for name in ('claude', 'codex', None))
            self.assertEqual((len(claude.slots), len(codex.slots), len(smoke.slots)), (80, 80, 160))
            self.assertEqual({r[3] for r in claude.slots}, {'claude'})
            self.assertEqual({r[3] for r in codex.slots}, {'codex'})
            self.assertEqual(smoke.slots, CELLS)
            seal(root)
            with mock.patch.object(driver.cell, 'run') as run:
                with self.assertRaisesRegex(ValueError, 'own lane'):
                    claude.dispatch(row('c081-'))
                with self.assertRaisesRegex(ValueError, 'arm A/B'):
                    claude.dispatch(['c999-D3-claude-C-r1', 'D3', 'C', 'claude', '1'])
                run.assert_not_called()
            path = runtime(root, 'grok')
            with self.assertRaisesRegex(ValueError, 'lane must be'):
                driver.Driver(path, [])
            data = json.loads(path.read_text())
            del data['lane']
            path.write_text(json.dumps(data))
            with self.assertRaises(KeyError):
                driver.Driver(path, [])

    def test_status_and_log_named_per_lane(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for name in ('claude', 'codex', None):
                lane(root, name).event('fixture', lane=name)
            output = root / 'output'
            self.assertEqual(sorted(p.name for p in output.iterdir()),
                             ['driver-claude.lock', 'driver-claude.log', 'driver-codex.lock', 'driver-codex.log',
                              'driver-smoke.lock', 'driver-smoke.log',
                              'driver-status-claude.json', 'driver-status-codex.json', 'driver-status-smoke.json'])
            for name, label in (('claude', 'claude'), ('codex', 'codex'), (None, 'smoke')):
                self.assertEqual([e['lane'] for e in events(root, label)], [name])
                self.assertEqual(json.loads((output / f'driver-status-{label}.json').read_text())['current']['lane'],
                                 name)

    def test_status_and_log_replaced_atomically(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            d = lane(root, 'claude')
            d.event('first')
            replaced = []
            real = driver.os.replace

            def record(source, target):
                replaced.append((Path(source), Path(target), Path(source).read_text()))
                return real(source, target)

            with mock.patch.object(driver.os, 'replace', side_effect=record):
                d.event('second')
            self.assertEqual([target.name for _, target, _ in replaced], ['driver-claude.log', 'driver-status-claude.json'])
            for source, target, text in replaced:
                self.assertEqual(source.parent, target.parent)
                self.assertEqual(text, target.read_text())
            self.assertEqual([e['event'] for e in events(root, 'claude')], ['first', 'second'])
            before = d.status_path.read_text()

            def interrupted(source, target):
                if Path(target) == d.status_path:
                    raise OSError('disk full')
                return real(source, target)

            with mock.patch.object(driver.os, 'replace', side_effect=interrupted):
                with self.assertRaisesRegex(OSError, 'disk full'):
                    d.event('third')
            self.assertEqual(d.status_path.read_text(), before)
            self.assertEqual(json.loads(before)['current']['event'], 'second')
            self.assertEqual([p.name for p in (root / 'output').iterdir() if p.name.startswith('.')], [])

    def test_cross_lane_latch_names_the_latched_lane(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            seal(root)
            claude, codex = lane(root, 'claude'), lane(root, 'codex')
            codex.assert_active()
            bad = dict(COMPLETE, scope_violations=['outside'])
            (root / 'output/verdict-c001-B5-claude-A-r1.json').write_text(json.dumps(bad))
            claude.latch_for('c001-B5-claude-A-r1', bad)
            with mock.patch.object(driver.cell, 'run') as run:
                codex.lock.close()  # the codex process ends; its restart sees the latch too
                for d in (codex, lane(root, 'codex'), claude):
                    with self.assertRaisesRegex(RuntimeError, 'harm latch in lane claude'):
                        d.assert_active()
                with self.assertRaisesRegex(RuntimeError, 'harm latch in lane claude'):
                    codex.dispatch(row('c081-'))
                run.assert_not_called()
            amendment = root / 'amendment-1.md'
            amendment.write_text('dated amendment')
            claude.clear_latch(amendment)
            codex.assert_active()
            smoke = lane(root, None)
            smoke.latch('smoke-codex-B', 'identity MISMATCH')
            with self.assertRaisesRegex(RuntimeError, 'harm latch in lane smoke'):
                codex.assert_active()


class Renewal(unittest.TestCase):
    def test_two_lanes_at_300_seconds_run_one_renewal(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            drivers = [lane(root, 'claude'), lane(root, 'codex')]
            keychain = {'expires': time.time() + 200}
            barrier = threading.Barrier(2)
            seen = set()
            commands = []

            def credential(_runtime):
                current = dict(expires=keychain['expires'], account=['account', 'org'], access_token='fake')
                if threading.get_ident() not in seen:  # both lanes read the old expiry before either renews
                    seen.add(threading.get_ident())
                    barrier.wait(timeout=10)
                return current

            def shell(argv, **_kwargs):
                if argv[:2] == ['claude', '--help']:
                    return subprocess.CompletedProcess(argv, 0, stdout='help')
                commands.append(argv)
                time.sleep(0.3)  # the other lane now waits on the lock
                keychain['expires'] = time.time() + 28800
                return subprocess.CompletedProcess(argv, 0, stdout='')

            results = {}
            with mock.patch.object(driver, 'credential', side_effect=credential), \
                    mock.patch.object(driver, 'renewal_command', return_value=['claude', '-p', 'renew']), \
                    mock.patch.object(driver.subprocess, 'run', side_effect=shell), \
                    mock.patch.object(driver.cell, 'claude_limits', return_value=WINDOWS), \
                    host():
                threads = [threading.Thread(target=lambda d=d: results.__setitem__(d.lane, d.ready()))
                           for d in drivers]
                for thread in threads:
                    thread.start()
                for thread in threads:
                    thread.join(timeout=30)
            self.assertEqual(results, {'claude': True, 'codex': True})
            self.assertEqual(commands, [['claude', '-p', 'renew']])
            kinds = {name: [e['event'] for e in events(root, name)] for name in ('claude', 'codex')}
            renewer = next(name for name, k in kinds.items() if 'renewal_attempt' in k)
            other = 'codex' if renewer == 'claude' else 'claude'
            self.assertEqual(kinds[renewer], ['renewal_attempt', 'renewed'])
            self.assertEqual(kinds[other], ['renewal_skipped'])
            self.assertTrue((root / 'renewal.lock').is_file())

    def test_failed_renewal_is_never_repeated_by_another_lane(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            claude, codex = lane(root, 'claude'), lane(root, 'codex')
            stuck = snapshot(200)
            commands = []

            def shell(argv, **_kwargs):
                if argv[:2] != ['claude', '--help']:
                    commands.append(argv)
                return subprocess.CompletedProcess(argv, 0, stdout='help')

            with mock.patch.object(driver, 'credential', return_value=stuck), \
                    mock.patch.object(driver, 'renewal_command', return_value=['claude', '-p', 'renew']), \
                    mock.patch.object(driver.subprocess, 'run', side_effect=shell), \
                    mock.patch.object(driver.cell, 'claude_limits') as limits, host():
                self.assertFalse(claude.ready())
                self.assertFalse(codex.ready())
                self.assertFalse(claude.ready())
            self.assertEqual(len(commands), 1)
            limits.assert_not_called()
            self.assertEqual([e['reason'] for e in events(root, 'claude') if e['event'] == 'hold'],
                             ['renewal did not advance expiry', 'renewal needs owner'])
            self.assertEqual([(e['event'], e.get('reason')) for e in events(root, 'codex')],
                             [('hold', 'renewal needs owner')])


class Guards(unittest.TestCase):
    def test_token_guard_3600_for_a_cell_and_1500_for_an_assessor_redo(self):
        self.assertEqual(driver.cell.MIN_TOKEN_SECONDS, 3600)
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            d = lane(root, 'claude')
            for minimum, seconds, ready in ((3600, 3595, False), (3600, 3605, True),
                                            (1500, 1495, False), (1500, 1505, True)):
                with self.subTest(minimum=minimum, seconds=seconds), \
                        mock.patch.object(driver, 'credential', return_value=snapshot(seconds)), \
                        mock.patch.object(driver.cell, 'claude_limits', return_value=WINDOWS) as limits, \
                        host():
                    self.assertEqual(d.ready(minimum), ready)
                    self.assertEqual(limits.call_count, int(ready))
                    if not ready:
                        self.assertEqual(events(root, 'claude')[-1]['reason'], 'awaiting renewal window')
            slots = [row('c001-'), row('c002-')]
            d.lock.close()
            d = lane(root, 'claude', slots)
            (d.output / f'verdict-{slots[1][0]}.json').write_text(json.dumps(dict(
                status='STOP', reason='assessment failed: timeout', identity={'status': 'MATCH'},
                owner_status='EXITED_0')))
            with mock.patch.object(d, 'ready', return_value=True) as ready, \
                    mock.patch.object(d, 'dispatch', return_value=True):
                d.run()
            self.assertEqual([call.args[0] for call in ready.call_args_list], [3600, 1500])

    def test_one_usage_read_per_dispatch_and_429_holds_60_seconds(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            seal(root)
            d = lane(root, 'claude', [row('c001-'), row('c002-')])
            run, called = cells(d.output, {r[0]: [COMPLETE] for r in d.slots})
            limited = urllib.error.HTTPError('https://api.anthropic.com/api/oauth/usage', 429,
                                             'Too Many Requests', None, None)
            with mock.patch.object(driver, 'credential', return_value=snapshot(20000)), \
                    mock.patch.object(driver.cell, 'claude_limits', side_effect=[limited, WINDOWS, WINDOWS]) as limits, \
                    mock.patch.object(driver.cell, 'run', side_effect=run), \
                    mock.patch.object(driver.time, 'sleep') as sleep, host():
                d.run()
            self.assertEqual(called, [r[0] for r in d.slots])
            self.assertEqual(limits.call_count, 3)
            self.assertEqual([call.args for call in sleep.call_args_list], [(60,)])
            self.assertEqual([e['reason'] for e in events(root, 'claude') if e['event'] == 'hold'],
                             ['Claude window check failed: HTTP Error 429: Too Many Requests'])
            source = (HERE / 'driver.py').read_text()
            self.assertEqual(source.count('claude_limits('), 1)

    def test_95_percent_window_holds_and_94_dispatches(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            d = lane(root, 'codex')
            for used, ready in ((95, False), (94, True)):
                windows = {name: {'used': used, 'resets': '2026-11-12T00:00:00+00:00'} for name in WINDOWS}
                with self.subTest(used=used), \
                        mock.patch.object(driver, 'credential', return_value=snapshot(20000)), \
                        mock.patch.object(driver.cell, 'claude_limits', return_value=windows), \
                        host():
                    self.assertEqual(d.ready(), ready)
            self.assertEqual([e['reason'] for e in events(root, 'codex') if e['event'] == 'hold'],
                             ['Claude window near exhaustion'])

    def test_the_windows_the_account_reports(self):
        # O8: the seven-day window always; five-hour and model-scoped weekly windows when reported; nothing else.
        week, five = {'used': 10, 'resets': '2026-11-15T00:00:00+00:00'}, {'used': 10, 'resets': '2026-11-11T20:00:00+00:00'}
        cases = [({'seven_day': week}, True, None),  # the account of 2026-11-11 reports no five-hour window
                 ({'seven_day': week, 'nimbus_quill': {'used': 100.0, 'resets': None}}, True, None),
                 ({'seven_day': week, 'seven_day_opus': dict(week, used=94)}, True, None),
                 ({'seven_day': week, 'seven_day_opus': dict(week, used=95)}, False, 'Claude window near exhaustion'),
                 ({'seven_day': week, 'five_hour': dict(five, used=95)}, False, 'Claude window near exhaustion'),
                 ({'five_hour': five}, False, 'Claude window evidence unavailable: no seven-day window'),
                 ({}, False, 'Claude window evidence unavailable: no seven-day window')]
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            d = lane(root, 'claude')
            for windows, ready, reason in cases:
                with self.subTest(windows=sorted(windows)), \
                        mock.patch.object(driver, 'credential', return_value=snapshot(20000)), \
                        mock.patch.object(driver.cell, 'claude_limits', return_value=windows), host():
                    self.assertEqual(d.ready(), ready)
                    holds = [e for e in events(root, 'claude') if e['event'] == 'hold']
                    self.assertEqual(holds[-1]['reason'] if not ready else None, reason)
                    if reason == 'Claude window near exhaustion':
                        self.assertNotIn('nimbus_quill', holds[-1]['windows'])
            d.state['split_wait'] = {}
            with mock.patch.object(driver, 'credential', return_value=snapshot(20000)), host(), \
                    mock.patch.object(driver.cell, 'claude_limits',
                                      return_value={'seven_day': week, 'seven_day_opus': dict(week, used=99)}):
                self.assertFalse(d.ready(slot='c002', previous='c001'))  # a split block waits on the weekly limit
            self.assertEqual(d.state['split_wait']['c002']['resets'], {'seven_day_opus': week['resets']})
            with mock.patch.object(driver, 'credential', return_value=snapshot(20000)), host(), \
                    mock.patch.object(driver.cell, 'claude_limits', return_value={'seven_day': week}):
                self.assertTrue(d.ready(slot='c002', previous='c001'))  # the waited window is gone: no KeyError

    def test_disk_floor_16_gib_from_run_cell(self):
        self.assertEqual(driver.cell.HEADROOM_BYTES, 16 * GIB)
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            d = lane(root, 'claude')
            with mock.patch.object(driver, 'credential', return_value=snapshot(20000)) as credential, \
                    mock.patch.object(driver.cell, 'claude_limits', return_value=WINDOWS) as limits:
                with host(16 * GIB - 1):
                    self.assertFalse(d.ready())
                credential.assert_not_called()
                limits.assert_not_called()
                self.assertEqual(events(root, 'claude')[-1]['reason'],
                                 f'output volume has {16 * GIB - 1} bytes free, below {16 * GIB}')
                with host(16 * GIB):
                    self.assertTrue(d.ready())

    def test_cell_disk_floor_inside_the_image(self):
        for total in (100 * GIB, 2 * 1024 * GIB):
            floor = max(10 * GIB, (total + 49) // 50) + 2 * GIB
            for short, ready in (('/cell', False), ('/tmp', False), (None, True)):
                with self.subTest(total=total, short=short), tempfile.TemporaryDirectory() as temp:
                    root = Path(temp)
                    measured = {path: {'total': total, 'used': 0, 'free': floor - (path == short)}
                                for path in ('/cell', '/tmp')}
                    docker = mock.Mock(return_value=subprocess.CompletedProcess([], 0, stdout=json.dumps(measured)))
                    with mock.patch.object(driver, 'credential', return_value=snapshot(20000)), \
                            mock.patch.object(driver.cell, 'claude_limits', return_value=WINDOWS) as limits, \
                            mock.patch.object(driver.Driver, 'image', return_value=True), \
                            mock.patch.object(driver.shutil, 'disk_usage', return_value=mock.Mock(free=20 * GIB)), \
                            mock.patch.object(driver.subprocess, 'run', docker):
                        d = lane(root, 'codex')
                        self.assertEqual(d.ready(), ready)
                        self.assertEqual(limits.call_count, int(ready))
                        d.lock.close()
                        if not ready:  # a restart measures again and holds again
                            self.assertFalse(lane(root, 'codex').ready())
                    argv = docker.call_args.args[0]
                    self.assertEqual(argv[:3], ['docker', 'run', '--rm'])
                    self.assertIn(f'type=bind,src={root / "output"},dst=/cell,readonly', argv)
                    self.assertIn('type=volume,dst=/tmp', argv)
                    self.assertEqual(argv[argv.index('--network') + 1], 'none')
                    self.assertEqual(argv[-4:], ['sha256:test', 'python3', '-c', driver.DISK_PROBE])
                    holds = [e['reason'] for e in events(root, 'codex') if e['event'] == 'hold']
                    self.assertEqual(holds, [] if ready else [
                        f'cell disk below the delivery floor: {short} has {floor - 1} bytes free, below {floor}'] * 2)
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            failed = subprocess.CalledProcessError(125, ['docker', 'run'], stderr='no space left on device')
            with mock.patch.object(driver.subprocess, 'run', side_effect=failed):
                self.assertFalse(lane(root, 'codex').cell_disk())
            self.assertTrue(events(root, 'codex')[-1]['reason'].startswith('cell disk check failed:'))
            probe = driver.DISK_PROBE.replace("('/cell', '/tmp')", repr((temp, str(HERE))))
            measured = json.loads(subprocess.run(['python3', '-c', probe], check=True, capture_output=True,
                                                 text=True).stdout)
            self.assertEqual({path: sorted(value) for path, value in measured.items()},
                             {temp: ['free', 'total', 'used'], str(HERE): ['free', 'total', 'used']})

    def test_measured_dispatch_needs_a_pass_seal(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            d = lane(root, 'claude')
            measured = row('c001-')
            run, called = cells(d.output, {measured[0]: [COMPLETE], 'smoke-claude-A': [COMPLETE]})
            with mock.patch.object(driver.cell, 'run', side_effect=run):
                for status in (None, 'PENDING', 'FAIL'):
                    if status:
                        seal(root, status)
                    with self.subTest(status=status), self.assertRaisesRegex(RuntimeError, 'SMOKE qualification'):
                        d.dispatch(measured)
                self.assertEqual(called, [])
                (root / 'instructions.seal.json').unlink()
                self.assertTrue(lane(root, None).dispatch(['smoke-claude-A', 'SMOKE', 'A', 'claude']))
                seal(root)
                self.assertTrue(d.dispatch(measured))
            self.assertEqual(called, ['smoke-claude-A', measured[0]])

    def test_seven_day_deadline_from_the_shared_smoke_start(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            now = datetime.datetime.now(datetime.timezone.utc)
            started = root / 'output/smoke-claude-A/run/started.json'
            started.parent.mkdir(parents=True)
            for age, active in ((datetime.timedelta(days=7, seconds=-60), True),
                                (datetime.timedelta(days=7, seconds=60), False)):
                started.write_text(json.dumps({'started_at': (now - age).timestamp()}))
                for name in ('claude', 'codex'):
                    with self.subTest(age=age, lane=name):
                        (root / f'output/driver-status-{name}.json').unlink(missing_ok=True)
                        d = lane(root, name)
                        self.assertEqual(d.state['first_smoke_dispatch'],
                                         datetime.datetime.fromtimestamp((now - age).timestamp(),
                                                                         datetime.timezone.utc).isoformat())
                        if active:
                            d.assert_active()
                        else:
                            with self.assertRaisesRegex(RuntimeError, '7-day deadline reached'):
                                d.assert_active()
                            self.assertEqual(events(root, name)[-1]['reason'], '7-day deadline reached')
                        d.lock.close()

    def test_a_lane_adopts_the_fixed_caps_and_refuses_any_other(self):
        """G1: a fresh lane status adopts SMOKE's start with caps 95/95 (allowed); a runtime with 0257's 85/70 caps,
        or a status file that registered them, is refused (violating)."""
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            started = root / 'output/smoke-codex-B/run/started.json'
            started.parent.mkdir(parents=True)
            started.write_text(json.dumps({'started_at': time.time() - 60}))
            d = lane(root, 'claude')
            self.assertEqual(d.state['registered_caps'], {'seven_day': 95, 'five_hour': 95})
            d.lock.close()
            path = runtime(root, 'codex')
            path.write_text(json.dumps(dict(json.loads(path.read_text()), caps={'seven_day': 70, 'five_hour': 85})))
            with self.assertRaisesRegex(ValueError, 'registration caps must be seven_day=95 and five_hour=95'):
                driver.Driver(path, [])
            status = root / 'output/driver-status-claude.json'
            status.write_text(json.dumps(dict(json.loads(status.read_text()),
                                              registered_caps={'seven_day': 70, 'five_hour': 85})))
            with self.assertRaisesRegex(RuntimeError, 'registered caps differ from 95/95'):
                lane(root, 'claude')

    def test_finished_verdict_is_skipped_on_restart(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            seal(root)
            first, second = row('c081-'), row('c082-')
            d = lane(root, 'codex', [first, second])
            (d.output / f'verdict-{first[0]}.json').write_text(json.dumps(COMPLETE))
            run, called = cells(d.output, {second[0]: [COMPLETE]})
            with mock.patch.object(d, 'ready', return_value=True) as ready, \
                    mock.patch.object(driver.cell, 'run', side_effect=run):
                d.run()
            self.assertEqual(called, [second[0]])
            ready.assert_called_once()
            self.assertEqual([(e['event'], e.get('cell')) for e in events(root, 'codex')],
                             [('skip_finished', first[0]), ('run', second[0]), ('complete', None)])


class Faults(unittest.TestCase):
    def run_lane(self, root, name, slots, outcomes):
        seal(root)
        d = lane(root, name, slots)
        run, called = cells(d.output, outcomes)
        with mock.patch.object(d, 'ready', return_value=True), \
                mock.patch.object(driver.cell, 'run', side_effect=run), \
                mock.patch.object(driver.time, 'sleep'):
            try:
                d.run()
            finally:
                self.called = called
                d.lock.close()  # the lane's process ends
        return d

    def test_launch_fault_is_archived_and_redispatched_unless_second_in_a_row(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            slots = [row(f'c00{i}-') for i in range(1, 5)]  # B5 then F10, AB on r1
            d = self.run_lane(root, 'claude', slots, {
                slots[0][0]: [COMPLETE], slots[1][0]: [LAUNCH, COMPLETE],
                slots[2][0]: [COMPLETE], slots[3][0]: [LAUNCH, COMPLETE]})
            self.assertEqual(self.called, [slots[0][0], slots[1][0], slots[1][0], slots[2][0], slots[3][0],
                                           slots[3][0]])
            for name in (slots[1][0], slots[3][0]):
                self.assertEqual(json.loads((d.output / f'verdict-{name}.stop-1.json').read_text())['reason'],
                                 LAUNCH['reason'])
                self.assertTrue((d.output / f'{name}.stop-1').is_dir())
                self.assertEqual(d.verdict(name)['status'], 'COMPLETE')
            self.assertNotIn('harm_latch', d.state)
            self.assertNotIn('launch_fault', d.state)

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            slots = [row('c002-')]
            with self.assertRaisesRegex(RuntimeError, 'harm latch in lane claude'):
                self.run_lane(root, 'claude', slots, {slots[0][0]: [LAUNCH, dict(LAUNCH, reason='B launch fault: x')]})
            name = slots[0][0]
            self.assertEqual(self.called, [name, name])
            latch = json.loads((root / 'output/driver-status-claude.json').read_text())['harm_latch']
            self.assertEqual(latch['cell'], name)
            self.assertIn('second B launch fault in a row', latch['reason'])
            self.assertEqual(json.loads((root / f'output/verdict-{name}.json').read_text())['reason'],
                             'B launch fault: x')
            self.assertTrue((root / f'output/verdict-{name}.stop-1.json').is_file())
            with self.assertRaisesRegex(RuntimeError, 'harm latch in lane claude'):
                lane(root, 'codex').assert_active()

    def test_launch_fault_identity_and_teardown(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            d = lane(root, 'claude')
            for fault in (LAUNCH, MEMORY, ACCOUNT):  # a redispatched fault can leave no model record
                for status in ('UNKNOWN', 'UNVERIFIED', 'MATCH'):
                    d.latch_for('slot', dict(fault, identity={'status': status}))
            self.assertNotIn('harm_latch', d.state)
            for fault in (LAUNCH, ACCOUNT):  # a wrong model always latches
                d.latch_for('slot', dict(fault, identity={'status': 'MISMATCH'}))
                self.assertEqual(d.state.pop('harm_latch')['reason'], 'identity MISMATCH')
            d.latch_for('slot', dict(ACCOUNT, reason='instruction assertion: x'))  # unexplained gaps latch as before
            self.assertEqual(d.state.pop('harm_latch')['reason'], 'identity UNVERIFIED')
            d.latch_for('slot', dict(ACCOUNT, reason='instruction assertion: x', identity={'status': 'UNKNOWN'}))
            self.assertEqual(d.state['harm_latch']['reason'], 'identity UNKNOWN')
        for verdict in (LAUNCH, MEMORY):
            with self.subTest(reason=verdict['reason']), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                seal(root)
                d = lane(root, 'claude')
                name = row('c002-')[0]
                (d.output / name).mkdir()
                (d.output / f'verdict-{name}.json').write_text(json.dumps(dict(verdict, teardown='FAILED')))
                with mock.patch.object(driver.cell, 'run') as run:
                    with self.assertRaisesRegex(RuntimeError, f'STOP {verdict["reason"]}'):
                        d.dispatch(row('c002-'))
                    run.assert_not_called()
                self.assertFalse((d.output / f'verdict-{name}.stop-1.json').exists())

    def test_memory_kill_and_account_fault_redispatched_once_then_both_lanes_stop(self):
        for fault in (MEMORY, ACCOUNT):
            with self.subTest(fault=fault['reason']), tempfile.TemporaryDirectory() as temp:  # allowed: once per slot
                root = Path(temp)
                slots = [row('c081-'), row('c082-')]
                d = self.run_lane(root, 'codex', slots, {slots[0][0]: [fault, COMPLETE], slots[1][0]: [fault, COMPLETE]})
                self.assertEqual(self.called, [slots[0][0], slots[0][0], slots[1][0], slots[1][0]])
                self.assertTrue(all(d.verdict(r[0])['status'] == 'COMPLETE' for r in slots))
                self.assertNotIn('harm_latch', d.state)

            with self.subTest(fault=fault['reason'], repeat=True), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                name = row('c081-')[0]
                with self.assertRaisesRegex(RuntimeError, f'{name}: STOP {fault["reason"]}'):
                    self.run_lane(root, 'codex', [row('c081-')], {name: [fault, fault]})
                self.assertEqual(self.called, [name, name])
                self.assertEqual(json.loads((root / f'output/verdict-{name}.json').read_text())['reason'],
                                 fault['reason'])
                self.assertTrue((root / f'output/verdict-{name}.stop-1.json').is_file())
                latch = json.loads((root / 'output/driver-status-codex.json').read_text())['harm_latch']
                self.assertEqual((latch['cell'], latch['reason']), (name, f'STOP {fault["reason"]}'))
                with self.assertRaisesRegex(RuntimeError, 'harm latch in lane codex'):  # the other lane stops too
                    lane(root, 'claude').assert_active()
                with mock.patch.object(driver.cell, 'run') as run:  # a restart keeps the STOP and the latch
                    with self.assertRaisesRegex(RuntimeError, 'harm latch in lane codex'):
                        lane(root, 'codex').dispatch(row('c081-'))
                    run.assert_not_called()

        with tempfile.TemporaryDirectory() as temp:  # each kind counts on its own: a memory kill, then an account fault
            root = Path(temp)
            name = row('c081-')[0]
            d = self.run_lane(root, 'codex', [row('c081-')], {name: [MEMORY, ACCOUNT, COMPLETE]})
            self.assertEqual(self.called, [name] * 3)
            self.assertEqual(d.verdict(name)['status'], 'COMPLETE')

    def test_a_restart_finds_a_repeated_fault_and_latches(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            seal(root)
            name = row('c001-')[0]
            (root / 'output').mkdir()
            (root / f'output/verdict-{name}.stop-1.json').write_text(json.dumps(dict(ACCOUNT, cell=name)))
            (root / f'output/verdict-{name}.json').write_text(json.dumps(dict(ACCOUNT, cell=name)))
            with mock.patch.object(driver.cell, 'run') as run:
                with self.assertRaisesRegex(RuntimeError, f'{name}: STOP shared account fault'):
                    lane(root, 'claude').dispatch(row('c001-'))
                run.assert_not_called()
            with self.assertRaisesRegex(RuntimeError, 'harm latch in lane claude'):
                lane(root, 'codex').assert_active()


    def test_assertion_stop_latches_both_lanes(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            name = row('c002-')[0]
            stop = dict(status='STOP', reason='instruction assertion: B status line missing', teardown='CLEAN',
                        identity={'status': 'MATCH'}, owner_status='EXITED_0')
            with self.assertRaisesRegex(RuntimeError, 'STOP instruction assertion'):
                self.run_lane(root, 'claude', [row('c002-')], {name: [stop]})
            self.assertEqual(self.called, [name])
            latch = json.loads((root / 'output/driver-status-claude.json').read_text())['harm_latch']
            self.assertEqual((latch['cell'], latch['reason']), (name, 'STOP ' + stop['reason']))
            with self.assertRaisesRegex(RuntimeError, 'harm latch in lane claude'):
                lane(root, 'codex').assert_active()
            with mock.patch.object(driver.cell, 'run') as run:  # a restart keeps both the STOP and the latch
                with self.assertRaisesRegex(RuntimeError, 'harm latch in lane claude'):
                    lane(root, 'claude', [row('c002-')]).dispatch(row('c002-'))
                run.assert_not_called()
        with tempfile.TemporaryDirectory() as temp:  # a STOP found on restart with no latch yet latches too
            root = Path(temp)
            seal(root)
            d = lane(root, 'codex')
            name = row('c081-')[0]
            (d.output / f'verdict-{name}.json').write_text(json.dumps(dict(stop, cell=name)))
            with mock.patch.object(driver.cell, 'run') as run:
                with self.assertRaisesRegex(RuntimeError, 'STOP instruction assertion'):
                    d.dispatch(row('c081-'))
                run.assert_not_called()
            with self.assertRaisesRegex(RuntimeError, 'harm latch in lane codex'):
                lane(root, 'claude').assert_active()

    def test_quota_fault_archived_and_assessor_fault_regraded(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            name = row('c001-')[0]
            quota = dict(status='STOP', reason='shared account fault during execution: quota',
                         identity={'status': 'MATCH'}, owner_status='EXITED_1')
            d = self.run_lane(root, 'claude', [row('c001-')], {name: [quota, COMPLETE]})
            self.assertEqual(self.called, [name, name])
            self.assertTrue((d.output / f'verdict-{name}.stop-1.json').is_file())
            path = d.output / f'verdict-{name}.json'
            path.write_text(json.dumps(dict(status='STOP', reason='assessment failed: timeout',
                                            identity={'status': 'MATCH'}, owner_status='EXITED_0')))
            d.approved_account = ['account', 'org']

            def regrade(*_args, **_kwargs):
                path.write_text(json.dumps(COMPLETE))
                return 0

            with mock.patch.object(driver.cell, 'regrade', side_effect=regrade) as regraded, \
                    mock.patch.object(driver.cell, 'run') as run:
                self.assertTrue(d.dispatch(row('c001-')))
                run.assert_not_called()
            regraded.assert_called_once_with(d.runtime_path, name, expected_account=['account', 'org'])

    def test_docker_loss_is_proven_archived_and_redispatched(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            seal(root)
            d = lane(root, 'claude')
            name = row('c001-')[0]
            container, volume, cid = 'devlyn-0231-owner', 'devlyn-0233-tmp-owner', 'a' * 64
            (d.output / name / 'run').mkdir(parents=True)
            (d.output / name / 'run/started.json').write_text(json.dumps({
                'create_argv': ['create', '--name', container, f'type=volume,src={volume},dst=/tmp'],
                'tmp_volume': volume, 'started_at': time.time()}))
            (d.output / f'verdict-{name}.json').write_text(json.dumps(dict(
                status='STOP', teardown='FAILED', identity={'status': 'MATCH'}, owner_status='EXITED_NONZERO',
                reason='teardown failed: Cannot connect to the Docker daemon at unix:///docker.sock')))
            removed = []
            inspected = dict(Id=cid, Name='/' + container, Config={'Labels': {'devlyn.task': '0233'}},
                             Mounts=[{'Type': 'volume', 'Name': volume}],
                             State={'Running': False, 'Pid': 0, 'Status': 'exited'})

            def docker(argv, **_kwargs):
                if argv[1:3] == ['ps', '-aq']:
                    value = '' if removed or 'name=' in argv[-1] else cid
                elif argv[1] == 'inspect':
                    value = json.dumps([inspected])
                elif argv[1:3] == ['volume', 'ls']:
                    value = ''
                else:
                    removed.append(argv[1:])
                    value = ''
                return subprocess.CompletedProcess(argv, 0, stdout=value)

            run, called = cells(d.output, {name: [COMPLETE]})
            with mock.patch.object(driver.subprocess, 'run', side_effect=docker), \
                    mock.patch.object(driver.cell, 'run', side_effect=run):
                self.assertTrue(d.dispatch(row('c001-')))
            self.assertEqual(removed, [['rm', cid], ['volume', 'rm', volume]])
            self.assertEqual(called, [name])
            self.assertTrue((d.output / f'{name}.stop-1/run/started.json').is_file())


class OneProcessPerLane(unittest.TestCase):
    def test_a_lane_runs_once_and_other_lanes_are_free(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            first = lane(root, 'claude')
            with self.assertRaisesRegex(RuntimeError, 'lane claude already has a driver process'):
                lane(root, 'claude')
            others = [lane(root, 'codex'), lane(root, None)]  # allowed: the other lanes
            path = runtime(root, 'claude')
            amendment = root / 'amendment.md'
            amendment.write_text('x')
            with self.assertRaisesRegex(RuntimeError, 'already has a driver process'):  # no latch clearing meanwhile
                driver.Driver(path, []).clear_latch(amendment)
            first.lock.close()
            lane(root, 'claude')  # allowed: the first process ended
            for other in others:
                other.lock.close()

    def test_the_lock_holds_across_processes_and_is_released_when_its_process_ends(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'output').mkdir()
            holder = subprocess.Popen(['python3', '-c', (
                'import fcntl, sys; lock = open(sys.argv[1], "a"); fcntl.flock(lock, fcntl.LOCK_EX); '
                'print("held", flush=True); sys.stdin.read()'), str(root / 'output/driver-codex.lock')],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
            try:
                self.assertEqual(holder.stdout.readline().strip(), 'held')
                with self.assertRaisesRegex(RuntimeError, 'lane codex already has a driver process'):
                    lane(root, 'codex')
                self.assertFalse((root / 'output/driver-status-codex.json').exists())  # refused before any write
            finally:
                holder.stdin.close()
                holder.wait(10)
            lane(root, 'codex').event('started')


class RunCellContract(unittest.TestCase):
    @unittest.skipUnless((HERE / 'run_cell.py').is_file(), 'X/run_cell.py is written by the cell item')
    def test_real_run_cell_has_what_the_driver_calls(self):
        real = load('run_cell', HERE / 'run_cell.py')
        self.assertEqual(real.MIN_TOKEN_SECONDS, 3600)
        self.assertEqual(real.HEADROOM_BYTES, 16 * GIB)
        self.assertTrue(callable(real.base.fingerprint) and callable(real.urllib.request.urlopen))
        for name, keywords in (('run', ['expected_account']), ('regrade', ['expected_account']),
                               ('claude_limits', []), ('image_identity', [])):
            parameters = inspect.signature(getattr(real, name)).parameters
            self.assertTrue(all(parameters[k].kind is inspect.Parameter.KEYWORD_ONLY for k in keywords), name)
        fake = load('fake_run_cell', HERE / 'fixtures/driver/run_cell.py')
        for name in ('run', 'regrade', 'claude_limits', 'image_identity'):
            self.assertEqual(list(inspect.signature(getattr(real, name)).parameters),
                             list(inspect.signature(getattr(fake, name)).parameters), name)


if __name__ == '__main__':
    unittest.main()
