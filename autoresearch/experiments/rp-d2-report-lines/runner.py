"""Serial rp-d2 adapter; runner.py <runtime> smoke|measured [--through-pair N]."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import time

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('prepare_rpd2_runner', HERE / 'prepare.py')
prepare = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prepare)
load, PRIOR = prepare.load, prepare.PRIOR
legacy = load('runner_rpd1_rpd2', PRIOR / 'runner.py')
legacy.prepare = prepare.legacy
legacy.github = github = prepare.github
read, write, digest, require = legacy.read, legacy.write, legacy.digest, github.require
cell = legacy.cell
PAIRS = [(task, engine) for _, task, engine in legacy.SCHEDULE]
SCHEDULE = [(f'm{2 * pair + offset + 1:02}', task, engine)
            for pair, (task, engine) in enumerate(PAIRS) for offset in range(2)]
ARMS = {SCHEDULE[2 * pair + offset][0]: arm for pair in range(8)
        for offset, arm in enumerate(('X', 'Y') if pair % 2 == 0 else ('Y', 'X'))}


def smoke_slots(attempt=1):
    if type(attempt) is not int or attempt not in (1, 2):
        raise ValueError('smoke_attempt must be 1 or 2 (the registered spares)')
    prefix = 'smoke' if attempt == 1 else 'smoke2'
    return [(f'{prefix}-{engine}-{arm}', 'SM', engine) for engine in ('claude', 'codex') for arm in ('X', 'Y')]


def arm_for(name):
    if name in ARMS:
        return ARMS[name]
    require(name in {row[0] for attempt in (1, 2) for row in smoke_slots(attempt)}, 'unregistered rp-d2 slot')
    return name[-1]


def frozen_runtime(runtime):
    return {key: value for key, value in runtime.items() if key not in ('auth', 'auth_manifest_sha256', 'renewed_from')}


def runtime_binding(runtime):
    return hashlib.sha256(json.dumps(frozen_runtime(runtime), sort_keys=True).encode()).hexdigest()


def solo_route(tasks, config, arm):
    require(arm in ('X', 'Y'), 'unregistered rp-d2 arm')
    return legacy.solo_route(tasks, config, arm)


def codex_account(path):
    raw = cell.auth.read_private(cell.auth.directory(path), 'codex.json')
    try:
        account = json.loads(raw)['tokens']['account_id']
    except (ValueError, KeyError, TypeError):
        raise ValueError('invalid Codex account identity') from None
    require(isinstance(account, str) and bool(account.strip()), 'invalid Codex account identity')
    return hashlib.sha256(account.encode()).hexdigest()[:12]


# Both grading paths call 0242's global; keep 0238's unused H/P initializer probes separate.
legacy.legacy.policy.check.__globals__['base_policy'].route_for = solo_route
legacy.smoke_slots = smoke_slots
legacy.SCHEDULE = SCHEDULE
legacy.BOOT_REFUSALS |= {'measured Claude requires boot_catalogs.claude.' + arm for arm in ('X', 'Y')}


def accounting_only(verdict):
    """Recognize counter uncertainty, never an arbitrary accounting/parser failure."""
    gaps = verdict.get('usage_gaps')
    if not gaps:
        return False
    if verdict['config'] == 'claude':
        allowed = {'error or retry outside scope', 'usage is not an object',
                   'invalid thinking counter object', 'invalid token counter',
                   'terminal counters incomplete', 'thinking exceeds output',
                   'invalid native aggregate counters', 'child result aggregate mismatch',
                   'whole native aggregate mismatch', 'owner-only aggregate mismatch'}
        return all(gap in allowed for gap in gaps)
    return all(re.fullmatch(r'rollout \S+ has no usable counters|'
                            r'plain root \S+: footer (?:None|\d+) vs trace (?:None|\d+)|'
                            r'thread \S+: rollout counters \[[\d, None]+\] vs trace \[[\d, None]+\]', gap)
               for gap in gaps)


class AccountingContinuation(legacy.legacy.Runner):
    """Resume the skipped checks before rp-d1 archives/deletes, without rerunning the owner."""

    def run(self, name, task, arm, config):
        result = super().run(name, task, arm, config)
        path = Path(self.runtime['output']) / f'verdict-{name}.json'
        if self.runtime['phase'] != 'measured' or not path.exists():
            return result
        verdict = read(path)
        if not (verdict['status'] == 'STOP' and verdict['usage'] == 'UNKNOWN' and
                verdict.get('reason') == 'ValueError: whole-run usage UNKNOWN' and accounting_only(verdict)):
            return result
        out = path.parent / name
        # Preserve the original verdict, including its wall time and accounting diagnostics.
        original = out / 'accounting-stop.json'
        original.write_bytes(path.read_bytes())
        verdict['accounting_stop_sha256'] = digest(original)
        try:
            require(verdict['identity']['status'] == 'MATCH', 'model identity is not MATCH')
            pair = verdict['peer_policy']
            require(pair['status'] == 'MATCH' and not pair['gaps'] and not pair['violations'],
                    'peer identity/evidence is not MATCH')
            require(verdict['teardown'] == 'CLEAN' and not (out / 'pat-scan.json').exists(),
                    'continuation requires clean teardown and PAT scans')
            manifest_path = github.safe_file(out, 'evidence.manifest.json')
            require(digest(manifest_path) == verdict['evidence_manifest_sha256'], 'evidence seal binding changed')
            manifest = read(manifest_path)
            require(not manifest['failures'] and bool(manifest['files']), 'incomplete evidence seal')
            for filename, expected in manifest['files'].items():
                require(digest(github.safe_file(out, filename)) == expected, 'sealed evidence changed')
            # These are the same post-accounting gates and grading order as 0255/0238.
            expected_catalogs = self.boot_expectation(arm, config)
            verdict['boot_catalogs'] = self.boot_catalogs(out, config)
            if expected_catalogs is not None:
                expected_catalogs = {key: sorted(value, key=lambda item: json.dumps(item, sort_keys=True))
                                     for key, value in expected_catalogs.items()}
                require(verdict['boot_catalogs'] == expected_catalogs, 'boot catalog contamination or drift')
            verdict['quota'] = self.frame.quota.classify(out)
            require(not verdict['quota']['execution'], 'authentication or quota fault during execution')
            self.unchanged(out)
            verdict['snapshot'] = self.frame.locate.locate(out)
            started = time.monotonic()
            checked = self.frame.check.check(out, self.runtime)
            delivered = legacy.legacy.delivery.check(out, verdict['snapshot'], self.frame.locate, self.packet)
            write(out / 'delivery.json', delivered)
            verdict.update(checked, source_check_pass=checked['product_check_pass'], delivery=delivered,
                           delivery_pass=delivered['passed'], deterministic_seconds=time.monotonic() - started)
            verdict['status'] = ('PRODUCT_INCOMPLETE' if not delivered['passed'] or
                                verdict['owner_status'] != 'EXITED_0' or pair['protocol_violations'] else
                                'ADJUDICATE' if checked['adjudication_needed'] else
                                'CHECKS_PASS' if checked['product_check_pass'] else 'PRODUCT_INCOMPLETE')
            write(out / 'checked.json', dict(snapshot=self.packet.tree(out / 'snapshot'),
                  checks_sha256=digest(out / 'checks.json'), delivery_sha256=digest(out / 'delivery.json')))
        except (OSError, ValueError, KeyError, TypeError, RuntimeError, subprocess.SubprocessError) as exc:
            # No exception payload may leak a credential into a verdict.
            verdict.update(status='STOP', reason='rp-d2 continuation failed: ' + type(exc).__name__)
        verdict.update(usage='UNKNOWN', input_tokens=None, output_tokens=None)
        write(path, verdict)
        return 2 if verdict['status'] == 'STOP' else 0


# The diamond puts this hook between rp-d1's lifecycle and its 0255 owner runner.
# rp-d1 still owns archive -> done_check -> delete/404 -> final PAT scan for every cell.
class Runner(legacy.Runner, AccountingContinuation):
    def __init__(self, runtime_path, tasks_path=None, *, phase=None):
        original = read(runtime_path)
        require(phase is None or phase == original['phase'], 'phase differs from staged runtime')
        super().__init__(runtime_path, tasks_path, phase=phase)
        self.frozen = runtime_binding(original)
        if 'renewed_from' in original:
            previous = original['renewed_from']
            require(digest(Path(previous['path'])) == previous['sha256'], 'previous runtime binding changed')
            require(frozen_runtime(read(previous['path'])) == frozen_runtime(original),
                    'renewal changed frozen inputs/account')
        # rp-d1 inputs() requires release; retain its full census and add both tarballs below.
        self.runtime['release'] = self.runtime['releases']['X']
        self.active_arm = None
        launch = self.frame.cell_run.run

        def bound_launch(out, runtime):
            require(codex_account(runtime['auth']) == runtime['codex_account'], 'Codex account binding mismatch')
            prepare.verify_release(runtime)
            prepare.binding(out, runtime, arm_for(out.name))
            return launch(out, runtime)

        self.frame.cell_run.run = bound_launch

    def inputs(self):
        result = super().inputs()
        paths = [*HERE.glob('*.py'), HERE / 'DESIGN.md', HERE / 'README.md',
                 PRIOR / 'registration.json', Path(self.runtime['arms_file'])]
        paths += [Path(release['tarball']) for release in self.runtime['releases'].values()]
        result.update({str(path): digest(path) for path in paths})
        return result

    def validate(self, name):
        require(runtime_binding(read(self.runtime_path)) == self.frozen, 'staged runtime changed')
        require(codex_account(self.runtime['auth']) == self.runtime['codex_account'], 'Codex account binding mismatch')
        require(digest(Path(self.runtime['models_cache'])) == self.runtime['models_cache_sha256'], 'models cache changed')
        prepare.verify_release(self.runtime)
        return super().validate(name)

    def repository(self, name):
        require(re.fullmatch('[A-Za-z0-9][A-Za-z0-9-]*', self.runtime['run_id']), 'invalid run_id')
        arm_for(name)
        repository = f'fysoul17/rpd2-{self.runtime["run_id"]}-{name}'
        github.url(repository)
        return repository

    def materialize(self, runtime, name, task, arm, config):
        require(arm == 'B' and self.active_arm == arm_for(name), 'attempt arm/installed route mismatch')
        return prepare.prepare(runtime, name, task, self.active_arm, config, inherited=self.frame.prepare,
                               tasks=self.tasks, tasks_path=self.tasks_path,
                               repository=self.repository(name), remaining=self.remaining(name))

    def boot_expectation(self, arm, config):
        selected = self.active_arm if arm == 'B' else arm
        require(selected in ('X', 'Y'), 'boot catalog requires a bound rp-d2 arm')
        return super().boot_expectation(selected, config)

    def prior_deleted(self, name):
        slots = [row[0] for row in self.smoke + SCHEDULE]
        index = slots.index(name)
        previous = slots[:4] if name == 'm01' else slots[max(0, index - 1):index]
        for slot in previous:
            root = self.runtime['smoke_output' if slot in slots[:4] else 'output']
            record = read(Path(root) / slot / 'rp-verdict.json')
            require(record['status'] not in ('STOP', 'UNKNOWN', 'NOT_RUN'), 'schedule already stopped')
            if name == 'm01':
                require(record['status'] in ('PASS', 'ADJUDICATE'), 'smoke did not establish working delivery')
            receipt = record['repository_cleanup']
            require(receipt.get('repository') == self.repository(slot) and receipt.get('status') == 'DELETED'
                    and receipt.get('http_status') == 404 and receipt.get('archive_manifest_sha256'),
                    'previous repository has no archived deletion/404 receipt')
            require(record['arm'] == arm_for(slot) and
                    record['release'] == prepare.release_identity(self.runtime, arm_for(slot)),
                    'previous slot arm/package binding mismatch')
            require(record['account'] == self.runtime['account'] and
                    record['codex_account'] == self.runtime['codex_account'], 'model accounts changed since smoke')
            if slot in ARMS:
                require(record['frozen_runtime_sha256'] == self.frozen, 'frozen runtime changed between slots')
            if name in ARMS and int(name[1:]) % 2 == 0:
                require(record['auth_manifest_sha256'] == self.runtime['auth_manifest_sha256'] and
                        record['auth'] == self.runtime['auth'], 'model auth renewal refused within a pair')

    def run(self, name, task, arm, config):
        require((name, task, config) in self.slots() and arm == arm_for(name), 'unregistered slot/task/engine/arm')
        self.active_arm = arm
        try:
            result = super().run(name, task, 'B', config)
            path = Path(self.runtime['output']) / name / 'rp-verdict.json'
            record = read(path)
            record.update(schema='rp-d2-verdict-v1', arm=arm, release=prepare.release_identity(self.runtime, arm),
                          account=self.runtime['account'], codex_account=self.runtime['codex_account'], auth=self.runtime['auth'],
                          auth_manifest_sha256=self.runtime['auth_manifest_sha256'], frozen_runtime_sha256=self.frozen)
            write(path, record)
            return result
        finally:
            self.active_arm = None

    def completed_prefix(self):
        records, missing = [], False
        output = Path(self.runtime['output'])
        for name, task, config in self.slots():
            path = output / name / 'rp-verdict.json'
            if not path.exists():
                require(not (output / name).exists() and not (output / f'verdict-{name}.json').exists(),
                        'partial slot exists; preserve it, never replay')
                missing = True
                continue
            require(not missing, 'non-prefix slot records; preserve them, never replay')
            record = read(path)
            require((record['cell'], record['task'], record['config'], record['arm']) ==
                    (name, task, config, arm_for(name)), 'recorded slot binding mismatch')
            require(record['frozen_runtime_sha256'] == self.frozen, 'frozen runtime changed')
            records.append(record)
        return records

    def schedule(self, through_pair=None):
        require(through_pair is None or self.runtime['phase'] == 'measured' and
                type(through_pair) is int and 1 <= through_pair <= 8, 'through-pair requires measured pair 1..8')
        slots = self.slots()
        limit = 2 * through_pair if through_pair is not None else len(slots)
        records = self.completed_prefix()
        require(len(records) <= limit, 'requested pair precedes completed slots')
        stopped = any(row['status'] in ('STOP', 'UNKNOWN', 'NOT_RUN') for row in records)
        for name, task, config in slots[len(records):]:
            if not stopped and len(records) == limit:
                break
            arm = arm_for(name)
            if stopped:
                out = Path(self.runtime['output']) / name
                out.mkdir(parents=True, exist_ok=False)
                record = dict(cell=name, task=task, config=config, arm=arm, status='NOT_RUN',
                    phase=self.runtime['phase'], measurement_eligible=self.runtime['phase'] == 'measured',
                    delivery_assessment='NOT_ASSESSED', dispatched=False, frozen_runtime_sha256=self.frozen,
                    reason='earlier slot stopped the schedule')
                write(out / 'rp-verdict.json', record)
            else:
                stopped = self.run(name, task, arm, config) != 0
                record = read(Path(self.runtime['output']) / name / 'rp-verdict.json')
            records.append(record)
        write(Path(self.runtime['output']) / 'rp-schedule.json', dict(
            status='STOP' if stopped else 'RECORDED' if len(records) == len(slots) else 'PAUSED',
            phase=self.runtime['phase'], slots=records, dispatched=sum(row['dispatched'] for row in records)))
        return 2 if stopped else 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('runtime', type=Path)
    parser.add_argument('phase', choices=('smoke', 'measured'))
    parser.add_argument('--through-pair', type=int)
    args = parser.parse_args()
    return Runner(args.runtime, phase=args.phase).schedule(args.through_pair)


if __name__ == '__main__':
    raise SystemExit(main())
