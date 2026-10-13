"""Pre-registered rp-d1 aggregation; reads measured evidence without running cells.

summarize.py <measured-output-dir> --review astra=<dir> --review grok=<dir>
summarize.py --review-template <measured-output-dir> <slot>

Both forms accept --checklists <reevaluation-dir>. Corrected delivery status and
checklists are used together; summary.json is then written there, leaving raw
output untouched. Original runner statuses and costs remain visible.

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
import hashlib
import importlib.util
import json
import math
import os
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


def corrected_delivery(output, checklists, slot):
    reevaluation = read(checklists / 'reevaluation.json')
    census = reevaluation['raw_census']
    require(reevaluation['schema'] == 'rp-d1-reevaluation-v1' and reevaluation['status'] == 'COMPLETE' and
            Path(reevaluation['measured_output']).resolve() == output.resolve() and
            census['unchanged'] is True and census['before'] == census['after'],
            'correction is not a completed unchanged reevaluation of this output')
    rows = [row for row in reevaluation['slots'] if row['cell'] == slot]
    require(len(rows) == 1, 'correction must contain exactly one record for ' + slot)
    row = rows[0]
    expected = {name: entry['sha256'] for name, entry in census['before'].items()
                if name.startswith((slot + '/', 'archives/' + slot + '/')) or
                name in ('rp-schedule.json', f'verdict-{slot}.json')}
    required = {slot + '/' + name for name in ('rp-verdict.json', 'report-checklist.json', 'final.txt')}
    required.update(('rp-schedule.json', f'verdict-{slot}.json', f'archives/{slot}/manifest.json'))
    require(required <= expected.keys() and row['input_sha256'] == expected, 'incomplete correction input hashes')
    for name in expected:
        relative = Path(name)
        parent = github.safe_file(output, str(relative.parent)) if relative.parent != Path('.') else output
        path = parent / relative.name
        actual = (dict(type='symlink', sha256=hashlib.sha256(os.fsencode(path.readlink())).hexdigest())
                  if path.is_symlink() else dict(type='file', **github.record_file(github.safe_file(output, name))))
        require(actual == census['before'][name], 'correction input changed: ' + name)
    checklist = checklist_for(checklists, slot)
    delivery = read(checklists / slot / 'github-delivery.json')
    require(delivery['status'] in ('ADJUDICATE', 'PRODUCT_INCOMPLETE') and
            delivery['checklist'] == checklist, 'corrected delivery/checklist mismatch')
    require(row['original'] == dict(status=read(output / slot / 'rp-verdict.json')['status'],
                                   facts=checklist_for(output, slot)['facts']) and
            row['corrected'] == dict(status=delivery['status'], facts=checklist['facts']),
            'correction facts/status binding changed')
    return delivery['status'], checklist


def review_template(output, slot, checklists=None):
    records = {row['cell']: row for row in measured_records(output)}
    require(slot in records, 'unregistered slot')
    if checklists is not None and records[slot]['status'] in ('ADJUDICATE', 'PRODUCT_INCOMPLETE'):
        _, checklist = corrected_delivery(output, checklists, slot)
    else:
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


def summarize(output, reviews, checklists=None):
    require(set(reviews) == set(REVIEWERS), 'both astra and grok review directories are required')
    require(len({path.resolve() for path in reviews.values()}) == len(REVIEWERS),
            'astra and grok review directories must be distinct')
    slots = []
    for record in measured_records(output):
        status, grades = record['status'], {}
        checklist = None
        if checklists is not None and status in ('ADJUDICATE', 'PRODUCT_INCOMPLETE'):
            try:
                status, checklist = corrected_delivery(output, checklists, record['cell'])
            except (OSError, ValueError, TypeError, KeyError, github.EvidenceError) as exc:
                status = 'UNAVAILABLE'
                grades = {name: dict(status='PENDING', reason='correction unavailable: ' + str(exc))
                          for name in REVIEWERS}
        delivery_status = status
        if grades or status in ('ADJUDICATE', 'PASS'):
            try:
                if not grades and checklist is None:
                    checklist = checklist_for(output, record['cell'])
            except (OSError, ValueError, TypeError, KeyError, github.EvidenceError) as exc:
                grades = {name: dict(status='PENDING', reason='checklist unavailable: ' + str(exc))
                          for name in REVIEWERS}
            else:
                if not grades:
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
        if checklists is not None:
            row['corrected_status'] = delivery_status
        if status == 'FAILED':
            row['failure'] = 'product' if delivery_status == 'PRODUCT_INCOMPLETE' else 'report'
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
    if any('corrected_status' in row for row in summary['slots']):
        lines.extend(['', '| Slot | Original rp-verdict | Corrected delivery | Result |', '|---|---|---|---|'])
        lines.extend(f"| {row['cell']} | {row['runner_status']} | {row['corrected_status']} | {row['status']} |"
                     for row in summary['slots'])
    return '\n'.join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    parser.add_argument('slot', nargs='?')
    parser.add_argument('--review', action='append', default=[], metavar='REVIEWER=DIR')
    parser.add_argument('--review-template', action='store_true')
    parser.add_argument('--checklists', type=Path)
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
        if args.checklists is not None:
            require(not args.checklists.resolve().is_relative_to(args.output.resolve()) and
                    not args.output.resolve().is_relative_to(args.checklists.resolve()),
                    'checklists and measured output must not overlap')
        if args.review_template:
            print(json.dumps(review_template(args.output, args.slot, args.checklists), indent=2))
        else:
            summary = summarize(args.output, reviews, args.checklists)
            target = (args.output / 'summary.json' if args.checklists is None else
                      github.safe_file(args.checklists, 'summary.json'))
            write(target, summary)
            print(markdown(summary))
    except (OSError, ValueError, TypeError, KeyError, github.EvidenceError) as exc:
        parser.exit(2, 'rp-d1 summary: ' + str(exc) + '\n')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
