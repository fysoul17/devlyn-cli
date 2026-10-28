"""Amendment 1: record an attempt whose driver died before its verdict as an archived STOP attempt.

Usage: amend1_record.py <runtime.json> <cell> <held directory> <teardown error>

<held directory> is the attempt's directory under the output root after its teardown was proved, set aside under
another name so the slot could rerun. This runs the recording that the owner lifecycle and run_cell.run did not
reach, with their own functions. It stages the verdict outside the archive pattern, then renames the attempt
<cell>.stop-N and publishes verdict-<cell>.stop-N.json. Every step rewrites its own files or is one rename, and a
staged verdict fixes N, so an interrupted run can be repeated. Run it only while no driver runs: its Driver instance
rewrites driver-status.json.
"""
import json
import sys
from pathlib import Path

EXPERIMENT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(EXPERIMENT))
import driver  # noqa: E402
import run_cell  # noqa: E402

lifecycle = run_cell.load('cell_init_v1', EXPERIMENT.parent / '0237/cell-init-v1.py')
REASON = 'host fault (amendment 1): '


def publish(log, held, staged):
    """The two final renames, in order. Repeating them after an interruption finishes the same suffix."""
    output = log.output
    attempt = staged.name.removeprefix('.amend1-verdict-').removesuffix('.json')  # <cell>.stop-N
    if (output / held).is_dir():
        (output / held).rename(output / attempt)
    if not (output / attempt).is_dir():
        raise SystemExit(f'{attempt}: archived directory missing; the staged verdict stays unpublished')
    verdict_path = output / f'verdict-{attempt}.json'
    staged.rename(verdict_path)
    verdict = json.loads(verdict_path.read_text())
    log.event('host_fault_recorded', cell=verdict['cell'], archived_as=attempt, verdict=verdict_path.name,
              amendment='amendment-1.md', usage=verdict['usage'], usage_lower_bound=verdict['usage_lower_bound'],
              owner_seconds=verdict['owner_seconds'])
    print(json.dumps({k: verdict[k] for k in ('cell', 'arm', 'owner_status', 'owner_seconds', 'usage',
                                               'usage_lower_bound', 'input_tokens', 'output_tokens',
                                               'evidence_manifest_sha256')}))


def record(runtime_path, name, held, error):
    log = driver.Driver(runtime_path, [])
    output = log.output
    staged = sorted(output.glob(f'.amend1-verdict-{name}.stop-*.json'))
    if staged:
        return publish(log, held, staged[0])
    out = output / held  # every recording function reads paths relative to the attempt, never its directory name
    started = json.loads((out / 'run/started.json').read_text())
    plan = json.loads((out / 'plan.json').read_text())
    preserved, tmp = out / 'host-fault-tmp', out / 'tmp'
    if not preserved.is_dir() and not (tmp.is_dir() and any(tmp.iterdir())):
        raise SystemExit(f'{held}: the preserved /tmp is missing')
    stdout = out / 'run/stdout'
    for number, line in enumerate(stdout.read_text().splitlines(), 1):  # blind.transcript's rule
        if line.strip():
            try:
                json.loads(line)
            except ValueError:
                raise SystemExit(f'{held}: malformed owner stream line {number}')
    try:
        identity = lifecycle.identity(out, plan)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        identity = dict(status='UNVERIFIED', violations=[f'identity check failed: {exc}'])
    if identity['status'] != 'MATCH':  # the registered latch acts before any archive
        log.latch_for(name, dict(status='STOP', owner_status='HOST_FAULT', identity=identity))
        raise SystemExit(f'{held}: identity {identity["status"]}; the run stops for an owner decision')
    if preserved.is_dir():  # one rename over the empty tmp/; rmdir refuses a populated one
        if tmp.exists():
            tmp.rmdir()
        preserved.rename(tmp)
    owner = dict(started, owner_status='HOST_FAULT', seconds=stdout.stat().st_mtime - started['started_at'],
                 teardown='FAILED', teardown_error=error, identity=identity)
    (out / 'run/result.json').write_text(json.dumps(owner, indent=2))
    (out / 'final.txt').write_text(lifecycle.base.final_message(lifecycle.lines(stdout), plan['engine']))
    sealed, collection_failures = run_cell.seal_after_teardown(out)
    if collection_failures:
        raise SystemExit(f'{held}: evidence collection failed: ' + '; '.join(collection_failures[:3]))
    recorded = run_cell.usage.record(out)
    session = run_cell.usage.evidence.inventory(out, plan)['claude_owner']['session']
    # The death leaves exactly one gap, the owner's missing result envelope; the transcript sum is then a lower bound.
    lower_bound = (recorded['completeness'] != 'COMPLETE'
                   and recorded['gaps'] == [f'Claude session {session} has no result envelope'])
    venue = json.loads((out / 'seal.json').read_text())['venue']
    verdict = dict(cell=name, task=plan['task'], arm=plan['arm'], config=plan['config'],
                   claude_limits_before=venue['claude_limits'], claude_account_before=venue['account'],
                   owner_status=owner['owner_status'], owner_seconds=owner['seconds'], teardown=owner['teardown'],
                   identity=identity, usage=recorded['completeness'], usage_lower_bound=lower_bound,
                   input_tokens=recorded['input_tokens'], output_tokens=recorded['output_tokens'],
                   quota=run_cell.quota.classify(out),
                   trace_bytes=sum(p.stat().st_size for p in (out / 'cell/trace').rglob('*') if p.is_file()),
                   evidence_manifest_sha256=sealed, collection_failures=collection_failures,
                   teardown_error=error, status='STOP', reason=REASON + error)
    try:
        verdict['diagnostics'] = run_cell.diagnostics.record(out)
    except (OSError, ValueError, TypeError, KeyError) as exc:
        verdict['diagnostics'] = dict(status='UNKNOWN', error=f'{type(exc).__name__}: {exc}')
    number = 1
    while (output / f'verdict-{name}.stop-{number}.json').exists() or (output / f'{name}.stop-{number}').exists():
        number += 1
    staged = output / f'.amend1-verdict-{name}.stop-{number}.json'
    run_cell.write_verdict(staged, verdict)  # returns 2 for any STOP; only the file shows it was written
    if not staged.is_file() or json.loads(staged.read_text()) != json.loads(json.dumps(verdict)):
        staged.unlink(missing_ok=True)
        raise SystemExit(f'{staged.name}: not written')
    publish(log, held, staged)


if __name__ == '__main__':
    if len(sys.argv) != 5:
        raise SystemExit(__doc__)
    record(*sys.argv[1:])
