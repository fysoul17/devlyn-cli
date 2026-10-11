"""0238 prospective pair adapter; no automatic scheduling or assessor dispatch.

Reuse 0237 isolation/delivery and the matched 0234 native evidence/accounting set.
Only new controls are registered peer routes, per-turn receipts and F23 supplement.
"""
from __future__ import annotations

import argparse
import importlib.util
from pathlib import Path
import json
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


prior = load('runner0237', HERE.parent / '0237/runner.py')
policy = load('policy0238', HERE / 'policy.py')
read, write, digest, delivery = prior.read, prior.write, prior.digest, prior.delivery


class Runner(prior.Runner):
    def __init__(self, runtime_path, tasks_path=None):
        runtime = read(runtime_path)
        if tasks_path is None and not runtime.get('tasks_file'):
            raise ValueError('0238 requires an explicit registered tasks_file')
        super().__init__(runtime_path, tasks_path)
        m = self.frame
        m.cell_run = load('cell0238', HERE.parent / '0234/cell.py')
        m.usage = load('usage0238', HERE.parent / '0234/record_usage.py')
        m.usage.evidence = m.cell_run.evidence
        m.check = load('check0238', HERE.parent / '0234/check.py')
        for module in (m.cell_run.evidence, m.check, m.check.base):
            module.TASKS = self.tasks
        m.check.SECONDS = m.check.base.SECONDS = self.tasks['watchdog_seconds']['evaluator']
        self.original_evaluate = m.check.evaluate
        m.check.evaluate = self.evaluate
        m.prepare.ARMS = ('A', 'B', 'S', 'H', 'P')
        # The legacy materializer reads HERE/tasks.json for its baseline field.
        # Keep that existing path readable; reseal the actual registered task file below.
        m.prepare.HERE = HERE.parent / '0233'
        for config in ('claude', 'codex'):
            for arm in ('H', 'P'):
                policy.route_for(self.tasks, config, arm)

    def inputs(self):
        result = super().inputs()
        paths = [HERE / name for name in ('runner.py', 'policy.py', 'peer.py', 'f23_precision.py')]
        paths += list((HERE.parent / '0234').glob('*.py'))
        result.update({str(path): digest(path) for path in paths})
        return result

    def prepare(self, name, task, arm, config):
        out = super().prepare(name, task, arm, config)
        plan = read(out / 'plan.json')
        claude = self.tasks['routes']['claude']['owner']
        settings = out / 'home/.claude/settings.json'
        write(settings, dict(read(settings), model=claude['model'], effortLevel=claude['effort']))
        plan['env']['CLAUDE_CODE_EFFORT_LEVEL'] = claude['effort']
        base = load('prepare0222defaults', HERE.parent / '0222/prepare.py')
        text = base.codex_toml(self.tasks['routes']['codex']['owner'])
        if text.count('[projects."/work"]') != 1:
            raise ValueError('unexpected inherited Codex project trust')
        codex = out / 'home/.codex/config.toml'
        codex.write_text(text.replace('[projects."/work"]', '[projects."/cell/work"]'))
        write(out / 'plan.json', plan)
        baseline = read(out / 'baseline.json')
        baseline['tasks_sha256'] = digest(self.tasks_path)
        write(out / 'baseline.json', baseline)
        seal = read(out / 'seal.json')
        seal['prepared']['home/.codex/config.toml'] = digest(codex)
        seal['prepared'] = {name: digest(out / name) for name in seal['prepared']}
        write(out / 'seal.json', seal)
        self.unchanged(out)
        return out

    def evaluate(self, work, task_id, runtime):
        result = super().evaluate(work, task_id, runtime)
        if task_id != 'F23':
            return result
        check = self.frame.check
        witness = Path(runtime['control']) / 'oracle/experiments/0238/f23_precision.py'
        if digest(witness) != digest(HERE / 'f23_precision.py'):
            raise ValueError('F23 supplemental oracle differs from frozen implementation')
        raw = check.in_image(runtime, work, ['python3', '-B',
                             '/control/autoresearch/experiments/0238/f23_precision.py', '/cell/work'])
        # This supplement explicitly uses exit 1 for a valid observed FAIL.
        # The inherited last_json intentionally discards all nonzero exits.
        try:
            decoded = json.loads(raw['stdout'])
        except (ValueError, TypeError) as exc:
            raise ValueError('F23 supplemental oracle returned malformed JSON') from exc
        rows = decoded.get('rows') if isinstance(decoded, dict) else None
        if (raw['exit_code'] not in (0, 1) or not isinstance(rows, list)
                or decoded.get('schema') != '0238-f23-precision-v1'
                or decoded.get('status') != ('PASS' if raw['exit_code'] == 0 else 'FAIL')
                or any(not isinstance(row, dict) for row in rows)
                or sorted(row.get('id', '') for row in rows) != ['offset-equivalence', 'submillisecond-order']
                or any(row.get('status') not in ('PASS', 'FAIL') for row in rows)
                or (raw['exit_code'] == 0) != all(row['status'] == 'PASS' for row in rows)):
            raise ValueError('F23 supplemental oracle returned no unambiguous verdict')
        result['rows'] += [dict(id=row['id'], status=row['status']) for row in rows]
        result['raw'].append(raw)
        return result

    def run(self, name, task, arm, config):
        self.validate(name)
        expected_catalogs = self.boot_expectation(arm, config)
        output = Path(self.runtime['output'])
        output.mkdir(parents=True, exist_ok=True)
        verdict = output / f'verdict-{name}.json'
        if verdict.exists() or (output / name).exists():
            raise ValueError('cell already exists; preserve it and choose a new registered identity')
        venue, blocked = self.preflight()
        if blocked:
            write(output / f'not-dispatched-{name}.json', dict(reason=blocked))
            return 3
        out = self.prepare(name, task, arm, config)
        record = dict(cell=name, task=task, arm=arm, config=config, venue=venue,
                      phase=self.runtime['phase'], measurement_eligible=self.runtime['phase'] == 'measured',
                      assessment='NOT_REQUESTED', input_tokens=None, output_tokens=None, usage='UNKNOWN')
        started = time.monotonic()
        try:
            owner = self.frame.cell_run.run(out, self.runtime)
            record.update(owner_status=owner['owner_status'], owner_seconds=owner['seconds'],
                          identity=owner['identity'], teardown=owner['teardown'])
            sealed, errors = self.frame.seal_after_teardown(out)
            record['evidence_manifest_sha256'] = sealed
            usage = self.frame.usage.record(out)
            record['usage'] = usage['completeness']
            record['usage_gaps'] = usage['gaps']
            pair = policy.check(out, read(out / 'plan.json'), self.tasks, self.frame.cell_run.evidence)
            write(out / 'peer-policy.json', pair)
            record['peer_policy'] = pair
            if pair['gaps']:
                usage['gaps'] += ['peer: ' + gap for gap in pair['gaps']]
                usage['completeness'] = 'PARTIAL' if usage['input_tokens'] or usage['output_tokens'] else 'UNKNOWN'
                write(out / 'usage.json', usage)
                record.update(usage=usage['completeness'], usage_gaps=usage['gaps'])
            if usage['completeness'] == 'COMPLETE':
                record.update(input_tokens=usage['input_tokens'], output_tokens=usage['output_tokens'])
            else:
                record['known_usage_lower_bound'] = {key: usage[key] for key in ('input_tokens', 'output_tokens')}
            if owner['teardown'] != 'CLEAN' or errors:
                raise ValueError('teardown or evidence collection failed: ' + str(errors))
            if owner['identity']['status'] != 'MATCH':
                raise ValueError('model identity ' + owner['identity']['status'])
            if pair['status'] != 'MATCH':
                raise ValueError('peer model identity/evidence ' + pair['status'])
            if usage['completeness'] != 'COMPLETE':
                raise ValueError('whole-run usage ' + usage['completeness'])
            record['boot_catalogs'] = self.boot_catalogs(out, config)
            if expected_catalogs is not None:
                expected_catalogs = {key: sorted(value, key=lambda item: json.dumps(item, sort_keys=True))
                                     for key, value in expected_catalogs.items()}
                if record['boot_catalogs'] != expected_catalogs:
                    raise ValueError('boot catalog contamination or drift')
            quota = self.frame.quota.classify(out)
            record['quota'] = quota
            if quota['execution']:
                raise ValueError('authentication or quota fault during execution')
            self.unchanged(out)
            record['snapshot'] = self.frame.locate.locate(out)
            evaluator_start = time.monotonic()
            checked = self.frame.check.check(out, self.runtime)
            delivered = delivery.check(out, record['snapshot'], self.frame.locate, self.packet)
            write(out / 'delivery.json', delivered)
            record.update(checked, source_check_pass=checked['product_check_pass'],
                          delivery=delivered, delivery_pass=delivered['passed'],
                          deterministic_seconds=time.monotonic() - evaluator_start)
            record['status'] = ('PRODUCT_INCOMPLETE' if not delivered['passed'] or owner['owner_status'] != 'EXITED_0' or pair['protocol_violations']
                                else 'ADJUDICATE' if checked['adjudication_needed']
                                else 'CHECKS_PASS' if checked['product_check_pass']
                                else 'PRODUCT_INCOMPLETE')
            # This digest protects later assessment of exactly the source whose checks were recorded.
            write(out / 'checked.json', dict(snapshot=self.packet.tree(out / 'snapshot'),
                                             checks_sha256=digest(out / 'checks.json'),
                                             delivery_sha256=digest(out / 'delivery.json')))
        except (OSError, ValueError, KeyError, TypeError, RuntimeError, subprocess.SubprocessError) as exc:
            record.update(status='STOP', reason=f'{type(exc).__name__}: {exc}')
        record['run_and_checks_seconds'] = time.monotonic() - started
        write(verdict, record)
        return 2 if record['status'] == 'STOP' else 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_subparsers(dest='action', required=True)
    for name in ('run', 'prepare', 'assess'):
        action = actions.add_parser(name)
        action.add_argument('runtime', type=Path)
        action.add_argument('name')
        if name != 'assess':
            action.add_argument('task')
            action.add_argument('arm', choices=('A', 'B', 'S', 'H', 'P'))
            action.add_argument('config', choices=('claude', 'codex'))
    args = parser.parse_args()
    try:
        runner = Runner(args.runtime)
        if args.action == 'assess':
            return runner.assess(args.name)
        if args.action == 'prepare':
            print(runner.prepare(args.name, args.task, args.arm, args.config))
            return 0
        return runner.run(args.name, args.task, args.arm, args.config)
    except (OSError, ValueError, KeyError, TypeError, RuntimeError, subprocess.SubprocessError) as exc:
        print(json.dumps(dict(status='STOP', reason=f'{type(exc).__name__}: {exc}')), file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
