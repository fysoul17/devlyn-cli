"""Offline tests for 0266's schedules and two-lane driver. driver.py runs from a temp copy beside the fake
fixtures/driver/run_cell.py, so no Docker, keychain, network or model is touched."""
import contextlib
import datetime
import http.client
import importlib.util
import inspect
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import threading
import time
import types
import unittest
from unittest import mock
import urllib.error

HERE = Path(__file__).resolve().parent


def load(name, path):
    spec = importlib.util.spec_from_file_location('test_0266_driver_' + name, path)
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


def go(root, candidate='K3'):
    """A GO screen decision: lanes whose rows hold the registered C start only with one (prepare.selected)."""
    (root / 'screen-decision.json').write_text(json.dumps(dict(decision='GO', candidate=candidate)))


def lane(root, name, slots=(), decided=True):
    if decided and not (root / 'screen-decision.json').exists():
        go(root)
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


def refused(code=429, retry_after=None):
    """The usage endpoint's refusal as urlopen raises it: an HTTPError with the response's headers."""
    headers = http.client.HTTPMessage()
    if retry_after is not None:
        headers['Retry-After'] = retry_after
    return urllib.error.HTTPError('https://api.anthropic.com/api/oauth/usage', code, http.client.responses[code],
                                  headers, None)


def unread(root, name):
    """The lane's window_unread events (amendment 1), without their time."""
    return [{k: v for k, v in e.items() if k not in ('at', 'event')}
            for e in events(root, name) if e['event'] == 'window_unread']


def latched(root, name):
    """The lane's harm latch as its status file holds it (None: no latch, or no status written)."""
    path = root / 'output' / f'driver-status-{name}.json'
    return json.loads(path.read_text()).get('harm_latch') if path.is_file() else None


COMPLETE = dict(status='COMPLETE', scope_violations=[], teardown='CLEAN', identity={'status': 'MATCH'},
                owner_status='EXITED_0')
LAUNCH = dict(status='STOP', reason='launch fault: run-package-missing', teardown='CLEAN',
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
    def test_counts_order_and_committed_files(self):
        written = generate.generate()
        self.assertEqual({name: len(rows) for name, rows in written.items()},
                         {'cells.tsv': 176, 'screen.tsv': 18, 'smoke.tsv': 4})
        self.assertEqual(written['smoke.tsv'], [('smoke-claude-B', 'SMOKE', 'B', 'claude'),
                                               ('smoke-claude-C', 'SMOKE', 'C-K3', 'claude'),
                                               ('smoke-codex-B', 'SMOKE', 'B', 'codex'),
                                               ('smoke-codex-C', 'SMOKE', 'C-K3', 'codex')])
        for name, rows in written.items():
            self.assertEqual(generate.render(rows), (HERE / name).read_text())
            self.assertTrue(all(len(line.split('\t')) == len(rows[0])
                                for line in (HERE / name).read_text().splitlines()))
        measured = written['cells.tsv']
        self.assertEqual(len({r[0] for r in measured}), 176)
        self.assertEqual(len({r[1:] for r in measured}), 176)
        for i, (name, task, arm, config, replicate) in enumerate(measured, 1):
            self.assertEqual(name, f'c{i:03d}-{task}-{config}-{arm}-r{replicate}')
        self.assertEqual(driver.rows([str(HERE / 'cells.tsv')]), [list(map(str, r)) for r in measured])
        self.assertEqual(driver.rows([str(HERE / 'screen.tsv')]), [list(map(str, r)) for r in written['screen.tsv']])

    def test_panel_order(self):
        # DESIGN "Panel": Claude for r = 1..16 the F10 block then the F11 block, then for r = 1..8 the B5, D3 and D4
        # blocks; Codex for r = 1..8 the B5, F10, F11 and D3 blocks. Claude's lane first in the file.
        measured = generate.generate()['cells.tsv']
        claude, codex = ([r for r in measured if r[3] == config] for config in ('claude', 'codex'))
        self.assertEqual((len(claude), len(codex)), (112, 64))
        self.assertEqual(measured[:112], claude)
        self.assertEqual([(r[1], r[4]) for r in claude[:64]],
                         [(task, rep) for rep in range(1, 17) for task in ('F10', 'F11') for _ in 'BC'])
        self.assertEqual([(r[1], r[4]) for r in claude[64:]],
                         [(task, rep) for rep in range(1, 9) for task in ('B5', 'D3', 'D4') for _ in 'BC'])
        self.assertEqual([(r[1], r[4]) for r in codex],
                         [(task, rep) for rep in range(1, 9) for task in ('B5', 'F10', 'F11', 'D3') for _ in 'BC'])

    def test_blocks_alternate_bc_and_cb(self):
        measured = generate.generate()['cells.tsv']
        for i in range(0, 176, 2):
            block = measured[i:i + 2]
            self.assertEqual({(r[1], r[3], r[4]) for r in block}, {(block[0][1], block[0][3], block[0][4])})
            self.assertEqual(''.join(r[2] for r in block), 'BC' if block[0][4] % 2 else 'CB')
        replicates = {'claude': {'F10': 16, 'F11': 16, 'B5': 8, 'D3': 8, 'D4': 8},
                      'codex': {'B5': 8, 'F10': 8, 'F11': 8, 'D3': 8}}
        for config, tasks in replicates.items():
            for task, n in tasks.items():
                for arm in 'BC':
                    self.assertEqual(sorted(r[4] for r in measured if r[1:4] == (task, arm, config)),
                                     list(range(1, n + 1)))

    def test_screen_rotates_the_candidates(self):
        # DESIGN "Stage S": per candidate 4 F10 and 2 F11 cells on Claude; six rounds of one cell per candidate, the
        # candidates' order rotating, so no candidate runs all its cells first.
        screen = generate.generate()['screen.tsv']
        self.assertEqual({r[3] for r in screen}, {'claude'})
        for candidate in ('K1', 'K2', 'K3'):
            own = [r for r in screen if r[2] == f'C-{candidate}']
            self.assertEqual(sorted((r[1], r[4]) for r in own), [('F10', 1), ('F10', 2), ('F10', 3), ('F10', 4),
                                                                ('F11', 1), ('F11', 2)])
        rounds = [screen[i:i + 3] for i in range(0, 18, 3)]
        self.assertEqual([r[0][1] for r in rounds], ['F10', 'F11', 'F10', 'F10', 'F11', 'F10'])
        for number, three in enumerate(rounds):
            self.assertEqual({r[1] for r in three}, {three[0][1]})
            self.assertEqual(sorted(r[2] for r in three), ['C-K1', 'C-K2', 'C-K3'])
            self.assertEqual(three[0][2], f'C-K{number % 3 + 1}')  # the round's first candidate rotates
        last_first = {k: max(i for i, r in enumerate(screen) if r[2] == f'C-{k}') for k in ('K1', 'K2', 'K3')}
        first = {k: min(i for i, r in enumerate(screen) if r[2] == f'C-{k}') for k in ('K1', 'K2', 'K3')}
        self.assertTrue(all(last_first[k] > max(first.values()) for k in first))  # nobody finishes before all start


class LaneControls(unittest.TestCase):
    def test_registered_lanes_refuse_to_start_without_a_go(self):
        # DESIGN "Stage S": no registered run without a GO; the lane refuses before it takes its lock or writes its
        # status, so nothing is latched. The screen's and SMOKE's lanes need no decision (their C names its package).
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for decision in (None, dict(decision='STOP', candidate='K3'), dict(decision='UNDECIDED', candidate=None)):
                with self.subTest(decision=decision):
                    (root / 'screen-decision.json').unlink(missing_ok=True)
                    if decision:
                        (root / 'screen-decision.json').write_text(json.dumps(decision))
                    with self.assertRaisesRegex(RuntimeError, 'lane claude refuses to start: .*no registered run'):
                        lane(root, 'claude', CELLS, decided=False)
                    self.assertFalse((root / 'output/driver-status-claude.json').exists())
                    self.assertIsNone(latched(root, 'codex'))
            screen = driver.rows([str(HERE / 'screen.tsv')])
            self.assertEqual(len(lane(root, 'claude', screen, decided=False).slots), 18)
            self.assertEqual(len(lane(root, None, driver.rows([str(HERE / 'smoke.tsv')]), decided=False).slots), 4)
            go(root)
            self.assertEqual(len(lane(root, 'codex', CELLS).slots), 64)

    def test_lane_filter(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            claude, codex, smoke = (lane(root, name, CELLS) for name in ('claude', 'codex', None))
            self.assertEqual((len(claude.slots), len(codex.slots), len(smoke.slots)), (112, 64, 176))
            self.assertEqual({r[3] for r in claude.slots}, {'claude'})
            self.assertEqual({r[3] for r in codex.slots}, {'codex'})
            self.assertEqual(smoke.slots, CELLS)
            seal(root)
            with mock.patch.object(driver.cell, 'run') as run:
                with self.assertRaisesRegex(ValueError, 'own lane'):
                    claude.dispatch(row('c113-'))
                with self.assertRaisesRegex(ValueError, 'arm B/C/C-K1/C-K2/C-K3'):
                    claude.dispatch(['c999-D3-claude-A-r1', 'D3', 'A', 'claude', '1'])
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
            (root / 'output/verdict-c001-F10-claude-B-r1.json').write_text(json.dumps(bad))
            claude.latch_for('c001-F10-claude-B-r1', bad)
            with mock.patch.object(driver.cell, 'run') as run:
                codex.lock.close()  # the codex process ends; its restart sees the latch too
                for d in (codex, lane(root, 'codex'), claude):
                    with self.assertRaisesRegex(RuntimeError, 'harm latch in lane claude'):
                        d.assert_active()
                with self.assertRaisesRegex(RuntimeError, 'harm latch in lane claude'):
                    codex.dispatch(row('c113-'))
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
            with mock.patch.object(driver, 'credential', return_value=snapshot(1505)), \
                    mock.patch.object(driver.cell, 'claude_limits', side_effect=[refused()]), host():
                self.assertTrue(d.ready(1500))  # amendment 1: an assessor redo goes on unread too
            self.assertEqual(d.approved_account, ['account', 'org'])
            self.assertEqual(unread(root, 'claude'), [dict(retry_after=None)])
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

    def test_a_refused_read_dispatches_unread_and_the_next_dispatch_reads_again(self):
        # Amendment 1, rules 1 and 3: an HTTP 429 holds nothing; with no Retry-After in whole seconds it sets no
        # deadline, so every dispatch reads once. The cell gets the account as after a read that answered.
        for named in (None, '1.5', 'Fri, 13 Nov 2026 01:13:10 GMT'):
            with self.subTest(retry_after=named), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                seal(root)
                d = lane(root, 'claude', [row('c001-'), row('c002-')])
                run, called = cells(d.output, {r[0]: [COMPLETE] for r in d.slots})
                with mock.patch.object(driver, 'credential', return_value=snapshot(20000)), \
                        mock.patch.object(driver.cell, 'claude_limits', side_effect=[refused(retry_after=named)] * 2) as limits, \
                        mock.patch.object(driver.cell, 'run', side_effect=run) as cell_run, \
                        mock.patch.object(driver.time, 'sleep') as sleep, host():
                    d.run()
                self.assertEqual(called, [r[0] for r in d.slots])
                self.assertEqual([call.kwargs['expected_account'] for call in cell_run.call_args_list],
                                 [['account', 'org']] * 2)
                self.assertEqual(limits.call_count, 2)
                sleep.assert_not_called()
                self.assertEqual(unread(root, 'claude'), [dict(retry_after=None),  # c002 is c001's block's second slot
                                                          dict(retry_after=None, cell=d.slots[1][0])])
                self.assertFalse([e for e in events(root, 'claude') if e['event'] == 'hold'])
        source = (HERE / 'driver.py').read_text()
        self.assertEqual(source.count('claude_limits('), 1)

    def test_no_read_while_a_refusals_retry_after_runs(self):
        # Rule 3: a Retry-After of 900 s keeps the endpoint unread until 900 s have passed (the clock is the test's).
        # The deadline is in memory only: a lane started again inside a refusal's 900 s reads at once.
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            seal(root)
            d = lane(root, 'claude', [row('c001-'), row('c002-'), row('c003-')])
            start = time.time()
            clock = {'now': start}
            login = snapshot(20000)
            reads, answers = [], [refused(retry_after='900'), WINDOWS]
            run, called = cells(d.output, {r[0]: [COMPLETE] for r in d.slots})

            def limits(*_args):
                reads.append(clock['now'])
                answer = answers.pop(0)
                if isinstance(answer, Exception):
                    raise answer
                return answer

            def cell_run(*args, **kwargs):  # c001 ends 899 s after the refusal, c002 at 900 s
                result = run(*args, **kwargs)
                clock['now'] = start + (899 if len(called) == 1 else 900)
                return result
            with mock.patch.object(driver, 'credential', return_value=login), \
                    mock.patch.object(driver.cell, 'claude_limits', side_effect=limits), \
                    mock.patch.object(driver.cell, 'run', side_effect=cell_run), \
                    mock.patch.object(driver.time, 'time', side_effect=lambda: clock['now']), \
                    mock.patch.object(driver.time, 'sleep') as sleep, host():
                d.run()
            self.assertEqual(called, [r[0] for r in d.slots])
            self.assertEqual(reads, [start, start + 900])
            sleep.assert_not_called()
            until = datetime.datetime.fromtimestamp(start + 900, datetime.timezone.utc).isoformat()
            self.assertEqual(unread(root, 'claude'), [dict(retry_after=900), dict(until=until, cell=d.slots[1][0])])
            self.assertFalse([e for e in events(root, 'claude') if e['event'] == 'hold'])
            answers.extend([refused(retry_after='900'), WINDOWS])  # a refusal at 900 s, then the lane starts again
            with mock.patch.object(driver, 'credential', return_value=login), \
                    mock.patch.object(driver.cell, 'claude_limits', side_effect=limits), \
                    mock.patch.object(driver.time, 'time', side_effect=lambda: clock['now']), host():
                self.assertTrue(d.ready())
                d.lock.close()
                lane(root, 'claude').ready()  # the clock is still inside the new 900 s
            self.assertEqual(reads[2:], [start + 900] * 2)
            self.assertNotIn('unread_until', d.status_path.read_text())

    def test_a_split_wait_holds_while_the_windows_are_unread(self):
        # Rule 2: a slot waiting on a split window's reset holds on a refused read and inside its Retry-After (no read
        # there); once that has run, a read that answers applies the wait as before: the same reset holds, a new one
        # dispatches. A wait recorded for another account is dropped as before, and the slot then dispatches unread.
        slot, previous = row('c002-')[0], row('c001-')[0]
        resets = {'seven_day': '2026-11-12T00:00:00+00:00'}
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            d = lane(root, 'claude')
            d.state['split_wait'][slot] = {'account': ['account', 'org'], 'resets': resets}
            with mock.patch.object(driver, 'credential', return_value=snapshot(20000)), \
                    mock.patch.object(driver.cell, 'claude_limits', side_effect=[refused(retry_after='900')]) as limits, \
                    host():  # one read: the second ready() falls inside the refusal's 900 s
                self.assertFalse(d.ready(slot=slot, previous=previous))
                self.assertFalse(d.ready(slot=slot, previous=previous))
            self.assertEqual(limits.call_count, 1)
            self.assertIsNone(d.approved_account)
            holds = [e for e in events(root, 'claude') if e['event'] == 'hold']
            self.assertEqual([(e['reason'], e['cell'], e['waits']) for e in holds],
                             [('awaiting split window reset: windows unread', slot, resets)] * 2)
            self.assertEqual(holds[0]['retry_after'], 900)  # the refusal, then the dispatch inside its Retry-After
            self.assertEqual(holds[1]['until'], datetime.datetime.fromtimestamp(
                d.unread_until, datetime.timezone.utc).isoformat())
            self.assertEqual(unread(root, 'claude'), [])
            self.assertEqual(d.state['split_wait'][slot]['resets'], resets)
            later = {'seven_day': {'used': 0, 'resets': '2026-11-19T00:00:00+00:00'}}
            with mock.patch.object(driver, 'credential', return_value=snapshot(20000)), \
                    mock.patch.object(driver.cell, 'claude_limits', side_effect=[WINDOWS, later]) as limits, \
                    mock.patch.object(driver.time, 'time', return_value=d.unread_until), host():  # its 900 s have run
                self.assertFalse(d.ready(slot=slot, previous=previous))  # read again: the waited reset is unchanged
                self.assertEqual(events(root, 'claude')[-1]['reason'], 'awaiting split window reset')
                self.assertTrue(d.ready(slot=slot, previous=previous))  # a new reset ends the wait
            self.assertEqual(limits.call_count, 2)
            d.unread_until = 0.0
            d.state['split_wait'][slot] = {'account': ['other', 'org'], 'resets': resets}
            with mock.patch.object(driver, 'credential', return_value=snapshot(20000)), \
                    mock.patch.object(driver.cell, 'claude_limits', side_effect=[refused()]), host():
                self.assertTrue(d.ready(slot=slot, previous=previous))
            self.assertEqual([e['event'] for e in events(root, 'claude')][-2:],
                             ['split_wait_account_changed', 'window_unread'])
            self.assertNotIn(slot, d.state['split_wait'])
            self.assertEqual(d.approved_account, ['account', 'org'])

    def test_other_read_failures_hold_and_read_again_after_60_seconds(self):
        # Rule 4: another HTTP status (its Retry-After sets nothing), a network error, an answer that is not JSON and a
        # read without the seven-day window hold as before.
        cases = [(refused(500, retry_after='900'), 'Claude window check failed: HTTP Error 500: Internal Server Error'),
                 (urllib.error.URLError('timed out'), 'Claude window check failed: <urlopen error timed out>'),
                 (json.JSONDecodeError('Expecting value', '<html>', 0),  # a ValueError, as json.load raises it
                  'Claude window check failed: Expecting value: line 1 column 1 (char 0)'),
                 ({'five_hour': WINDOWS['five_hour']}, 'Claude window evidence unavailable: no seven-day window')]
        for failure, reason in cases:
            with self.subTest(reason=reason), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                seal(root)
                d = lane(root, 'claude', [row('c001-')])
                run, called = cells(d.output, {r[0]: [COMPLETE] for r in d.slots})
                with mock.patch.object(driver, 'credential', return_value=snapshot(20000)), \
                        mock.patch.object(driver.cell, 'claude_limits', side_effect=[failure, WINDOWS]) as limits, \
                        mock.patch.object(driver.cell, 'run', side_effect=run), \
                        mock.patch.object(driver.time, 'sleep') as sleep, host():
                    d.run()
                self.assertEqual(called, [r[0] for r in d.slots])
                self.assertEqual(limits.call_count, 2)
                self.assertEqual([call.args for call in sleep.call_args_list], [(60,)])
                self.assertEqual([e['reason'] for e in events(root, 'claude') if e['event'] == 'hold'], [reason])
                self.assertEqual(unread(root, 'claude'), [])

    def test_a_read_that_answers_after_a_refusal_keeps_the_cap(self):
        # Rules 1 and 4: a refusal unblocks one dispatch only; the next read that answers at 95% holds as before.
        high = {name: {'used': 95, 'resets': '2026-11-12T00:00:00+00:00'} for name in WINDOWS}
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            seal(root)
            d = lane(root, 'claude', [row('c001-'), row('c003-')])
            run, called = cells(d.output, {r[0]: [COMPLETE] for r in d.slots})
            with mock.patch.object(driver, 'credential', return_value=snapshot(20000)), \
                    mock.patch.object(driver.cell, 'claude_limits', side_effect=[refused(), high, WINDOWS]) as limits, \
                    mock.patch.object(driver.cell, 'run', side_effect=run), \
                    mock.patch.object(driver.time, 'sleep') as sleep, host():
                d.run()
            self.assertEqual(called, [r[0] for r in d.slots])
            self.assertEqual(limits.call_count, 3)
            self.assertEqual([call.args for call in sleep.call_args_list], [(60,)])
            self.assertEqual([e['reason'] for e in events(root, 'claude') if e['event'] == 'hold'],
                             ['Claude window near exhaustion'])
            self.assertEqual(unread(root, 'claude'), [dict(retry_after=None)])

    def test_operator_hold_holds_every_dispatch_until_its_file_is_removed(self):
        # While <runtime root>/operator-hold exists no new cell starts: a hold every 60 s, never a verdict or a stop,
        # and the other pre-dispatch checks run again once it is gone.
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            seal(root)
            d = lane(root, 'claude', [row('c001-'), row('c002-')])
            run, called = cells(d.output, {r[0]: [COMPLETE] for r in d.slots})
            hold = root / driver.OPERATOR_HOLD
            hold.write_text('')
            sleeps = []

            def sleep(seconds):  # the operator removes the file during the second wait
                sleeps.append(seconds)
                self.assertEqual(called, [])
                self.assertFalse(list(d.output.glob('verdict-*')))
                if len(sleeps) == 2:
                    hold.unlink()
            with mock.patch.object(driver, 'credential', return_value=snapshot(20000)) as credential, \
                    mock.patch.object(driver.cell, 'claude_limits', return_value=WINDOWS), \
                    mock.patch.object(driver.cell, 'run', side_effect=run), \
                    mock.patch.object(driver.time, 'sleep', side_effect=sleep), host():
                d.run()
            self.assertEqual(sleeps, [60, 60])
            self.assertEqual(called, [r[0] for r in d.slots])
            self.assertEqual([e['reason'] for e in events(root, 'claude') if e['event'] == 'hold'],
                             ['operator hold', 'operator hold'])
            self.assertEqual(credential.call_count, 2)  # the checks after the hold, once per dispatch
            self.assertNotIn('harm_latch', d.state)
            self.assertEqual(d.state['split_blocks'], [])

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
            run, called = cells(d.output, {measured[0]: [COMPLETE], 'smoke-claude-B': [COMPLETE]})
            with mock.patch.object(driver.cell, 'run', side_effect=run):
                for status in (None, 'PENDING', 'FAIL'):
                    if status:
                        seal(root, status)
                    with self.subTest(status=status), self.assertRaisesRegex(RuntimeError, 'SMOKE qualification'):
                        d.dispatch(measured)
                self.assertEqual(called, [])
                (root / 'instructions.seal.json').unlink()
                self.assertTrue(lane(root, None).dispatch(['smoke-claude-B', 'SMOKE', 'B', 'claude']))
                seal(root)
                self.assertTrue(d.dispatch(measured))
            self.assertEqual(called, ['smoke-claude-B', measured[0]])

    def test_seven_day_deadline_from_the_shared_smoke_start(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            now = datetime.datetime.now(datetime.timezone.utc)
            started = root / 'output/smoke-claude-B/run/started.json'
            started.parent.mkdir(parents=True)
            for age, active in ((datetime.timedelta(days=7, seconds=-60), True),
                                (datetime.timedelta(days=7, seconds=60), False)):
                started.write_text(json.dumps({'started_at': (now - age).timestamp()}))
                for name in ('claude', 'codex'):
                    with self.subTest(age=age, lane=name):
                        for label in ('claude', 'codex'):  # each lane on its own; the latch it sets is checked below
                            (root / f'output/driver-status-{label}.json').unlink(missing_ok=True)
                        d = lane(root, name)
                        self.assertEqual(d.state['first_smoke_dispatch'],
                                         datetime.datetime.fromtimestamp((now - age).timestamp(),
                                                                         datetime.timezone.utc).isoformat())
                        if active:
                            d.assert_active()
                        else:
                            with self.assertRaisesRegex(RuntimeError, '7-day deadline reached'):
                                d.assert_active()
                            self.assertEqual([(e['event'], e['reason']) for e in events(root, name)[-2:]],
                                             [('stop', '7-day deadline reached'), ('harm_latch', '7-day deadline reached')])
                            other = lane(root, 'codex' if name == 'claude' else 'claude')  # stop() latches both lanes
                            with self.assertRaisesRegex(driver.Stopped, f'harm latch in lane {name}'):
                                other.assert_active()
                            other.lock.close()
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
            first, second = row('c113-'), row('c114-')
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

    def test_a_launch_fault_is_archived_and_redispatched_once_per_slot(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            slots = [row(f'c00{i}-') for i in range(1, 5)]  # F10 then F11, BC on r1
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

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            slots = [row('c002-')]
            with self.assertRaisesRegex(driver.Stopped, 'STOP launch fault: x'):
                self.run_lane(root, 'claude', slots, {slots[0][0]: [LAUNCH, dict(LAUNCH, reason='launch fault: x')]})
            name = slots[0][0]
            self.assertEqual(self.called, [name, name])
            latch = json.loads((root / 'output/driver-status-claude.json').read_text())['harm_latch']
            self.assertEqual(latch['cell'], name)
            self.assertEqual(latch['reason'], 'STOP launch fault: x')
            self.assertEqual(json.loads((root / f'output/verdict-{name}.json').read_text())['reason'],
                             'launch fault: x')
            self.assertTrue((root / f'output/verdict-{name}.stop-1.json').is_file())
            with self.assertRaisesRegex(RuntimeError, 'harm latch in lane claude'):
                lane(root, 'codex').assert_active()

        # Once per slot, not once in a row: a memory kill between the slot's two launch faults (its owner launched)
        # is itself redispatched, and the launch fault after it is still the slot's repeat.
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            name = row('c002-')[0]
            with self.assertRaisesRegex(driver.Stopped, 'STOP launch fault: y'):
                self.run_lane(root, 'claude', [row('c002-')],
                              {name: [LAUNCH, MEMORY, dict(LAUNCH, reason='launch fault: y')]})
            self.assertEqual(self.called, [name, name, name])
            self.assertEqual([json.loads((root / f'output/verdict-{name}.stop-{n}.json').read_text())['reason']
                              for n in (1, 2)], [LAUNCH['reason'], MEMORY['reason']])

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
                slots = [row('c113-'), row('c114-')]
                d = self.run_lane(root, 'codex', slots, {slots[0][0]: [fault, COMPLETE], slots[1][0]: [fault, COMPLETE]})
                self.assertEqual(self.called, [slots[0][0], slots[0][0], slots[1][0], slots[1][0]])
                self.assertTrue(all(d.verdict(r[0])['status'] == 'COMPLETE' for r in slots))
                self.assertNotIn('harm_latch', d.state)

            with self.subTest(fault=fault['reason'], repeat=True), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                name = row('c113-')[0]
                with self.assertRaisesRegex(RuntimeError, f'{name}: STOP {fault["reason"]}'):
                    self.run_lane(root, 'codex', [row('c113-')], {name: [fault, fault]})
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
                        lane(root, 'codex').dispatch(row('c113-'))
                    run.assert_not_called()

        with tempfile.TemporaryDirectory() as temp:  # each kind counts on its own: a memory kill, then an account fault
            root = Path(temp)
            name = row('c113-')[0]
            d = self.run_lane(root, 'codex', [row('c113-')], {name: [MEMORY, ACCOUNT, COMPLETE]})
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
            name = row('c113-')[0]
            (d.output / f'verdict-{name}.json').write_text(json.dumps(dict(stop, cell=name)))
            with mock.patch.object(driver.cell, 'run') as run:
                with self.assertRaisesRegex(RuntimeError, 'STOP instruction assertion'):
                    d.dispatch(row('c113-'))
                run.assert_not_called()
            with self.assertRaisesRegex(RuntimeError, 'harm latch in lane codex'):
                lane(root, 'claude').assert_active()

    def test_an_unproved_assessor_teardown_latches_both_lanes_without_a_regrade(self):
        """H3: violating, 'assessor teardown unproved' is no assessor fault: not regraded, not redispatched, latched
        for both lanes. (Allowed, an assessor fault is regraded: the next test.)"""
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            name = row('c001-')[0]
            stop = dict(status='STOP', reason='assessor teardown unproved: cannot prove container x is gone',
                        teardown='CLEAN', identity={'status': 'MATCH'}, owner_status='EXITED_0', owner_ran=True)
            with mock.patch.object(driver.cell, 'regrade') as regraded, \
                    self.assertRaisesRegex(driver.Stopped, 'STOP assessor teardown unproved'):
                self.run_lane(root, 'claude', [row('c001-')], {name: [stop]})
            regraded.assert_not_called()
            self.assertEqual(self.called, [name])
            self.assertEqual(latched(root, 'claude')['reason'], 'STOP ' + stop['reason'])
            with self.assertRaisesRegex(driver.Stopped, 'harm latch in lane claude'):
                lane(root, 'codex').assert_active()

    def test_a_terminal_stop_from_a_regrade_latches_both_lanes_before_any_wait(self):
        """Re-check HIGH 2: violating, a regrade that comes back `assessor teardown unproved` (neither regraded nor
        redispatched) latches both lanes at once, as the same STOP does after a cell run: the lane ends with no sleep
        and no further ready(), which here would hold. Allowed: a regrade that comes back with an assessor fault
        again is regraded at the next dispatch and sets no latch."""
        fault = dict(status='STOP', reason='assessment failed: timeout', teardown='CLEAN', identity={'status': 'MATCH'},
                     owner_status='EXITED_0', owner_ran=True)
        unproved = dict(fault, reason='assessor teardown unproved: cannot prove container x is gone')

        def regrading(root, outcomes, ready):
            seal(root)
            name = row('c001-')[0]
            d = lane(root, 'claude', [row('c001-')])
            (d.output / name).mkdir()
            path = d.output / f'verdict-{name}.json'
            path.write_text(json.dumps(fault))

            def regrade(*_args, **_kwargs):
                verdict = outcomes.pop(0)
                path.write_text(json.dumps(verdict))
                return 2 if verdict['status'] == 'STOP' else 0
            stack = contextlib.ExitStack()
            readied = stack.enter_context(mock.patch.object(d, 'ready', side_effect=ready))
            regraded = stack.enter_context(mock.patch.object(driver.cell, 'regrade', side_effect=regrade))
            run = stack.enter_context(mock.patch.object(driver.cell, 'run'))
            sleep = stack.enter_context(mock.patch.object(driver.time, 'sleep'))
            try:
                with stack:
                    d.run()
            finally:
                d.lock.close()
                run.assert_not_called()
                self.mocks = dict(ready=readied, regrade=regraded, sleep=sleep)
            return d

        calls = []

        class Held(BaseException):
            """Ends the old code's wait loop: run() latches no BaseException that is not an Exception."""

        def holds_after_the_first(*args):
            calls.append(args)
            if len(calls) > 3:
                raise Held(f'ready() called {len(calls)} times')
            return len(calls) == 1
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            with self.assertRaisesRegex(driver.Stopped, f'{row("c001-")[0]}: STOP assessor teardown unproved'):
                regrading(root, [unproved], holds_after_the_first)
            self.assertEqual((calls, self.mocks['regrade'].call_count), ([(1500, None, None)], 1))
            self.mocks['sleep'].assert_not_called()
            self.assertEqual(latched(root, 'claude')['reason'], 'STOP ' + unproved['reason'])
            with self.assertRaisesRegex(driver.Stopped, 'harm latch in lane claude'):
                lane(root, 'codex').assert_active()
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            d = regrading(root, [dict(fault, reason='assessment failed: again'), COMPLETE], lambda *_args: True)
            self.assertEqual((self.mocks['regrade'].call_count, self.mocks['sleep'].call_count), (2, 1))
            self.assertEqual(d.verdict(row('c001-')[0])['status'], 'COMPLETE')
            self.assertIsNone(latched(root, 'claude'))

    def test_a_terminal_stop_met_at_a_restart_latches_both_lanes_before_any_wait(self):
        """Second re-check (HIGH): a STOP was written and the process died before its latch. Violating: at the
        restart the lane meets a STOP that is neither regraded nor redispatched; it latches both lanes at once and
        never calls ready(), which could hold for a long time while the other lane went on dispatching. Allowed: a
        STOP that is regraded still waits on ready() first and sets no latch."""
        terminal = dict(status='STOP', reason='assessor teardown unproved: cannot prove container x is gone',
                        teardown='CLEAN', identity={'status': 'MATCH'}, owner_status='EXITED_0', owner_ran=True)

        class Held(BaseException):
            """Ends the wait loop: run() latches no BaseException that is not an Exception."""

        def restart(root, verdict):
            seal(root)
            name = row('c001-')[0]
            d = lane(root, 'claude', [row('c001-')])
            (d.output / name).mkdir()
            (d.output / f'verdict-{name}.json').write_text(json.dumps(verdict))
            self.assertIsNone(latched(root, 'claude'))  # the process died before it wrote the latch
            with mock.patch.object(d, 'ready', side_effect=Held('ready() was reached')) as ready, \
                    mock.patch.object(driver.cell, 'run') as run, mock.patch.object(driver.cell, 'regrade') as regrade, \
                    mock.patch.object(driver.time, 'sleep') as sleep:
                try:
                    d.run()
                finally:
                    d.lock.close()
                    self.mocks = dict(ready=ready, run=run, regrade=regrade, sleep=sleep)

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            with self.assertRaisesRegex(driver.Stopped, f'{row("c001-")[0]}: STOP assessor teardown unproved'):
                restart(root, terminal)
            for called in self.mocks.values():
                called.assert_not_called()
            self.assertEqual(latched(root, 'claude')['reason'], 'STOP ' + terminal['reason'])
            with self.assertRaisesRegex(driver.Stopped, 'harm latch in lane claude'):
                lane(root, 'codex').assert_active()
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            with self.assertRaises(Held):  # a regradable STOP is not terminal: the lane goes on to its readiness wait
                restart(root, dict(terminal, reason='assessment failed: timeout'))
            self.mocks['ready'].assert_called_once()
            self.assertIsNone(latched(root, 'claude'))

    def test_a_second_launch_fault_met_at_a_restart_latches_both_lanes_before_any_wait(self):
        """Third re-check (Grok, HIGH): the retried slot's second B launch fault was written and the process died
        before the latch. Violating: at the restart that STOP must not be redispatched a third time; with the slot's
        first fault in the archive it latches both lanes before any ready() wait. Allowed: a slot's first launch
        fault met at a restart is still redispatched (it goes on to its readiness wait and sets no latch)."""
        class Held(BaseException):
            """Ends the wait loop: run() latches no BaseException that is not an Exception."""

        def restart(root, archived):
            seal(root)
            b = next(r for r in CELLS if r[2] == 'B' and r[3] == 'claude')
            d = lane(root, 'claude', [b])
            (d.output / b[0]).mkdir()
            (d.output / f'verdict-{b[0]}.json').write_text(json.dumps(LAUNCH))
            if archived:
                (d.output / f'verdict-{b[0]}.stop-1.json').write_text(json.dumps(LAUNCH))
            with mock.patch.object(d, 'ready', side_effect=Held('ready() was reached')) as ready, \
                    mock.patch.object(driver.cell, 'run') as run, mock.patch.object(driver.time, 'sleep'):
                try:
                    d.run()
                finally:
                    d.lock.close()
                    self.mocks = dict(ready=ready, run=run)
            return b[0]

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            with self.assertRaisesRegex(driver.Stopped, 'STOP launch fault'):
                restart(root, True)
            self.mocks['ready'].assert_not_called()
            self.mocks['run'].assert_not_called()
            self.assertEqual(latched(root, 'claude')['reason'], 'STOP ' + LAUNCH['reason'])
            with self.assertRaisesRegex(driver.Stopped, 'harm latch in lane claude'):
                lane(root, 'codex').assert_active()
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            with self.assertRaises(Held):
                restart(root, False)
            self.mocks['ready'].assert_called_once()
            self.assertIsNone(latched(root, 'claude'))

    def test_an_attempt_without_a_verdict_met_at_a_restart_latches_both_lanes_before_any_wait(self):
        """The lane was killed inside a cell: its folder is there and no verdict is. Violating: the restart must not
        wait on ready() and then fail in prepare; it latches both lanes at once, since the interrupted attempt's
        container may still run. Allowed: a slot with neither a folder nor a verdict goes on to its readiness wait."""
        class Held(BaseException):
            """Ends the wait loop: run() latches no BaseException that is not an Exception."""

        def restart(root, interrupted):
            seal(root)
            name = row('c001-')[0]
            d = lane(root, 'claude', [row('c001-')])
            if interrupted:
                (d.output / name / 'run').mkdir(parents=True)
            with mock.patch.object(d, 'ready', side_effect=Held('ready() was reached')) as ready, \
                    mock.patch.object(driver.cell, 'run') as run, mock.patch.object(driver.time, 'sleep'):
                try:
                    d.run()
                finally:
                    d.lock.close()
                    self.mocks = dict(ready=ready, run=run)

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            with self.assertRaisesRegex(driver.Stopped, 'an attempt without a verdict'):
                restart(root, True)
            self.mocks['ready'].assert_not_called()
            self.mocks['run'].assert_not_called()
            self.assertIn('an attempt without a verdict', latched(root, 'claude')['reason'])
            with self.assertRaisesRegex(driver.Stopped, 'harm latch in lane claude'):
                lane(root, 'codex').assert_active()
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            with self.assertRaises(Held):
                restart(root, False)
            self.mocks['ready'].assert_called_once()
            self.assertIsNone(latched(root, 'claude'))

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

    def test_docker_29_daemon_loss_reads_as_a_docker_fault(self):
        # Docker 29.9.2's own answer with the daemon unreachable (checked on this host with a dead DOCKER_HOST), and
        # the form 0257-0261 met; any other teardown failure is not a Docker loss and stays a STOP.
        lost = ('failed to connect to the docker API at unix:///Users/u/.docker/run/docker.sock; check if the path is '
                'correct and if the daemon is running: dial unix /Users/u/.docker/run/docker.sock: connect: '
                'connection refused', 'Cannot connect to the Docker daemon at unix:///var/run/docker.sock. '
                'Is the docker daemon running?')
        stop = dict(status='STOP', teardown='FAILED', reason='teardown failed: container survived kill')
        for text in lost:
            self.assertTrue(driver.docker_fault(dict(stop, teardown_error=text)), text)
        for verdict in (stop, dict(stop, teardown_error='error: no such object: x'),
                        dict(stop, teardown='CLEAN', teardown_error=lost[0]), dict(COMPLETE, teardown_error=lost[0]), None):
            self.assertFalse(driver.docker_fault(verdict), verdict)

    def docker_loss(self, root, *, owner=True, volume=True, owner_ran=True, preserve=None, on_volume=True,
                    sealed=('after', [])):
        """A Docker-loss STOP of one slot recovered by dispatch, against a fake Docker that holds the attempt's owner
        container (owner) and /tmp volume (volume). preserve: what cell.py's preserve_tmp raises (it otherwise copies
        the volume into the cell and removes it). Returns (dispatch's result or the exception, Docker's calls, the
        fakes, the slot's name)."""
        seal(root)
        d = lane(root, 'claude')
        name = row('c001-')[0]
        container, vol, cid = 'devlyn-0231-owner', 'devlyn-0233-tmp-owner', 'a' * 64
        out = d.output / name
        (out / 'run').mkdir(parents=True)
        (out / 'tmp').mkdir()
        (out / 'plan.json').write_text(json.dumps(dict(tmp=str(out / 'tmp'), image='sha256:test')))
        (out / 'run/started.json').write_text(json.dumps({
            'create_argv': ['create', '--name', container, f'type=volume,src={vol},dst=/tmp'],
            'tmp_volume': vol, 'started_at': time.time()}))
        (d.output / f'verdict-{name}.json').write_text(json.dumps(dict(
            status='STOP', teardown='FAILED', identity={'status': 'MATCH'}, owner_status='EXITED_NONZERO',
            owner_ran=owner_ran, evidence_manifest_sha256='before',
            reason='teardown failed: failed to connect to the docker API at unix:///docker.sock')))
        containers = {cid: dict(Id=cid, Name='/' + container, Config={'Labels': {'devlyn.task': '0233'}},
                                Mounts=[{'Type': 'volume', 'Name': vol if on_volume else 'other'}],
                                State={'Running': False, 'Pid': 0, 'Status': 'exited'})} if owner else {}
        volumes, calls = {vol} if volume else set(), []

        def docker(argv, **_kwargs):
            args = argv[1:]
            calls.append(args)
            if args[:2] == ['ps', '-aq']:
                found = args[-1]
                value = '\n'.join(c for c, item in containers.items()
                                  if found == f'name=^{item["Name"]}$'
                                  or any(found == f'volume={m["Name"]}' for m in item['Mounts']))
            elif args[0] == 'inspect':
                value = json.dumps([containers[args[1]]])
            elif args[:2] == ['volume', 'ls']:
                value = '\n'.join(v for v in volumes if args[-1] == f'name=^{v}$')
            elif args[0] == 'rm':
                del containers[args[1]]
                value = ''
            else:
                raise AssertionError(f'unexpected docker call {args}')
            return subprocess.CompletedProcess(argv, 0, stdout=value)

        def preserve_tmp(volume_, dest, image):
            calls.append(['preserve_tmp', volume_, str(dest), image])
            if preserve:
                raise preserve
            (dest / 'helper-worktree.txt').write_text('kept')
            volumes.discard(volume_)
        fakes = dict(preserve=mock.Mock(side_effect=preserve_tmp),
                     seal=mock.Mock(return_value=sealed),
                     evidence=mock.Mock(side_effect=lambda out_, record: dict(
                         record, snapshot={'kind': 'anchor'}, scope_violations=[], changed=['src/x.js'])))
        run, called = cells(d.output, {name: [COMPLETE]})
        with mock.patch.object(driver.subprocess, 'run', side_effect=docker), \
                mock.patch.object(driver.cell, 'run', side_effect=run), \
                mock.patch.object(driver.cell, 'cell_run', types.SimpleNamespace(preserve_tmp=fakes['preserve']),
                                  create=True), \
                mock.patch.object(driver.cell, 'seal_after_teardown', fakes['seal'], create=True), \
                mock.patch.object(driver.cell, 'stop_evidence', fakes['evidence'], create=True):
            try:
                result = d.dispatch(row('c001-'))
            except RuntimeError as exc:
                result = exc
        fakes.update(called=called, volumes=volumes, containers=containers, out=out, lane=d)
        d.lock.close()
        return result, calls, fakes, name

    def test_docker_loss_is_proven_archived_and_redispatched(self):
        """H5, allowed: the attempt's containers are removed, its /tmp volume is preserved into the cell (then removed)
        before anything else touches it, the cell is sealed again with /tmp in it, its tree and scope are kept, and
        the attempt is archived with tmp_recovery and redispatched."""
        with tempfile.TemporaryDirectory() as temp:
            result, calls, fakes, name = self.docker_loss(Path(temp))
            output = Path(temp) / 'output'
            self.assertIs(result, True)
            self.assertEqual((fakes['containers'], fakes['volumes']), ({}, set()))
            self.assertEqual([c[0] for c in calls if c[0] in ('rm', 'preserve_tmp')], ['rm', 'preserve_tmp'])
            out = fakes['out']
            self.assertEqual(calls[[c[0] for c in calls].index('preserve_tmp')],
                             ['preserve_tmp', 'devlyn-0233-tmp-owner', str(out / 'tmp'), 'sha256:test'])
            fakes['seal'].assert_called_once_with(out)
            fakes['evidence'].assert_called_once()
            archived = json.loads((output / f'verdict-{name}.stop-1.json').read_text())
            self.assertEqual((archived['tmp_recovery'], archived['evidence_manifest_sha256'], archived['scope_violations'],
                              archived['changed'], archived['owner_ran']),
                             ('preserved', 'after', [], ['src/x.js'], True))
            self.assertEqual((output / f'{name}.stop-1/tmp/helper-worktree.txt').read_text(), 'kept')
            self.assertEqual(fakes['called'], [name])
            proven = next(e for e in events(Path(temp), 'claude') if e['event'] == 'docker_teardown_proven')
            self.assertEqual(proven['tmp'], 'preserved')

    def test_docker_loss_recovers_when_the_owner_or_the_volume_is_already_gone(self):
        """H5, allowed: the cell's own teardown had removed the owner before Docker was lost (run/started.json still
        proves the attempt), or the volume no longer exists (nothing to preserve, recorded as such). An attempt
        whose owner did not run is archived without a tree or scope."""
        for owner, volume, owner_ran, tmp in ((False, True, True, 'preserved'), (True, False, True, 'volume absent'),
                                              (True, True, False, 'preserved')):
            with self.subTest(owner=owner, volume=volume, owner_ran=owner_ran), \
                    tempfile.TemporaryDirectory() as temp:
                result, calls, fakes, name = self.docker_loss(Path(temp), owner=owner, volume=volume,
                                                               owner_ran=owner_ran)
                self.assertIs(result, True)
                self.assertEqual((fakes['containers'], fakes['volumes']), ({}, set()))
                self.assertEqual(fakes['preserve'].call_count, int(volume))
                self.assertEqual(fakes['evidence'].call_count, int(owner_ran))
                archived = json.loads((Path(temp) / f'output/verdict-{name}.stop-1.json').read_text())
                self.assertEqual(archived['tmp_recovery'], tmp)
                self.assertEqual('scope_violations' in archived, owner_ran)
                self.assertEqual(fakes['called'], [name])

    def test_a_docker_recovery_that_cannot_be_proved_stops_both_lanes_and_keeps_the_volume(self):
        """H5, violating: /tmp cannot be preserved, the recorded owner is not on the attempt's volume, or the cell
        cannot be sealed again: the lane stops with the harm latch set, nothing is archived or redispatched, and the
        volume stays for the orchestrator."""
        cases = (('preserve', dict(preserve=subprocess.CalledProcessError(1, ['docker', 'run'])), True,
                  'Docker teardown proof failed'),
                 ('owner elsewhere', dict(on_volume=False), True, 'recorded owner container was not found on its volume'),
                 ('seal', dict(sealed=(None, ['tmp/x: permission denied'])), False,
                  'evidence collection failed after the Docker recovery: tmp/x: permission denied'))
        for label, change, volume_kept, reason in cases:
            with self.subTest(label), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                result, calls, fakes, name = self.docker_loss(root, **change)
                self.assertIsInstance(result, driver.Stopped)
                self.assertIn(reason, str(result))
                self.assertEqual(bool(fakes['volumes']), volume_kept)
                self.assertEqual(fakes['called'], [])
                fakes['evidence'].assert_not_called()
                self.assertTrue((root / f'output/verdict-{name}.json').is_file())
                self.assertFalse((root / f'output/verdict-{name}.stop-1.json').exists())
                latch = json.loads((root / 'output/driver-status-claude.json').read_text())['harm_latch']
                self.assertEqual(latch['cell'], None)
                self.assertIn(reason, latch['reason'])
                with self.assertRaisesRegex(driver.Stopped, 'harm latch in lane claude'):
                    lane(root, 'codex').assert_active()


class LaneEnd(unittest.TestCase):
    """H4 (b): an exception that ends a lane sets the harm latch with its text, so the other lane stops dispatching;
    an operator's interrupt does not, nor does a lane that ends on a latch already set or on a STOP whose latch an
    amendment cleared."""

    def run_lane(self, root, side_effect, slots=None):
        seal(root)
        d = lane(root, 'claude', slots or [row('c001-')])
        with mock.patch.object(d, 'ready', return_value=True), \
                mock.patch.object(driver.cell, 'run', side_effect=side_effect), \
                mock.patch.object(driver.time, 'sleep'):
            try:
                d.run()
            finally:
                d.lock.close()

    def test_an_error_that_ends_a_lane_latches_both_lanes_until_cleared(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            with self.assertRaisesRegex(OSError, 'disk full'):
                self.run_lane(root, OSError(28, 'disk full'))
            latch = json.loads((root / 'output/driver-status-claude.json').read_text())['harm_latch']
            self.assertEqual(latch, dict(cell=None, verdict_sha256=None, reason=(
                f'lane claude ended at {row("c001-")[0]}: OSError: [Errno 28] disk full')))
            codex = lane(root, 'codex')
            with self.assertRaisesRegex(driver.Stopped, 'harm latch in lane claude'):
                codex.assert_active()
            amendment = root / 'amendment-1.md'
            amendment.write_text('resolved')
            claude = lane(root, 'claude')
            claude.clear_latch(amendment)  # a latch with no verdict clears like any other
            codex.assert_active()
            self.assertEqual(claude.state['cleared_latches'][-1]['cell'], None)
            claude.latch(None, 'a second lane end')  # a cleared lane end exempts no later one
            with self.assertRaisesRegex(driver.Stopped, 'a second lane end'):
                codex.assert_active()
            claude.lock.close()
            codex.lock.close()

    def test_a_lane_that_fails_while_it_is_set_up_stops_the_other(self):
        """Re-check MEDIUM 4: violating, an error in the constructor after the lane lock is taken (caps that are not
        95/95, a malformed SMOKE start) sets the latch with its text, so the other lane stops at its next check.
        Allowed: a second start of a lane that is already running is refused before any write and touches no latch."""
        def bad_caps(root, path):
            path.write_text(json.dumps(dict(json.loads(path.read_text()), caps={'seven_day': 70, 'five_hour': 85})))

        def bad_start(root, _path):
            started = root / 'output/smoke-claude-B/run/started.json'
            started.parent.mkdir(parents=True)
            started.write_text(json.dumps({'started_at': 'soon'}))
        for spoil, error in ((bad_caps, 'registration caps must be seven_day=95 and five_hour=95'),
                             (bad_start, 'malformed SMOKE start: started_at must be numeric')):
            with self.subTest(error=error), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                peer = lane(root, 'codex')
                peer.assert_active()
                path = runtime(root, 'claude')
                spoil(root, path)
                with self.assertRaisesRegex(ValueError, error):
                    driver.Driver(path, [])
                latch = latched(root, 'claude')
                self.assertEqual((latch['cell'], latch['verdict_sha256']), (None, None))
                self.assertRegex(latch['reason'], '^lane claude failed while it was set up: ValueError: .*' + error)
                with self.assertRaisesRegex(driver.Stopped, 'harm latch in lane claude'):
                    peer.assert_active()
                peer.lock.close()
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            first, peer = lane(root, 'claude'), lane(root, 'codex')
            first.event('started')
            status = root / 'output/driver-status-claude.json'
            before = status.read_text()
            with self.assertRaisesRegex(RuntimeError, 'lane claude already has a driver process'):
                lane(root, 'claude')
            self.assertEqual(status.read_text(), before)
            self.assertIsNone(latched(root, 'claude'))
            first.assert_active()
            peer.assert_active()
            first.lock.close()
            peer.lock.close()

    def test_an_interrupt_or_a_latch_already_set_adds_no_latch(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            with self.assertRaises(KeyboardInterrupt):
                self.run_lane(root, KeyboardInterrupt())
            self.assertIsNone(latched(root, 'claude'))
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            other = lane(root, 'codex')
            other.latch(None, 'codex ended')
            with self.assertRaisesRegex(driver.Stopped, 'harm latch in lane codex'):
                self.run_lane(root, AssertionError('never dispatched'))
            self.assertIsNone(latched(root, 'claude'))
            other.lock.close()

    def test_a_stop_whose_latch_was_cleared_ends_its_lane_without_a_new_latch(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            name = row('c002-')[0]
            stop = dict(status='STOP', reason='instruction assertion: x', teardown='CLEAN',
                        identity={'status': 'MATCH'}, owner_status='EXITED_0', owner_ran=True)
            with self.assertRaisesRegex(driver.Stopped, 'STOP instruction assertion'):
                self.run_lane(root, cells(root / 'output', {name: [stop]})[0], [row('c002-')])
            amendment = root / 'amendment-1.md'
            amendment.write_text('resolved')
            claude = lane(root, 'claude')
            claude.clear_latch(amendment)
            claude.lock.close()
            with self.assertRaisesRegex(driver.Stopped, 'STOP instruction assertion'):
                self.run_lane(root, AssertionError('a STOP is not run again'), [row('c002-')])
            self.assertIsNone(latched(root, 'claude'))
            lane(root, 'codex').assert_active()


class ScreenStops(unittest.TestCase):
    """F5 and F7: DESIGN "Stage S" runs no screen cell again; a screen slot left at a STOP reads as an unknown."""
    SCREEN = driver.rows([str(HERE / 'screen.tsv')])

    def run_lane(self, root, slots, outcomes):
        seal(root)
        d = lane(root, 'claude', slots)
        run, called = cells(d.output, outcomes)
        with mock.patch.object(d, 'ready', return_value=True), mock.patch.object(driver.cell, 'run', side_effect=run), \
                mock.patch.object(driver.time, 'sleep'):
            try:
                d.run()
            finally:
                self.called = called
                d.lock.close()
        return d

    def clear(self, root):
        amendment = root / 'amendment.md'
        amendment.write_text('resolved')
        claude = lane(root, 'claude')
        claude.clear_latch(amendment)
        claude.lock.close()

    def test_a_cleared_screen_stop_is_passed_and_the_rows_after_it_run(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            slots = self.SCREEN[:3]
            first = slots[0][0]
            with self.assertRaisesRegex(driver.Stopped, f'{first}: STOP memory kill'):
                self.run_lane(root, slots, {first: [dict(MEMORY, owner_ran=True)]})
            self.assertEqual(self.called, [first])  # an owner ran: not run again (F7)
            self.assertFalse(list((root / 'output').glob(f'verdict-{first}.stop-*')))
            stopped = (root / f'output/verdict-{first}.json').read_text()
            with self.assertRaisesRegex(driver.Stopped, 'harm latch in lane claude'):  # not cleared: still stops
                self.run_lane(root, slots, {})
            self.clear(root)
            d = self.run_lane(root, slots, {name: [COMPLETE] for name, *_ in slots[1:]})
            self.assertEqual(self.called, [name for name, *_ in slots[1:]])
            self.assertEqual((root / f'output/verdict-{first}.json').read_text(), stopped)  # it keeps its verdict
            self.assertEqual([e['cell'] for e in events(root, 'claude') if e['event'] == 'skip_cleared_stop'], [first])
            self.assertNotIn('harm_latch', d.state)

    def test_an_uncleared_screen_stop_met_at_a_restart_stops_the_lane(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            first = self.SCREEN[0][0]
            (root / 'output').mkdir()
            (root / f'output/verdict-{first}.json').write_text(json.dumps(dict(MEMORY, owner_ran=True, cell=first)))
            with self.assertRaisesRegex(driver.Stopped, f'{first}: STOP memory kill'):
                self.run_lane(root, self.SCREEN[:2], {})
            self.assertEqual(self.called, [])
            self.assertEqual(latched(root, 'claude')['cell'], first)

    def test_a_screen_launch_fault_is_run_again_once(self):
        # No owner ran in a launch fault, so the screen cell has not run yet.
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            first = self.SCREEN[0][0]
            launch = dict(LAUNCH, owner_ran=False)
            self.run_lane(root, self.SCREEN[:1], {first: [launch, COMPLETE]})
            self.assertEqual(self.called, [first, first])
            self.assertTrue((root / f'output/verdict-{first}.stop-1.json').is_file())

    def test_the_registered_run_still_runs_a_memory_kill_again(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            name = row('c002-')[0]
            self.run_lane(root, [row('c002-')], {name: [dict(MEMORY, owner_ran=True), COMPLETE]})
            self.assertEqual(self.called, [name, name])


class Accounts(unittest.TestCase):
    def test_the_login_changing_between_cells_neither_stops_nor_holds(self):
        """D-c (DESIGN Operations "Accounts"): ready() takes whichever account is the host's default login. Cells on
        two accounts dispatch with no hold and no latch, each with the account its own ready() approved; a cell whose
        login changed after ready() (run_cell's preflight exits 3, test_cell checks that side) runs after one 60 s
        wait on the next ready()'s account."""
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            seal(root)
            d = lane(root, 'claude', [row('c001-'), row('c002-'), row('c003-')])
            first, second = ['first', 'org'], ['second', 'org']
            dispatched = []

            def run(_runtime, name, *_args, expected_account=None):
                dispatched.append((name, expected_account))
                if len(dispatched) == 2:  # the login moved to `second` between ready() and the cell's own read
                    return 3
                (d.output / name).mkdir()
                (d.output / f'verdict-{name}.json').write_text(json.dumps(dict(
                    COMPLETE, cell=name, claude_account_before=expected_account)))
                return 0
            reads = [snapshot(20000, first), snapshot(20000, first), snapshot(20000, second), snapshot(20000, first)]
            with mock.patch.object(driver, 'credential', side_effect=reads), \
                    mock.patch.object(driver.cell, 'claude_limits', return_value=WINDOWS), \
                    mock.patch.object(driver.cell, 'run', side_effect=run), \
                    mock.patch.object(driver.time, 'sleep') as sleep, host():
                d.run()
            names = [r[0] for r in d.slots]
            self.assertEqual(dispatched, [(names[0], first), (names[1], first), (names[1], second), (names[2], first)])
            self.assertEqual([call.args for call in sleep.call_args_list], [(60,)])
            log = events(root, 'claude')
            self.assertFalse([e for e in log if e['event'] in ('hold', 'harm_latch', 'stop', 'split_block')])
            self.assertEqual([(e['event'], e.get('rc')) for e in log if e['event'] in ('run', 'complete')],
                             [('run', 0), ('run', 3), ('run', 0), ('run', 0), ('complete', None)])
            self.assertEqual([d.verdict(name)['claude_account_before'] for name in names], [first, second, first])


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
        # The Docker-loss recovery's calls, which the driver tests patch onto the fake (H2, H5). The recovery has proved
        # the teardown, so it calls stop_evidence with out and record alone: proved defaults to true.
        for function, parameters in ((real.stop_evidence, ['out', 'record', 'proved']),
                                     (real.seal_after_teardown, ['out']),
                                     (real.cell_run.preserve_tmp, ['volume', 'dest', 'image'])):
            self.assertEqual(list(inspect.signature(function).parameters), parameters, function.__name__)
        self.assertIs(inspect.signature(real.stop_evidence).parameters['proved'].default, True)


if __name__ == '__main__':
    unittest.main()
