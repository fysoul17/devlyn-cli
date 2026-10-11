"""Prospective Claude receipt-accounting runner; historical studies stay frozen."""
import argparse
import importlib.util
import json
from pathlib import Path
import subprocess
import time

HERE = Path(__file__).resolve().parent


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


legacy = load('runner0253_receipts', HERE.parent / '0253/runner.py')
accounting = load('accounting0254_runner', HERE.parent / '0254/audit.py')
diagnostics = load('diagnostics0255', HERE.parent / '0234/diagnostics.py')
read, write, digest = legacy.read, legacy.write, legacy.digest
# Select the effective private orchestration after0240/0242 policy amendments.
# Reading this binding preserves those guards without changing any module global.
policy = legacy.Runner.run.__globals__['policy']
helper_invocations = policy.check.__globals__['base_policy'].helper_invocations
delivery = legacy.Runner.run.__globals__['delivery']


class Runner(legacy.Runner):
    def inputs(self):
        paths = (Path(__file__), HERE.parent / '0254/audit.py')
        return dict(super().inputs(), **{str(path): digest(path) for path in paths})

    def account(self, out, manifest_sha256):
        owner = self.tasks['routes']['claude']['owner']
        report = accounting.audit(out, manifest_sha256=manifest_sha256,
                                  model=owner['model'], effort=owner['effort'],
                                  account=self.runtime['account'][0])
        gaps = list(report['gaps'])
        if report['status'] == 'MATCH':
            try:
                # Parser failure must not erase an observed foreign native carrier.
                carriers = (Path('home/.codex/sessions'), Path('cell/trace'))
                sealed_files = read(out / 'evidence.manifest.json')['files']
                if (any(Path(name).is_relative_to(carrier) for name in sealed_files for carrier in carriers)
                        or any((out / carrier).is_symlink() for carrier in carriers)
                        or any(path.is_file() or path.is_symlink() for carrier in carriers
                               for path in (out / carrier).rglob('*'))):
                    gaps.append('foreign native evidence carrier outside scope')
                evidence = self.frame.cell_run.evidence
                inv = evidence.inventory(out, read(out / 'plan.json'))
                foreign = ('rollouts', 'native', 'seated', 'inferences', 'headers',
                           'owner_threads', 'worker_threads', 'owner_launched_codex',
                           'owner_launched_claude', 'envelopes', 'unreadable', 'gaps')
                if any(inv[key] for key in foreign) or any(inv['attempted'].values()):
                    gaps.append('independent invocation or incomplete native inventory outside scope')
                paths = [out / 'run/stdout', *sorted((out / accounting.PROJECTS).rglob('*.jsonl'))]
                rows = [row for path in paths for row in evidence.lines(path)]
                # A provisional block need not contain all tool calls in the terminal body.
                rows += [dict(type='assistant', message=read(out / path)) for path in report['sources']
                         if path.endswith('.response.json')]
                # Transcript user prompts can be strings; only assistant tool inputs
                # are launch evidence, so user/tool-result payloads are not needed here.
                rows = [row for row in rows if row.get('type') == 'assistant']
                for row in rows:
                    content = row['message'].get('content', [])
                    if not isinstance(content, list) or any(not isinstance(block, dict) for block in content):
                        raise ValueError('unsupported assistant content in launch inventory')
                commands = [diagnostics.text_of(call) for call in diagnostics.calls(rows, 'claude')]
                if any(diagnostics.launch_engine(command) is not None or helper_invocations(command)
                       for command in commands):
                    gaps.append('independent native CLI launch outside scope')
            except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
                gaps.append('native scope inventory failed: ' + type(exc).__name__)
        complete = report['status'] == 'MATCH' and not gaps
        usage = dict(schema='0255-native-usage-v1', completeness='COMPLETE' if complete else 'UNKNOWN',
                     input_tokens=report['input_tokens'] if complete else None,
                     output_tokens=report['output_tokens'] if complete else None,
                     gaps=gaps, source='0254-native-receipts-v1')
        return usage, report

    def run(self, name, task, arm, config):
        if config == 'codex':
            return super().run(name, task, arm, config)
        if config != 'claude' or arm not in ('A', 'B', 'S'):
            raise ValueError('0255 supports Claude solo arms A/B/S only')
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
            usage, closure = self.account(out, sealed)
            write(out / 'native-receipts.json', closure)
            record['claude_accounting'] = closure
            pair = policy.check(out, read(out / 'plan.json'), self.tasks, self.frame.cell_run.evidence)
            write(out / 'peer-policy.json', pair)
            record['peer_policy'] = pair
            if pair['status'] != 'MATCH' or pair['gaps']:
                usage['gaps'].append('peer identity or evidence outside supported scope')
            if owner['teardown'] != 'CLEAN' or errors:
                usage['gaps'].append('teardown or evidence collection failed')
            if usage['gaps']:
                usage.update(completeness='UNKNOWN', input_tokens=None, output_tokens=None)
            write(out / 'usage.json', usage)
            record.update(usage=usage['completeness'], usage_gaps=usage['gaps'],
                          input_tokens=usage['input_tokens'], output_tokens=usage['output_tokens'])
            if usage['completeness'] != 'COMPLETE':
                raise ValueError('whole-run usage UNKNOWN')
            if owner['identity']['status'] != 'MATCH':
                raise ValueError('model identity ' + owner['identity']['status'])
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
    parser.add_argument('runtime', type=Path)
    parser.add_argument('name')
    parser.add_argument('task')
    parser.add_argument('arm', choices=('A', 'B', 'S', 'H', 'P'))
    parser.add_argument('config', choices=('claude', 'codex'))
    args = parser.parse_args()
    try:
        return Runner(args.runtime).run(args.name, args.task, args.arm, args.config)
    except (OSError, ValueError, KeyError, TypeError, RuntimeError, subprocess.SubprocessError) as exc:
        print(json.dumps(dict(status='STOP', reason=f'{type(exc).__name__}: {exc}')))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
