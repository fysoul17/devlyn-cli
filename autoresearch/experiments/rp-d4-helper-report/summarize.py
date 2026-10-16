"""Bound two-reviewer grading and the frozen rp-d4 ordered decision.

The inherited CLI accepts --review-template OUTPUT SLOT and
OUTPUT --review astra=DIR --review grok=DIR. Smoke is never graded or counted.
"""
import importlib.util
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('runner_rpd4_summary', HERE / 'runner.py')
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)
prior = runner.load('summary_rpd3_rpd4', HERE.parent / 'rp-d3-prompt-ablation/summarize.py')
legacy, base = prior.legacy, prior.base
base.runner = runner
github, read, write, require = base.github, base.read, base.write, base.require
REVIEWERS, CATEGORIES, METRICS = base.REVIEWERS, github.CATEGORIES, legacy.METRICS
aggregate = legacy.aggregate
checklist_for, review_template = base.checklist_for, base.review_template
inherited_grade_review = base.grade_review


def measured_records(output):
    schedule = read(output / 'rp-schedule.json')
    records = schedule['slots']
    if schedule.get('status') == 'PAUSED':
        require(schedule['phase'] == 'measured' and 0 < len(records) <= 8 and len(records) % 2 == 0 and
                [(row['cell'], row['task'], row['config']) for row in records] == runner.SCHEDULE[:len(records)],
                'paused schedule must be a complete measured pair prefix')
        require(schedule['dispatched'] == len(records), 'paused schedule dispatch count mismatch')
        for row in records:
            require(row == read(output / row['cell'] / 'rp-verdict.json') and row['phase'] == 'measured' and
                    row['measurement_eligible'] is True and row['dispatched'] is True and
                    row['status'] in ('PASS', 'ADJUDICATE', 'PRODUCT_INCOMPLETE'), 'invalid paused verdict')
        records = list(records)
        for cell, task, config in runner.SCHEDULE[len(records):]:
            require(not (output / cell).exists() and not (output / f'verdict-{cell}.json').exists(),
                    'unrecorded attempt exists after paused prefix')
            arm = runner.arm_for(cell)
            records.append(dict(cell=cell, task=task, config=config, arm=arm, dispatched=False,
                status='NOT_RUN', delivery_assessment='NOT_ASSESSED',
                prompt_sha256=runner.prepare.PROMPT_SHA256[arm]))
    else:
        records = legacy.inherited_records(output)
    releases = {}
    for row in records:
        arm = runner.arm_for(row['cell'])
        require(row['arm'] == arm and row['prompt_sha256'] == runner.prepare.PROMPT_SHA256[arm],
                'schedule/verdict arm/prompt binding mismatch')
        if row['dispatched']:
            release = row['release']
            require(release == releases.setdefault(arm, release), 'schedule/verdict release binding mismatch')
            if 'releases' in schedule:
                require(release == schedule['releases'][arm], 'schedule/registered release binding mismatch')
    return records


def grade_review(checklist, path, reviewer):
    """Retain FALSE separately without changing the inherited adjudication."""
    grade = inherited_grade_review(checklist, path, reviewer)
    if grade['status'] in ('PASS', 'FAIL'):
        review = read(path)
        grade['findings'] = {key: review['claims'][key]['finding'] for key in CATEGORIES}
    return grade


base.measured_records, base.grade_review = measured_records, grade_review
supported = prior.supported


def cost_gate(x, y):
    """0232 §6: compare all-attempt cost per success, including its zero rules."""
    if y['successes'] == 0:
        return dict(passes=False, strict_improvement=False, dominance=False,
                    reason='S_Y = 0: the candidate cannot pass the cost gate')
    if x['successes'] == 0:
        return dict(passes=True, strict_improvement=True, dominance=True,
                    reason='dominance over the zero-success control; no raw-sum comparison')
    costs = {key: dict(X=x['cost_per_success'][key], Y=y['cost_per_success'][key]) for key in METRICS}
    if any(not base.number(value) for metric in costs.values() for value in metric.values()):
        return dict(passes=None, strict_improvement=None, dominance=False,
                    reason='unknown per-success costs cannot establish the inequalities', metrics=costs)
    worse = [key for key, value in costs.items() if value['Y'] > value['X']]
    better = [key for key, value in costs.items() if value['Y'] < value['X']]
    strict = y['successes'] > x['successes'] or bool(better)
    return dict(passes=not worse, strict_improvement=strict, dominance=False, metrics=costs,
                reason='higher Y cost per success: ' + ', '.join(worse) if worse else
                       'strict improvement with every cost per success no higher' if strict else
                       'equal successes and all three costs tied')


def decision(slots, arms, guard_pass):
    ready = len(slots) == 10 and all(
        row['dispatched'] and row['runner_status'] not in ('STOP', 'UNKNOWN', 'NOT_RUN') and
        row['delivery_pass'] and row.get('merge_refused') is False and row['usage'] == 'COMPLETE' and
        set(row['reviews']) == set(REVIEWERS) and
        all(grade['status'] in ('PASS', 'FAIL') for grade in row['reviews'].values()) for row in slots)
    if not ready:
        return dict(decision='INCONCLUSIVE', follow_up=[], reason=
                    'requires all ten dispatched, every delivery passed and both reviews adjudicated; '
                    'STOP, UNKNOWN usage or merge_refused overrides')
    x, y = arms['X'], arms['Y']
    if x['cleanup_supported'] >= 2:
        return dict(decision='BASELINE MOVED', follow_up=[], reason='X cleanup >= 2/4; no adoption')
    if y['cleanup_supported'] <= 1:
        return dict(decision='REJECT', follow_up=[], reason='Y cleanup <= 1/4; product unchanged')
    no_false = not any(row['arm'] == 'Y' and any('FALSE' in grade['findings'].values()
                       for grade in row['reviews'].values()) for row in slots)
    conditions = dict(cleanup=y['cleanup_supported'] >= 3, no_y_false=no_false,
        other_categories=all(y[key + '_supported'] >= x[key + '_supported']
                             for key in CATEGORIES if key != 'cleanup'),
        successes=y['successes'] >= x['successes'], claude_guard=guard_pass)
    cost = cost_gate(x, y)
    result = dict(conditions=conditions, cost=cost, follow_up=[])
    if all(conditions.values()):
        if cost['passes'] is None:
            return dict(result, decision='INCONCLUSIVE', reason=cost['reason'])
        if cost['passes'] and cost['strict_improvement']:
            return dict(result, decision='ADOPT', reason='all registered adoption conditions hold')
        return dict(result, decision='HOLD', reason=cost['reason'] + '; owner decides the follow-up')
    if y['cleanup_supported'] >= 3 and y['reconciliation_supported'] < 4:
        result['follow_up'] = ['reconciliation is the next candidate']
    return dict(result, decision='MIXED', reason='an adoption condition other than cost or strict improvement failed')


def tallies(rows):
    return dict(aggregate(rows), delivery_pass=sum(row['delivery_pass'] for row in rows),
                **{category + '_supported': sum(row[category + '_supported'] for row in rows)
                   for category in CATEGORIES})


def summarize(output, reviews, checklists=None):
    result = legacy.inherited_summary(output, reviews, checklists)
    records = {row['cell']: row for row in measured_records(output)}
    slots = result['slots']
    for row in slots:
        record = records[row['cell']]
        row['arm'] = runner.arm_for(row['cell'])
        row['merge_refused'] = record.get('merge_refused')
        delivery = row.get('corrected_status', record['delivery_assessment'])
        effective = row.get('corrected_status', record['status'])
        row['delivery_pass'] = (delivery in ('PASS', 'ADJUDICATE') and effective in ('PASS', 'ADJUDICATE') and
            record.get('inherited_status') not in ('PRODUCT_INCOMPLETE', 'STOP', 'UNKNOWN') and
            not row['merge_refused'])
        if row['merge_refused'] or row['status'] == 'SUCCESS' and not row['delivery_pass']:
            row.update(status='FAILED', failure='product')
        for category in CATEGORIES:
            row[category + '_supported'] = supported(row, category)
    measured = [row for row in slots if row['config'] == 'codex']
    arms = {arm: tallies([row for row in measured if row['arm'] == arm]) for arm in ('X', 'Y')}
    pairs = [dict(pair=i + 1, task=measured[2 * i]['task'],
        arms={arm: tallies([row for row in measured[2 * i:2 * i + 2] if row['arm'] == arm]) for arm in ('X', 'Y')},
        outcomes=[{key: row[key] for key in ('cell', 'arm', 'status', 'delivery_pass',
                  *(category + '_supported' for category in CATEGORIES))}
                  for row in measured[2 * i:2 * i + 2]]) for i in range(4)]
    guards = [row for row in slots if row['config'] == 'claude']
    guard = dict(passed=len(guards) == 2 and all(all(row[key + '_supported'] for key in CATEGORIES)
                                             for row in guards),
                 slots=[row['cell'] for row in guards], **tallies(guards))
    return dict(schema='rp-d4-summary-v1', phase='measured', slots=slots, arms=arms, pairs=pairs, guard=guard,
                decision=decision(slots, arms, guard['passed']))


def markdown(summary):
    lines = [legacy.inherited_markdown(dict(engines=summary['arms'], slots=summary['slots'])), '',
             '| Arm | Delivery pass | Cleanup | Verification | Merge | Reconciliation |',
             '|---|---:|---:|---:|---:|---:|']
    for arm, row in summary['arms'].items():
        values = [row[key] for key in ('delivery_pass', 'cleanup_supported', 'verification_supported',
                                      'merge_supported', 'reconciliation_supported')]
        lines.append('| ' + arm + ' | ' + ' | '.join(str(value) + '/4' for value in values) + ' |')
    lines += ['', '| Pair | Task | Outcomes in dispatch order |', '|---|---|---|']
    for pair in summary['pairs']:
        outcomes = '; '.join(row['cell'] + ' ' + row['arm'] + ': ' + row['status'] + ', ' + ', '.join(
            category + '=' + str(row[category + '_supported']) for category in CATEGORIES)
            for row in pair['outcomes'])
        lines.append(f"| {pair['pair']} | {pair['task']} | {outcomes} |")
    result = summary['decision']
    lines += ['', 'Claude Y guard: ' + ('PASS' if summary['guard']['passed'] else 'FAIL'), '',
              result['decision'] + ': ' + result['reason']]
    if 'cost' in result:
        lines.append('Cost: ' + result['cost']['reason'])
    lines += ['- Next: ' + follow for follow in result['follow_up']]
    return '\n'.join(lines)


base.summarize, base.markdown = summarize, markdown
main = base.main


if __name__ == '__main__':
    raise SystemExit(main())
