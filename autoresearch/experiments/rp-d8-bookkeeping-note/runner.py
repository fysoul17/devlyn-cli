"""rp-d8 schedule over rp-d6's sealed, serial native lifecycle."""
import argparse
import importlib.util
import os
from pathlib import Path
import re
from types import FunctionType, ModuleType

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('runner_rpd6_rpd8', HERE.parent / 'rp-d6-claude-delivery/runner.py')
legacy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(legacy)
base_load, PRIOR = legacy.load, legacy.PRIOR
prepare = base_load('prepare_rpd8_runner', HERE / 'prepare.py')
github = prepare.github


def share_evidence_error(module):
    """Unify trusted exception identity without replacing private GitHub hooks."""
    pending, seen = [module], set()
    while pending:
        current = pending.pop()
        path = Path(getattr(current, '__file__', ''))
        if (id(current) in seen or path.parent.parent != HERE.parent or
                not path.parent.name.startswith('rp-d') or path.name.startswith('test_')):
            continue
        seen.add(id(current))
        namespace = vars(current)
        if path == PRIOR / 'github.py':
            namespace['EvidenceError'] = github.EvidenceError
        for value in tuple(namespace.values()):
            if isinstance(value, ModuleType):
                pending.append(value)
            elif isinstance(value, FunctionType) and value.__globals__.get('__file__') == github.__file__:
                # Aliased require() can outlive its original module reference.
                value.__globals__['EvidenceError'] = github.EvidenceError
        if 'load' in namespace:
            namespace['load'] = load
    return module


def load(name, path):
    return share_evidence_error(base_load(name, path))


share_evidence_error(legacy)
share_evidence_error(prepare)
registered = load('schedule_rpd8_runner', HERE / 'schedule.py')
SCHEDULE, ARMS = registered.SCHEDULE, registered.ARMS
smoke_slots, arm_for, effort_for = registered.smoke_slots, registered.arm_for, registered.effort_for
auth, cell, github = legacy.auth, legacy.cell, prepare.github
read, write, digest, require = legacy.read, legacy.write, legacy.digest, legacy.require
smoke, scan = legacy.smoke, legacy.scan
frozen_runtime, runtime_binding = legacy.frozen_runtime, legacy.runtime_binding
codex_account = auth.codex_account
prior = load('runner_rpd7_rpd8', HERE.parent / 'rp-d7-prompt-delivery/runner.py')
credential = FunctionType(prior.credential.__code__, prior.credential.__globals__ | {'cell': cell})
cell.credential = credential


def smoke_registry(run_id):
    require(isinstance(run_id, str) and re.fullmatch('[A-Za-z0-9][A-Za-z0-9-]*', run_id), 'invalid run_id')
    return Path.home() / '.devlyn/rp-d8-runs' / run_id


def smoke_inputs(runtime):
    return dict(legacy.base_smoke_inputs(runtime), token_gate_sha256=runtime['token_gate_sha256'],
                prompt_body_sha256=prepare.P1_SHA256)


base_qualify = legacy.qualify


def qualify(record):
    result = base_qualify(record)
    result['checks']['prompt'] = (record.get('prompt_binding') == 'MATCH' and
                                  record.get('prompt_sha256') == prepare.P1_SHA256)
    result['status'] = 'PASS' if all(result['checks'].values()) else 'FAIL'
    return result


for module in (legacy, legacy.legacy, legacy.legacy.legacy):
    module.SCHEDULE, module.ARMS, module.arm_for = SCHEDULE, ARMS, arm_for
    module.smoke_slots, module.smoke_registry = smoke_slots, smoke_registry
legacy.prepare = legacy.legacy.prepare = prepare
legacy.github = legacy.legacy.github = github
legacy.effort_for, legacy.qualify = effort_for, qualify
legacy.legacy.smoke_inputs = smoke_inputs
legacy.ancestor.SCHEDULE, legacy.ancestor.smoke_slots = SCHEDULE, smoke_slots
legacy.ancestor.prepare, legacy.ancestor.github = prepare.legacy.legacy.legacy.legacy, github
slot_tasks, smoke_registration = legacy.slot_tasks, legacy.smoke_registration


def route_watch(pid_file=None, log_file=None):
    """Observe the operator's watcher; missing evidence is explicitly unknown."""
    result = dict(alive=None, last_line=None, pid=None, pid_file=None, log_file=None)
    if pid_file is None:
        result['reason'] = 'route watcher not configured'
        return result
    pid_file = Path(pid_file)
    log_file = Path(log_file) if log_file else pid_file.with_suffix('.log')
    result.update(pid_file=str(pid_file), log_file=str(log_file))
    errors = []
    try:
        raw = pid_file.read_text().strip()
        if re.fullmatch('[1-9][0-9]*', raw) is None:
            raise ValueError('invalid route watcher PID')
        result['pid'] = int(raw)
        try:
            os.kill(result['pid'], 0)
            result['alive'] = True
        except ProcessLookupError:
            result['alive'] = False
        except PermissionError:
            result['alive'] = True
    except (OSError, ValueError, OverflowError) as exc:
        errors.append('PID observation unavailable: ' + type(exc).__name__)
    try:
        with log_file.open('rb') as stream:
            stream.seek(0, os.SEEK_END)
            end = stream.tell()
            # Read backwards until the complete last line is available.
            tail = b''
            while end and tail.rstrip(b'\r\n').count(b'\n') < 1:
                size = min(end, 4096)
                end -= size
                stream.seek(end)
                tail = stream.read(size) + tail
            lines = tail.decode('utf-8').splitlines()
            line = lines[-1] if lines else ''
            if re.fullmatch(r'\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ default-route interface: [A-Za-z0-9]+', line):
                result['last_line'] = line
            else:
                errors.append('log tail not in watcher format')
    except (OSError, UnicodeError) as exc:
        errors.append('log observation unavailable: ' + type(exc).__name__)
    if errors:
        result['reason'] = '; '.join(errors)
    return result


class Runner(legacy.Runner):
    def __init__(self, runtime_path, tasks_path=None, *, phase=None, route_watch_pid_file=None, route_watch_log=None):
        super().__init__(runtime_path, tasks_path, phase=phase)
        self.route_watch_pid_file, self.route_watch_log = route_watch_pid_file, route_watch_log
        self.route_observation = None
        self.grading = load('grading_rpd8_runner', HERE / 'grading.py')
        self.local_only = load('local_only_rpd8_runner', HERE / 'local_only.py')
        self.capture = load('capture_rpd8_runner', HERE / 'capture.py')
        self.capture.install(self, github)
        github.done_check = self.grading.done_check
        assess = self.grading.assess

        def bound_assess(out, record, **kwargs):
            prepare.prompt_binding(out, record['release'])
            record.update(prompt_binding='MATCH', full_prompt_sha256=digest(out / 'prompt.txt'),
                          route_watch=self.route_observation)
            return assess(out, record, **kwargs)

        self.grading.assess = bound_assess

    def inputs(self):
        return super().inputs() | {str(path): digest(path) for path in
            [*HERE.glob('*.py'), HERE / 'DESIGN.md', HERE / 'README.md',
             *prior.HERE.glob('*.py'), prior.HERE / 'DESIGN.md', prior.HERE / 'README.md']}

    def repository(self, name):
        arm_for(name)
        if name == 'g06':
            return None
        repository = f'fysoul17/rpd8-{self.runtime["run_id"]}-{name}'
        github.url(repository)
        return repository

    def remaining(self, name):
        # The no-origin materializer accepts no remote provisioning targets,
        # even though this schedule now has two guards after the local cell.
        return [] if name == 'g06' else super().remaining(name)

    def materialize(self, *args, **kwargs):
        out = super().materialize(*args, **kwargs)
        self.capture.baseline(out)
        return out

    def validate(self, name):
        gate = load('gate_rpd8_runner', HERE / 'rendered_gate.py')
        gate.validate(read(self.runtime['token_gate']), self.runtime['arms_file'])
        return super().validate(name)

    def record_binding(self, record):
        super().record_binding(record)
        if record['status'] not in ('STOP', 'UNKNOWN', 'NOT_RUN'):
            require(record.get('prompt_binding') == 'MATCH', 'previous P1 prompt binding mismatch')

    def prior_deleted(self, name):
        # rp-d6's remote cleanup check cannot apply to g06, whose successor is
        # new in this study. Everything else retains its serial custody checks.
        if name != 'g07':
            return super().prior_deleted(name)
        _, state = smoke_registration(self.base_runtime)
        require(state['status'] == 'QUALIFIED', 'smoke is unqualified')
        record = read(Path(self.runtime['output']) / 'g06/rp-verdict.json')
        require(record['status'] not in ('STOP', 'UNKNOWN', 'NOT_RUN'), 'schedule already stopped')
        require(record.get('effort_binding') == 'MATCH', 'previous sealed effort mismatch; STOP')
        receipt = record['repository_cleanup']
        require(receipt.get('repository') is None and receipt.get('status') == 'NOT_APPLICABLE' and
                receipt.get('archive_manifest_sha256'), 'g06 has no sealed local archive receipt')
        require(digest(Path(self.runtime['output']) / 'archives/g06/manifest.json') ==
                receipt['archive_manifest_sha256'], 'g06 local archive manifest changed')
        self.record_binding(record)
        require(record['codex_account'] == self.base_runtime['codex_account'] and
                record['account'] == self.base_runtime['claude_account'], 'previous model account mismatch')
        require(record['frozen_runtime_sha256'] == self.frozen, 'frozen runtime changed between slots')

    def run(self, name, task, arm, config):
        self.route_observation = route_watch(self.route_watch_pid_file, self.route_watch_log)
        result = super().run(name, task, arm, config)
        if self.runtime['phase'] != 'smoke':
            self.stamp_record(name)
        return result

    def stamp_record(self, name):
        path = Path(self.runtime['output']) / name / 'rp-verdict.json'
        record = read(path)
        record.update(schema='rp-d8-verdict-v1', route_watch=self.route_observation)
        prompt = path.parent / 'prompt.txt'
        if record.get('dispatched') and prompt.is_file():
            record.setdefault('full_prompt_sha256', digest(prompt))
        write(path, record)

    def finish_smoke(self):
        # Stamp before the inherited registration freezes verdict digests.
        if self.active_name is not None:
            self.stamp_record(self.active_name)
        return super().finish_smoke()

    def schedule(self, through_pair=None, through_guard=None):
        require(through_pair is None or self.runtime['phase'] == 'measured' and
                type(through_pair) is int and 1 <= through_pair <= 8, 'through-pair requires measured pair 1..8')
        require(through_guard is None or self.runtime['phase'] == 'measured' and
                type(through_guard) is int and 1 <= through_guard <= 8, 'through-guard requires guard 1..8')
        require(through_pair is None or through_guard is None, 'choose a pair or guard boundary')
        slots = self.slots()
        limit = 2 * through_pair if through_pair else 16 + through_guard if through_guard else len(slots)
        records = self.completed_prefix()
        require(len(records) <= limit, 'requested boundary precedes completed slots')
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
                    route_watch=dict(alive=None, last_line=None, reason='slot not dispatched after STOP'),
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
    boundary = parser.add_mutually_exclusive_group()
    boundary.add_argument('--through-pair', type=int)
    boundary.add_argument('--through-guard', type=int)
    parser.add_argument('--route-watch-pid-file', type=Path)
    parser.add_argument('--route-watch-log', type=Path)
    args = parser.parse_args()
    if args.route_watch_log and not args.route_watch_pid_file:
        parser.error('--route-watch-log requires --route-watch-pid-file')
    return Runner(args.runtime, phase=args.phase, route_watch_pid_file=args.route_watch_pid_file,
                  route_watch_log=args.route_watch_log).schedule(args.through_pair, args.through_guard)


if __name__ == '__main__':
    raise SystemExit(main())
