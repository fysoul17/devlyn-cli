"""Codex prompt ablation over the frozen serial rp-d2/rp-d1 lifecycle."""
import argparse
import importlib.util
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('prepare_rpd3_runner', HERE / 'prepare.py')
prepare = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prepare)
load, PRIOR, github = prepare.load, prepare.PRIOR, prepare.github
legacy = load('runner_rpd2_rpd3', HERE.parent / 'rp-d2-report-lines/runner.py')
auth = load('auth_rpd3_runner', HERE / 'auth.py')
read, write, digest, require = legacy.read, legacy.write, legacy.digest, github.require
cell = legacy.cell
frozen_runtime, runtime_binding, codex_account = legacy.frozen_runtime, legacy.runtime_binding, legacy.codex_account
SCHEDULE = [(f'm{i:02}', 'BV' if i <= 4 else 'Z0', 'codex') for i in range(1, 9)]
ARMS = dict(zip((row[0] for row in SCHEDULE), ('P0', 'P1', 'P1', 'P0', 'P0', 'P1', 'P1', 'P0')))


def smoke_slots(attempt=1):
    require(type(attempt) is int and attempt in (1, 2), 'smoke_attempt must be 1 or 2')
    prefix = 'smoke' if attempt == 1 else 'smoke2'
    return [(f'{prefix}-codex-{arm}', 'SM', 'codex') for arm in ('P0', 'P1')]


def arm_for(name):
    if name in ARMS:
        return ARMS[name]
    require(name in {row[0] for attempt in (1, 2) for row in smoke_slots(attempt)}, 'unregistered rp-d3 slot')
    return name[-2:]


def solo_route(tasks, config, arm):
    require(config == 'codex' and arm in prepare.PROMPT_SHA256, 'unregistered rp-d3 route')
    return legacy.legacy.solo_route(tasks, config, arm)


legacy.SCHEDULE, legacy.ARMS, legacy.arm_for = SCHEDULE, ARMS, arm_for
legacy.legacy.SCHEDULE, legacy.legacy.smoke_slots = SCHEDULE, smoke_slots
legacy.legacy.prepare = prepare.legacy.legacy
legacy.legacy.github = github
legacy.legacy.legacy.policy.check.__globals__['base_policy'].route_for = solo_route


class Runner(legacy.Runner):
    def __init__(self, runtime_path, tasks_path=None, *, phase=None):
        original = read(runtime_path)
        require(phase is None or phase == original['phase'], 'phase differs from staged runtime')
        # Skip only rp-d2's two-release constructor; keep every lower lifecycle hook.
        legacy.legacy.Runner.__init__(self, runtime_path, tasks_path, phase=phase)
        self.frozen = runtime_binding(original)
        if 'renewed_from' in original:
            previous = original['renewed_from']
            require(digest(previous['path']) == previous['sha256'], 'previous runtime binding changed')
            require(frozen_runtime(read(previous['path'])) == frozen_runtime(original), 'renewal changed frozen inputs/account')
        self.runtime['release'] = self.runtime['releases']['B']
        self.active_arm = None
        launch = self.frame.cell_run.run
        launch.keywords['check_auth'] = auth.preflight

        def bound_launch(out, runtime):
            self.check_auth(runtime)
            prepare.verify_release(runtime)
            prepare.binding(out, runtime, arm_for(out.name))
            return launch(out, runtime)

        self.frame.cell_run.run = bound_launch

    @staticmethod
    def check_auth(runtime):
        venue, blocked = auth.preflight(runtime)
        require(blocked is None, blocked or 'Codex authentication refused')
        return venue

    def preflight(self):
        return auth.preflight(self.runtime)

    def inputs(self):
        result = legacy.legacy.Runner.inputs(self)
        paths = [*HERE.glob('*.py'), HERE / 'DESIGN.md', HERE / 'README.md',
                 *legacy.HERE.glob('*.py'), legacy.HERE / 'README.md', legacy.HERE / 'DESIGN.md',
                 PRIOR / 'registration.json', Path(self.runtime['arms_file'])]
        result.update({str(path): digest(path) for path in paths})
        return result

    def validate(self, name):
        arm_for(name)
        require(runtime_binding(read(self.runtime_path)) == self.frozen, 'staged runtime changed')
        self.check_auth(self.runtime)
        require(digest(self.runtime['models_cache']) == self.runtime['models_cache_sha256'], 'models cache changed')
        prepare.prompt_body(arm_for(name))
        prepare.verify_release(self.runtime)
        return legacy.legacy.Runner.validate(self, name)

    def repository(self, name):
        arm_for(name)
        repository = f'fysoul17/rpd3-{self.runtime["run_id"]}-{name}'
        github.url(repository)
        return repository

    def native_prompt(self, caller):
        return prepare.native_prompt(caller, self.active_arm)

    def materialize(self, runtime, name, task, arm, config):
        require(arm == 'B' and self.active_arm == arm_for(name), 'attempt arm/installed route mismatch')
        return prepare.prepare(runtime, name, task, self.active_arm, config, inherited=self.frame.prepare,
                               tasks=self.tasks, tasks_path=self.tasks_path,
                               repository=self.repository(name), remaining=self.remaining(name))

    def boot_expectation(self, arm, config):
        require(config == 'codex' and arm in ('B', 'P0', 'P1'), 'rp-d3 is Codex only')
        return None

    def record_binding(self, record):
        arm = arm_for(record['cell'])
        require(record['arm'] == arm and record['prompt_sha256'] == prepare.PROMPT_SHA256[arm] and
                record['release'] == prepare.release_identity(self.runtime, arm), 'verdict prompt/release binding mismatch')

    def prior_deleted(self, name):
        slots = [row[0] for row in self.smoke + SCHEDULE]
        index = slots.index(name)
        previous = slots[:2] if name == 'm01' else slots[max(0, index - 1):index]
        for slot in previous:
            smoke = slot in slots[:2]
            record = read(Path(self.runtime['smoke_output' if smoke else 'output']) / slot / 'rp-verdict.json')
            require(record['status'] not in ('STOP', 'UNKNOWN', 'NOT_RUN'), 'schedule already stopped')
            if name == 'm01':
                require(record['status'] in ('PASS', 'ADJUDICATE'), 'smoke did not establish working delivery')
            receipt = record['repository_cleanup']
            require(receipt.get('repository') == self.repository(slot) and receipt.get('status') == 'DELETED' and
                    receipt.get('http_status') == 404 and receipt.get('archive_manifest_sha256'),
                    'previous repository has no archived deletion/404 receipt')
            self.record_binding(record)
            prefix = 'smoke_' if smoke and self.runtime['phase'] == 'measured' else ''
            require(record['codex_account'] == self.runtime[prefix + 'codex_account'], 'previous Codex account mismatch')
            if slot in ARMS:
                require(record['frozen_runtime_sha256'] == self.frozen, 'frozen runtime changed between slots')
            if name in ARMS and int(name[1:]) % 2 == 0:
                require(record['auth_manifest_sha256'] == self.runtime['auth_manifest_sha256'] and
                        record['auth'] == self.runtime['auth'], 'model auth renewal refused within a pair')

    def run(self, name, task, arm, config):
        require((name, task, config) in self.slots() and arm == arm_for(name), 'unregistered slot/task/engine/arm')
        self.active_arm = arm
        try:
            result = legacy.legacy.Runner.run(self, name, task, 'B', config)
            path = Path(self.runtime['output']) / name / 'rp-verdict.json'
            record = read(path)
            record.update(schema='rp-d3-verdict-v1', arm=arm, prompt_sha256=prepare.PROMPT_SHA256[arm],
                          release=prepare.release_identity(self.runtime, arm), codex_account=self.runtime['codex_account'],
                          auth=self.runtime['auth'], auth_manifest_sha256=self.runtime['auth_manifest_sha256'],
                          frozen_runtime_sha256=self.frozen)
            write(path, record)
            return result
        finally:
            self.active_arm = None

    def completed_prefix(self):
        records = super().completed_prefix()
        for row in records:
            if row['status'] != 'NOT_RUN':
                self.record_binding(row)
        return records

    def schedule(self, through_pair=None):
        require(through_pair is None or type(through_pair) is int and 1 <= through_pair <= 4,
                'through-pair requires measured pair 1..4')
        result = super().schedule(through_pair)
        # The reused scheduler emits NOT_RUN rows after STOP; bind those identities too.
        path = Path(self.runtime['output']) / 'rp-schedule.json'
        schedule = read(path)
        for row in schedule['slots']:
            if row['status'] == 'NOT_RUN':
                row.update(prompt_sha256=prepare.PROMPT_SHA256[row['arm']],
                           release=prepare.release_identity(self.runtime, row['arm']))
                write(path.parent / row['cell'] / 'rp-verdict.json', row)
        write(path, schedule)
        return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('runtime', type=Path)
    parser.add_argument('phase', choices=('smoke', 'measured'))
    parser.add_argument('--through-pair', type=int)
    args = parser.parse_args()
    return Runner(args.runtime, phase=args.phase).schedule(args.through_pair)


if __name__ == '__main__':
    raise SystemExit(main())
