"""Claude max/high slots over rp-d4's sealed, serial delivery lifecycle."""
import argparse
from copy import deepcopy
import importlib.util
from pathlib import Path
import re
from types import FunctionType

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('runner_rpd4_rpd5', HERE.parent / 'rp-d4-helper-report/runner.py')
legacy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(legacy)
load, PRIOR = legacy.load, legacy.PRIOR
prepare = load('prepare_rpd5_runner', HERE / 'prepare.py')
auth = load('auth_rpd5_runner', HERE / 'auth.py')
github, cell = prepare.github, legacy.cell
read, write, digest, require = legacy.read, legacy.write, legacy.digest, legacy.require
smoke, scan = legacy.smoke, legacy.scan
frozen_runtime, runtime_binding = legacy.frozen_runtime, legacy.runtime_binding
codex_account = auth.codex_account
SCHEDULE = [('c01', 'BV', 'claude'), ('c02', 'BV', 'claude'),
            ('c03', 'Z0', 'claude'), ('c04', 'Z0', 'claude')]
ARMS = {name: 'X' for name, _, _ in SCHEDULE}
EFFORTS = dict(c01='max', c02='high', c03='high', c04='max',
               **{'smoke-claude': 'high', 'smoke2-claude': 'high'})


def smoke_slots(attempt=1):
    require(type(attempt) is int and attempt in (1, 2), 'smoke_attempt must be 1 or 2')
    return [('smoke-claude' if attempt == 1 else 'smoke2-claude', 'SM', 'claude')]


def effort_for(name):
    require(name in EFFORTS, 'unregistered rp-d5 slot')
    return EFFORTS[name]


def arm_for(name):
    effort_for(name)
    return 'X'


def slot_tasks(phase, name):
    require(phase in ('smoke', 'measured') and
            name in [row[0] for row in (SCHEDULE if phase == 'measured' else smoke_slots(1) + smoke_slots(2))],
            'unregistered phase/slot')
    tasks = deepcopy(read(PRIOR / ('smoke-tasks.json' if phase == 'smoke' else 'tasks.json')))
    owner = tasks['routes']['claude']['owner']
    require(owner == dict(engine='claude', model='claude-opus-5-5', effort='max'), 'frozen Claude route changed')
    owner['effort'] = effort_for(name)
    return tasks


def smoke_registry(run_id):
    require(isinstance(run_id, str) and re.fullmatch('[A-Za-z0-9][A-Za-z0-9-]*', run_id), 'invalid run_id')
    return Path.home() / '.devlyn/rp-d5-runs' / run_id


smoke_inputs, smoke_registration = legacy.smoke_inputs, legacy.smoke_registration
# Rebind private instances so rp-d4 retains its scan, smoke registry and closure
# implementation while selecting this study's one release and registered slots.
legacy.prepare, legacy.auth, legacy.github = prepare, auth, github
legacy.SCHEDULE, legacy.ARMS, legacy.arm_for = SCHEDULE, ARMS, arm_for
legacy.smoke_slots, legacy.smoke_registry = smoke_slots, smoke_registry
legacy.legacy.SCHEDULE, legacy.legacy.ARMS, legacy.legacy.arm_for = SCHEDULE, ARMS, arm_for
ancestor = legacy.legacy.legacy  # rp-d1, through rp-d4 -> rp-d2
ancestor.SCHEDULE, ancestor.smoke_slots = SCHEDULE, smoke_slots
ancestor.prepare, ancestor.github = prepare.legacy.legacy.legacy, github


def qualify(record, analysis):
    """Report style is ungraded; delivery, effort and reconciled stages are required."""
    checks = dict(delivery=record.get('status') in ('PASS', 'ADJUDICATE') and
                  record.get('delivery_assessment') in ('PASS', 'ADJUDICATE') and
                  record.get('inherited_status') not in ('PRODUCT_INCOMPLETE', 'STOP', 'UNKNOWN', 'NOT_RUN') and
                  record.get('merge_refused') is False,
                  effort=analysis.get('effort_binding') == 'MATCH',
                  accounting=analysis.get('status') == 'MATCH',
                  stages=bool(analysis.get('stages')) and
                  all(row.get('stage') != 'UNKNOWN' for row in analysis['stages']))
    return dict(status='PASS' if all(checks.values()) else 'FAIL', checks=checks)


class Runner(legacy.Runner):
    def repository(self, name):
        arm_for(name)
        repository = f'fysoul17/rpd5-{self.runtime["run_id"]}-{name}'
        github.url(repository)
        return repository

    def inputs(self):
        return dict(super().inputs(), **{str(path): digest(path) for path in
            [*HERE.glob('*.py'), HERE / 'DESIGN.md', HERE / 'README.md']})

    def select_slot(self, name):
        expected = slot_tasks(self.runtime['phase'], name)
        path = Path(self.runtime['control']).parent / 'tasks' / (name + '.json')
        require(read(path) == expected, 'slot task projection differs beyond registered effort')
        self.tasks, self.tasks_path = expected, path
        for module in (self.frame.prepare, self.frame.check, self.frame.check.base,
                       self.frame.assess, self.frame.cell_run.evidence, self.frame.usage.evidence):
            module.TASKS = self.tasks

    def validate(self, name):
        self.select_slot(name)
        return super().validate(name)

    def boot_expectation(self, arm, config):
        require(config == 'claude' and arm in ('B', 'X'), 'unregistered rp-d5 route')
        return None

    def record_binding(self, record):
        super().record_binding(record)
        require(record.get('effort') == effort_for(record['cell']), 'verdict effort binding mismatch')

    def prior_deleted(self, name):
        _, state = smoke_registration(self.base_runtime)
        require(state['status'] == ('QUALIFIED' if name in ARMS else 'STAGED'),
                'smoke attempt is consumed or unqualified')
        slots = [row[0] for row in self.smoke + SCHEDULE]
        index = slots.index(name)
        for slot in slots[max(0, index - 1):index]:
            is_smoke = slot in {row[0] for row in self.smoke}
            record = read(Path(self.runtime['smoke_output' if is_smoke else 'output']) / slot / 'rp-verdict.json')
            require(record['status'] not in ('STOP', 'UNKNOWN', 'NOT_RUN'), 'schedule already stopped')
            require(record.get('effort_binding') == 'MATCH', 'previous sealed effort mismatch; STOP')
            if name == 'c01':
                require(record.get('smoke_qualification', {}).get('status') == 'PASS' and
                        record['status'] in ('PASS', 'ADJUDICATE'), 'smoke not qualified')
            receipt = record['repository_cleanup']
            require(receipt.get('repository') == self.repository(slot) and receipt.get('status') == 'DELETED' and
                    receipt.get('http_status') == 404 and receipt.get('archive_manifest_sha256'),
                    'previous repository has no archived deletion/404 receipt')
            self.record_binding(record)
            require(record['account'] == self.base_runtime['claude_account'] and
                    record['codex_account'] == self.base_runtime['codex_account'], 'previous model account mismatch')
            if not is_smoke:
                require(record['frozen_runtime_sha256'] == self.frozen, 'frozen runtime changed between slots')

    def inherited_run(self, name, task, config):
        # rp-d1 checks an exact task contract before calling 0255. Project only
        # the registered effort in that check; all lower routes and the auditor
        # receive the same projected self.tasks, bound by its on-disk digest.
        source = ancestor.Runner.run
        task_file = PRIOR / ('smoke-tasks.json' if self.runtime['phase'] == 'smoke' else 'tasks.json')
        def projected_read(path):
            return slot_tasks(self.runtime['phase'], name) if Path(path) == task_file else read(path)
        adapted = FunctionType(source.__code__, source.__globals__ | {'read': projected_read},
                               source.__name__, source.__defaults__, source.__closure__)
        return adapted(self, name, task, 'B', config)

    def run(self, name, task, arm, config):
        require((name, task, config) in self.slots() and arm == arm_for(name), 'unregistered slot/task/engine/arm')
        self.active_arm = arm
        self.runtime = auth.for_engine(self.base_runtime, 'claude')
        self.frame.seal_after_teardown.keywords['runtime'] = self.runtime
        self.select_slot(name)
        try:
            result = self.inherited_run(name, task, config)
            out = Path(self.runtime['output']) / name
            path = out / 'rp-verdict.json'
            record = read(path)
            record.update(schema='rp-d5-verdict-v1', account=self.runtime['account'], arm=arm,
                effort=effort_for(name), prompt_sha256=prepare.PROMPT_SHA256[arm],
                release=prepare.release_identity(self.runtime, arm), codex_account=self.runtime['codex_account'],
                auth=self.runtime['auth'], auth_manifest_sha256=self.runtime['auth_manifest_sha256'],
                frozen_runtime_sha256=self.frozen, effort_binding='STOP')
            inherited = out.parent / ('verdict-' + name + '.json')
            if inherited.is_file():
                receipt = read(inherited)
                record.update({key: receipt[key] for key in ('owner_seconds', 'evidence_manifest_sha256') if key in receipt})
            if any((out / (engine + '-scan.json')).exists() for engine in ('codex', 'claude')):
                record.update(status='STOP', usage='UNKNOWN', input_tokens=None, output_tokens=None,
                    delivery_assessment='NOT_ASSESSED', revocation_required=True,
                    reason='Model credential scan hit or failed; slot stopped')
                result = 2
            if record['dispatched'] and not record.get('revocation_required'):
                try:
                    record['merge_refused'] = smoke.merge_refused(out)
                    if record['merge_refused'] and record['status'] not in ('STOP', 'UNKNOWN'):
                        record.update(status='PRODUCT_INCOMPLETE', delivery_assessment='PRODUCT_INCOMPLETE')
                    attribute = load('attribute_rpd5_runner', HERE / 'attribute.py')
                    analysis = attribute.analyze(out, manifest_sha256=record['evidence_manifest_sha256'],
                        expected_effort=effort_for(name), account=self.runtime['account'][0])
                    write(out / 'attribution.json', analysis)
                    record['effort_binding'] = analysis['effort_binding']
                    record['attribution_status'] = analysis['status']
                    if analysis['effort_binding'] != 'MATCH' or analysis['status'] != 'MATCH':
                        record.update(status='STOP', usage='UNKNOWN', input_tokens=None, output_tokens=None,
                                      reason='sealed effort or accounting qualification failed')
                        result = 2
                    if self.runtime['phase'] == 'smoke':
                        record['smoke_qualification'] = qualify(record, analysis)
                except (OSError, ValueError, KeyError, TypeError, RuntimeError):
                    record.update(status='STOP', reason='sealed evidence qualification failed')
                    result = 2
            write(path, record)
            if self.runtime['phase'] == 'smoke' and self.finish_smoke()['status'] in ('FAILED', 'STOP'):
                result = 2
            return result
        finally:
            self.active_arm = None
            self.runtime = self.base_runtime
            self.frame.seal_after_teardown.keywords['runtime'] = self.base_runtime

    def schedule(self, through_slot=None):
        require(through_slot is None or self.runtime['phase'] == 'measured' and
                type(through_slot) is int and 1 <= through_slot <= 4, 'through-slot requires measured slot 1..4')
        slots = self.slots()
        limit = through_slot if through_slot is not None else len(slots)
        records = self.completed_prefix()
        require(len(records) <= limit, 'requested slot precedes completed slots')
        stopped = any(row['status'] in ('STOP', 'UNKNOWN', 'NOT_RUN') for row in records)
        for name, task, config in slots[len(records):]:
            if not stopped and len(records) == limit:
                break
            if stopped:
                out = Path(self.runtime['output']) / name
                out.mkdir(parents=True, exist_ok=False)
                record = dict(cell=name, task=task, config=config, arm='X', effort=effort_for(name),
                    status='NOT_RUN', phase=self.runtime['phase'], measurement_eligible=self.runtime['phase'] == 'measured',
                    delivery_assessment='NOT_ASSESSED', dispatched=False, frozen_runtime_sha256=self.frozen,
                    prompt_sha256=prepare.PROMPT_SHA256['X'], release=prepare.release_identity(self.runtime, 'X'),
                    reason='earlier slot stopped the schedule')
                write(out / 'rp-verdict.json', record)
            else:
                stopped = self.run(name, task, 'X', config) != 0
                record = read(Path(self.runtime['output']) / name / 'rp-verdict.json')
            records.append(record)
        write(Path(self.runtime['output']) / 'rp-schedule.json', dict(
            status='STOP' if stopped else 'RECORDED' if len(records) == len(slots) else 'PAUSED',
            phase=self.runtime['phase'], slots=records, dispatched=sum(row['dispatched'] for row in records),
            releases={'X': prepare.release_identity(self.runtime, 'X')}))
        return 2 if stopped else 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('runtime', type=Path)
    parser.add_argument('phase', choices=('smoke', 'measured'))
    parser.add_argument('--through-slot', type=int)
    args = parser.parse_args()
    return Runner(args.runtime, phase=args.phase).schedule(args.through_slot)


if __name__ == '__main__':
    raise SystemExit(main())
