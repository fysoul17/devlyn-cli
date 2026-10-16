"""Bound two-reviewer grading and the registered rp-d3 routing decision."""
import importlib.util
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('runner_rpd3_summary', HERE / 'runner.py')
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)
legacy = runner.load('summary_rpd2_rpd3', HERE.parent / 'rp-d2-report-lines/summarize.py')
base = legacy.legacy
base.runner = runner
github, read, write, require = base.github, base.read, base.write, base.require
REVIEWERS = base.REVIEWERS
aggregate = legacy.aggregate
checklist_for, review_template = base.checklist_for, base.review_template


def measured_records(output):
    schedule = read(output / 'rp-schedule.json')
    records = schedule['slots']
    if schedule.get('status') == 'PAUSED':
        require(schedule['phase'] == 'measured' and 0 < len(records) < 8 and len(records) % 2 == 0 and
                [(row['cell'], row['task'], row['config']) for row in records] == runner.SCHEDULE[:len(records)],
                'paused schedule must be a complete measured pair prefix')
        require(schedule['dispatched'] == len(records), 'paused schedule dispatch count mismatch')
        for row in records:
            require(row == read(output / row['cell'] / 'rp-verdict.json') and row['phase'] == 'measured' and
                    row['measurement_eligible'] is True and row['dispatched'] is True and
                    row['status'] in ('PASS', 'ADJUDICATE', 'PRODUCT_INCOMPLETE'), 'invalid paused verdict')
        # Missing slots are presentation-only NOT_RUN rows; never write or reserve them.
        records = list(records)
        for cell, task, config in runner.SCHEDULE[len(records):]:
            require(not (output / cell).exists() and not (output / f'verdict-{cell}.json').exists(),
                    'unrecorded attempt exists after paused prefix')
            arm = runner.arm_for(cell)
            records.append(dict(cell=cell, task=task, config=config, arm=arm, dispatched=False,
                status='NOT_RUN', delivery_assessment='NOT_ASSESSED',
                prompt_sha256=runner.prepare.PROMPT_SHA256[arm],
                release=dict(sha256=runner.prepare.pack.RELEASE_SHA256)))
    else:
        records = legacy.inherited_records(output)
    for row in records:
        arm = runner.arm_for(row['cell'])
        require(row['arm'] == arm and row['prompt_sha256'] == runner.prepare.PROMPT_SHA256[arm] and
                row['release']['sha256'] == runner.prepare.pack.RELEASE_SHA256,
                'schedule/verdict prompt/release binding mismatch')
    return records


base.measured_records = measured_records


def supported(row, category):
    return set(row['reviews']) == set(REVIEWERS) and all(
        grade['status'] in ('PASS', 'FAIL') and category not in grade['failed']
        for grade in row['reviews'].values())


def decision(slots, arms):
    ready = len(slots) == 8 and all(
        row['dispatched'] and row['runner_status'] not in ('STOP', 'UNKNOWN', 'NOT_RUN') and
        row['delivery_pass'] and set(row['reviews']) == set(REVIEWERS) and
        all(grade['status'] in ('PASS', 'FAIL') for grade in row['reviews'].values()) for row in slots)
    if not ready:
        return dict(decision='INCONCLUSIVE', follow_up=[],
                    reason='requires all eight dispatched, every delivery passed and both reviews adjudicated; STOP overrides')
    p0, p1 = arms['P0'], arms['P1']
    if p1['successes'] >= 3 and p0['successes'] <= 1:
        return dict(decision='PROMPT-SENSITIVE', reason='P1 report >= 3/4 and P0 report <= 1/4',
                    follow_up=['a registered benchmark-prompt change with its own Claude check (owner decision)'])
    if p0['successes'] <= 1 and p1['successes'] <= 1 and p1['cleanup_supported'] <= 1 and p1['reconciliation_supported'] <= 1:
        return dict(decision='NO RESCUE', reason='the historical outline survived the deletion',
                    follow_up=['a product reporting candidate'])
    follow = []
    if p0['successes'] >= 2:
        return dict(decision='MIXED', reason='no attribution', follow_up=[])
    elif p1['cleanup_supported'] >= 3 and p1['successes'] <= 2:
        follow.append('follow the category that still fails')
    elif p1['reconciliation_supported'] >= 3 and p1['cleanup_supported'] <= 1:
        follow.append('measure the rp-d2 Y cleanup paragraph with this sentence still absent')
    return dict(decision='MIXED', reason='every other pattern', follow_up=follow)


def summarize(output, reviews, checklists=None):
    result = legacy.inherited_summary(output, reviews, checklists)
    records = {row['cell']: row for row in measured_records(output)}
    slots = result['slots']
    for row in slots:
        record = records[row['cell']]
        row['arm'] = runner.arm_for(row['cell'])
        delivery = row.get('corrected_status', record['delivery_assessment'])
        row['delivery_pass'] = delivery in ('PASS', 'ADJUDICATE')
        for category in ('cleanup', 'reconciliation'):
            row[category + '_supported'] = supported(row, category)
    arms = {}
    for arm in ('P0', 'P1'):
        rows = [row for row in slots if row['arm'] == arm]
        arms[arm] = dict(aggregate(rows), **{key: sum(row[key] for row in rows)
                        for key in ('delivery_pass', 'cleanup_supported', 'reconciliation_supported')})
    pairs = [dict(pair=i + 1, task=slots[2 * i]['task'], outcomes=[{
        key: row[key] for key in ('cell', 'arm', 'status', 'delivery_pass', 'cleanup_supported', 'reconciliation_supported')}
        for row in slots[2 * i:2 * i + 2]]) for i in range(4)]
    return dict(schema='rp-d3-summary-v1', phase='measured', slots=slots, arms=arms, pairs=pairs,
                decision=decision(slots, arms))


def markdown(summary):
    table = legacy.inherited_markdown(dict(engines=summary['arms'], slots=summary['slots']))
    lines = [table, '', '| Arm | Delivery pass | Cleanup supported by both | Reconciliation supported by both |',
             '|---|---:|---:|---:|']
    for arm, row in summary['arms'].items():
        lines.append(f"| {arm} | {row['delivery_pass']}/4 | {row['cleanup_supported']}/4 | {row['reconciliation_supported']}/4 |")
    lines += ['', '| Pair | Task | Outcomes in dispatch order |', '|---|---|---|']
    for pair in summary['pairs']:
        outcomes = '; '.join(f"{row['cell']} {row['arm']}: {row['status']}, delivery={row['delivery_pass']}, "
                             f"cleanup={row['cleanup_supported']}, reconciliation={row['reconciliation_supported']}"
                             for row in pair['outcomes'])
        lines.append(f"| {pair['pair']} | {pair['task']} | {outcomes} |")
    result = summary['decision']
    lines += ['', result['decision'] + ': ' + result['reason']]
    lines += ['- Next: ' + follow for follow in result['follow_up']]
    return '\n'.join(lines)


base.summarize, base.markdown = summarize, markdown
main = base.main


if __name__ == '__main__':
    raise SystemExit(main())
