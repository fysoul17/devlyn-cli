"""rp-d1 report grading, grouped by arm/engine, plus the registered adoption rule."""
import importlib.util
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('runner_rpd2_summary', HERE / 'runner.py')
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)
legacy = runner.load('summary_rpd1_rpd2', runner.PRIOR / 'summarize.py')
legacy.runner = runner
github = legacy.github
read, write, require = legacy.read, legacy.write, legacy.require
REVIEWERS = legacy.REVIEWERS
METRICS = ('owner_seconds', 'input_tokens', 'output_tokens')
inherited_records, inherited_summary, inherited_markdown = legacy.measured_records, legacy.summarize, legacy.markdown
checklist_for, review_template = legacy.checklist_for, legacy.review_template


def measured_records(output):
    records = inherited_records(output)
    for row in records:
        require(row['arm'] == runner.arm_for(row['cell']), 'schedule/verdict arm mismatch')
    return records


legacy.measured_records = measured_records


def aggregate(rows):
    dispatched = [row for row in rows if row['dispatched']]
    complete = all(row['usage'] == 'COMPLETE' for row in dispatched)
    counts = {key: sum(row['status'] == status for row in rows) for key, status in
              (('successes', 'SUCCESS'), ('failures', 'FAILED'), ('pending', 'PENDING'), ('not_assessed', 'NOT_ASSESSED'))}
    totals = {key: sum(row[key] for row in dispatched) if (key == 'owner_seconds' or complete) and
              all(row[key] is not None for row in dispatched) else None
              for key in METRICS}
    return dict(attempts_dispatched=len(dispatched), **counts, totals=totals,
        completeness='COMPLETE' if complete else 'UNKNOWN',
        wall_completeness='COMPLETE' if totals['owner_seconds'] is not None else 'UNKNOWN',
        cost_per_success={key: value / counts['successes'] if complete and counts['successes'] and value is not None
                          else None for key, value in totals.items()})


def adoption(arms):
    rows = []
    for engine in ('claude', 'codex'):
        x, y = (arms[arm][engine] for arm in ('X', 'Y'))
        unresolved = any(row['pending'] or row['not_assessed'] or row['attempts_dispatched'] != 4 for row in (x, y))
        quality = ('UNKNOWN' if unresolved else 'WORSE' if y['successes'] < x['successes'] else
                   'IMPROVED' if y['successes'] > x['successes'] else 'UNCHANGED')
        reason = ('pending/unassessed or undispatched slots' if unresolved else
                  f"X={x['successes']}/4, Y={y['successes']}/4 successes")
        rows.append(dict(engine=engine, row='quality', status=quality, reason=reason))
        if unresolved:
            rows.append(dict(engine=engine, row='cost', status='UNKNOWN', reason='success denominators unresolved'))
        elif not x['successes'] or not y['successes']:
            rows.append(dict(engine=engine, row='cost', status='NO_BASELINE', reason='no baseline: one or both arms have zero successes'))
        else:
            metrics = {key: dict(X=x['cost_per_success'][key], Y=y['cost_per_success'][key]) for key in METRICS}
            if (any(row['completeness'] != 'COMPLETE' or row['wall_completeness'] != 'COMPLETE' for row in (x, y))
                    or any(not legacy.number(value) for metric in metrics.values() for value in metric.values())):
                status, reason = 'UNKNOWN', 'UNKNOWN usage or wall on a compared cost row blocks adoption'
            else:
                worse = [key for key, metric in metrics.items() if metric['Y'] > metric['X']]
                better = [key for key, metric in metrics.items() if metric['Y'] < metric['X']]
                status = 'WORSE' if worse else 'IMPROVED' if better else 'UNCHANGED'
                reason = ('higher Y cost per success: ' + ', '.join(worse) if worse else
                          'lower Y cost per success: ' + ', '.join(better) if better else 'all costs per success equal')
            rows.append(dict(engine=engine, row='cost', status=status, reason=reason, metrics=metrics))
    statuses = {row['status'] for row in rows}
    decision = ('REJECT' if 'WORSE' in statuses else 'INCONCLUSIVE' if 'UNKNOWN' in statuses else
                'ADOPT' if 'IMPROVED' in statuses else 'REJECT')
    return dict(decision=decision, rows=rows,
                reason='no engine improves' if statuses <= {'UNCHANGED', 'NO_BASELINE'} else
                       'see quality and cost rows')


def summarize(output, reviews, checklists=None):
    result = inherited_summary(output, reviews, checklists)
    for row in result['slots']:
        row['arm'] = runner.arm_for(row['cell'])
    arms = {arm: {engine: aggregate([row for row in result['slots'] if row['arm'] == arm and row['config'] == engine])
                  for engine in ('claude', 'codex')} for arm in ('X', 'Y')}
    return dict(schema='rp-d2-summary-v1', phase='measured', slots=result['slots'], arms=arms, adoption=adoption(arms))


def markdown(summary):
    grouped = {arm + '/' + engine: row for arm, engines in summary['arms'].items() for engine, row in engines.items()}
    table = inherited_markdown(dict(engines=grouped, slots=summary['slots']))
    decision = summary['adoption']
    return table + '\n\n' + decision['decision'] + ': ' + decision['reason'] + '\n' + '\n'.join(
        f"- {row['engine']} {row['row']}: {row['status']} — {row['reason']}" for row in decision['rows'])


legacy.summarize, legacy.markdown = summarize, markdown
main = legacy.main


if __name__ == '__main__':
    raise SystemExit(main())
