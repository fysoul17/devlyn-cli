"""Thin rp-d6 registration with the rp-d8 gate and pair-boundary renewal."""
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('runner_rpd8_stage', HERE / 'runner.py')
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)
legacy = runner.load('stage_rpd6_rpd8', HERE.parent / 'rp-d6-claude-delivery/stage.py')
gate = runner.load('gate_rpd8_stage', HERE / 'rendered_gate.py')
read, write, digest, require = runner.read, runner.write, runner.digest, runner.require
pack, auth = runner.prepare.pack, runner.auth
tree = legacy.tree
disjoint_auth, recorded_stage_root = legacy.disjoint_auth, legacy.recorded_stage_root
legacy.runner, legacy.pack, legacy.auth = runner, pack, auth
cache_input = legacy.cache_input


def token_gate_input(args):
    if args.phase == 'measured':
        previous = read(args.stage_dir / 'runtime-smoke.json')
        source, expected = Path(previous['token_gate']), previous['token_gate_sha256']
    elif args.smoke_attempt == 2:
        first = read(runner.smoke_registry(args.run_id) / 'attempt-1.json')
        previous = read(first['runtime'])
        source, expected = Path(previous['token_gate']), first['inputs']['token_gate_sha256']
    else:
        require(args.token_gate is not None, 'registration requires --token-gate')
        source, expected = Path(args.token_gate), None
    require(not source.is_symlink() and source.is_file(), 'token gate must be a regular file')
    binding = digest(source)
    require(expected is None or expected == binding, 'registered token gate changed')
    gate.validate(read(source), args.arms)
    return source.resolve(), binding


def reserve_smoke(args, guard, cache_sha256, gate_sha256):
    runner.smoke_slots(args.smoke_attempt)
    root = runner.smoke_registry(args.run_id)
    inputs = runner.smoke_inputs(dict(arms_file=args.arms, image=args.image,
        codex_account=auth.codex_account(args.auth), claude_account=guard['account'],
        models_cache_sha256=cache_sha256, token_gate_sha256=gate_sha256))
    previous = root / 'attempt-1.json'
    if args.smoke_attempt == 2:
        first = read(previous)
        runner.smoke_registration(read(first['runtime']))
        require(first['status'] == 'FAILED', 'spare requires a failed first smoke without credential revocation')
        require(first['inputs'] == inputs, 'spare changed registered inputs')
        for verdict in first['verdicts']:
            row = read(verdict)
            if row['dispatched']:
                receipt = row.get('repository_cleanup', {})
                require(receipt.get('repository') == f'fysoul17/rpd8-{args.run_id}-{row["cell"]}' and
                        receipt.get('status') == 'DELETED' and receipt.get('http_status') == 404 and
                        receipt.get('archive_manifest_sha256'), 'failed smoke lacks archived deletion/404 receipt')
    else:
        require(not previous.exists() and not (root / 'attempt-2.json').exists(), 'run already staged; never replay')
    state = dict(status='STAGING', inputs=inputs, runtime=str(args.stage_dir.resolve() / 'runtime-smoke.json'))
    if args.smoke_attempt == 2:
        state['previous_sha256'] = digest(previous)
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    path = root / f'attempt-{args.smoke_attempt}.json'
    with path.open('x') as stream:
        json.dump(state, stream, indent=2)
    return path, state


def renewal_allowed(previous, codex_account, claude_account, completed):
    require(codex_account == previous['codex_account'] and claude_account == previous['claude_account'],
            'renewal requires identical Codex and Claude accounts')
    count = len(completed)
    require(previous['phase'] == 'measured' and 0 < count < len(runner.SCHEDULE) and
            (count >= 16 or count % 2 == 0), 'renewal requires a completed pair or guard boundary')
    require(all(row['status'] in ('PASS', 'ADJUDICATE', 'PRODUCT_INCOMPLETE') and
                (row['config'] != 'claude' or row.get('effort_binding') == 'MATCH') and
                row.get('prompt_binding') == 'MATCH' for row in completed),
            'stopped schedule cannot renew or resume')


legacy.token_gate_input, legacy.reserve_smoke = token_gate_input, reserve_smoke
legacy.renewal_allowed = renewal_allowed
stage, renew, check, main = legacy.stage, legacy.renew, legacy.check, legacy.main

if __name__ == '__main__':
    main()
