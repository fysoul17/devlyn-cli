from pathlib import Path
from datetime import datetime, timezone
import ast
import hashlib
import json

ROOT = Path(__file__).resolve().parent
MAPS = {
    'OR1': [('recursive-ownership-boundaries', ['C1', 'C2']),
            ('open-transaction-refresh-isolation', ['C2', 'C6']),
            ('optimistic-conflict-preserves-loser', ['C2', 'C3', 'C4']),
            ('disjoint-rebase-preserves-deletions', ['C1', 'C3', 'C4']),
            ('overlap-rebase-is-atomic', ['C4', 'C6']),
            ('absent-delete-retains-write-intent', ['C4', 'C6']),
            ('failed-save-retry', ['C3', 'C5']),
            ('failed-read-rebase-recovery', ['C2', 'C4', 'C5']),
            ('atomic-backend-conflict-boundary', ['C3', 'C4', 'C5']),
            ('closed-lifecycle-and-durable-store', ['C2', 'C3', 'C5', 'C6'])],
    'OR2': [('coalescing-and-independent-keys', ['C1']),
            ('recursive-result-and-backend-isolation', ['C1', 'C2']),
            ('one-waiter-cancellation-isolation', ['C1', 'C4']),
            ('sole-waiter-cancel-and-rejoin', ['C1', 'C4']),
            ('stale-success-keeps-new-flight', ['C1', 'C3']),
            ('out-of-order-generations', ['C1', 'C3']),
            ('shared-failure-can-retry', ['C1', 'C5']),
            ('stale-failure-keeps-new-flight', ['C1', 'C3', 'C5']),
            ('backend-cancellation-can-retry', ['C1', 'C5']),
            ('shutdown-owns-retired-operations', ['C3', 'C6']),
            ('shutdown-awaits-cleanup', ['C6']),
            ('consumer-instance-isolation', ['C1', 'C3', 'C6'])],
}
GOALS = {
    'OR1': "Fix Folio workspace saves and recovery. Editors have seen local edits leak into snapshots, a failed save leave an editor unusable, and rebase lose unrelated changes. Repair the existing ownership, optimistic commit, and persistence recovery behavior described in docs/contract.md. Keep the public API and run python3 -B checks/run_checks.py; add focused coverage for the repaired paths.",
    'OR2': "Fix Relay's keyed loader. Cancelling a request, invalidating a key during a fetch, and retrying after backend failure can leave other requests or cached data in the wrong state. Repair the existing sharing, ownership, invalidation, recovery, and shutdown behavior described in docs/contract.md. Keep the public API and run python3 -B checks/run_checks.py; add focused coverage for the repaired paths.",
}
for task, rows in MAPS.items():
    path = ROOT / task
    contract = (path / 'visible/docs/contract.md').read_text()
    lines = contract.splitlines()
    citations = {}
    for index, line in enumerate(lines):
        if len(line) >= 4 and line[0] == 'C' and line[1].isdigit() and line[2:5] == ' — ':
            end = index + 1
            while end < len(lines) and lines[end]:
                end += 1
            citations[line[:2]] = {'path': 'visible/docs/contract.md', 'start_line': index + 1, 'end_line': end, 'quote': '\n'.join(lines[index:end])}
    oracle_tree = ast.parse((path / 'hidden/oracle.py').read_text())
    oracle_names = next(ast.literal_eval(node.value) for node in oracle_tree.body if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == 'NAMES' for target in node.targets))
    assert oracle_names == [name for name, clauses in rows]
    task_json = dict(id=task, format='confirmation-v1', goal=GOALS[task], language='python', runtime='Python 3.11+ standard library',
        visible_files=['visible/' + str(file.relative_to(path / 'visible')) for file in sorted((path / 'visible').rglob('*')) if file.is_file()],
        allowed=[('visible/folio/**' if task == 'OR1' else 'visible/relay/**'), 'visible/checks/**'],
        public_command=['python3', '-B', 'checks/run_checks.py'], public_checks=['cd visible && python3 -B checks/run_checks.py'],
        oracle_command=['python3', '-B', 'hidden/oracle.py', '<visible-root>'], oracle=oracle_names,
        gold_reference='gold/', oracle_exit_semantics='0 = valid per-manifestation result (including product failures); nonzero = oracle/apparatus failure. The 0237 last_json parser discards JSON on nonzero exit.')
    (path / 'task.json').write_text(json.dumps(task_json, indent=2) + '\n')
    (path / 'contract-map.json').write_text(json.dumps({'scope': 'Only public APIs, public backend protocol, files addressed through public FileStore(path), and asyncio events/futures are exercised. No private implementation state is read or altered.', 'manifestations': [{'id': name, 'contract': [citations[clause] for clause in clauses]} for name, clauses in rows]}, indent=2) + '\n')

prediction = {
    'recorded_at': datetime.now(timezone.utc).isoformat(),
    'principles': ['No guesswork: predictions precede execution.', 'No workaround: semantic contracts are evaluated via public boundaries.', 'No overengineering: two compact standard-library packages.', 'Production ready: failures must preserve recoverability.'],
    'commands': ['python3 -B calibrate.py'],
    'expected': {
        'OR1': {'baseline_public': True, 'gold_public': True, 'baseline_pass': ['open-transaction-refresh-isolation', 'closed-lifecycle-and-durable-store'], 'gold_pass': [name for name, clauses in MAPS['OR1']], 'fault_control_fail': ['recursive-ownership-boundaries']},
        'OR2': {'baseline_public': True, 'gold_public': True, 'baseline_pass': ['coalescing-and-independent-keys', 'stale-failure-keeps-new-flight', 'shutdown-awaits-cleanup', 'consumer-instance-isolation'], 'gold_pass': [name for name, clauses in MAPS['OR2']], 'fault_control_fail': ['stale-success-keeps-new-flight', 'out-of-order-generations']},
    },
    'fault_controls': {'OR1': 'Gold put retains the supplied document instead of taking its recursive copy.', 'OR2': 'Gold _load publishes a retired successful result by dropping its generation publication guard.'},
    'determinism': 'Event handshakes and explicitly settled futures control asynchronous order. Three-second per-scenario watchdogs detect deadlocks; success does not depend on elapsed time. Each oracle runs in a fresh interpreter; evaluated trees are read only.',
}
calibration = ROOT / 'calibration'
calibration.mkdir(exist_ok=True)
prediction_path = calibration / 'prediction.json'
if prediction_path.exists():
    raise SystemExit('refusing to rewrite prospective prediction')
prediction_path.write_text(json.dumps(prediction, indent=2) + '\n')
print('Wrote task metadata, exact contract quotations, and prospective prediction.')
