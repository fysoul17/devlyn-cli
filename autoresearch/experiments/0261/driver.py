"""Serial 0261 dispatcher. Run under caffeinate -dimsu: driver.py <runtime.json> <cells.tsv>[:prefix] ..."""
import datetime
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

import importlib.util

HERE = Path(__file__).resolve().parent


def load(name):
    spec = importlib.util.spec_from_file_location('driver0261_' + name, HERE / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


cell = load('run_cell')
WINDOWS = ('seven_day', 'five_hour')


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


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


def fits(windows, caps):
    return all(windows[window]['used'] < caps[window] for window in WINDOWS)


def docker_fault(verdict):
    return (bool(verdict) and verdict.get('status') == 'STOP' and verdict.get('teardown') == 'FAILED'
            and 'Cannot connect to the Docker daemon' in
            str(verdict.get('teardown_error', '')) + str(verdict.get('reason', '')))


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
        self.slots = slots
        self.caps = self.runtime['caps']
        self.approved_account = None
        if self.caps != {'seven_day': 95, 'five_hour': 95}:
            raise ValueError('registration caps must be seven_day=95 and five_hour=95')
        self.status_path = self.output / 'driver-status.json'
        self.state = json.loads(self.status_path.read_text()) if self.status_path.exists() else {
            'renewed_expiries': [], 'split_blocks': [], 'split_wait': {}}
        self.state.setdefault('split_wait', {})
        self.reconcile_smoke_starts()
        if self.state.get('registered_caps') not in (None, self.caps):
            self.stop('registered caps differ from 95/95')

    def event(self, kind, **fields):
        record = dict(at=datetime.datetime.now(datetime.timezone.utc).isoformat(), event=kind, **fields)
        with (self.output / 'driver.log').open('a') as stream:
            stream.write(json.dumps(record, sort_keys=True) + '\n')
        self.state.update(current=record)
        self.status_path.write_text(json.dumps(self.state, indent=2) + '\n')

    def stop(self, reason):
        self.event('stop', reason=reason)
        raise RuntimeError(reason)

    def clear_latch(self, amendment):
        if not Path(amendment).is_file():
            raise ValueError(f'amendment file does not exist: {amendment}')
        latch = self.state.get('harm_latch')
        if not latch:
            raise ValueError('no harm latch to clear')
        verdict = self.output / f'verdict-{latch["cell"]}.json'
        if not verdict.is_file():
            raise ValueError(f'latched verdict missing: {verdict}')
        sha = digest(verdict)
        if latch.get('verdict_sha256') and latch['verdict_sha256'] != sha:
            raise ValueError('latched verdict changed before amendment')
        cleared = dict(cell=latch['cell'], amendment=str(Path(amendment).resolve()), verdict_sha256=sha)
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
        reason = None
        if identity in ('MISMATCH', 'UNVERIFIED') or (identity == 'UNKNOWN' and launched):
            reason = f'identity {identity}'
        elif verdict.get('status') != 'STOP':
            if not isinstance(verdict.get('scope_violations'), list) or verdict['scope_violations']:
                reason = 'scope_violations missing or non-empty'
            elif verdict.get('teardown') != 'CLEAN':
                reason = f'teardown {verdict.get("teardown")}'
            elif identity != 'MATCH':
                reason = f'identity {identity}'
        if reason:
            path = self.output / f'verdict-{name}.json'
            sha = digest(path) if path.is_file() else None
            if any(item['cell'] == name and item['verdict_sha256'] == sha
                   for item in self.state.get('cleared_latches', ())):
                return
            self.state['harm_latch'] = dict(cell=name, reason=reason, verdict_sha256=sha)
            self.event('harm_latch', cell=name, reason=reason)

    def assert_active(self):
        if self.state.get('harm_latch'):
            raise RuntimeError('harm latch: ' + str(self.state['harm_latch']))
        first = self.state.get('first_smoke_dispatch')
        if first and datetime.datetime.now(datetime.timezone.utc) >= datetime.datetime.fromisoformat(first) + datetime.timedelta(days=14):
            self.stop('14-day deadline reached')

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

    def ready(self, min_token_seconds=6300, slot=None, previous=None):
        self.approved_account = None
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
                return False
            if renewed['expires'] <= expiry:
                self.event('hold', reason='renewal did not advance expiry', expiry=expiry)
                return False
            self.event('renewed', expiry=renewed['expires'])
            if renewed['expires'] - time.time() < min_token_seconds:
                return False
            snapshot = renewed
        try:
            windows = cell.claude_limits(self.runtime, snapshot['access_token'])
        except (OSError, ValueError, KeyError) as exc:
            self.event('hold', reason=f'Claude window check failed: {exc}')
            return False
        if any(window not in windows for window in WINDOWS):
            self.event('hold', reason='Claude window evidence unavailable')
            return False
        waiting = self.state['split_wait'].get(slot, {}) if slot else {}
        if waiting and 'account' in waiting and waiting['account'] != snapshot['account']:
            del self.state['split_wait'][slot]
            self.event('split_wait_account_changed', cell=slot, before=waiting['account'],
                       after=snapshot['account'])
            waiting = {}
        waits = waiting.get('resets', waiting)
        if waiting and any(same_window(windows[window]['resets'], reset) for window, reset in waits.items()):
            self.event('hold', reason='awaiting split window reset', cell=slot, waits=waits)
            return False
        if waiting:
            del self.state['split_wait'][slot]
        if not fits(windows, self.caps):
            if slot:
                exceeded = {window: windows[window]['resets'] for window in WINDOWS
                            if windows[window]['used'] >= self.caps[window]}
                self.state['split_wait'][slot] = {'account': snapshot['account'], 'resets': exceeded}
                if exceeded:
                    split = f'{previous}:{slot}'
                    if split not in self.state['split_blocks']:
                        self.state['split_blocks'].append(split)
                        self.event('split_block', block=split, waits=exceeded)
            self.event('hold', reason='Claude window near exhaustion', windows=windows, caps=self.caps)
            return False
        if not self.image():
            return False
        self.approved_account = snapshot['account'].copy()
        return True

    def verdict(self, name):
        path = self.output / f'verdict-{name}.json'
        return json.loads(path.read_text()) if path.is_file() else None

    def prove_docker_teardown(self, name):
        """Remove the stopped containers and /tmp volume recorded for this attempt."""
        try:
            started = json.loads((self.output / name / 'run/started.json').read_text())
            argv = started['create_argv']
            volume = started['tmp_volume']
            if (argv[0] != 'create' or argv.count('--name') != 1
                    or f'type=volume,src={volume},dst=/tmp' not in argv):
                raise ValueError('owner container identity is missing from started.json')
            owner_name = argv[argv.index('--name') + 1]

            def docker(*args):
                return subprocess.run(['docker', *args], check=True, capture_output=True, text=True).stdout.strip()

            ids = docker('ps', '-aq', '--no-trunc', '--filter', f'volume={volume}').splitlines()
            owner = json.loads(docker('inspect', owner_name))[0]
            if owner['Id'] not in ids or owner['Name'] != '/' + owner_name:
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
            docker('volume', 'rm', volume)
            if docker('volume', 'ls', '-q', '--filter', f'name=^{volume}$'):
                raise ValueError('volume removal could not be verified')
        except (OSError, ValueError, KeyError, IndexError, TypeError, AttributeError,
                subprocess.SubprocessError) as exc:
            self.stop(f'{name}: Docker teardown proof failed: {exc}')
        self.event('docker_teardown_proven', cell=name, source='run/started.json create_argv and tmp_volume',
                   found=found, removed=[item['id'] for item in found], removed_volume=volume)

    def dispatch(self, row):
        name, task, arm, config = row[:4]
        if arm not in ('B', 'C') or config != 'claude':
            raise ValueError('0261 requires arm B/C and config claude')
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
            if reason.startswith(('assessment failed', 'assessor produced', 'assessment held:')):
                rc = cell.regrade(self.runtime_path, name, expected_account=self.approved_account)
                self.event('regrade', cell=name, rc=rc)
                self.latch_for(name, self.verdict(name))
                self.assert_active()
                return rc == 0
            infrastructure_fault = docker_fault(verdict)
            if reason.startswith('shared account fault during execution:') or infrastructure_fault:
                if infrastructure_fault:
                    self.prove_docker_teardown(name)
                number = 1
                while (self.output / f'verdict-{name}.stop-{number}.json').exists():
                    number += 1
                (self.output / f'verdict-{name}.json').rename(self.output / f'verdict-{name}.stop-{number}.json')
                (self.output / name).rename(self.output / f'{name}.stop-{number}')
            else:
                raise RuntimeError(f'{name}: STOP {reason}')
        if task == 'SMOKE' and not self.state.get('first_smoke_dispatch'):
            first = datetime.datetime.now(datetime.timezone.utc).isoformat()
            self.state['first_smoke_dispatch'] = first
            self.state['registered_caps'] = self.caps.copy()
            self.event('first_smoke_dispatch', cell=name, started_at=first)
        rc = cell.run(self.runtime_path, name, task, arm, config, expected_account=self.approved_account)
        self.event('run', cell=name, rc=rc)
        finished = self.verdict(name)
        if task == 'SMOKE':
            if rc == 3 and not any(self.output.glob('smoke-*/run/started.json')):
                self.state.pop('first_smoke_dispatch', None)
                self.state.pop('registered_caps', None)
                self.event('smoke_start_refused', cell=name)
            self.reconcile_smoke_starts()
        self.latch_for(name, finished)
        self.assert_active()
        if rc == 2:
            verdict = self.verdict(name)
            reason = verdict.get('reason', '') if verdict else 'no verdict'
            if not (reason.startswith(('assessment failed', 'assessor produced', 'assessment held:',
                                       'shared account fault during execution:')) or docker_fault(verdict)):
                raise RuntimeError(f'{name}: STOP {reason}')
        return rc == 0

    def run(self):
        i = 0
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
            second = i > 0 and self.slots[i - 1][1] == task and self.slots[i - 1][3] == config and self.slots[i - 1][-1] == row[-1]
            assessment = bool(verdict and str(verdict.get('reason', '')).startswith(
                ('assessment failed', 'assessor produced', 'assessment held:')))
            if not self.ready(1500 if assessment else 6300,
                              name if second else None, self.slots[i - 1][0] if second else None):
                time.sleep(60)
                continue
            if self.dispatch(row):
                i += 1
            else:
                time.sleep(60)
        self.event('complete', cells=len(self.slots))


if __name__ == '__main__':
    if len(sys.argv) >= 4 and sys.argv[1] == '--clear-latch':
        Driver(sys.argv[3], []).clear_latch(sys.argv[2])
    else:
        Driver(sys.argv[1], rows(sys.argv[2:])).run()
