"""0266 dispatcher: one serial process per lane, both lanes on one output folder. Run under caffeinate -dimsu:
driver.py <runtime.json> <cells.tsv>[:prefix] ...  The runtime's lane (null, claude or codex) selects the rows it runs.
A lane's process holds an exclusive lock on <output>/driver-<lane>.lock for its whole life (--clear-latch too), so a
lane never runs twice. A STOP that is not redispatched sets the harm latch, which stops both lanes; a lane with a cell
running lets it finish. So does stop(), and any other exception that ends a lane (an operator's interrupt aside): the
latch carries its text, so the other lane stops dispatching too. A registered slot's failed teardown latches like any
STOP; once an amendment has cleared that latch, the lane started again proves the teardown, archives the attempt and
runs the slot again (amendment 2)."""
import datetime
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import uuid

import importlib.util

HERE = Path(__file__).resolve().parent


def load(name):
    spec = importlib.util.spec_from_file_location('driver0266_' + name, HERE / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


cell = load('run_cell')
LANES = (None, 'claude', 'codex')
REGRADE = ('assessment failed', 'assessor produced', 'assessment held:')
LAUNCH_FAULT, MEMORY_KILL = 'launch fault: ', 'memory kill: '
ACCOUNT_FAULT = 'shared account fault during execution: '  # a Codex refresh_token_reused among them (quota.py)
ONCE = (LAUNCH_FAULT, MEMORY_KILL, ACCOUNT_FAULT)  # redispatched once per slot; a repeat on the slot stays a STOP
TEARDOWN_FAILED = 'teardown failed: '  # amendment 2: redispatched on a registered slot once an amendment cleared it
GIB = 2**30
COLUMNS = ('B', 'C', 'C-K1', 'C-K2', 'C-K3')  # the schedules' arm columns (prepare.arm_package)
OPERATOR_HOLD = 'operator-hold'  # in the runtime root: while it exists, no lane starts a new cell
# 4.3.30's delivery helper measures its target with shutil.disk_usage and refuses below max(10 GiB, 2% of the total).
DISK_PROBE = "import json, shutil; print(json.dumps({p: shutil.disk_usage(p)._asdict() for p in ('/cell', '/tmp')}))"


class Stopped(RuntimeError):
    """A lane ends on a harm latch already set (its own or another lane's), or on a STOP whose latch an amendment
    cleared: run() sets no further latch for it."""


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def replace(path, text):
    """Write a whole file through a temp file in its folder and os.replace, so no reader sees part of it."""
    fd, temp = tempfile.mkstemp(dir=path.parent, prefix=f'.{path.name}.')
    try:
        with os.fdopen(fd, 'w') as stream:
            stream.write(text)
        os.replace(temp, path)
    except BaseException:
        Path(temp).unlink(missing_ok=True)
        raise


def rows(args):
    result = []
    for arg in args:
        file, separator, prefix = arg.partition(':')
        for line in Path(file).read_text().splitlines():
            if line and not line.startswith('#'):
                row = line.split()
                if len(row) not in (4, 5):
                    raise ValueError(f'{file}: malformed cell row')
                if not separator or row[0].startswith(prefix):
                    result.append(row)
    if len({row[0] for row in result}) != len(result):
        raise ValueError('duplicate cell slot')
    return result


def same_window(first, second):
    if not first or not second:
        return False
    try:
        a = datetime.datetime.fromisoformat(first)
        b = datetime.datetime.fromisoformat(second)
        return abs((a - b).total_seconds()) < 600
    except (TypeError, ValueError):
        return False


def counted(windows):
    """The usage windows a dispatch is held on (DESIGN Operations "Windows", O8): the seven-day window, and the
    five-hour window and model-scoped weekly limits (seven_day_*) when the account reports them. The endpoint's other
    entries (feature codenames, extra usage) are no window."""
    return {name: value for name, value in windows.items()
            if name in ('seven_day', 'five_hour') or name.startswith('seven_day_')}


def exceeded(windows, caps):
    """The counted windows at or above their cap, with their resets; a weekly limit takes the seven-day cap."""
    return {name: value['resets'] for name, value in windows.items()
            if value['used'] >= caps.get(name, caps['seven_day'])}


def docker_fault(verdict):
    """A teardown that failed because the Docker daemon could not be reached: "Cannot connect to the Docker daemon" up
    to 0261's Docker, "failed to connect to the docker API" from Docker 29 (read in any letter case, as O9)."""
    if not verdict or verdict.get('status') != 'STOP' or verdict.get('teardown') != 'FAILED':
        return False
    text = (str(verdict.get('teardown_error', '')) + str(verdict.get('reason', ''))).lower()
    return any(lost in text for lost in ('cannot connect to the docker daemon', 'failed to connect to the docker api'))


def credential(runtime):
    raw = subprocess.run(['security', 'find-generic-password', '-s', 'Claude Code-credentials', '-w'],
                         check=True, capture_output=True, text=True).stdout
    oauth = json.loads(raw)['claudeAiOauth']
    expiry = oauth['expiresAt'] / 1000
    if expiry - time.time() <= 300:
        return dict(expires=expiry, account=None, access_token=oauth['accessToken'])
    request = cell.urllib.request.Request('https://api.anthropic.com/api/oauth/profile', headers={
        'Authorization': 'Bearer ' + oauth['accessToken'], 'anthropic-beta': 'oauth-2025-04-20'})
    with cell.urllib.request.urlopen(request, timeout=20) as response:
        profile = json.load(response)
    identity = [cell.base.fingerprint(profile['account']['uuid']),
                cell.base.fingerprint(profile['organization']['uuid'])]
    return dict(expires=expiry, account=identity, access_token=oauth['accessToken'])


def renewal_command(runtime, help_text):
    command = runtime['renewal_command']
    if not isinstance(command, list) or not command or command[0] != 'claude' or not all(isinstance(x, str) for x in command):
        raise ValueError('renewal_command must be a claude argv array')
    for flag in ('-p', '--tools', '--strict-mcp-config', '--mcp-config'):
        if flag not in command or flag not in help_text:
            raise ValueError(f'renewal command/help missing {flag}')
    if command[command.index('--tools') + 1] != '' or json.loads(command[command.index('--mcp-config') + 1]) != {'mcpServers': {}}:
        raise ValueError('renewal command must disable tools and MCP servers')
    return command


class Driver:
    def __init__(self, runtime_path, slots):
        self.runtime_path = Path(runtime_path)
        self.runtime = json.loads(self.runtime_path.read_text())
        self.output = Path(self.runtime['output'])
        self.output.mkdir(parents=True, exist_ok=True)
        self.lane = self.runtime['lane']
        if self.lane not in LANES:
            raise ValueError('lane must be null, claude or codex')
        label = self.lane or 'smoke'
        if any(row[2] == 'C' for row in slots if self.lane in (None, row[3])):  # the registered run's C (cells.tsv)
            try:  # DESIGN "Stage S": no registered run without a GO whose package is the sealed one; nothing latched
                cell.prepare.selected(self.runtime)
            except ValueError as exc:
                raise RuntimeError(f'lane {label} refuses to start: {exc}') from None
        self.lock = open(self.output / f'driver-{label}.lock', 'a')  # held until the process ends
        try:
            fcntl.flock(self.lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            self.lock.close()
            raise RuntimeError(f'lane {label} already has a driver process: driver-{label}.lock is held') from None
        self.status_path = self.output / f'driver-status-{label}.json'
        self.log_path = self.output / f'driver-{label}.log'
        # A status file that cannot be read ends this lane here and the other at its next check, which reads it too.
        self.state = json.loads(self.status_path.read_text()) if self.status_path.exists() else {
            'renewed_expiries': [], 'split_blocks': [], 'split_wait': {}}
        try:  # from here on a lane that fails while it is set up stops the other one too, as run() does
            self.renewal_lock = Path(self.runtime['renewal_lock'])
            self.slots = [row for row in slots if self.lane in (None, row[3])]
            self.caps = self.runtime['caps']
            self.approved_account = None
            self.unread_until = 0.0  # amendment 1: the end of a refused read's Retry-After, in memory only
            if self.caps != {'seven_day': 95, 'five_hour': 95}:
                raise ValueError('registration caps must be seven_day=95 and five_hour=95')
            self.state.setdefault('split_wait', {})
            self.reconcile_smoke_starts()
            if self.state.get('registered_caps') not in (None, self.caps):
                self.stop('registered caps differ from 95/95')
        except Stopped:
            raise
        except Exception as exc:
            self.latch(None, f'lane {label} failed while it was set up: {type(exc).__name__}: {exc}')
            raise

    def event(self, kind, **fields):
        record = dict(at=datetime.datetime.now(datetime.timezone.utc).isoformat(), event=kind, **fields)
        log = self.log_path.read_text() if self.log_path.exists() else ''
        replace(self.log_path, log + json.dumps(record, sort_keys=True) + '\n')
        self.state.update(current=record)
        replace(self.status_path, json.dumps(self.state, indent=2) + '\n')

    def stop(self, reason):
        """End this lane and, through the harm latch, the other one."""
        self.event('stop', reason=reason)
        self.latch(None, reason)
        raise Stopped(reason)

    def lanes(self):
        """Every lane's state in the shared output folder: this lane's from memory, the others' from their files."""
        states = {self.lane or 'smoke': self.state}
        for path in sorted(self.output.glob('driver-status-*.json')):
            states.setdefault(path.name[len('driver-status-'):-len('.json')], json.loads(path.read_text()))
        return states

    def clear_latch(self, amendment):
        if not Path(amendment).is_file():
            raise ValueError(f'amendment file does not exist: {amendment}')
        latch = self.state.get('harm_latch')
        if not latch:
            raise ValueError('no harm latch to clear')
        if self.verdict_sha(latch['cell']) != latch['verdict_sha256']:  # a lane's own end latches with no verdict
            raise ValueError('latched verdict changed before amendment')
        cleared = dict(cell=latch['cell'], amendment=str(Path(amendment).resolve()), verdict_sha256=latch['verdict_sha256'])
        self.state.setdefault('cleared_latches', []).append(cleared)
        del self.state['harm_latch']
        self.event('latch_cleared', **cleared)

    def reconcile_smoke_starts(self):
        starts = []
        for path in self.output.glob('smoke-*/run/started.json'):
            try:
                value = json.loads(path.read_text())['started_at']
                if type(value) not in (int, float):
                    raise ValueError('started_at must be numeric')
                starts.append(datetime.datetime.fromtimestamp(value, datetime.timezone.utc))
            except (OSError, ValueError, KeyError, OverflowError) as exc:
                raise ValueError(f'{path}: malformed SMOKE start: {exc}') from exc
        if self.state.get('first_smoke_dispatch'):
            starts.append(datetime.datetime.fromisoformat(self.state['first_smoke_dispatch']))
        if starts:
            first = min(starts).isoformat()
            if self.state.get('first_smoke_dispatch') != first:
                self.state['first_smoke_dispatch'] = first
                self.state.setdefault('registered_caps', self.caps.copy())
                self.event('first_smoke_dispatch', started_at=first)

    def latch_for(self, name, verdict):
        if not verdict or self.state.get('harm_latch'):
            return
        identity = (verdict.get('identity') or {}).get('status')
        launched = bool(verdict.get('owner_status'))
        # A fault the driver redispatches can leave no model record (a launch refused, an owner killed, a login or
        # quota refused): its gap is no identity failure. A wrong model always is.
        explained = str(verdict.get('reason', '')).startswith(ONCE)
        reason = None
        if identity == 'MISMATCH' or (
                (identity == 'UNVERIFIED' or (identity == 'UNKNOWN' and launched)) and not explained):
            reason = f'identity {identity}'
        elif verdict.get('status') != 'STOP':
            if not isinstance(verdict.get('scope_violations'), list) or verdict['scope_violations']:
                reason = 'scope_violations missing or non-empty'
            elif verdict.get('teardown') != 'CLEAN':
                reason = f'teardown {verdict.get("teardown")}'
            elif identity != 'MATCH':
                reason = f'identity {identity}'
        if reason:
            self.latch(name, reason)

    def verdict_sha(self, name):
        """The sha256 of a slot's current verdict; None for no slot (a lane's own end) or no verdict."""
        path = self.output / f'verdict-{name}.json'
        return digest(path) if name and path.is_file() else None

    def cleared(self, name):
        """Whether an amendment cleared the latch of the slot's current verdict."""
        sha = self.verdict_sha(name)
        return bool(sha) and any(item['cell'] == name and item['verdict_sha256'] == sha
                                 for item in self.state.get('cleared_latches', ()))

    def latch(self, name, reason):
        """Set the harm latch for a slot's verdict (name), or with no slot for the lane's own end. A verdict whose latch
        an amendment cleared is not latched again; nothing else is exempt."""
        if self.state.get('harm_latch'):
            return
        if self.cleared(name):
            return
        self.state['harm_latch'] = dict(cell=name, reason=reason, verdict_sha256=self.verdict_sha(name))
        self.event('harm_latch', cell=name, reason=reason)

    def assert_active(self):
        for lane, state in self.lanes().items():
            if state.get('harm_latch'):
                raise Stopped(f'harm latch in lane {lane}: {state["harm_latch"]}')
        first = self.state.get('first_smoke_dispatch')
        if first and datetime.datetime.now(datetime.timezone.utc) >= datetime.datetime.fromisoformat(first) + datetime.timedelta(days=7):
            self.stop('7-day deadline reached')

    def image(self):
        if cell.image_identity(self.runtime):
            return True
        tarball = Path(self.runtime['image_tarball'])
        if not tarball.is_file():
            self.event('hold', reason='image tarball missing')
            return False
        try:
            subprocess.run(['docker', 'load', '-i', str(tarball)], check=True,
                           capture_output=True, text=True)
        except subprocess.CalledProcessError as exc:
            stderr = (exc.stderr or '').splitlines()
            self.event('hold', reason=f'docker load failed: {stderr[0] if stderr else exc}')
            return False
        if not cell.image_identity(self.runtime):
            raise RuntimeError('image identity mismatch after docker load')
        self.event('image_loaded')
        return True

    def cell_disk(self):
        """Free space as the cell image sees it on /cell (a bind of the output volume) and on a fresh /tmp volume:
        each needs the delivery helper's floor plus 2 GiB, so the helper never refuses in B for want of disk."""
        argv = ['docker', 'run', '--rm', '--name', 'devlyn-0266-disk-' + uuid.uuid4().hex, '--network', 'none',
                '--read-only', '--cap-drop', 'ALL', '--security-opt', 'no-new-privileges',
                '--mount', f'type=bind,src={self.output},dst=/cell,readonly', '--mount', 'type=volume,dst=/tmp',
                self.runtime['image'], 'python3', '-c', DISK_PROBE]
        try:
            measured = json.loads(subprocess.run(argv, check=True, capture_output=True, text=True,
                                                 timeout=120).stdout)
            short = []
            for path in ('/cell', '/tmp'):
                floor = max(10 * GIB, (measured[path]['total'] + 49) // 50) + 2 * GIB
                if measured[path]['free'] < floor:
                    short.append(f'{path} has {measured[path]["free"]} bytes free, below {floor}')
        except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as exc:
            self.event('hold', reason=f'cell disk check failed: {exc}')
            return False
        if short:
            self.event('hold', reason='cell disk below the delivery floor: ' + '; '.join(short))
            return False
        return True

    def renew(self, expiry, min_token_seconds):
        """The host renewal at <= 300 s, under the lock every lane shares: one renewal command per expiry."""
        with open(self.renewal_lock, 'a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            try:
                renewed = credential(self.runtime)
            except (OSError, ValueError, KeyError, subprocess.CalledProcessError) as exc:
                self.event('hold', reason=f'credential renewal check failed: {exc}')
                return None
            if renewed['expires'] > expiry:
                self.event('renewal_skipped', expiry=expiry, renewed=renewed['expires'])
            elif any(expiry in state.get('renewed_expiries', ()) for state in self.lanes().values()):
                self.event('hold', reason='renewal needs owner', expiry=expiry)
                return None
            else:
                help_text = subprocess.run(['claude', '--help'], check=True, capture_output=True, text=True).stdout
                command = renewal_command(self.runtime, help_text)
                self.state['renewed_expiries'].append(expiry)
                self.event('renewal_attempt', expiry=expiry)
                try:
                    subprocess.run(command, capture_output=True, text=True, timeout=180)
                except (subprocess.TimeoutExpired, OSError) as exc:
                    self.event('renewal_command_error', expiry=expiry, reason=str(exc))
                try:
                    renewed = credential(self.runtime)
                except (OSError, ValueError, KeyError, subprocess.CalledProcessError) as exc:
                    self.event('hold', reason=f'credential renewal check failed: {exc}')
                    return None
                if renewed['expires'] <= expiry:
                    self.event('hold', reason='renewal did not advance expiry', expiry=expiry)
                    return None
                self.event('renewed', expiry=renewed['expires'])
        return renewed if renewed['expires'] - time.time() >= min_token_seconds else None

    def ready(self, min_token_seconds=cell.MIN_TOKEN_SECONDS, slot=None, previous=None):
        self.approved_account = None
        if (self.output.parent / OPERATOR_HOLD).exists():  # host courtesy: no new cell while the operator's file exists
            self.event('hold', reason='operator hold')
            return False
        free = shutil.disk_usage(self.output).free
        if free < cell.HEADROOM_BYTES:
            self.event('hold', reason=f'output volume has {free} bytes free, below {cell.HEADROOM_BYTES}')
            return False
        try:
            snapshot = credential(self.runtime)
        except (OSError, ValueError, KeyError, subprocess.CalledProcessError) as exc:
            self.event('hold', reason=f'credential snapshot failed: {exc}')
            return False
        remaining = snapshot['expires'] - time.time()
        if remaining < min_token_seconds:
            expiry = snapshot['expires']
            if expiry in self.state['renewed_expiries']:
                self.event('hold', reason='renewal needs owner', expiry=expiry)
                return False
            if remaining > 300:
                self.event('hold', reason='awaiting renewal window', expiry=expiry)
                return False
            snapshot = self.renew(expiry, min_token_seconds)
            if not snapshot:
                return False
        if not self.image() or not self.cell_disk():  # local holds first: the usage endpoint is read once per dispatch
            return False
        unread = None  # amendment 1: why no window was read (a refused read, or its Retry-After still running)
        if time.time() < self.unread_until:
            unread = dict(until=datetime.datetime.fromtimestamp(self.unread_until, datetime.timezone.utc).isoformat())
        else:
            try:
                windows = counted(cell.claude_limits(self.runtime, snapshot['access_token']))
            except (OSError, ValueError, KeyError) as exc:
                if not isinstance(exc, urllib.error.HTTPError) or exc.code != 429:
                    self.event('hold', reason=f'Claude window check failed: {exc}')
                    return False
                named = exc.headers.get('Retry-After', '')  # whole seconds set the deadline; anything else, none
                unread = dict(retry_after=int(named) if named.isascii() and named.isdigit() else None)
                if unread['retry_after'] is not None:
                    self.unread_until = time.time() + unread['retry_after']
        if unread is None and 'seven_day' not in windows:  # a read without it is a failed read, never a pass
            self.event('hold', reason='Claude window evidence unavailable: no seven-day window')
            return False
        waiting = self.state['split_wait'].get(slot, {}) if slot else {}
        if waiting and 'account' in waiting and waiting['account'] != snapshot['account']:
            del self.state['split_wait'][slot]
            self.event('split_wait_account_changed', cell=slot, before=waiting['account'],
                       after=snapshot['account'])
            waiting = {}
        waits = waiting.get('resets', waiting)
        if unread is not None:  # a split wait holds: its reset cannot be confirmed; anything else dispatches
            if waiting:
                self.event('hold', reason='awaiting split window reset: windows unread', cell=slot, waits=waits,
                           **unread)
                return False
            self.event('window_unread', **unread, **({'cell': slot} if slot else {}))
            self.approved_account = snapshot['account'].copy()
            return True
        if waiting and any(same_window(windows.get(window, {}).get('resets'), reset) for window, reset in waits.items()):
            self.event('hold', reason='awaiting split window reset', cell=slot, waits=waits)
            return False
        if waiting:
            del self.state['split_wait'][slot]
        over = exceeded(windows, self.caps)
        if over:
            if slot:
                self.state['split_wait'][slot] = {'account': snapshot['account'], 'resets': over}
                split = f'{previous}:{slot}'
                if split not in self.state['split_blocks']:
                    self.state['split_blocks'].append(split)
                    self.event('split_block', block=split, waits=over)
            self.event('hold', reason='Claude window near exhaustion', windows=windows, caps=self.caps)
            return False
        self.approved_account = snapshot['account'].copy()
        return True

    def verdict(self, name):
        path = self.output / f'verdict-{name}.json'
        return json.loads(path.read_text()) if path.is_file() else None

    def screen_slot(self, name):
        """Whether the slot is a screen row (arm column C-K<n>, not SMOKE): DESIGN "Stage S" runs no screen cell
        again."""
        row = next((row for row in self.slots if row[0] == name), None)
        return bool(row) and row[2].startswith('C-K') and row[1] != 'SMOKE'

    def redispatch(self, name, verdict):
        """Whether a STOP is archived and its slot run again: a proven Docker loss, the slot's first launch fault,
        memory kill or shared account fault, and (amendment 2) a registered slot's failed teardown once an amendment
        has cleared its latch; dispatch() proves the teardown of a Docker loss or a failed teardown first (recover).
        Anything else, a repeat of one of those three on the slot among it and a failed teardown no amendment cleared,
        stays a STOP, which the caller latches for both lanes. The repeat is read from the slot's archive, so it is a
        STOP at a restart too. A screen slot is run again only when no owner ran in the STOP (DESIGN "Stage S" rule 4:
        no screen cell is run again), and never for a failed teardown."""
        if self.screen_slot(name) and verdict.get('owner_ran') is not False:
            return False
        reason = str(verdict.get('reason', ''))
        if reason.startswith(TEARDOWN_FAILED) and self.cleared(name) and not self.screen_slot(name):
            return True
        kind = next((prefix for prefix in ONCE if reason.startswith(prefix)), None)
        if kind and any(str(json.loads(path.read_text()).get('reason', '')).startswith(kind)
                        for path in self.output.glob(f'verdict-{name}.stop-*.json')):
            return False
        if reason.startswith((LAUNCH_FAULT, MEMORY_KILL)):
            return verdict.get('teardown') == 'CLEAN'
        return reason.startswith(ACCOUNT_FAULT) or docker_fault(verdict)

    def prove_docker_teardown(self, name):
        """End an attempt whose teardown did not finish (a Docker loss, or a failed teardown an amendment cleared:
        amendment 2) as a normal teardown ends it: its stopped containers removed (the owner among them, unless the
        cell's own teardown had removed it already: run/started.json names the owner and the /tmp volume either way),
        then, while the volume still exists, its /tmp preserved into the cell by preserve_tmp (run_cell.py's, which
        removes the volume), and both proven gone; the attempt's credential copy must be gone from scratch first.
        Returns how /tmp ended: 'preserved' or 'volume absent'. A step that fails or cannot be proved stops both lanes
        and leaves the volume in place."""
        try:
            started = json.loads((self.output / name / 'run/started.json').read_text())
            plan = json.loads((self.output / name / 'plan.json').read_text())
            if (Path(self.runtime['scratch']) / 'credentials' / plan['name']).exists():  # 0265/cell.py's secret
                raise ValueError("the attempt's credential copy is still in scratch")
            argv = started['create_argv']
            volume = started['tmp_volume']
            if (argv[0] != 'create' or argv.count('--name') != 1
                    or f'type=volume,src={volume},dst=/tmp' not in argv):
                raise ValueError('owner container identity is missing from started.json')
            owner_name = argv[argv.index('--name') + 1]

            def docker(*args):
                return subprocess.run(['docker', *args], check=True, capture_output=True, text=True).stdout.strip()

            ids = docker('ps', '-aq', '--no-trunc', '--filter', f'volume={volume}').splitlines()
            owner = docker('ps', '-aq', '--no-trunc', '--filter', f'name=^/{owner_name}$')
            if owner and owner not in ids:
                raise ValueError('recorded owner container was not found on its volume')
            found = []
            for cid in ids:
                item = json.loads(docker('inspect', cid))[0]
                if (item['Id'] != cid or item['Config']['Labels'].get('devlyn.task') != '0233'
                        or not any(mount['Name'] == volume for mount in item['Mounts'] if mount['Type'] == 'volume')):
                    raise ValueError(f'container {cid} does not match the attempt volume and label')
                if item['State']['Running'] or item['State']['Pid'] != 0:
                    raise ValueError(f'container {cid} is still running')
                found.append(dict(id=cid, name=item['Name'], state=item['State']['Status']))
            for item in found:
                docker('rm', item['id'])
            if (docker('ps', '-aq', '--no-trunc', '--filter', f'volume={volume}')
                    or docker('ps', '-aq', '--no-trunc', '--filter', f'name=^/{owner_name}$')):
                raise ValueError('container removal could not be verified')
            tmp = 'volume absent'
            if docker('volume', 'ls', '-q', '--filter', f'name=^{volume}$'):
                cell.cell_run.preserve_tmp(volume, Path(plan['tmp']), plan['image'])
                tmp = 'preserved'
            if docker('volume', 'ls', '-q', '--filter', f'name=^{volume}$'):
                raise ValueError('volume removal could not be verified')
        except (OSError, ValueError, KeyError, IndexError, TypeError, AttributeError,
                subprocess.SubprocessError) as exc:
            self.stop(f'{name}: Docker teardown proof failed: {exc}')
        self.event('docker_teardown_proven', cell=name, source='run/started.json create_argv and tmp_volume',
                   found=found, removed=[item['id'] for item in found], removed_volume=volume, tmp=tmp)
        return tmp

    def recover(self, name, verdict):
        """A Docker loss, or a registered slot's failed teardown whose latch an amendment cleared (amendment 2), before
        it is archived: ended as a normal teardown ends a cell (prove_docker_teardown), sealed again now that /tmp is
        in the cell (run_cell.seal_after_teardown, as after a normal teardown) and, when its owner ran, given the
        evidence of DESIGN "The rule for attempts" (run_cell.stop_evidence, which replaces a scope_error the cell's
        own STOP wrote). The verdict records how /tmp ended (tmp_recovery) and is replaced atomically."""
        tmp = self.prove_docker_teardown(name)
        sealed, failures = cell.seal_after_teardown(self.output / name)
        if failures:
            self.stop(f'{name}: evidence collection failed after the Docker recovery: ' + '; '.join(failures[:3]))
        record = dict(verdict, tmp_recovery=tmp, evidence_manifest_sha256=sealed)
        if record.get('owner_ran'):
            record = cell.stop_evidence(self.output / name, record)
        replace(self.output / f'verdict-{name}.json', json.dumps(record, indent=2))

    def dispatch(self, row):
        name, task, arm, config = row[:4]
        if arm not in COLUMNS or config not in ('claude', 'codex') or self.lane not in (None, config):
            raise ValueError(f'{name}: 0266 requires arm {"/".join(COLUMNS)} and config claude/codex in its own lane')
        self.assert_active()
        if task != 'SMOKE':
            seal = self.output.parent / 'instructions.seal.json'
            try:
                qualified = json.loads(seal.read_text())['qualification']['status'] == 'PASS'
            except (OSError, ValueError, KeyError, TypeError):
                qualified = False
            if not qualified:
                raise RuntimeError('SMOKE qualification missing or failed')
        verdict = self.verdict(name)
        self.latch_for(name, verdict)
        self.assert_active()
        if verdict:
            if verdict['status'] != 'STOP':
                self.event('skip_finished', cell=name)
                return True
            reason = verdict.get('reason', '')
            if reason.startswith(REGRADE):
                rc = cell.regrade(self.runtime_path, name, expected_account=self.approved_account)
                self.event('regrade', cell=name, rc=rc)
                self.latch_for(name, self.verdict(name))
                self.assert_active()
                self.terminal(name, rc)
                return rc == 0
            if self.redispatch(name, verdict):
                if docker_fault(verdict) or reason.startswith(TEARDOWN_FAILED):  # its teardown is proved first
                    self.recover(name, verdict)
                number = 1
                while (self.output / f'verdict-{name}.stop-{number}.json').exists():
                    number += 1
                (self.output / f'verdict-{name}.json').rename(self.output / f'verdict-{name}.stop-{number}.json')
                (self.output / name).rename(self.output / f'{name}.stop-{number}')
            else:
                self.latch(name, f'STOP {reason}')  # any other STOP stops both lanes, as it stopped the one driver
                raise Stopped(f'{name}: STOP {reason}')
        if task == 'SMOKE' and not self.state.get('first_smoke_dispatch'):
            first = datetime.datetime.now(datetime.timezone.utc).isoformat()
            self.state['first_smoke_dispatch'] = first
            self.state['registered_caps'] = self.caps.copy()
            self.event('first_smoke_dispatch', cell=name, started_at=first)
        rc = cell.run(self.runtime_path, name, task, arm, config, expected_account=self.approved_account)
        finished = self.verdict(name)
        self.event('run', cell=name, rc=rc)
        if task == 'SMOKE':
            if rc == 3 and not any(self.output.glob('smoke-*/run/started.json')):
                self.state.pop('first_smoke_dispatch', None)
                self.state.pop('registered_caps', None)
                self.event('smoke_start_refused', cell=name)
            self.reconcile_smoke_starts()
        self.latch_for(name, finished)
        self.assert_active()
        self.terminal(name, rc)
        return rc == 0

    def terminal(self, name, rc):
        """A STOP that run_cell returned (rc 2), from a cell run or from a regrade, and that is neither regraded nor
        redispatched stops both lanes now, before the lane waits on anything."""
        if rc == 2:
            verdict = self.verdict(name)
            reason = verdict.get('reason', '') if verdict else 'no verdict'
            if not (verdict and (reason.startswith(REGRADE) or self.redispatch(name, verdict))):
                self.latch(name, f'STOP {reason}')
                raise Stopped(f'{name}: STOP {reason}')

    def run(self):
        """The lane's slots in order. Any exception but Stopped and an operator's interrupt sets the harm latch with
        its text before it ends the process, so the other lane stops dispatching too."""
        i, name = 0, None
        try:
            while i < len(self.slots):
                self.assert_active()
                row = self.slots[i]
                name, task, arm, config = row[:4]
                verdict = self.verdict(name)
                self.latch_for(name, verdict)
                self.assert_active()
                if verdict and verdict['status'] != 'STOP':
                    self.event('skip_finished', cell=name)
                    i += 1
                    continue
                if verdict and self.screen_slot(name) and self.cleared(name) and not (
                        str(verdict.get('reason', '')).startswith(REGRADE) or self.redispatch(name, verdict)):
                    self.event('skip_cleared_stop', cell=name)  # DESIGN "Stage S": the slot reads as an unknown
                    i += 1
                    continue
                if verdict:  # a STOP met at a restart (written, then the process died before its latch): one that is
                    self.terminal(name, 2)  # neither regraded nor redispatched stops both lanes before any wait
                elif (self.output / name).exists():  # an attempt the lane was interrupted in: its container may still
                    reason = 'an attempt without a verdict (the lane was interrupted in it)'  # run, and prepare would
                    self.latch(name, reason)  # refuse its folder only after a readiness wait
                    raise Stopped(f'{name}: {reason}')
                second = (i > 0 and self.slots[i - 1][1] == task and self.slots[i - 1][3] == config
                          and self.slots[i - 1][-1] == row[-1])
                assessment = bool(verdict and str(verdict.get('reason', '')).startswith(REGRADE))
                if not self.ready(1500 if assessment else cell.MIN_TOKEN_SECONDS,
                                  name if second else None, self.slots[i - 1][0] if second else None):
                    time.sleep(60)
                    continue
                if self.dispatch(row):
                    i += 1
                else:
                    time.sleep(60)
        except Stopped:
            raise
        except Exception as exc:
            self.latch(None, f'lane {self.lane or "smoke"} ended at {name}: {type(exc).__name__}: {exc}')
            raise
        self.event('complete', cells=len(self.slots))


if __name__ == '__main__':
    if len(sys.argv) >= 4 and sys.argv[1] == '--clear-latch':
        Driver(sys.argv[3], []).clear_latch(sys.argv[2])
    else:
        Driver(sys.argv[1], rows(sys.argv[2:])).run()
