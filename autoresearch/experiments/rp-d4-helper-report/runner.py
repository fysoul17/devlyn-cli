"""Helper-report measurement over the frozen serial rp-d2/rp-d1 lifecycle."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re
from types import FunctionType

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('prepare_rpd4_runner', HERE / 'prepare.py')
prepare = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prepare)
load, PRIOR, github = prepare.load, prepare.PRIOR, prepare.github
legacy = load('runner_rpd2_rpd4', HERE.parent / 'rp-d2-report-lines/runner.py')
auth = load('auth_rpd4_runner', HERE / 'auth.py')
read, write, digest, require = legacy.read, legacy.write, legacy.digest, github.require
cell = legacy.cell
codex_account = auth.codex_account


def frozen_runtime(runtime):
    return {key: value for key, value in legacy.frozen_runtime(runtime).items()
            if key not in ('claude_auth', 'claude_auth_manifest_sha256')}

def runtime_binding(runtime):
    return hashlib.sha256(json.dumps(frozen_runtime(runtime), sort_keys=True).encode()).hexdigest()


SCHEDULE = [(f'm{i:02}', 'BV' if i <= 4 else 'Z0', 'codex') for i in range(1, 9)] + [
    ('g01', 'BV', 'claude'), ('g02', 'Z0', 'claude')]
ARMS = dict(zip((row[0] for row in SCHEDULE), ('X', 'Y', 'Y', 'X', 'X', 'Y', 'Y', 'X', 'Y', 'Y')))
prior_runner = load('runner_rpd3_scan_rpd4', HERE.parent / 'rp-d3-prompt-ablation/runner.py')
# Reuse the exact rp-d3 token scan with this private module's credential provider.
codex_scan = FunctionType(prior_runner.scan.__code__, prior_runner.scan.__globals__ | {
    'auth': auth, 'pat_scan': cell.scan, 'write': write})
codex_scan.__kwdefaults__ = prior_runner.scan.__kwdefaults__
pat_scan = cell.scan


def scan(out, runtime, *, roots=None):
    roots = tuple(roots) if roots is not None else (out,)
    codex_scan(out, runtime, roots=roots)
    if runtime.get('auth_engine', 'codex') != 'claude':
        return
    try:
        raw = auth.read_private(auth.directory(runtime['auth']), 'claude.env')
        tokens = [line.partition(b'=')[2] for line in raw.splitlines()
                  if line.startswith(b'CLAUDE_CODE_OAUTH_TOKEN=')]
        if len(tokens) != 1 or not tokens[0] or b'\0' in tokens[0]:
            raise ValueError('invalid Claude bearer snapshot')
        scanner = FunctionType(pat_scan.__code__, pat_scan.__globals__ | {
            'credential': lambda _runtime: (None, tokens[0])})
        scanner(out, runtime, roots=roots)
    except (OSError, ValueError, KeyError, TypeError):
        try:
            write(out / 'claude-scan.json', dict(status='STOP', revocation_required=True))
        finally:
            raise ValueError('Claude credential scan hit or failed; slot stopped') from None


cell.scan = scan
smoke = load('smoke_rpd4_runner', HERE / 'smoke.py')


def smoke_slots(attempt=1):
    require(type(attempt) is int and attempt in (1, 2), 'smoke_attempt must be 1 or 2')
    prefix = 'smoke' if attempt == 1 else 'smoke2'
    return [(f'{prefix}-codex-{arm}', 'SM', 'codex') for arm in ('X', 'Y')]


def smoke_registry(run_id):
    require(isinstance(run_id, str) and re.fullmatch('[A-Za-z0-9][A-Za-z0-9-]*', run_id), 'invalid run_id')
    return Path.home() / '.devlyn/rp-d4-runs' / run_id


def smoke_inputs(runtime):
    return dict(arms_sha256=digest(runtime['arms_file']), **{key: runtime[key] for key in
        ('image', 'codex_account', 'claude_account', 'models_cache_sha256')})


def smoke_evidence(state):
    require(digest(state['runtime']) == state['runtime_sha256'], 'registered smoke runtime changed')
    for path, binding in state.get('verdicts', {}).items():
        require(digest(path) == binding, 'registered smoke evidence changed')


def smoke_registration(runtime):
    root = smoke_registry(runtime['run_id'])
    latest = 2 if (root / 'attempt-2.json').exists() else 1
    require(runtime['smoke_attempt'] == latest, 'smoke attempt was superseded; never replay')
    path = root / f'attempt-{latest}.json'
    state = read(path)
    require(state['status'] != 'STAGING', 'smoke staging did not finish')
    require(state['runtime'] == str(Path(runtime['control']).parent / 'runtime-smoke.json') and
            state['inputs'] == smoke_inputs(runtime), 'registered smoke inputs or stage changed')
    smoke_evidence(state)
    if latest == 2:
        previous = root / 'attempt-1.json'
        require(digest(previous) == state['previous_sha256'] and read(previous)['status'] == 'FAILED',
                'spare smoke is not bound to its failed first attempt')
        smoke_evidence(read(previous))
    return path, state


def arm_for(name):
    if name in ARMS:
        return ARMS[name]
    require(name in {row[0] for attempt in (1, 2) for row in smoke_slots(attempt)}, 'unregistered rp-d4 slot')
    return name[-1]


def solo_route(tasks, config, arm):
    require(config in ('codex', 'claude') and arm in prepare.PROMPT_SHA256, 'unregistered rp-d4 route')
    return legacy.legacy.solo_route(tasks, config, arm)


legacy.SCHEDULE, legacy.ARMS, legacy.arm_for = SCHEDULE, ARMS, arm_for
legacy.legacy.SCHEDULE, legacy.legacy.smoke_slots = SCHEDULE, smoke_slots
legacy.legacy.prepare = prepare.legacy.legacy
legacy.legacy.github = github
legacy.legacy.legacy.policy.check.__globals__['base_policy'].route_for = solo_route


class Runner(legacy.Runner):
    def __init__(self, runtime_path, tasks_path=None, *, phase=None):
        original = read(runtime_path)
        smoke_registration(original)
        require(phase is None or phase == original['phase'], 'phase differs from staged runtime')
        # Skip only rp-d2's two-release constructor; keep every lower lifecycle hook.
        legacy.legacy.Runner.__init__(self, runtime_path, tasks_path, phase=phase)
        self.frozen = runtime_binding(original)
        if 'renewed_from' in original:
            previous = original['renewed_from']
            require(digest(previous['path']) == previous['sha256'], 'previous runtime binding changed')
            require(frozen_runtime(read(previous['path'])) == frozen_runtime(original), 'renewal changed frozen inputs/account')
        self.runtime['release'] = self.runtime['releases']['X']
        self.active_arm = None
        self.base_runtime = self.runtime
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
                 *auth.codex.HERE.glob('*.py'), auth.codex.HERE / 'DESIGN.md',
                 Path(self.base_runtime['claude_auth']) / 'manifest.json',
                 *[Path(r['tarball']) for r in self.runtime['releases'].values()],
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
        repository = f'fysoul17/rpd4-{self.runtime["run_id"]}-{name}'
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
        require(config in ('codex', 'claude') and arm in ('B', 'X', 'Y'), 'unregistered rp-d4 route')
        return None

    def record_binding(self, record):
        arm = arm_for(record['cell'])
        require(record['arm'] == arm and record['prompt_sha256'] == prepare.PROMPT_SHA256[arm] and
                record['release'] == prepare.release_identity(self.runtime, arm), 'verdict prompt/release binding mismatch')

    def prior_deleted(self, name):
        _, state = smoke_registration(self.base_runtime)
        require(state['status'] == ('QUALIFIED' if name in ARMS else 'STAGED'), 'smoke attempt is consumed or unqualified')
        slots = [row[0] for row in self.smoke + SCHEDULE]
        index = slots.index(name)
        previous = slots[:2] if name == 'm01' else slots[max(0, index - 1):index]
        for slot in previous:
            smoke = slot in slots[:2]
            record = read(Path(self.runtime['smoke_output' if smoke else 'output']) / slot / 'rp-verdict.json')
            require(record['status'] not in ('STOP', 'UNKNOWN', 'NOT_RUN'), 'schedule already stopped')
            if name == 'm01':
                require(record.get('smoke_qualification', {}).get('status') == 'PASS', 'smoke not qualified')
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
                require(record['auth_manifest_sha256'] == auth.for_engine(self.base_runtime, 'claude' if name.startswith('g') else 'codex')['auth_manifest_sha256'] and
                        record['auth'] == auth.for_engine(self.base_runtime, 'claude' if name.startswith('g') else 'codex')['auth'], 'model auth renewal refused within a pair')

    def run(self, name, task, arm, config):
        require((name, task, config) in self.slots() and arm == arm_for(name), 'unregistered slot/task/engine/arm')
        _, state = smoke_registration(self.base_runtime)
        require(state['status'] == ('QUALIFIED' if name in ARMS else 'STAGED'), 'smoke attempt is consumed or unqualified')
        self.active_arm = arm
        self.runtime = auth.for_engine(self.base_runtime, config)
        self.frame.seal_after_teardown.keywords['runtime'] = self.runtime
        try:
            result = legacy.legacy.Runner.run(self, name, task, 'B', config)
            path = Path(self.runtime['output']) / name / 'rp-verdict.json'
            record = read(path)
            if any((path.parent / (engine + '-scan.json')).exists() for engine in ('codex', 'claude')):
                record.update(status='STOP', usage='UNKNOWN', input_tokens=None, output_tokens=None,
                              delivery_assessment='NOT_ASSESSED', revocation_required=True,
                              reason='Model credential scan hit or failed; slot stopped')
                result = 2
            if record['dispatched'] and not record.get('revocation_required'):
                try:
                    record['merge_refused'] = smoke.merge_refused(path.parent)
                    if record['merge_refused'] and record['status'] not in ('STOP', 'UNKNOWN'):
                        record.update(status='PRODUCT_INCOMPLETE', delivery_assessment='PRODUCT_INCOMPLETE')
                    if self.runtime['phase'] == 'smoke' and record['status'] in ('PASS', 'ADJUDICATE'):
                        require((path.parent / 'report-checklist.json').is_file(), 'smoke checklist missing')
                        record['smoke_qualification'] = smoke.qualify(path.parent) if arm == 'Y' else {'status': 'PASS'}
                except (OSError, ValueError, KeyError, TypeError, RuntimeError):
                    record.update(status='STOP', reason='helper evidence qualification failed')
                    result = 2
            record.update(schema='rp-d4-verdict-v1', account=self.runtime['account'], arm=arm, prompt_sha256=prepare.PROMPT_SHA256[arm],
                          release=prepare.release_identity(self.runtime, arm), codex_account=self.runtime['codex_account'],
                          auth=self.runtime['auth'], auth_manifest_sha256=self.runtime['auth_manifest_sha256'],
                          frozen_runtime_sha256=self.frozen)
            write(path, record)
            if self.runtime['phase'] == 'smoke':
                state = self.finish_smoke()
                if state['status'] in ('FAILED', 'STOP'):
                    result = 2
            return result
        finally:
            self.active_arm = None
            self.runtime = self.base_runtime
            self.frame.seal_after_teardown.keywords['runtime'] = self.base_runtime

    def finish_smoke(self):
        path, state = smoke_registration(self.base_runtime)
        if state['status'] != 'STAGED':
            return state
        records = self.completed_prefix()
        failed = any(row['status'] not in ('PASS', 'ADJUDICATE') or
                     row.get('smoke_qualification', {}).get('status') != 'PASS' for row in records)
        if not failed and len(records) != len(self.smoke):
            return state
        state['status'] = ('STOP' if self.runtime['smoke_attempt'] == 2 or
                           any(row.get('revocation_required') for row in records) else 'FAILED') if failed else 'QUALIFIED'
        state['verdicts'] = {str(Path(self.runtime['smoke_output']) / row['cell'] / 'rp-verdict.json'):
                            digest(Path(self.runtime['smoke_output']) / row['cell'] / 'rp-verdict.json')
                            for row in records}
        write(path, state)
        return state

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
        schedule['releases'] = {arm: prepare.release_identity(self.runtime, arm) for arm in ('X', 'Y')}
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
