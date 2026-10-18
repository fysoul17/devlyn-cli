"""Registered rp-d6 schedule over rp-d4's sealed serial delivery lifecycle."""
import argparse
from copy import deepcopy
import importlib.util
from pathlib import Path
import re
from types import FunctionType

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('runner_rpd4_rpd6', HERE.parent / 'rp-d4-helper-report/runner.py')
legacy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(legacy)
load, PRIOR = legacy.load, legacy.PRIOR
prepare = load('prepare_rpd6_runner', HERE / 'prepare.py')
auth = load('auth_rpd6_runner', HERE / 'auth.py')
github, cell = prepare.github, legacy.cell
read, write, digest, require = legacy.read, legacy.write, legacy.digest, legacy.require
smoke, scan = legacy.smoke, legacy.scan
frozen_runtime, runtime_binding = legacy.frozen_runtime, legacy.runtime_binding
codex_account = auth.codex_account
SCHEDULE = [(f'm{i:02}', 'BV' if i <= 4 else 'Z0', 'claude') for i in range(1, 9)] + [
    ('g01', 'BV', 'codex'), ('g02', 'Z0', 'codex'), ('g03', 'BV', 'claude'),
    ('g04', 'BV', 'claude'), ('g05', 'Z0', 'claude'), ('g06', 'BV', 'claude')]
ARMS = dict(zip((row[0] for row in SCHEDULE), ('X', 'Y', 'Y', 'X', 'X', 'Y', 'Y', 'X', *('Y',) * 6)))


def smoke_slots(attempt=1):
    require(type(attempt) is int and attempt in (1, 2), 'smoke_attempt must be 1 or 2')
    prefix = 'smoke' if attempt == 1 else 'smoke2'
    return [(prefix + '-' + engine, 'SM', engine) for engine in ('claude', 'codex')]


def arm_for(name):
    if name in ARMS:
        return ARMS[name]
    require(name in {row[0] for attempt in (1, 2) for row in smoke_slots(attempt)}, 'unregistered rp-d6 slot')
    return 'Y'


def effort_for(name):
    arm_for(name)
    return 'max' if name == 'g03' else 'high'


def slot_tasks(phase, name):
    require(phase in ('smoke', 'measured') and name in {row[0] for row in
            (SCHEDULE if phase == 'measured' else smoke_slots(1) + smoke_slots(2))}, 'unregistered phase/slot')
    tasks = deepcopy(read(PRIOR / ('smoke-tasks.json' if phase == 'smoke' else 'tasks.json')))
    require(tasks['routes']['claude']['owner'] == dict(engine='claude', model='claude-opus-5-5', effort='max'),
            'frozen Claude route changed')
    require(tasks['routes']['codex']['owner'] == dict(engine='codex', model='gpt-6-sol', effort='high',
                                                     child_model='gpt-6-sol', child_effort='high'),
            'frozen Codex route changed')
    tasks['routes']['claude']['owner']['effort'] = effort_for(name)
    return tasks


def smoke_registry(run_id):
    require(isinstance(run_id, str) and re.fullmatch('[A-Za-z0-9][A-Za-z0-9-]*', run_id), 'invalid run_id')
    return Path.home() / '.devlyn/rp-d6-runs' / run_id


base_smoke_inputs = legacy.smoke_inputs


def smoke_inputs(runtime):
    return dict(base_smoke_inputs(runtime), token_gate_sha256=runtime['token_gate_sha256'])


smoke_registration = legacy.smoke_registration
legacy.smoke_inputs = smoke_inputs
legacy.prepare, legacy.auth, legacy.github = prepare, auth, github
legacy.SCHEDULE, legacy.ARMS, legacy.arm_for = SCHEDULE, ARMS, arm_for
legacy.smoke_slots, legacy.smoke_registry = smoke_slots, smoke_registry
legacy.legacy.SCHEDULE, legacy.legacy.ARMS, legacy.legacy.arm_for = SCHEDULE, ARMS, arm_for
ancestor = legacy.legacy.legacy  # rp-d1 through rp-d4 -> rp-d2
ancestor.SCHEDULE, ancestor.smoke_slots = SCHEDULE, smoke_slots
ancestor.prepare, ancestor.github = prepare.legacy.legacy.legacy, github


def qualify(record):
    """Smoke establishes instrumentation; delivery is an unqualified observation."""
    cleanup = record.get('repository_cleanup', {})
    checks = dict(owner=record.get('dispatched') is True and record.get('owner_status') == 'EXITED_0',
        binding=record.get('release_binding') == 'MATCH',
        effort=record.get('config') != 'claude' or record.get('effort_binding') == 'MATCH',
        usage=record.get('usage') == 'COMPLETE',
        archive=bool(cleanup.get('archive_manifest_sha256')),
        deleted=cleanup.get('status') == 'DELETED' and cleanup.get('http_status') == 404,
        lifecycle=record.get('status') not in ('STOP', 'UNKNOWN', 'NOT_RUN') and not record.get('revocation_required'))
    return dict(status='PASS' if all(checks.values()) else 'FAIL', checks=checks,
                delivered=record.get('delivery_assessment') == 'PASS')


class Runner(legacy.Runner):
    def __init__(self, runtime_path, tasks_path=None, *, phase=None):
        super().__init__(runtime_path, tasks_path, phase=phase)
        self.active_name = None
        self.grading = load('grading_rpd6_runner', HERE / 'grading.py')
        self.local_only = load('local_only_rpd6_runner', HERE / 'local_only.py')
        github.done_check = self.grading.done_check
        # Normalize before inherited scope checks and the checked.json census,
        # not just after an inherited PRODUCT_INCOMPLETE has already been set.
        seen = set()
        for module in (self.packet, self.frame.prepare.packet, self.frame.check.packet,
                       self.frame.check.base.packet, self.frame.assess.packet):
            if id(module) in seen:
                continue
            seen.add(id(module))
            original = module.tree
            module.tree = lambda root, original=original: self.grading.normalize_tree(original(root))
        inherited_harness = self.frame.harness_unchanged
        self.frame.harness_unchanged = lambda out, baseline: (
            self.local_only.harness_unchanged(out, baseline) if out.name == 'g06'
            else inherited_harness(out, baseline))

    def repository(self, name):
        arm_for(name)
        if name == 'g06':
            return None
        repository = f'fysoul17/rpd6-{self.runtime["run_id"]}-{name}'
        github.url(repository)
        return repository

    def remaining(self, name):
        slots = [row[0] for row in self.smoke + SCHEDULE]
        return [self.repository(slot) for slot in slots[slots.index(name):] if slot != 'g06']

    def inputs(self):
        result = super().inputs()
        result.update({str(path): digest(path) for path in [*HERE.glob('*.py'), HERE / 'DESIGN.md', HERE / 'README.md',
            HERE.parent / 'rp-d5-claude-stages/attribute.py']})
        return result

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
        require(Path(self.runtime['models_cache']).resolve() ==
                Path(self.runtime['control']).parent.resolve() / 'models_cache.json',
                'models cache must be the frozen stage copy')
        require(Path(self.runtime['token_gate']).resolve() ==
                Path(self.runtime['control']).parent.resolve() / 'token-gate.json' and
                digest(self.runtime['token_gate']) == self.runtime['token_gate_sha256'],
                'rendered token gate differs from registration')
        return super().validate(name)

    def native_prompt(self, caller):
        return prepare.native_prompt(caller, self.active_arm, self.active_name)

    def materialize(self, runtime, name, task, arm, config):
        require(arm == 'B' and self.active_arm == arm_for(name), 'attempt arm/installed route mismatch')
        return prepare.prepare(runtime, name, task, self.active_arm, config, inherited=self.frame.prepare,
            tasks=self.tasks, tasks_path=self.tasks_path, repository=self.repository(name), remaining=self.remaining(name))

    def record_binding(self, record):
        arm = arm_for(record['cell'])
        require(record['arm'] == arm and record['prompt_sha256'] == prepare.prompt_sha256(record['cell']) and
                record['release'] == prepare.release_identity(self.runtime, arm) and
                record['effort'] == effort_for(record['cell']), 'verdict prompt/release/effort binding mismatch')

    def prior_deleted(self, name):
        _, state = smoke_registration(self.base_runtime)
        require(state['status'] == ('QUALIFIED' if name in ARMS else 'STAGED'), 'smoke attempt consumed or unqualified')
        slots = [row[0] for row in self.smoke + SCHEDULE]
        index = slots.index(name)
        for slot in (slots[:2] if name == 'm01' else slots[max(0, index - 1):index]):
            is_smoke = slot in {row[0] for row in self.smoke}
            record = read(Path(self.runtime['smoke_output' if is_smoke else 'output']) / slot / 'rp-verdict.json')
            require(record['status'] not in ('STOP', 'UNKNOWN', 'NOT_RUN'), 'schedule already stopped')
            if name == 'm01':
                require(record.get('smoke_qualification', {}).get('status') == 'PASS', 'smoke not qualified')
            if record['config'] == 'claude':
                require(record.get('effort_binding') == 'MATCH', 'previous sealed effort mismatch; STOP')
            receipt = record['repository_cleanup']
            require(receipt.get('repository') == self.repository(slot) and receipt.get('status') == 'DELETED' and
                    receipt.get('http_status') == 404 and receipt.get('archive_manifest_sha256'),
                    'previous repository has no archived deletion/404 receipt')
            self.record_binding(record)
            require(record['codex_account'] == self.base_runtime['codex_account'] and
                    record['account'] == auth.for_engine(self.base_runtime, record['config'])['account'],
                    'previous model account mismatch')
            if not is_smoke:
                require(record['frozen_runtime_sha256'] == self.frozen, 'frozen runtime changed between slots')
            if name.startswith('m') and int(name[1:]) % 2 == 0:
                selected = auth.for_engine(self.base_runtime, 'claude')
                require(record['auth_manifest_sha256'] == selected['auth_manifest_sha256'] and
                        record['auth'] == selected['auth'], 'model auth renewal refused within a pair')

    def inherited_run(self, name, task, config):
        if name == 'g06':
            return self.local_only.run(self, name, task, config,
                lambda *args: ancestor.legacy.Runner.run(self, *args), scan)
        source = ancestor.Runner.run
        task_file = PRIOR / ('smoke-tasks.json' if self.runtime['phase'] == 'smoke' else 'tasks.json')
        def projected_read(path):
            return slot_tasks(self.runtime['phase'], name) if Path(path) == task_file else read(path)
        adapted = FunctionType(source.__code__, source.__globals__ | {'read': projected_read},
                               source.__name__, source.__defaults__, source.__closure__)
        return adapted(self, name, task, 'B', config)

    def run(self, name, task, arm, config):
        require((name, task, config) in self.slots() and arm == arm_for(name), 'unregistered slot/task/engine/arm')
        _, state = smoke_registration(self.base_runtime)
        require(state['status'] == ('QUALIFIED' if name in ARMS else 'STAGED'), 'smoke attempt consumed or unqualified')
        self.active_arm, self.active_name = arm, name
        self.runtime = auth.for_engine(self.base_runtime, config)
        self.frame.seal_after_teardown.keywords['runtime'] = self.runtime
        self.select_slot(name)
        try:
            result = self.inherited_run(name, task, config)
            out = Path(self.runtime['output']) / name
            path = out / 'rp-verdict.json'
            record = read(path)
            record.update(schema='rp-d6-verdict-v1', account=self.runtime['account'], arm=arm, effort=effort_for(name),
                prompt_sha256=prepare.prompt_sha256(name), release=prepare.release_identity(self.runtime, arm),
                codex_account=self.runtime['codex_account'], auth=self.runtime['auth'],
                auth_manifest_sha256=self.runtime['auth_manifest_sha256'], frozen_runtime_sha256=self.frozen,
                effort_binding='UNKNOWN' if config == 'claude' else 'NOT_APPLICABLE', release_binding='UNKNOWN')
            inherited = out.parent / ('verdict-' + name + '.json')
            if inherited.is_file():
                receipt = read(inherited)
                record.update({key: receipt[key] for key in ('owner_seconds', 'owner_status', 'evidence_manifest_sha256')
                               if key in receipt})
            if any((out / (engine + '-scan.json')).exists() for engine in ('pat', 'codex', 'claude')):
                record.update(status='STOP', usage='UNKNOWN', input_tokens=None, output_tokens=None,
                    delivery_assessment='NOT_ASSESSED', revocation_required=True,
                    reason='Credential scan hit or failed; slot stopped')
                result = 2
            if record['dispatched'] and not record.get('revocation_required'):
                try:
                    # These were checked immediately before launch; post-run checks
                    # bind sealed plan/baseline identities without requiring owner-
                    # writable installed files to remain unchanged after execution.
                    plan, baseline = (read(out / f) for f in ('plan.json', 'baseline.json'))
                    require(all(r['arm'] == arm and r['release'] == record['release'] and
                                r['prompt_body_sha256'] == record['prompt_sha256'] for r in (plan, baseline)),
                            'sealed release/prompt binding mismatch')
                    record['release_binding'] = 'MATCH'
                    record['merge_refused'] = smoke.merge_refused(out)
                    if config == 'claude':
                        attribute = load('attribute_rpd5_rpd6', HERE.parent / 'rp-d5-claude-stages/attribute.py')
                        record['effort_binding'] = attribute.effort_binding(out, record['evidence_manifest_sha256'], effort_for(name))
                        if record['effort_binding'] != 'MATCH':
                            record.update(status='STOP', reason='sealed Claude request effort differs from slot')
                            result = 2
                    record['grading'] = self.grading.assess(out, record, archive_root=out.parent / 'archives' / name)
                    write(out / 'grading.json', record['grading'])
                    record['grading_sha256'] = digest(out / 'grading.json')
                except (OSError, ValueError, KeyError, TypeError, RuntimeError):
                    record.update(status='STOP', reason='sealed evidence qualification failed')
                    result = 2
            if self.runtime['phase'] == 'smoke':
                record['smoke_qualification'] = qualify(record)
            write(path, record)
            if self.runtime['phase'] == 'smoke' and self.finish_smoke()['status'] in ('FAILED', 'STOP'):
                result = 2
            return result
        finally:
            self.active_arm = self.active_name = None
            self.runtime = self.base_runtime
            self.frame.seal_after_teardown.keywords['runtime'] = self.base_runtime

    def finish_smoke(self):
        path, state = smoke_registration(self.base_runtime)
        if state['status'] != 'STAGED':
            return state
        records = self.completed_prefix()
        failed = any(row.get('smoke_qualification', {}).get('status') != 'PASS' for row in records)
        if not failed and len(records) != len(self.smoke):
            return state
        terminal = any(row.get('revocation_required') for row in records)
        state['status'] = ('STOP' if terminal or self.runtime['smoke_attempt'] == 2 else 'FAILED') if failed else 'QUALIFIED'
        state['verdicts'] = {str(Path(self.runtime['smoke_output']) / row['cell'] / 'rp-verdict.json'):
                            digest(Path(self.runtime['smoke_output']) / row['cell'] / 'rp-verdict.json') for row in records}
        write(path, state)
        return state

    def schedule(self, through_pair=None):
        require(through_pair is None or self.runtime['phase'] == 'measured' and
                type(through_pair) is int and 1 <= through_pair <= 4, 'through-pair requires measured pair 1..4')
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
                record = dict(cell=name, task=task, config=config, arm=arm, effort=effort_for(name),
                    status='NOT_RUN', phase=self.runtime['phase'], measurement_eligible=self.runtime['phase'] == 'measured',
                    delivery_assessment='NOT_ASSESSED', dispatched=False, frozen_runtime_sha256=self.frozen,
                    prompt_sha256=prepare.prompt_sha256(name), release=prepare.release_identity(self.runtime, arm),
                    reason='earlier slot stopped the schedule')
                write(out / 'rp-verdict.json', record)
            else:
                stopped = self.run(name, task, arm, config) != 0
                record = read(Path(self.runtime['output']) / name / 'rp-verdict.json')
            records.append(record)
        write(Path(self.runtime['output']) / 'rp-schedule.json', dict(
            status='STOP' if stopped else 'RECORDED' if len(records) == len(slots) else 'PAUSED',
            phase=self.runtime['phase'], slots=records, dispatched=sum(row['dispatched'] for row in records),
            releases={arm: prepare.release_identity(self.runtime, arm) for arm in ('X', 'Y')}))
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
