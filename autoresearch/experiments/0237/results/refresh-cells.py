"""Refresh derived 0237 cells.json/cells.md from final verdicts only; no execution or regrading."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def read(path):
    return json.loads(path.read_text())


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def tree(root):
    result = {}
    for path in sorted(root.rglob('*')):
        name = path.relative_to(root)
        if name.parts[0] in ('.git', '.devlyn'):
            continue
        if path.is_symlink():
            result[str(name)] = 'link:' + str(path.readlink())
        elif path.is_file():
            result[str(name)] = f'{digest(path)}:{path.stat().st_mode & 0o777:o}'
    return result


def link(path):
    return dict(path=str(path), sha256=digest(path)) if path.is_file() else None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--live', type=Path, default=Path('/Users/aipalm/.local/share/nx01/0237-live'))
    args = parser.parse_args()
    live = args.live.resolve()
    runtime_path = live / 'runtime-discovery-max.json'
    runtime = read(runtime_path)
    tasks_path = Path(runtime['tasks_file'])
    tasks = {task['id']: task for task in read(tasks_path)['tasks']}
    out = Path(runtime['output'])
    journals = [live / 'dispatch-discovery.jsonl', live / 'dispatch-discovery-af1.jsonl']
    events = {}
    for journal in journals:
        for line in journal.read_text().splitlines():
            event = json.loads(line)
            if event.get('cell'):
                events.setdefault(event['cell'], {})[event['event']] = event
    rows = []
    for verdict_path in sorted(out.glob('verdict-d*.json')):
        verdict = read(verdict_path)
        if verdict['task'] not in ('EQ3-UA1', 'EQ3-AF1'):
            continue
        cell = out / verdict['cell']
        plan, baseline, seal = (read(cell / name) for name in ('plan.json', 'baseline.json', 'seal.json'))
        row = {key: verdict.get(key) for key in (
            'cell', 'task', 'arm', 'config', 'status', 'reason', 'owner_status', 'owner_seconds',
            'run_and_checks_seconds', 'deterministic_seconds', 'input_tokens', 'output_tokens',
            'usage', 'usage_gaps', 'known_usage_lower_bound', 'source_check_pass', 'delivery_pass',
            'public_pass', 'oracle', 'scope_violations', 'changed', 'assessment', 'identity', 'teardown')}
        row['task_disposition'] = ('EXCLUDED_ORACLE_CONTRACT' if row['task'] == 'EQ3-UA1'
                                   else 'AVAILABLE_DIAGNOSTIC_NO_CANDIDATE_DECISION')
        row['registered_route'] = dict(model=plan['model'], effort=plan['effort'])
        row['protocol_measurement_eligible'] = verdict.get('measurement_eligible')
        row['source'] = dict(baseline_commit=baseline['allocation_sha'],
                            selected_snapshot=verdict.get('snapshot'), delivery=verdict.get('delivery'))
        row['dispatcher_events'] = events.get(row['cell'], {})
        if {'START', 'FINISH'} <= row['dispatcher_events'].keys():
            times = row['dispatcher_events']
            row['dispatcher_elapsed_seconds_not_owner_time'] = (
                datetime.fromisoformat(times['FINISH']['time']) -
                datetime.fromisoformat(times['START']['time'])).total_seconds()
        names = ['baseline.json', 'seal.json', 'usage.json', 'run/result.json', 'checks.json',
                 'checks-raw.json', 'checked.json', 'delivery.json', 'snapshot.json', 'evidence.manifest.json']
        row['evidence'] = {name: link(cell / name) for name in names}
        row['evidence']['verdict'] = link(verdict_path)
        row['usage_detail'] = read(cell / 'usage.json') if (cell / 'usage.json').exists() else None
        row['input_bindings'] = {str(path): dict(sealed_sha256=seal['inputs'].get(str(path)),
            current_sha256=digest(path)) for path in (
                runtime_path, tasks_path, Path(runtime['control'] + '.manifest.json'))}
        row['baseline_tasks_sha256_note'] = dict(value=baseline.get('tasks_sha256'),
            meaning='Inherited prepare field hashes sibling tasks.json; selected tasks are bound by seal.inputs above.')
        if (cell / 'checked.json').is_file():
            checked = read(cell / 'checked.json')
            actual = tree(cell / 'snapshot')
            row['checked_binding'] = dict(snapshot_matches=actual == checked['snapshot'],
                checks_match=digest(cell / 'checks.json') == checked['checks_sha256'],
                delivery_match=digest(cell / 'delivery.json') == checked['delivery_sha256'])
            if row['task'] == 'EQ3-AF1':
                original = {n: h for n, h in baseline['files'].items() if n.startswith('visible/')}
                changed = sorted(n for n, h in original.items() if actual.get(n) != h)
                added = sorted(n for n in actual if n.startswith('visible/') and n not in original)
                protected = [n for n in original if n.startswith('visible/qa/') or
                             n == 'visible/matching/crossmatch_reserver.py']
                predicates = {n: dict(baseline=original[n], evaluated=actual.get(n),
                                     unchanged=actual.get(n) == original[n]) for n in protected}
                oracle = Path(runtime['control']) / 'oracle/eq3/EQ3-AF1/oracle.py'
                manifest = read(Path(runtime['control'] + '.manifest.json'))
                row['af1_predicate_integrity'] = dict(
                    status='UNCHANGED' if all(p['unchanged'] for p in predicates.values()) else 'REQUIRES_SOURCE_REVIEW',
                    protected_files=predicates, changed_existing_visible=changed, added_visible=added,
                    baseline_matches_registered_source=all(
                        original.get(n, '').split(':')[0] == h for n, h in tasks[row['task']]['source_sha256'].items()),
                    hidden_oracle=link(oracle), hidden_oracle_matches_control_manifest=(
                        digest(oracle) == manifest['manifests']['oracle']['eq3/EQ3-AF1/oracle.py']))
        rows.append(row)
    finished = {row['cell'] for row in rows}
    unfinished = []
    for line in (live / 'cells-discovery-af1.tsv').read_text().splitlines():
        name, task, arm, config = line.split('\t')
        if name not in finished:
            unfinished.append(dict(cell=name, task=task, arm=arm, config=config,
                status='START_RECORDED_NO_FINAL_VERDICT' if 'START' in events.get(name, {}) else 'NO_START_OR_FINAL_VERDICT',
                outcome=None, costs=None))
    result = dict(schema='0237-derived-cells-v1', generated_at=datetime.now(timezone.utc).isoformat(),
        candidate_decision='NOT_MADE_BY_THIS_SUMMARY', runtime=link(runtime_path), tasks=link(tasks_path),
        control_manifest=link(Path(runtime['control'] + '.manifest.json')), image=runtime['image'],
        accounting='Input is processed input inclusive of cache; output already includes reasoning. Not billed tokens or dollars. '
                   'Owner totals include recorded native children; research assessors are separate. Missing costs remain unknown.',
        endpoint='Source checks plus local commit matching the assessed source; not PR/merge or full North Star delivery.',
        exclusions=dict(UA1='Entire task excluded by oracle-contract audit; all five raw verdicts and costs retained.',
                        MI1_BD1='Retired before measured dispatch; not missing successful cells.'),
        owner_time_note='Use owner_seconds, not dispatcher START/FINISH elapsed. review-boundary.jsonl records a dispatcher-only hold.',
        review_boundary=link(live / 'review-boundary.jsonl'), oracle_audit_hold=link(live / 'halt-discovery-oracle-audit.json'),
        cells=rows, unfinished_af1=unfinished)
    (HERE / 'cells.json').write_text(json.dumps(result, indent=2) + '\n')
    text = ['# 0237 completed-cell evidence', '', f"As of {result['generated_at']}. Derived from final verdict files only; no regrading or C admission/rejection.", '',
        'UA1 is excluded as a whole because of unsupported oracle requirements. Its five raw outcomes and charged attempts remain below. AF1 rows are available diagnostics, not a claim of general correctness. Missing final verdicts have no outcome or cost assigned.', '',
        'A is native CLI; B is installed 4.2.3; C adds the caller/consumer contract-discovery sentence. The separately admitted helper/docs fixes did not change these frozen measured packages.', '',
        '| Cell | Raw status | Source / local delivery | Hidden rows | Owner s | Input incl. cache | Output | Usage |',
        '| --- | --- | --- | --- | --- | --- | --- | --- |']
    for row in rows:
        oracle = ', '.join(x['id'] + '=' + x['status'] for x in row.get('oracle') or []) or 'unknown'
        if row.get('oracle') and all(x['status'] == 'PASS' for x in row['oracle']):
            oracle = f"{len(row['oracle'])}/{len(row['oracle'])} PASS"
        seconds = f"{row['owner_seconds']:.3f}" if row['owner_seconds'] is not None else 'unknown'
        costs = [f'{row[key]:,}' if row[key] is not None else 'unknown' for key in ('input_tokens', 'output_tokens')]
        flag = lambda value: 'PASS' if value is True else 'FAIL' if value is False else 'unknown'
        text.append(f"| [{row['cell']}]({row['evidence']['verdict']['path']}) | {row['status']} | "
                    f"{flag(row['source_check_pass'])} / {flag(row['delivery_pass'])} | {oracle} | {seconds} | "
                    f"{costs[0]} | {costs[1]} | {row['usage']} |")
    text += ['', 'Not finalized (excluded from the table, never inferred to pass): ' +
             (', '.join(f"`{r['cell']}` ({r['status']})" for r in unfinished) or 'none') + '.', '',
             '## Source and predicate integrity', '']
    for row in rows:
        audit = row.get('af1_predicate_integrity')
        if not audit:
            continue
        text.append(f"- `{row['cell']}`: original QA files and `matching/crossmatch_reserver.py`: **{audit['status']}**. "
                    f"Changed existing visible files: {', '.join(audit['changed_existing_visible']) or 'none'}. "
                    f"Added: {', '.join(audit['added_visible']) or 'none'}. "
                    f"Evaluated snapshot/check/delivery binding: {row['checked_binding']}. "
                    f"Baseline matches registered source: {audit['baseline_matches_registered_source']}; hidden oracle matches control: {audit['hidden_oracle_matches_control_manifest']}.")
    text += ['', 'The d13 through d18 source diffs were also read: all implement hold recording and expiry reconciliation; none replaces or changes the evaluated predicates. d14 adds `qa/run_expiry_checks.py`; d16 and d18 add `qa/test_hold_intake.py`. These assert behavior through the original consumers. Any later modified predicate requires independent review before using its result. See [AF1 source audit](af1-source-audit.md) for final resource ratios and [helper accounting audit](af1-helper-audit.md) for bounded interpretation.', '',
        '## Accounting and provenance', '', result['accounting'], '', result['endpoint'], '',
        'Dispatcher timestamps can include parent holds. The recorded d14 review hold began 03:22:29 UTC and resumed 03:40:42 UTC; its owner_seconds comes from the completed child run and does not include the subsequent dispatcher wait. Do not substitute dispatcher elapsed time.', '',
        f"[Runtime]({runtime_path}), [selected tasks]({tasks_path}), [control manifest]({runtime['control']}.manifest.json), "
        f"[review hold/resume]({live / 'review-boundary.jsonl'}), [UA1 exclusion](eq3-contract-audit-ua1.md). "
        '[cells.json](cells.json) retains per-cell source, oracle, usage breakdown, delivery, seal/checked hashes and raw evidence links. The inherited baseline tasks_sha256 labels sibling tasks.json; selected-task identity is taken from seal.inputs, not that field.', '',
        'This report excludes smoke/advice costs from measured-cell comparisons; their separate retained outcomes, including ultra cancellation/partial usage, remain unchanged. No cross-engine aggregate or candidate decision is computed.', '',
        'Refresh after later final verdicts: `python3 -B autoresearch/experiments/0237/results/refresh-cells.py`. It reads completed evidence and writes only cells.json/cells.md.', '']
    (HERE / 'cells.md').write_text('\n'.join(text))
    print(json.dumps(dict(completed=len(rows), excluded_ua1=sum(r['task'] == 'EQ3-UA1' for r in rows),
                          completed_af1=sum(r['task'] == 'EQ3-AF1' for r in rows), unfinished_af1=len(unfinished))))


if __name__ == '__main__':
    main()
