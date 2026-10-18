"""Claude high P1 slots over the unchanged rp-d6 sealed serial lifecycle."""
import argparse
import importlib.util
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('runner_rpd6_rpd7', HERE.parent / 'rp-d6-claude-delivery/runner.py')
legacy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(legacy)
load, PRIOR = legacy.load, legacy.PRIOR
prepare = load('prepare_rpd7_runner', HERE / 'prepare.py')
auth, cell = legacy.auth, legacy.cell
github = prepare.github
read, write, digest, require = legacy.read, legacy.write, legacy.digest, legacy.require
smoke, scan = legacy.smoke, legacy.scan
SCHEDULE = [(f'm{i:02}', 'BV' if i % 2 else 'Z0', 'claude') for i in range(1, 5)]
ARMS = {name: 'X' for name, _, _ in SCHEDULE}


def smoke_slots(attempt=1):
    require(type(attempt) is int and attempt in (1, 2), 'smoke_attempt must be 1 or 2')
    return [('smoke-claude' if attempt == 1 else 'smoke2-claude', 'SM', 'claude')]


def arm_for(name):
    prepare.registered(name)
    return 'X'


def effort_for(name):
    arm_for(name)
    return 'high'


slot_tasks = legacy.slot_tasks


def smoke_registry(run_id):
    require(isinstance(run_id, str) and re.fullmatch('[A-Za-z0-9][A-Za-z0-9-]*', run_id), 'invalid run_id')
    return Path.home() / '.devlyn/rp-d7-runs' / run_id


def smoke_inputs(runtime):
    return dict(legacy.base_smoke_inputs(runtime), prompt_body_sha256=prepare.P1_SHA256)


base_qualify = legacy.qualify


def qualify(record):
    result = base_qualify(record)
    result['checks']['prompt'] = (record.get('prompt_binding') == 'MATCH' and
                                  record.get('prompt_sha256') == prepare.P1_SHA256)
    result['status'] = 'PASS' if all(result['checks'].values()) else 'FAIL'
    return result


# These instances are private; rp-d6 and its other importers remain unchanged.
for module in (legacy, legacy.legacy, legacy.legacy.legacy):
    module.SCHEDULE, module.ARMS, module.arm_for = SCHEDULE, ARMS, arm_for
    module.smoke_slots, module.smoke_registry = smoke_slots, smoke_registry
legacy.prepare = legacy.legacy.prepare = prepare
legacy.github = legacy.legacy.github = github
legacy.effort_for, legacy.qualify = effort_for, qualify
legacy.legacy.smoke_inputs = smoke_inputs
legacy.ancestor.SCHEDULE, legacy.ancestor.smoke_slots = SCHEDULE, smoke_slots
legacy.ancestor.prepare, legacy.ancestor.github = prepare.legacy.legacy.legacy.legacy, github
smoke_registration = legacy.smoke_registration


class Runner(legacy.Runner):
    def __init__(self, runtime_path, tasks_path=None, *, phase=None):
        super().__init__(runtime_path, tasks_path, phase=phase)
        self.grading = load('grading_rpd7_runner', HERE / 'grading.py')
        github.done_check = self.grading.done_check
        assess = self.grading.assess

        def bound_assess(out, record, **kwargs):
            prepare.prompt_binding(out, record['release'])
            record['prompt_binding'] = 'MATCH'
            return assess(out, record, **kwargs)

        self.grading.assess = bound_assess

    def inputs(self):
        return super().inputs() | {str(path): digest(path) for path in
            [*HERE.glob('*.py'), HERE / 'DESIGN.md', HERE / 'README.md']}

    def repository(self, name):
        arm_for(name)
        repository = f'fysoul17/rpd7-{self.runtime["run_id"]}-{name}'
        github.url(repository)
        return repository

    def validate(self, name):
        self.select_slot(name)
        require(Path(self.runtime['models_cache']).resolve() ==
                Path(self.runtime['control']).parent.resolve() / 'models_cache.json',
                'models cache must be the frozen stage copy')
        return legacy.legacy.Runner.validate(self, name)

    def record_binding(self, record):
        super().record_binding(record)
        require(record['config'] == 'claude', 'only Claude slots are registered')
        if record['status'] not in ('STOP', 'UNKNOWN', 'NOT_RUN'):
            require(record.get('prompt_binding') == 'MATCH', 'previous P1 prompt binding mismatch')

    def prior_deleted(self, name):
        arm_for(name)
        _, state = smoke_registration(self.base_runtime)
        require(state['status'] == ('QUALIFIED' if name in ARMS else 'STAGED'), 'smoke attempt consumed or unqualified')
        slots = [row[0] for row in self.smoke + SCHEDULE]
        index = slots.index(name)
        for slot in slots[max(0, index - 1):index]:
            is_smoke = slot in {row[0] for row in self.smoke}
            record = read(Path(self.runtime['smoke_output' if is_smoke else 'output']) / slot / 'rp-verdict.json')
            require(record['status'] not in ('STOP', 'UNKNOWN', 'NOT_RUN'), 'schedule already stopped')
            if name == 'm01':
                require(record.get('smoke_qualification', {}).get('status') == 'PASS', 'smoke not qualified')
            require(record.get('effort_binding') == 'MATCH', 'previous sealed effort mismatch; STOP')
            receipt = record['repository_cleanup']
            require(receipt.get('repository') == self.repository(slot) and receipt.get('status') == 'DELETED' and
                    receipt.get('http_status') == 404 and receipt.get('archive_manifest_sha256'),
                    'previous repository has no archived deletion/404 receipt')
            self.record_binding(record)
            require(record['codex_account'] == self.base_runtime['codex_account'] and
                    record['account'] == self.base_runtime['claude_account'], 'previous model account mismatch')
            if not is_smoke:
                require(record['frozen_runtime_sha256'] == self.frozen, 'frozen runtime changed between slots')

    def schedule(self, through_slot=None):
        require(through_slot is None or self.runtime['phase'] == 'measured' and
                type(through_slot) is int and 1 <= through_slot <= 4, 'through-slot requires measured slot 1..4')
        slots = self.slots()
        limit = through_slot if through_slot is not None else len(slots)
        records = self.completed_prefix()
        require(len(records) <= limit, 'requested boundary precedes completed slots')
        stopped = any(row['status'] in ('STOP', 'UNKNOWN', 'NOT_RUN') for row in records)
        for name, task, config in slots[len(records):]:
            if not stopped and len(records) == limit:
                break
            if stopped:
                out = Path(self.runtime['output']) / name
                out.mkdir(parents=True, exist_ok=False)
                record = dict(cell=name, task=task, config=config, arm='X', effort='high', status='NOT_RUN',
                    phase=self.runtime['phase'], measurement_eligible=self.runtime['phase'] == 'measured',
                    delivery_assessment='NOT_ASSESSED', dispatched=False, frozen_runtime_sha256=self.frozen,
                    prompt_sha256=prepare.prompt_sha256(name), release=prepare.release_identity(self.runtime, 'X'),
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
