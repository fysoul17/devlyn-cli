"""One registered capture probe; it cannot grade or start an efficacy study."""
import argparse
import importlib.util
import json
from pathlib import Path
import subprocess
import time

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('capture0253', HERE / 'runner.py')
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)
accounting = runner.legacy.load('accounting0253_unchanged', HERE.parent / '0238/claude-accounting-v1.py')
policy = runner.legacy.load('policy0253_unchanged', HERE.parent / '0238/policy.py')
registration = runner.read(HERE / 'registration.json')


class Probe(runner.Runner):
    def native_prompt(self, caller):
        return registration['prompt']

    def inputs(self):
        paths = (Path(__file__), HERE / 'registration.json')
        return dict(super().inputs(), **{str(path): runner.digest(path) for path in paths})


def run(runtime_path, bindings_path):
    app = Probe(runtime_path)
    frozen = runner.read(bindings_path)
    if app.inputs() != frozen:
        raise ValueError('probe bindings changed')
    root = Path(app.runtime['output']).parent
    name = registration['name']
    record = dict(name=name, started_at=time.time(), status='STOP')
    # An interrupted invocation is not permission to dispatch it again.
    with (root / f'dispatch-{name}.json').open('x') as stream:
        json.dump(record, stream)
    try:
        venue, blocked = app.preflight()
        if blocked:
            raise ValueError('preflight: ' + blocked)
        record['venue'] = venue
        out = app.prepare(name, registration['task'], registration['arm'], registration['config'])
        record['owner'] = app.frame.cell_run.run(out, app.runtime)
        seal, errors = app.frame.seal_after_teardown(out)
        record.update(evidence_manifest_sha256=seal, seal_errors=errors)
        record['usage'] = app.frame.usage.record(out)
        receipts, _ = policy.receipts(out, app.frame.cell_run.evidence)
        record['unchanged_accounting'] = accounting.audit(out, app.frame.cell_run.evidence, receipts)
        record['peer_policy'] = policy.check(out, runner.read(out / 'plan.json'), app.tasks,
                                            app.frame.cell_run.evidence)
        record['catalogs'] = app.boot_catalogs(out, 'claude')
        expected = app.boot_expectation('B', 'claude')
        if expected is not None:
            expected = {key: sorted(value, key=lambda item: json.dumps(item, sort_keys=True))
                        for key, value in expected.items()}
        record['quota'] = app.frame.quota.classify(out)
        record['response'] = (out / 'final.txt').read_text().strip()
        bodies = out / 'home/.claude/api-bodies'
        record['body_files'] = sorted(path.name for path in bodies.iterdir())
        app.unchanged(out)
        if app.inputs() != frozen:
            raise ValueError('probe inputs changed')
        owner = record['owner']
        checks = dict(owner_exit=owner['owner_status'] == 'EXITED_0',
                      identity=owner['identity']['status'] == 'MATCH',
                      teardown=owner['teardown'] == 'CLEAN', sealed=not errors,
                      usage=record['usage']['completeness'] == 'COMPLETE',
                      transcript_accounting=record['unchanged_accounting']['status'] == 'MATCH',
                      peer_policy=record['peer_policy']['status'] == 'MATCH',
                      catalog=record['catalogs'] == expected,
                      quota=not record['quota']['execution'],
                      index_present=(bodies / 'index.jsonl').is_file(),
                      response=record['response'] == 'NATIVE_PARENT_READY')
        record['checks'] = checks
        # Observed is not acceptance: native request/child coverage needs its independent audit.
        record['status'] = 'CAPTURE_OBSERVED' if all(checks.values()) else 'STOP'
    except (OSError, ValueError, KeyError, TypeError, RuntimeError, subprocess.SubprocessError) as exc:
        record['error'] = f'{type(exc).__name__}: {exc}'
    finally:
        record['ended_at'] = time.time()
        with (root / f'result-{name}.json').open('x') as stream:
            json.dump(record, stream, indent=2)
    print(json.dumps({'name': name, 'status': record['status']}))
    return 0 if record['status'] == 'CAPTURE_OBSERVED' else 2


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('runtime', type=Path)
    parser.add_argument('bindings', type=Path)
    args = parser.parse_args()
    raise SystemExit(run(args.runtime, args.bindings))
