"""rp-d1 adapter over unchanged 0255/0254 accounting; serial, fail-closed delivery.

runner.py <runtime.json> smoke | measured
Runtime adds run_id, github_auth (private directory path), release (version,
tarball, sha256, registry integrity), and smoke_output (separate from output).
No credential value belongs in runtime, plan, command arguments or records.
"""
import argparse
from functools import partial
import importlib.util
import json
from pathlib import Path
import re
import subprocess

HERE = Path(__file__).resolve().parent


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


legacy = load('runner0255_rpd1', HERE.parent / '0255/runner.py')
prepare = load('prepare_rpd1_runner', HERE / 'prepare.py')
cell = load('cell_rpd1_runner', HERE / 'cell.py')
github = prepare.github
read, write, digest = legacy.read, legacy.write, legacy.digest
SCHEDULE = [('o01', 'BV', 'claude'), ('o02', 'BV', 'codex'), ('o03', 'Z0', 'codex'),
            ('o04', 'Z0', 'claude'), ('o05', 'Z0', 'claude'), ('o06', 'Z0', 'codex'),
            ('o07', 'BV', 'codex'), ('o08', 'BV', 'claude')]
SMOKE = [('smoke-claude', 'SM', 'claude'), ('smoke-codex', 'SM', 'codex')]
BOOT_REFUSALS = {'runtime phase must be smoke or measured',
                 'measured Claude requires boot_catalogs.claude.B',
                 'boot catalog must explicitly list skills, plugins and mcp_servers'}


def solo_route(tasks, config, _arm):
    # 0238's initializer validates unused H/P routes. This study registers only B.
    route = tasks['routes'][config]
    if (tasks['schema'] != 'rp-d1-delivery-cost-v1' or set(route) != {'owner'} or
            route['owner']['engine'] != config):
        raise ValueError('rp-d1 requires only the owner route')


legacy.policy.route_for = solo_route


class Runner(legacy.Runner):
    def __init__(self, runtime_path, tasks_path=None, *, phase=None):
        runtime = read(runtime_path)
        phase = phase or runtime['phase']
        if phase not in ('smoke', 'measured'):
            raise ValueError('runtime phase must be smoke or measured')
        output, smoke_output = (Path(runtime[key]).resolve() for key in ('output', 'smoke_output'))
        if output.is_relative_to(smoke_output) or smoke_output.is_relative_to(output):
            raise ValueError('smoke and measured output roots must not overlap')
        default_tasks = (HERE / 'smoke-tasks.json' if phase == 'smoke' else
                         runtime.get('tasks_file', HERE / 'tasks.json'))
        super().__init__(runtime_path, tasks_path or default_tasks)
        self.runtime['phase'] = phase
        if phase == 'smoke':
            self.runtime['output'] = str(smoke_output)
        self.frame.prepare.git = prepare.bootstrap_git
        self.frame.prepare.prepare = self.materialize
        self.frame.harness_unchanged = prepare.harness_unchanged
        inherited_launch = self.frame.cell_run.run
        inherited_launch.keywords['native'].evidence.seats = self.seats
        self.frame.cell_run.run = partial(cell.run, **inherited_launch.keywords)
        self.frame.seal_after_teardown = partial(cell.seal, runtime=self.runtime,
                                               inherited=self.frame.seal_after_teardown)

    def seats(self, plan):
        # 0234 inventories only owner/native-child seats; no worker or judge runs.
        owner = self.tasks['routes'][plan['config']]['owner']
        return dict(owner=owner, child=owner)

    def repository(self, name):
        run_id = self.runtime['run_id']
        if not re.fullmatch('[A-Za-z0-9][A-Za-z0-9-]*', run_id):
            raise ValueError('invalid run_id')
        repository = f'fysoul17/rpd1-{run_id}-{name}'
        github.url(repository)
        return repository

    def remaining(self, name):
        slots = [row[0] for row in SMOKE + SCHEDULE]
        return [self.repository(slot) for slot in slots[slots.index(name):]]

    def slots(self):
        return {'smoke': SMOKE, 'measured': SCHEDULE}[self.runtime['phase']]

    def native_prompt(self, caller):
        return (HERE / 'common.txt').read_text() + '\nCALLER CONTRACT\n' + json.dumps(caller, indent=2)

    def inputs(self):
        result = super().inputs()
        paths = [HERE / name for name in ('runner.py', 'prepare.py', 'cell.py', 'github.py', 'oracle.py',
                  'common.txt', 'tasks.json', 'smoke-tasks.json', 'Dockerfile', 'build.sh', 'DESIGN.md',
                  'test_apparatus.py', 'stage.py', 'test_stage.py')]
        paths += [p for p in (HERE / 'fixtures').rglob('*') if p.is_file() and '__pycache__' not in p.parts]
        paths.append(Path(self.runtime['release']['tarball']))
        result.update({str(path): digest(path) for path in paths})
        return result

    def materialize(self, runtime, name, task, arm, config):
        return prepare.prepare(runtime, name, task, arm, config, inherited=self.frame.prepare,
                               tasks=self.tasks, tasks_path=self.tasks_path,
                               repository=self.repository(name), remaining=self.remaining(name))

    def prepare(self, name, task, arm, config):
        out = super().prepare(name, task, arm, config)
        # 0237 checks /work then rewrites it; 0238 subsequently replaces the config.
        # Restore the registered config after those unchanged ancestor stages.
        if config == 'codex':
            path = out / 'home/.codex/config.toml'
            path.write_text(prepare.codex_toml(self.tasks['routes']['codex']['owner']).replace(
                '[projects."/work"]', '[projects."/cell/work"]'))
            seal = read(out / 'seal.json')
            seal['prepared']['home/.codex/config.toml'] = digest(path)
            write(out / 'seal.json', seal)
            self.unchanged(out)
        return out

    def evaluate(self, work, task_id, runtime):
        task = self.task(task_id)
        check = self.frame.check
        oracle = Path(runtime['control']) / 'oracle/experiments/rp-d1-delivery-cost/oracle.py'
        if digest(oracle) != digest(HERE / 'oracle.py'):
            raise ValueError('hidden oracle differs from frozen implementation')
        public = [check.in_image(runtime, work, ['sh', '-c',
                  'mkdir /tmp/public-work && cp -a /cell/work/. /tmp/public-work/ && cd /tmp/public-work && ' + cmd])
                  for cmd in task['public_checks']]
        for result in public:
            check.base.last_json(result)
        raw = check.in_image(runtime, work, ['python3', '-B',
                    '/control/autoresearch/experiments/rp-d1-delivery-cost/oracle.py', task_id, '/cell/work'])
        decoded = check.base.last_json(raw)
        if (raw['exit_code'] != 0 or not isinstance(decoded, dict) or
                decoded.get('schema') != 'rp-d1-oracle-v1' or
                sorted(row['id'] for row in decoded['rows']) != sorted(task['oracle']) or
                any(row['status'] not in ('PASS', 'FAIL') for row in decoded['rows'])):
            raise ValueError('oracle produced no unambiguous verdict')
        return dict(public=public, rows=decoded['rows'], raw=[raw])

    def prior_deleted(self, name):
        slots = [row[0] for row in SMOKE + SCHEDULE]
        index = slots.index(name)
        # o01 independently requires both smoke verdicts, even if one is lost later.
        predecessors = slots[:2] if name == 'o01' else slots[max(0, index - 1):index]
        for previous in predecessors:
            root = self.runtime['smoke_output' if previous in slots[:2] else 'output']
            record = read(Path(root) / previous / 'rp-verdict.json')
            if record['status'] in ('STOP', 'UNKNOWN', 'NOT_RUN'):
                raise ValueError('schedule already stopped')
            if previous in slots[:2] and record['status'] not in ('PASS', 'ADJUDICATE'):
                raise ValueError('smoke did not establish working delivery')
            receipt = record['repository_cleanup']
            if (receipt.get('repository') != self.repository(previous) or receipt.get('status') != 'DELETED'
                    or receipt.get('http_status') != 404 or not receipt.get('archive_manifest_sha256')):
                raise ValueError('previous repository has no archived deletion/404 receipt')

    def run(self, name, task, arm, config):
        if arm != 'B' or (name, task, config) not in self.slots():
            raise ValueError('unregistered rp-d1 slot/task/route')
        tasks_file = 'smoke-tasks.json' if self.runtime['phase'] == 'smoke' else 'tasks.json'
        if self.tasks != read(HERE / tasks_file):
            raise ValueError('phase requires its frozen rp-d1 tasks')
        output = Path(self.runtime['output'])
        out = output / name
        root = output / 'archives' / name
        if out.exists() or (output / f'verdict-{name}.json').exists():
            raise ValueError('slot already attempted; preserve it, never replay')
        output.mkdir(parents=True, exist_ok=True)
        record = dict(schema='rp-d1-verdict-v1', cell=name, task=task, config=config,
                      phase=self.runtime['phase'], measurement_eligible=self.runtime['phase'] == 'measured',
                      status='STOP', delivery_assessment='NOT_ASSESSED', dispatched=False,
                      usage='UNKNOWN', input_tokens=None, output_tokens=None)
        try:
            self.prior_deleted(name)
            github.precheck(self.remaining(name))
            super().run(name, task, arm, config)
            inherited = output / f'verdict-{name}.json'
            if not inherited.exists():
                raise github.EvidenceError(read(output / f'not-dispatched-{name}.json')['reason'])
            verdict = read(inherited)
            record.update(inherited_verdict_sha256=digest(inherited), inherited_status=verdict['status'],
                          dispatched=(out / 'run/started.json').exists(),
                          **{key: verdict[key] for key in ('usage', 'input_tokens', 'output_tokens')})
            # Never post-grade a STOP, including UNKNOWN/PARTIAL accounting.
            if verdict['status'] == 'STOP':
                record['reason'] = verdict['reason']
            else:
                record['status'] = verdict['status']
            # Cleanup is allowed after a STOP only with proven teardown and seal.
            if (verdict.get('teardown') == 'CLEAN' and verdict.get('evidence_manifest_sha256') and
                    not (out / 'pat-scan.json').exists()):
                record['repository_cleanup'] = dict(repository=self.repository(name), status='RETAINED',
                    reason='repository remains for manual cleanup; deletion requires a verified archive and confirmed 404')
                archived = github.archive(self.repository(name), root)
                record['archive'] = archived
                try:
                    if verdict['status'] != 'STOP':
                        done = github.done_check(out, root, verdict['snapshot'], self.frame.locate, self.packet)
                        write(out / 'report-checklist.json', done['checklist'])
                        write(out / 'github-delivery.json', done)
                        record['delivery_assessment'] = done['status']
                        if done['status'] == 'PRODUCT_INCOMPLETE' or verdict['status'] == 'PRODUCT_INCOMPLETE':
                            record['status'] = 'PRODUCT_INCOMPLETE'
                        else:
                            record['status'] = done['status']
                finally:
                    record['repository_cleanup'] = github.delete_archived(
                        self.repository(name), root, archived['manifest_sha256'])
            elif verdict['status'] != 'STOP':
                raise ValueError('delivery evidence has no clean teardown/seal')
        except github.EvidenceError as exc:
            record.update(status='STOP', reason=str(exc))
        except (OSError, ValueError, KeyError, TypeError, RuntimeError, subprocess.SubprocessError) as exc:
            # Do not serialize arbitrary subprocess output or exception payloads.
            reason = str(exc) if type(exc) is ValueError and str(exc) in BOOT_REFUSALS else (
                'rp-d1 instrumentation failed: ' + type(exc).__name__)
            record.update(status='STOP', reason=reason)
        finally:
            out.mkdir(parents=True, exist_ok=True, mode=0o700)
            record['dispatched'] = (out / 'run/started.json').exists()
            scan_failed = False
            try:
                # Include partial archives and the inherited records outside the slot directory.
                roots = [out] + [path for path in (root, output / f'verdict-{name}.json',
                         output / f'not-dispatched-{name}.json') if path.exists() or path.is_symlink()]
                cell.scan(out, self.runtime, roots=roots)
            except (OSError, ValueError):
                scan_failed = True
            if scan_failed or (out / 'pat-scan.json').exists():
                record.update(status='UNKNOWN', usage='UNKNOWN', input_tokens=None, output_tokens=None,
                              delivery_assessment='NOT_ASSESSED', revocation_required=True,
                              reason='PAT scan hit or failed; revoke PAT immediately')
            write(out / 'rp-verdict.json', record)
        return 2 if (record['status'] in ('STOP', 'UNKNOWN') or
                     self.runtime['phase'] == 'smoke' and record['status'] not in ('PASS', 'ADJUDICATE')) else 0

    def schedule(self):
        records, stopped = [], False
        for name, task, config in self.slots():
            if stopped:
                out = Path(self.runtime['output']) / name
                out.mkdir(parents=True, exist_ok=False)
                record = dict(cell=name, task=task, config=config, status='NOT_RUN',
                              phase=self.runtime['phase'], measurement_eligible=self.runtime['phase'] == 'measured',
                              delivery_assessment='NOT_ASSESSED', dispatched=False,
                              reason='earlier slot stopped the schedule')
                write(out / 'rp-verdict.json', record)
            else:
                stopped = self.run(name, task, 'B', config) != 0
                record = read(Path(self.runtime['output']) / name / 'rp-verdict.json')
            records.append(record)
        result = dict(status='STOP' if stopped else 'RECORDED', phase=self.runtime['phase'], slots=records,
                      dispatched=sum(row['dispatched'] for row in records))
        write(Path(self.runtime['output']) / 'rp-schedule.json', result)
        return 2 if stopped else 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('runtime', type=Path)
    parser.add_argument('phase', choices=('smoke', 'measured'))
    args = parser.parse_args()
    return Runner(args.runtime, phase=args.phase).schedule()


if __name__ == '__main__':
    raise SystemExit(main())
