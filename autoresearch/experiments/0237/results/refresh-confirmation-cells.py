"""Derive confirmation ledgers from final verdict-f*.json; never run models or regrade."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
import runpy

HERE = Path(__file__).resolve().parent
COMMON = runpy.run_path(str(HERE / 'refresh-cells.py'))
read, digest, tree, link = (COMMON[key] for key in ('read', 'digest', 'tree', 'link'))
COSTS = ('owner_seconds', 'input_tokens', 'output_tokens')


def binding(path, expected):
    actual = digest(path) if path.is_file() else None
    return dict(path=str(path), recorded_sha256=expected, current_sha256=actual,
                matches=expected is not None and actual == expected)


def load_recovery(path, slots, out):
    if not path.is_file():
        return None, {}
    record = read(path)
    replacements = record['replacements']
    if record['schema'] != '0237-confirmation-recovery-v1' or len(replacements) != 1:
        raise ValueError('Only the registered single authentication recovery is supported')
    original, replacement = next(iter(replacements.items()))
    scheduled = {s['cell']: s for s in slots}
    if original not in scheduled or replacement != original + '-auth1' or replacement in scheduled:
        raise ValueError('Invalid authentication recovery identity')
    slot = scheduled[original]
    guard = binding(Path(record['guard_evidence']), record['guard_sha256'])
    resume = binding(Path(record['resume_schedule']), record['resume_schedule_sha256'])
    remaining = [s for s in slots if s['schedule'] == slot['schedule']]
    remaining = remaining[remaining.index(slot):]
    expected = [[replacements.get(s['cell'], s['cell']), s['task'], s['arm'], s['config']] for s in remaining]
    actual = [line.split('\t') for line in Path(record['resume_schedule']).read_text().splitlines()] if resume['matches'] else None
    problems = []
    if not guard['matches'] or Path(record['guard_evidence']).resolve() != (out / ('not-dispatched-' + original + '.json')).resolve():
        problems.append('Original not-dispatched guard is missing, changed, or belongs to another cell.')
    if not resume['matches'] or actual != expected:
        problems.append('Resume schedule does not preserve the original remaining task/arm/engine order.')
    original_final = (out / ('verdict-' + original + '.json')).is_file()
    if original_final:
        problems.append('Original recovery cell has a final verdict; retain every attempt cost and do not complete this slot.')
    return dict(artifact=link(path), record=record, guard_binding=guard, resume_schedule_binding=resume,
                remaining_order_matches=actual == expected, original_final_present=original_final,
                status='MATCH' if not problems else 'REQUIRES_REVIEW', findings=problems), {replacement: slot}


def attempt_state(name, out, events, finalized):
    nondispatch = out / ('not-dispatched-' + name + '.json')
    state = dict(dispatcher_events=events.get(name, []), not_dispatched_evidence=link(nondispatch))
    if name in finalized:
        verdict = finalized[name]
        state.update(lifecycle='FINAL_VERDICT', status=verdict['status'])
        if 'reason' in verdict:
            state['reason'] = verdict['reason']
        return state
    state.update(status=None, outcome=None, costs=None)
    if nondispatch.is_file():
        return dict(state, lifecycle='NOT_DISPATCHED', reason=read(nondispatch))
    if any(e.get('event') == 'FINISH' for e in events.get(name, [])):
        return dict(state, lifecycle='UNKNOWN_FINAL_MISSING')
    if any(e.get('event') == 'START' for e in events.get(name, [])):
        return dict(state, lifecycle='PENDING_FINAL_VERDICT')
    return dict(state, lifecycle='NO_DISPATCH_RECORD')


def slot_state(slot, out, events, finalized, recovery, aliases):
    state = attempt_state(slot['cell'], out, events, finalized)
    replacement = next((name for name, original in aliases.items() if original['cell'] == slot['cell']), None)
    if replacement is None:
        return state
    retry = attempt_state(replacement, out, events, finalized)
    state.update(original_attempt=dict(state), replacement_cell=replacement, replacement_attempt=retry)
    if retry['lifecycle'] != 'NO_DISPATCH_RECORD':
        state.pop('reason', None)
        if 'reason' in retry:
            state['reason'] = retry['reason']
    if recovery['status'] != 'MATCH':
        return dict(state, lifecycle='RECOVERY_REQUIRES_REVIEW', status=None, outcome=None, costs=None)
    if replacement in finalized:
        verdict = finalized[replacement]
        if any(verdict.get(k) != slot[k] for k in ('task', 'config', 'arm')):
            return dict(state, lifecycle='RECOVERY_REQUIRES_REVIEW', status=None, outcome=None, costs=None)
        state.pop('outcome', None)
        state.pop('costs', None)
        return dict(state, lifecycle='FINAL_VERDICT', status=verdict['status'], effective_cell=replacement)
    if retry['lifecycle'] != 'NO_DISPATCH_RECORD':
        state.update(lifecycle=retry['lifecycle'], status=None, outcome=None, costs=None)
    return state


def aggregate(task, config, arm, slots, finals):
    scheduled = [s for s in slots if (s['task'], s['config'], s['arm']) == (task, config, arm)]
    rows = [r for r in finals if (r['task'], r['config'], r['arm']) == (task, config, arm)]
    correct = sum(r['status'] == 'CHECKS_PASS' for r in rows)
    totals, lower_bounds = {}, {}
    for key in COSTS:
        values = [r.get(key) for r in rows]
        totals[key] = sum(values) if values and all(isinstance(v, (int, float)) for v in values) else None
        known = [r.get(key) if r.get(key) is not None else
                 (r.get('known_usage_lower_bound') or {}).get(key) for r in rows]
        lower_bounds[key] = sum(v for v in known if isinstance(v, (int, float))) if any(
            isinstance(v, (int, float)) for v in known) else None
    ready = bool(scheduled) and all(s['lifecycle'] == 'FINAL_VERDICT' for s in scheduled)
    clean = bool(rows) and all(r['integrity']['status'] == 'MATCH' for r in rows)
    usage = bool(rows) and all(r.get('usage') == 'COMPLETE' for r in rows)
    return dict(task=task, config=config, arm=arm, scheduled=len(scheduled), finalized_attempts=len(rows),
        recorded_correct_completions=correct, raw_status_counts=dict(Counter(r['status'] for r in rows)),
        lifecycle_counts=dict(Counter(s['lifecycle'] for s in scheduled)),
        all_scheduled_final=ready, all_final_integrity_matched=clean, all_final_usage_complete=usage,
        finalized_attempt_cost=totals, known_final_cost_lower_bound=lower_bounds,
        per_recorded_correct_final_attempt_cost={k: totals[k] / correct if correct and totals[k] is not None
                                               else None for k in COSTS},
        per_correct_note='Undefined with zero recorded successes or missing total cost; unfinished attempts are not zero-cost.',
        comparison_state='COMPLETE_GROUP_PENDING_BLOCK_REVIEW' if ready and clean and usage
                         else 'INCOMPLETE_OR_REQUIRES_REVIEW')


def inspect_final(path, runtime, tasks, manifest, scheduled, aliases=None):
    verdict = read(path)
    cell = Path(runtime['output']) / verdict['cell']
    row = dict(verdict)
    row['in_frozen_schedule'] = verdict['cell'] in scheduled
    slot = scheduled.get(verdict['cell']) or (aliases or {}).get(verdict['cell'])
    row['scheduled_cell'] = slot['cell'] if slot else None
    row['evidence'] = {name: link(cell / name) for name in (
        'plan.json', 'baseline.json', 'seal.json', 'run/result.json', 'usage.json',
        'snapshot.json', 'checked.json', 'checks.json', 'checks-raw.json', 'delivery.json',
        'evidence.manifest.json')}
    row['evidence']['verdict'] = link(path)
    problems = []
    if slot is None:
        problems.append('Final attempt is outside the frozen schedule; retain its full cost and review its authorization.')
    else:
        if any(verdict.get(k) != slot[k] for k in ('task', 'config', 'arm')):
            problems.append('Verdict identity disagrees with its scheduled cell.')
    for name in ('baseline.json', 'seal.json', 'checked.json'):
        if not (cell / name).is_file():
            problems.append('Missing ' + name + '; original status is retained.')
    if (cell / 'seal.json').is_file():
        seal = read(cell / 'seal.json')
        row['sealed_inputs'] = [binding(Path(p), h) for p, h in seal['inputs'].items()]
        row['prepared_bindings'] = [binding(cell / p, h) for p, h in seal['prepared'].items()]
        if not all(b['matches'] for b in row['sealed_inputs'] + row['prepared_bindings']):
            problems.append('Sealed input or prepared metadata changed/missing.')
    if (cell / 'usage.json').is_file():
        row['usage_detail'] = read(cell / 'usage.json')
    if (cell / 'baseline.json').is_file():
        baseline = read(cell / 'baseline.json')
        legacy = HERE.parent / 'tasks.json'
        row['baseline_tasks_hash'] = binding(legacy, baseline.get('tasks_sha256'))
        row['baseline_tasks_hash']['meaning'] = 'Legacy prepare field refers to sibling tasks.json; selected tasks are bound by seal.inputs.'
        row['baseline_commit'] = baseline.get('allocation_sha')
    else:
        baseline = None
    if (cell / 'checked.json').is_file():
        checked = read(cell / 'checked.json')
        actual = tree(cell / 'snapshot')
        row['checked_binding'] = dict(snapshot_matches=actual == checked['snapshot'],
            checks=binding(cell / 'checks.json', checked['checks_sha256']),
            delivery=binding(cell / 'delivery.json', checked['delivery_sha256']))
        if not (row['checked_binding']['snapshot_matches'] and row['checked_binding']['checks']['matches']
                and row['checked_binding']['delivery']['matches']):
            problems.append('Evaluated snapshot/checks/delivery binding changed/missing.')
        if baseline is not None:
            original = {n: h for n, h in baseline['files'].items() if n.startswith('visible/')}
            protected = {n: dict(baseline=h, evaluated=actual.get(n), unchanged=actual.get(n) == h)
                         for n, h in original.items() if n.startswith(('visible/checks/', 'visible/qa/'))}
            registered = tasks.get(verdict['task'], {}).get('source_sha256')
            baseline_match = registered is not None and {n: h.split(':')[0] for n, h in original.items()} == registered
            row['source_audit'] = dict(baseline_matches_registered_source=baseline_match,
                changed_existing_visible=sorted(n for n, h in original.items() if actual.get(n) != h),
                added_visible=sorted(n for n in actual if n.startswith('visible/') and n not in original),
                existing_qa=protected, existing_qa_unchanged=all(v['unchanged'] for v in protected.values()),
                note='Byte audit only. Modified public QA requires source review; no oracle is rerun or verdict relabeled.')
            if not baseline_match:
                problems.append('Baseline visible source does not match the selected task registration.')
            if not row['source_audit']['existing_qa_unchanged']:
                problems.append('Existing public QA changed; independent review required before interpreting a pass.')
    oracle_name = 'eq3/' + verdict['task'] + '/oracle.py'
    if oracle_name in manifest['manifests']['oracle']:
        row['hidden_oracle_binding'] = binding(Path(runtime['control']) / 'oracle' / oracle_name,
                                              manifest['manifests']['oracle'][oracle_name])
        if not row['hidden_oracle_binding']['matches']:
            problems.append('Hidden oracle changed/missing.')
    row['integrity'] = dict(status='MATCH' if not problems else 'REQUIRES_REVIEW', findings=problems)
    return row


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime', type=Path, default=Path('/Users/aipalm/.local/share/nx01/0237-live/runtime-confirmation-max.json'))
    args = parser.parse_args()
    runtime_path = args.runtime.resolve()
    runtime, freeze_path = read(runtime_path), HERE / 'confirmation-registration-freeze.json'
    freeze = read(freeze_path)
    frozen_bindings = [binding(Path(p), h) for p, h in freeze['files'].items()]
    tasks_path = Path(runtime['tasks_file'])
    tasks = {t['id']: t for t in read(tasks_path)['tasks']}
    control_manifest = Path(runtime['control'] + '.manifest.json')
    manifest = read(control_manifest)
    schedules = [Path(p) for p in freeze['files'] if Path(p).name.startswith('cells-confirmation-') and p.endswith('.tsv')]
    slots = []
    for schedule in schedules:
        for line in schedule.read_text().splitlines():
            name, task, arm, config = line.split('\t')
            slots.append(dict(cell=name, task=task, arm=arm, config=config, schedule=str(schedule)))
    scheduled = {s['cell']: s for s in slots}
    if len(scheduled) != len(slots):
        raise ValueError('Duplicate cell identity in registered schedules')
    journals = sorted(runtime_path.parent.glob('dispatch-confirmation-*.jsonl'))
    events, journal_warnings = {}, []
    for journal in journals:
        lines = journal.read_text().splitlines()
        for number, line in enumerate(lines, 1):
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                if number != len(lines):
                    raise
                journal_warnings.append(f'{journal}:{number}: trailing partial record ignored; refresh later.')
                continue
            if event.get('cell'):
                events.setdefault(event['cell'], []).append(event)
    out = Path(runtime['output'])
    recovery, aliases = load_recovery(HERE / 'confirmation-recovery.json', slots, out)
    finals = [inspect_final(p, runtime, tasks, manifest, scheduled, aliases) for p in sorted(out.glob('verdict-f*.json'))]
    if recovery and recovery['status'] != 'MATCH':
        affected = set(aliases) | {s['cell'] for s in aliases.values()}
        for row in finals:
            if row['cell'] in affected:
                row['integrity']['status'] = 'REQUIRES_REVIEW'
                row['integrity']['findings'].extend(recovery['findings'])
    finalized = {r['cell']: r for r in finals}
    for slot in slots:
        slot.update(slot_state(slot, out, events, finalized, recovery, aliases))
    groups = sorted({(s['task'], s['config'], s['arm']) for s in slots + finals})
    aggregates = [aggregate(*group, slots, finals) for group in groups]
    blocks = []
    for task in sorted({s['task'] for s in slots}):
        block = [s for s in slots if s['task'] == task]
        done = sum(s['lifecycle'] == 'FINAL_VERDICT' for s in block)
        blocks.append(dict(task=task, scheduled=len(block), finalized=done,
            state='COMPLETE_PENDING_ROOT_REVIEW' if done == len(block) else 'INCOMPLETE_NO_DECISION',
            conditional=task != 'CF-CONFIG'))
    result = dict(schema='0237-confirmation-ledger-v1', generated_at=datetime.now(timezone.utc).isoformat(),
        decision='NOT_MADE_BY_DERIVED_LEDGER', runtime=link(runtime_path), tasks=link(tasks_path),
        control_manifest=link(control_manifest), image=runtime['image'], registration_freeze=link(freeze_path),
        frozen_registration_bindings=frozen_bindings, schedules=[link(p) for p in schedules],
        authentication_recovery=recovery,
        schedule_note='Full two-task fixed schedule retained. CF-LEASE is conditional; E1/B5 controls remain conditional in confirmation-registration.md.',
        journals=[link(p) for p in journals], journal_warnings=journal_warnings, blocks=blocks,
        accounting='All finalized attempts, including failures and recorded native children, remain charged. '
                   'Input includes cache; output includes reasoning. Costs are not billed tokens/dollars. '
                   'Use owner_seconds, not dispatcher elapsed; holds can delay FINISH. Research assessors are separate.',
        endpoint='Recorded source/oracle checks plus matching local commit; no PR/merge or general-correctness claim.',
        cells=finals, scheduled_cells=slots, aggregates=aggregates)
    (HERE / 'confirmation-cells.json').write_text(json.dumps(result, indent=2) + '\n')
    lines = ['# Confirmation evidence ledger', '', f"As of {result['generated_at']}. Final verdicts only; no regrading or admission decision.", '',
        result['accounting'], '', result['endpoint'], '',
        '| Block | Final / scheduled | State |', '| --- | ---: | --- |']
    lines += [f"| {b['task']} | {b['finalized']}/{b['scheduled']} | {b['state']} |" for b in blocks]
    lines += ['', '| Final cell | Raw status | Source / delivery | Owner s | Input incl. cache | Output | Usage | Integrity |',
              '| --- | --- | --- | ---: | ---: | ---: | --- | --- |']
    def fmt(value):
        return 'unknown' if value is None else f'{value:,.3f}' if isinstance(value, float) else f'{value:,}'
    for r in finals:
        checks = ' / '.join('PASS' if r.get(k) is True else 'FAIL' if r.get(k) is False else 'unknown'
                            for k in ('source_check_pass', 'delivery_pass'))
        lines.append(f"| [{r['cell']}]({r['evidence']['verdict']['path']}) | {r['status']} | {checks} | " +
                     ' | '.join(fmt(r.get(k)) for k in COSTS) + f" | {r.get('usage', 'UNKNOWN')} | {r['integrity']['status']} |")
    lines += ['', '| Task / engine / arm | Final attempts / scheduled | Recorded correct | Total owner s / input / output | Per recorded correct s / input / output |',
              '| --- | ---: | ---: | --- | --- |']
    for a in aggregates:
        total = ' / '.join(fmt(a['finalized_attempt_cost'][k]) for k in COSTS)
        per = ' / '.join(fmt(a['per_recorded_correct_final_attempt_cost'][k]) for k in COSTS)
        lines.append(f"| {a['task']} / {a['config']} / {a['arm']} | {a['finalized_attempts']}/{a['scheduled']} | "
                     f"{a['recorded_correct_completions']} | {total} | {per} |")
    lines += ['', 'Totals include final attempts only and are provisional until the block completes. Unknown costs and zero-success denominators stay undefined. '
              'Recorded correct means the original CHECKS_PASS status; an integrity/QA finding requires review and does not silently alter that status.', '',
              'Slots without an accepted final identity:', '']
    lines += [f"- `{s['cell']}`: {s['lifecycle']}; outcome/cost unknown." for s in slots if s['lifecycle'] != 'FINAL_VERDICT'] or ['None.']
    if recovery:
        original, replacement = next(iter(recovery['record']['replacements'].items()))
        lines += ['', f"Authentication recovery: `{original}` → `{replacement}`; binding {recovery['status']}. "
                  f"[Recovery artifact]({recovery['artifact']['path']}). The original guard stays recorded; a never-dispatched cell has no measured owner cost, not a zero-cost completion. "
                  'Both final identities, if present, are charged and require review; they cannot complete one slot.']
    lines += ['', f"[Frozen full schedule]({freeze_path}) · [Registration]({HERE.parent / 'confirmation-registration.md'}) · "
              '[Detailed bindings, original verdicts, source/QA hashes and aggregates](confirmation-cells.json). '
              'Legacy baseline task hashes label sibling tasks.json; selected task identity comes from seal.inputs.', '',
              f"Frozen registration bindings: {'MATCH' if all(b['matches'] for b in frozen_bindings) else 'REQUIRES REVIEW'}. "
              'Existing QA is checked byte-for-byte. Added/changed production source still requires normal source review; this ledger runs no tests.', '',
              'Refresh explicitly: `python3 -B autoresearch/experiments/0237/results/refresh-confirmation-cells.py`.', '']
    (HERE / 'confirmation-cells.md').write_text('\n'.join(lines))
    print(json.dumps(dict(finalized=len(finals), scheduled=len(slots), blocks=blocks, journal_warnings=journal_warnings)))


if __name__ == '__main__':
    main()
