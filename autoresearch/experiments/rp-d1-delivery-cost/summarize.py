"""Pre-registered rp-d1 aggregation; reads measured evidence without running cells.

summarize.py <measured-output-dir> --review astra=<dir> --review grok=<dir>
summarize.py --review-template <measured-output-dir> <slot>

Review files are <dir>/<slot>.json in distinct astra and grok directories. Set
the template's reviewer to astra-ultra or grok-4.7, respectively.
Fill every template category with a report
quotation, evidence keys and SUPPORTED, FALSE, MISSING or AMBIGUOUS. Empty quote
and evidence fields can describe an absent claim; an unfinished template is not
a review. A valid FAIL takes precedence over a missing/invalid peer review.
PENDING is counted separately. STOP/UNKNOWN and NOT_RUN are NOT_ASSESSED.
Missing wall measurements produce null wall totals, never partial sums or zero.
"""
import argparse
import importlib.util
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('runner_rpd1_summary', HERE / 'runner.py')
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)
github = runner.github
read, write, require = github.read, github.write, github.require
REVIEWERS = {'astra': 'astra-ultra', 'grok': 'grok-4.7'}
FINDINGS = ('SUPPORTED', 'FALSE', 'MISSING', 'AMBIGUOUS')


def measured_records(output):
    schedule = read(output / 'rp-schedule.json')
    require(schedule['phase'] == 'measured', 'only measured output may be summarized')
    records = schedule['slots']
    require([(row['cell'], row['task'], row['config']) for row in records] == runner.SCHEDULE,
            'schedule differs from the eight registered slots')
    for row in records:
        require(row == read(output / row['cell'] / 'rp-verdict.json'),
                row['cell'] + ': schedule/verdict mismatch')
        require(row['phase'] == 'measured' and row['measurement_eligible'] is True,
                row['cell'] + ': not a measured verdict')
        require(type(row['dispatched']) is bool, row['cell'] + ': invalid dispatch flag')
        require(row['status'] in ('PASS', 'ADJUDICATE', 'PRODUCT_INCOMPLETE', 'STOP', 'UNKNOWN', 'NOT_RUN'),
                row['cell'] + ': unsupported verdict status')
        require(row['dispatched'] or row['status'] in ('STOP', 'UNKNOWN', 'NOT_RUN'),
                row['cell'] + ': assessed attempt was not dispatched')
        require(row['status'] != 'NOT_RUN' or not row['dispatched'],
                row['cell'] + ': NOT_RUN attempt was dispatched')
    require(schedule['dispatched'] == sum(row['dispatched'] for row in records),
            'schedule dispatch count mismatch')
    return records


def checklist_for(output, slot):
    checklist = read(output / slot / 'report-checklist.json')
    require(isinstance(checklist['report'], str), 'invalid checklist report')
    for category in github.CATEGORIES:
        require(isinstance(checklist['facts'][category], str) and
                isinstance(checklist['evidence'][category], dict), 'invalid checklist category')
    return checklist


def review_template(output, slot):
    require(slot in {row['cell'] for row in measured_records(output)}, 'unregistered slot')
    checklist = checklist_for(output, slot)
    return dict(checklist_sha256=github.review_report(checklist)['checklist_sha256'], reviewer='',
                claims={category: dict(quote='', claim=checklist['facts'][category],
                                       evidence=list(checklist['evidence'][category]), finding='')
                        for category in github.CATEGORIES})


def grade_review(checklist, path, reviewer):
    try:
        review = read(path)
        require(isinstance(review, dict) and review.get('reviewer') == reviewer,
                'reviewer must be ' + reviewer)
        claims = review.get('claims')
        require(isinstance(claims, dict), 'invalid claims object')
        for category in github.CATEGORIES:
            claim = claims.get(category)
            require(isinstance(claim, dict) and isinstance(claim.get('quote'), str) and
                    isinstance(claim.get('claim'), str) and claim.get('finding') in FINDINGS and
                    isinstance(claim.get('evidence'), list) and
                    all(isinstance(key, str) for key in claim['evidence']),
                    'missing/invalid review category: ' + category)
        return github.review_report(checklist, review)
    except (OSError, ValueError, TypeError, KeyError, github.EvidenceError) as exc:
        return dict(status='PENDING', reason=str(exc))


def number(value, *, tokens=False):
    return (type(value) is int and value >= 0 if tokens else
            type(value) in (int, float) and math.isfinite(value) and value >= 0)


def costs(output, record):
    if not record['dispatched']:
        return dict(owner_seconds=None, input_tokens=None, output_tokens=None, usage='NOT_DISPATCHED')
    seconds = record.get('owner_seconds')
    if 'owner_seconds' not in record:
        inherited = output / ('verdict-' + record['cell'] + '.json')
        if inherited.exists() and record.get('inherited_verdict_sha256') == github.digest(inherited):
            seconds = read(inherited).get('owner_seconds')
    complete = record.get('usage') == 'COMPLETE' and all(
        number(record.get(key), tokens=True) for key in ('input_tokens', 'output_tokens'))
    return dict(owner_seconds=seconds if number(seconds) else None,
                input_tokens=record['input_tokens'] if complete else None,
                output_tokens=record['output_tokens'] if complete else None,
                usage='COMPLETE' if complete else 'UNKNOWN')


def summarize(output, reviews):
    require(set(reviews) == set(REVIEWERS), 'both astra and grok review directories are required')
    require(len({path.resolve() for path in reviews.values()}) == len(REVIEWERS),
            'astra and grok review directories must be distinct')
    slots = []
    for record in measured_records(output):
        status, grades = record['status'], {}
        if status in ('ADJUDICATE', 'PASS'):
            try:
                checklist = checklist_for(output, record['cell'])
            except (OSError, ValueError, TypeError, KeyError, github.EvidenceError) as exc:
                grades = {name: dict(status='PENDING', reason='checklist unavailable: ' + str(exc))
                          for name in REVIEWERS}
            else:
                grades = {name: grade_review(checklist, reviews[name] / (record['cell'] + '.json'), REVIEWERS[name])
                          for name in REVIEWERS}
            outcomes = {grade['status'] for grade in grades.values()}
            status = ('FAILED' if 'FAIL' in outcomes else
                      'SUCCESS' if outcomes == {'PASS'} else 'PENDING')
        else:
            status = {'PRODUCT_INCOMPLETE': 'FAILED',
                      'STOP': 'NOT_ASSESSED', 'UNKNOWN': 'NOT_ASSESSED', 'NOT_RUN': 'NOT_ASSESSED'}[status]
        row = {key: record[key] for key in ('cell', 'task', 'config', 'dispatched')}
        row.update(status=status, runner_status=record['status'], reviews=grades, **costs(output, record))
        if status == 'FAILED':
            row['failure'] = 'product' if record['status'] == 'PRODUCT_INCOMPLETE' else 'report'
        slots.append(row)
    engines = {}
    for engine in ('claude', 'codex'):
        rows = [row for row in slots if row['config'] == engine]
        dispatched = [row for row in rows if row['dispatched']]
        complete = all(row['usage'] == 'COMPLETE' for row in dispatched)
        counts = {key: sum(row['status'] == status for row in rows) for key, status in
                  (('successes', 'SUCCESS'), ('failures', 'FAILED'),
                   ('pending', 'PENDING'), ('not_assessed', 'NOT_ASSESSED'))}
        totals = {key: (sum(row[key] for row in dispatched)
                        if all(row[key] is not None for row in dispatched) else None)
                  for key in ('owner_seconds', 'input_tokens', 'output_tokens')}
        engines[engine] = dict(attempts_dispatched=len(dispatched), **counts, totals=totals,
            completeness='COMPLETE' if complete else 'UNKNOWN',
            wall_completeness='COMPLETE' if totals['owner_seconds'] is not None else 'UNKNOWN',
            cost_per_success={key: value / counts['successes'] if complete and counts['successes'] and value is not None
                              else None for key, value in totals.items()})
    return dict(schema='rp-d1-summary-v1', phase='measured', slots=slots, engines=engines)


def markdown(summary):
    lines = ['| Engine | Dispatched | Success | Failed | Pending | Not assessed | Wall s | Input | Output | Wall/success | Input/success | Output/success | Usage |',
             '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|']
    for engine, row in summary['engines'].items():
        values = [engine, *(row[key] for key in ('attempts_dispatched', 'successes', 'failures', 'pending',
                  'not_assessed')), *row['totals'].values(), *row['cost_per_success'].values(), row['completeness']]
        lines.append('| ' + ' | '.join('null' if value is None else str(value) for value in values) + ' |')
    return '\n'.join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    parser.add_argument('slot', nargs='?')
    parser.add_argument('--review', action='append', default=[], metavar='REVIEWER=DIR')
    parser.add_argument('--review-template', action='store_true')
    args = parser.parse_args(argv)
    if args.review_template:
        if not args.slot or args.review:
            parser.error('--review-template requires a slot and no --review arguments')
    elif args.slot:
        parser.error('a slot is only allowed with --review-template')
    reviews = {}
    for value in args.review:
        name, separator, directory = value.partition('=')
        if not separator or not directory or name not in REVIEWERS or name in reviews:
            parser.error('--review must name astra and grok once each as REVIEWER=DIR')
        reviews[name] = Path(directory)
    try:
        if args.review_template:
            print(json.dumps(review_template(args.output, args.slot), indent=2))
        else:
            summary = summarize(args.output, reviews)
            write(args.output / 'summary.json', summary)
            print(markdown(summary))
    except (OSError, ValueError, TypeError, KeyError, github.EvidenceError) as exc:
        parser.exit(2, 'rp-d1 summary: ' + str(exc) + '\n')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
