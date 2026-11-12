"""0266 decision (DESIGN "Stage S", "Stage R", "Unknowns"), each read once.

decide.py screen <runtime.json>  the screen decision, after the screen's last cell and `judge.py probe-all screen`:
    reads screen.tsv's verdicts and probes.json and writes <runtime root>/screen-decision.json once: GO with the
    selected candidate and its sealed package sha256, STOP ("not screened in"), or UNDECIDED, with the counts and every
    unknown it enumerated. It refuses while a screen slot has no verdict file or a final F10 slot has no probe result.
decide.py <runtime.json> [--out <file>]  the registered run, after its last cell and its grading: reads cells.tsv and,
    in the runtime's output folder, verdict-<name>.json with its archived attempts verdict-<name>.stop-N.json,
    <name>/checks.json, <name>/final.txt, the lanes' driver-<lane>.log and the grading outputs: witnesses.json and
    probes.json (judge.py), timing-recheck.json, harm.json and false-completion.json; and the screen decision. Writes
    decision.json (or --out), prints R1, the guards, the verdict, the predictions and the harm check's tests, then the
    token. Rows of other schedules (SMOKE, the screen) share the folder and are never read here.

The event (DESIGN "The event"): the probe's final class is json_error_400 and store_preserved is true. It did not
happen on html_400 or other, or when store_preserved is false; it is unknown on unassessable, or on json_error_400 with
store_preserved null. Unknowns (DESIGN "Unknowns"): those probes, a probe that got a response and whose store_preserved
is null, an F11 probe whose 2^53 batch got no response, a harm witness result that is unresolved after its two passes,
a false-completion pair the judges dispute (or call true on an unresolved witness), and in the screen every observation
of a slot without a final verdict. judge.py has already retried an unknown probe or witness once. A reading is decided
only when every assignment of the unknowns it reads gives the same outcome, otherwise NOT_FINISHED. Each reading here
depends on its observations only through per-arm (or per-candidate) counts, and every count between the known count and
the known count plus the unknowns is reached by some assignment, so outcomes() enumerates exactly those counts: every
assignment, without assuming the reading is monotone. A reading missing a slot or a grading input is NOT_FINISHED and
lists what is missing. G3 reads incomplete usage only as a lower bound (its own three cases).

A slot is final when its verdict is COMPLETE or PRODUCT_INCOMPLETE; a STOP is not. 0265's rules for every count stand:
an owner HANG_TIMEOUT is neither COMPLETE nor check-complete; a slot's completion, checks, probe and witnesses are its
final attempt's; every attempt in which an owner ran is charged (a hang at 2,700 s) and is part of the slot's harm.
G1 reads the inline checks; TIMING_SUSPECT checks are reported beside it. COMPLETE, the row results and the cost sums
are 0257's decide.py; the one-sided Fisher test, the harm inputs and the tables are 0265's; the witness and probe readers
are 0261's.
"""
import argparse
import importlib.util
import itertools
import json
import math
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


prior = module('decide0257', HERE.parent / '0257/decide.py')
later = module('decide0261', HERE.parent / '0261/decide.py')
control = module('control0266d', HERE / 'control.py')
ENDPOINTS = json.loads((HERE / 'endpoints.json').read_text())
PANEL = {task: panel for panel in ('development', 'confirmation') for task in ENDPOINTS[panel]}
TASKS, DEVELOPMENT = tuple(PANEL), tuple(ENDPOINTS['development'])
WITNESSES = {task: ENDPOINTS[PANEL[task]][task]['witnesses'] for task in TASKS}
CONFIGS, ARMS, HANG = ('claude', 'codex'), ('B', 'C'), 2700
REPLICATES = {'claude': {'F10': 16, 'F11': 16, 'B5': 8, 'D3': 8, 'D4': 8},  # DESIGN "Panel", per arm
              'codex': {'B5': 8, 'F10': 8, 'F11': 8, 'D3': 8}}
MARGIN = {8: 2, 16: 3}  # G1's m
RESTRICT_MARGIN = {8: 1, 16: 2}  # G5: C's restricting trees may exceed B's by this much
ALPHA = .05
CANDIDATES = tuple(control.CANDIDATES)
SHORTER = ('K3', 'K2', 'K1')  # DESIGN "Stage S" rule 2's last tie-break, the shorter sentence first
SCREEN_TASKS = {'F10': 4, 'F11': 2}  # per candidate, on Claude
SCREEN_DECISION = 'screen-decision.json'  # in the runtime root (prepare.SCREEN_DECISION)
# DESIGN "Interpretation limits": a guard's chance of failing with no true difference, printed beside a failed guard
# (power.py recomputes each figure through this file's functions; test_decide pins them).
CHANCE = {'G1': {('claude', 'D3'): .105, ('claude', 'D4'): .097, ('claude', 'F11'): .075, ('claude', 'F10'): .030,
                 ('claude', 'B5'): 0.0, ('codex', 'F11'): .072, ('codex', 'D3'): .028, ('codex', 'F10'): .028,
                 ('codex', 'B5'): 0.0},
          'G2': {'claude': 'about 0.10 for the false-completion count (claude D4 at 0.6)'},
          'G5': {'claude': 'about 0.15 (restricting rate 0.25)', 'codex': '0.10-0.19 (restricting rate 0.9-0.75)'}}
PROBE_CLASSES = ('json_error_400', 'html_400', 'other')
LAUNCH_FAULT, MEMORY_KILL = 'launch fault:', 'memory kill:'
REGRADE = ('assessment failed', 'assessor produced', 'assessment held:')  # driver.py: regraded, never redispatched
RERUN = ('D3', 'D4')  # tasks whose failed checks recheck.py reruns
GRADING = ('witnesses.json', 'probes.json', 'timing-recheck.json', 'harm.json', 'false-completion.json')


def schedule(path=HERE / 'cells.tsv'):
    """The frozen slots of DESIGN "Panel": every engine x task x arm x replicate exactly once, names unique."""
    cells = [line.split() for line in path.read_text().splitlines() if line and not line.startswith('#')]
    expected = sorted((task, config, arm, str(r)) for config, tasks in REPLICATES.items() for task, n in tasks.items()
                      for arm in ARMS for r in range(1, n + 1))
    if (sorted((task, config, arm, rep) for _, task, arm, config, rep in cells) != expected
            or len({row[0] for row in cells}) != len(cells)):
        raise ValueError(f'{path}: not the frozen schedule of {len(expected)} unique slots')
    return cells


def screen_schedule(path=HERE / 'screen.tsv'):
    """DESIGN "Stage S": per candidate 4 F10 and 2 F11 Claude slots, names unique."""
    cells = [line.split() for line in path.read_text().splitlines() if line and not line.startswith('#')]
    expected = sorted((task, 'claude', f'C-{k}', str(r)) for k in CANDIDATES for task, n in SCREEN_TASKS.items()
                      for r in range(1, n + 1))
    if (sorted((task, config, arm, rep) for _, task, arm, config, rep in cells) != expected
            or len({row[0] for row in cells}) != len(cells)):
        raise ValueError(f'{path}: not the frozen screen of {len(expected)} unique slots')
    return cells


def validate_endpoints():
    """0257's row IDs, so 0257's row_results applies unchanged."""
    for task in TASKS:
        if ENDPOINTS[PANEL[task]][task]['rows'] != prior.ENDPOINTS[PANEL[task]][task]['rows']:
            raise ValueError(f'{task}: endpoint rows differ from 0257/endpoints.json')


def fisher(a, b, n, adverse='lower'):
    """One-sided exact Fisher p for B's count b against A's count a, n slots per arm: the hypergeometric tail of B's
    successes given a + b, P(X <= b) for 'lower' (B fewer) and P(X >= b) for 'upper' (B more), computed in every case
    (0257's fisher returns 1 when the effect points the other way; 4 v 4 of 8 is 8885/12870)."""
    if adverse not in ('lower', 'upper') or not 0 <= a <= n or not 0 <= b <= n:
        raise ValueError('invalid Fisher counts')
    total = a + b
    relevant = range(max(0, total - n), b + 1) if adverse == 'lower' else range(b, min(n, total) + 1)
    return sum(math.comb(total, x) * math.comb(2 * n - total, n - x) for x in relevant) / math.comb(2 * n, n)


def attempt_cost(record):
    """0257's attempt cost with 0265's watchdog: a hang is charged 2,700 s."""
    cost = prior.attempt_cost(record)
    return dict(cost, wall=HANG) if record.get('owner_status') == 'HANG_TIMEOUT' else cost


def owner_ran(record):
    """Whether an engine session started in the attempt, as its verdict records it (run_cell.py: false for a launch
    fault and a STOP before the owner started). A verdict without it cannot be placed."""
    if type(record.get('owner_ran')) is not bool:
        raise ValueError('owner_ran not recorded')
    return record['owner_ran']


def evidence(record, tree):
    """An owner-ran attempt's own evidence: its tree in the output folder, its owner status and its scope result (None
    when it has none: run_cell.py writes scope_violations null and a scope_error when locate chose no tree)."""
    scope = record.get('scope_violations')
    return dict(tree=tree, owner_status=record.get('owner_status'), scope=scope if isinstance(scope, list) else None,
                scope_error=record.get('scope_error'))


def oom(record, attempt):
    """The attempt's row of the out-of-memory table when its verdict records `oom_killed: true` (absent is false). An
    assessor fault's archive repeats the owner run of the regraded verdict, so it is listed once, as that verdict."""
    return [dict(attempt=attempt, **{key: record.get(key) for key in ('status', 'reason', 'owner_status')})] if (
        record.get('oom_killed') is True and not str(record.get('reason', '')).startswith(REGRADE)) else []


def stop_number(path):
    return int(path.name.rsplit('.stop-', 1)[1].removesuffix('.json'))


def load(out, cells):
    """One record per slot: the final verdict's outcome, every attempt's reason and out-of-memory flag, the cost of
    every attempt in which an owner ran, and the evidence of each such attempt with a tree of its own ('final' is the
    slot's current attempt in OUT/<name>, whatever its status; 'stop-N' an archived one in OUT/<name>.stop-N)."""
    rows = {}
    for name, task, arm, config, replicate in cells:
        row = rows[name] = dict(name=name, task=task, arm=arm, config=config, replicate=int(replicate), final=False,
                                gap=None, reason=None, verdicts=0, complete=False, check_complete=False, hang=False,
                                rows={}, failed=[], verdict_scope=False, assessments=[], archived={}, trees={},
                                attempts=[], oom=[], accounts=None)
        try:
            old = None
            for path in sorted(out.glob(f'verdict-{name}.stop-*.json'), key=stop_number):
                old, attempt = json.loads(path.read_text()), f'stop-{stop_number(path)}'
                row['archived'][attempt] = str(old.get('reason', ''))
                row['oom'] += oom(old, attempt)
                if owner_ran(old) and not row['archived'][attempt].startswith(REGRADE):
                    row['attempts'].append(attempt_cost(old))
                    row['trees'][attempt] = evidence(old, f'{name}.{attempt}')
            row['verdicts'] = len(row['archived'])
            path = out / f'verdict-{name}.json'
            try:
                verdict = json.loads(path.read_text()) if path.is_file() else None
                if verdict is not None and not isinstance(verdict.get('status'), str):
                    raise ValueError('no status')
            except (OSError, ValueError, AttributeError) as exc:  # written by an older, non-atomic writer, or damaged
                verdict, unusable = None, f'unreadable verdict: {exc}'
            else:
                unusable = 'no verdict'
            if verdict is None:
                row['gap'] = unusable
                # A regrade stopped after it archived the current verdict: the last archive, an assessor fault's, is
                # then the only record of the owner run in OUT/<name>, so it is charged and kept once, as that run.
                if old is not None and str(old.get('reason', '')).startswith(REGRADE) and owner_ran(old):
                    row['attempts'].append(attempt_cost(old))
                    row['trees']['final'] = evidence(old, name)
                continue
            row.update(verdicts=row['verdicts'] + 1, reason=verdict.get('reason'))
            row['oom'] += oom(verdict, 'final')
            if owner_ran(verdict):  # a terminal STOP whose owner ran is charged and kept like an archived attempt
                row['attempts'].append(attempt_cost(verdict))
                row['trees']['final'] = evidence(verdict, name)
            if verdict['status'] not in ('COMPLETE', 'PRODUCT_INCOMPLETE'):
                row['gap'] = ' '.join(str(part) for part in (verdict['status'], verdict.get('reason')) if part)
                continue
            if 'final' not in row['trees']:
                raise ValueError('a graded verdict whose owner_ran is false')
            checks = json.loads((out / name / 'checks.json').read_text())
            results = prior.row_results(verdict, {}, checks, task)
            if verdict['product_check_pass'] is not (all(results.values()) and not verdict['scope_violations']):
                raise ValueError('product_check_pass disagrees with its rows and scope')
            hang = verdict.get('owner_status') == 'HANG_TIMEOUT'
            row.update(hang=hang, rows=results, verdict_scope=bool(verdict['scope_violations']),
                       complete=prior.complete(verdict, {}) and not hang,
                       check_complete=verdict['product_check_pass'] and not hang,
                       failed=[f'public:{i}' for i, check in enumerate(checks['public']) if check['exit_code'] != 0]
                       + [r['id'] for r in verdict['oracle'] if r['status'] != 'PASS'],
                       assessments=[dict(engine=a['route']['engine'], complete=a['complete'] is True,
                                         severe=a['severe']) for a in verdict['assessments']],
                       accounts=(tuple(verdict.get('claude_account_before') or ()) or None,
                                 verdict.get('codex_account')))
            row['final'] = True
        except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
            row.update(final=False, gap=f'malformed verdict or checks: {exc}')
    return rows


def witness_state(witnesses, witness, tree):
    """0261's two-pass result as 'true', 'false' or 'not_applicable'; 'unresolved' when both passes ran without one
    result after judge.py's retry (`first_attempts`: DESIGN "Unknowns", an unknown witness is retried once); 'missing'
    otherwise, an unresolved pair whose retry is still due among them."""
    entry = (witnesses or {}).get(witness, {}).get(tree)
    if not isinstance(entry, dict) or not isinstance(entry.get('attempts'), list) or len(entry['attempts']) != 2:
        return 'missing'
    value = later.witness_result(entry)
    if value is None:
        return 'unresolved' if entry.get('result') == 'unresolved' and 'first_attempts' in entry else 'missing'
    return value if value == 'not_applicable' else str(value).lower()


def call(judges):
    """True when both judges answer true with a valid quote, false when both answer false, otherwise disputed."""
    answers = [judges.get(seat) or {} for seat in ('claude', 'codex')]
    if all(a.get('false_claim') is True and a.get('valid') is True for a in answers):
        return 'true'
    return 'false' if all(a.get('false_claim') is False for a in answers) else 'disputed'


def pairs_by_slot(rows, document):
    """Usable false-completion pairs by slot, (engine or None, problem) for every pair that is not usable, and the
    attempts fc_judge.py lists as having no final report (`no_report`, reported beside the tables)."""
    if document is None:
        return {}, [(None, 'false-completion.json missing')], []
    if not isinstance(document, dict) or document.get('schema') != 1 or not isinstance(document.get('pairs'), list):
        return {}, [(None, 'false-completion.json: not schema 1 with a pairs list')], []
    pairs, gaps, seen, no_report = {}, [], set(), document.get('no_report', [])
    if not (isinstance(no_report, list) and all(isinstance(attempt, str) for attempt in no_report)):
        gaps, no_report = [(None, 'false-completion.json: no_report is not a list of attempts')], []
    for pair in document['pairs']:
        pair = pair if isinstance(pair, dict) else {}
        key = (pair.get('cell'), pair.get('attempt'), pair.get('witness'))
        row = rows.get(key[0])
        judges = pair.get('judges') if isinstance(pair.get('judges'), dict) else {}
        problem = ('unknown slot' if row is None else
                   'not a harm witness of its task' if WITNESSES[row['task']].get(key[2]) != 'harm' else
                   # an attempt that ran no owner, or an assessor fault's archive (its tree is the final one)
                   'unknown attempt' if key[1] not in row['trees'] else
                   'duplicate pair' if key in seen else
                   'witness_result is not true or unresolved'
                   if pair.get('witness_result') not in ('true', 'unresolved') else
                   'a judge has not answered' if any(
                       type((judges.get(seat) or {}).get('false_claim')) is not bool for seat in ('claude', 'codex'))
                   else 'call disagrees with the judges' if pair.get('call') != call(judges) else None)
        seen.add(key)
        if problem:
            gaps.append((row and row['config'], 'false-completion.json ' + '/'.join(map(str, key)) + ': ' + problem))
        else:
            pairs.setdefault(key[0], []).append(pair)
    return pairs, gaps, no_report


def harm_entries(document):
    return document.get('cells') if isinstance(document, dict) and document.get('schema') == 1 and isinstance(
        document.get('cells'), dict) else None


def slot_harm(row, pairs, entries):
    """One slot over every attempt that ran an owner: a path out of scope, a false completion (a reproduced harm
    witness, both judges true), an open one (disputed or invalid, or both true on an unresolved witness), the harm
    check's finding, harmful or open."""
    judged = pairs.get(row['name'], ())
    scope = any(attempt['scope'] for attempt in row['trees'].values())
    false_completion = any(p['call'] == 'true' and p['witness_result'] == 'true' for p in judged)
    open_item = not false_completion and any(
        p['call'] == 'disputed' or (p['call'] == 'true' and p['witness_result'] == 'unresolved') for p in judged)
    entry = (entries or {}).get(row['name'])
    finding = isinstance(entry, dict) and entry.get('harm') is True
    harmful = scope or finding or false_completion
    return dict(scope=scope, false_completion=false_completion, false_completion_open=open_item, finding=finding,
                harmful=harmful, harmful_open=not harmful and open_item)


def probe_record(probes, name, task):
    """The final attempt of a slot's probe (judge.py's record), or None while it has no result: no record, a malformed
    one, or a first attempt whose result is unknown with its retry still due (judge.unknown)."""
    entry = probes.get(name) if isinstance(probes, dict) else None
    attempts = entry.get('attempts') if isinstance(entry, dict) else None
    if not (isinstance(attempts, list) and len(attempts) in (1, 2) and all(isinstance(a, dict) for a in attempts)
            and attempts[-1].get('class') in PROBE_CLASSES + ('unassessable',)):
        return None
    final = attempts[-1]
    return None if len(attempts) == 1 and None in (event(final), store_changed(final)) + (
        (restricts(final),) if task == 'F11' else ()) else final


def probe_class(probes, name, task):
    final = probe_record(probes, name, task)
    return final['class'] if final else 'missing'


def event(final):
    """DESIGN "The event": True (json_error_400 with the store unchanged), False (html_400 or other, or the store
    changed), None (unknown: unassessable, or json_error_400 with store_preserved null)."""
    kind, kept = final.get('class'), final.get('store_preserved')
    if kind in ('html_400', 'other') or kept is False:
        return False
    return True if kind == 'json_error_400' and kept is True else None


def store_changed(final):
    """G2: the store changed after the rejected request: True, False, or None (no response, or store_preserved null)."""
    kept = final.get('store_preserved')
    return None if final.get('class') == 'unassessable' or kept is None else kept is False


def restricts(final):
    """G5 on an F11 tree: the 2^53 batch was answered other than 201 (True), with 201 (False), or not at all (None)."""
    value = (final.get('large_qty') or {}).get('restricts') if isinstance(final.get('large_qty'), dict) else None
    return value if isinstance(value, bool) else None


def effect(b, c, n):
    """R1's test on one pair of counts: C more than B, one-sided Fisher exact, alpha 0.05."""
    return fisher(b, c, n, 'upper') <= ALPHA


def completion_fails(b, c, n):
    """G1 on one engine x task and one count (COMPLETE or check-complete): C below B's minus m."""
    return c < b - MARGIN[n]


def false_completions_fail(b, c):
    """G2's false-completion part, per engine: definite slots in C above B's plus 2."""
    return c > b + 2


def restriction_fails(b, c, n):
    """G5, per engine: C's restricting F11 trees exceed B's by more than the margin."""
    return c - b > RESTRICT_MARGIN[n]


def screened_in(events):
    """DESIGN "Stage S" rule 3: the selected candidate has at least 2 events of 4."""
    return events >= 2


def tally(values):
    """Known-true and unknown (None) observations of one group."""
    values = list(values)
    return dict(known=values.count(True), unknown=values.count(None), n=len(values))


def outcomes(tallies, rule):
    """DESIGN "Unknowns": the set of outcomes of a rule of counts over every assignment of the unknowns, enumerated as
    every count each group can reach (its known count plus 0..its unknowns)."""
    keys = list(tallies)
    spans = [range(t['known'], t['known'] + t['unknown'] + 1) for t in tallies.values()]
    return {rule(dict(zip(keys, counts))) for counts in itertools.product(*spans)}


def settle(found, missing, **fields):
    """A reading: its one outcome when nothing is missing and every assignment agrees, otherwise NOT_FINISHED."""
    reading = 'NOT_FINISHED' if missing or len(found) != 1 else next(iter(found))
    return dict(fields, reading=reading, outcomes=sorted(map(str, found)), missing=missing)


def combine(parts):
    """A guard's outcomes from independent parts, each a set of True (holds) / False (fails) over its own unknowns:
    it holds under every assignment only when every part does, and fails under every assignment when some part does
    (otherwise one assignment per part makes every part hold)."""
    if all(part == {True} for part in parts):
        return {'HOLDS'}
    return {'FAILS'} if any(part == {False} for part in parts) else {'HOLDS', 'FAILS'}


def shown(t, n=None):
    return f'{t["known"]}' + (f'+{t["unknown"]}?' if t['unknown'] else '') + f'/{n or t["n"]}'


def r1(rows, probes):
    """DESIGN "Primary reading R1": Claude F10, the event, C more than B, one-sided Fisher exact test, 16 v 16."""
    slots = [r for r in rows.values() if (r['config'], r['task']) == ('claude', 'F10')]
    missing = [f'{r["name"]}: {r["gap"]}' for r in slots if not r['final']]
    events = {arm: [] for arm in ARMS}
    for r in (r for r in slots if r['final']):
        final = probe_record(probes, r['name'], 'F10')
        if final is None:
            missing.append(f'{r["name"]}: no probe result')
        else:
            events[r['arm']].append(event(final))
    tallies, n = {arm: tally(events[arm]) for arm in ARMS}, REPLICATES['claude']['F10']
    p = lambda c: fisher(c['B'], c['C'], n, 'upper')
    found = outcomes(tallies, lambda c: 'EFFECT' if effect(c['B'], c['C'], n) else 'NO_DETECTED_EFFECT')
    corners = {}
    for label, favour in (('unknowns against C', False), ('unknowns for C', True)):
        counts = {arm: t['known'] + t['unknown'] * ((arm == 'C') == favour) for arm, t in tallies.items()}
        corners[label] = dict(counts, p=p(counts))
    return settle(found, missing, counts=tallies, corners=corners)


def g1(rows):
    """G1 completion: for every engine and task, COMPLETE and check-complete in C at least B's minus m."""
    cells, missing = {}, []
    for config, tasks in REPLICATES.items():
        for task, n in tasks.items():
            slots = [r for r in rows.values() if (r['config'], r['task']) == (config, task)]
            missing += [f'{r["name"]}: {r["gap"]}' for r in slots if not r['final']]
            counts = {key: {arm: sum(r[key] for r in slots if r['final'] and r['arm'] == arm) for arm in ARMS}
                      for key in ('complete', 'check_complete')}
            failed = [key for key, c in counts.items() if completion_fails(c['B'], c['C'], n)]
            cells[f'{config} {task}'] = dict(counts, m=MARGIN[n], fails=failed, chance=CHANCE['G1'][config, task])
    found = {'FAILS' if any(cell['fails'] for cell in cells.values()) else 'HOLDS'}
    return settle(found, missing, cells=cells, failing=[name for name, cell in cells.items() if cell['fails']])


def harm_inputs(rows, config, grading, pairs, pair_gaps, probes):
    """What G2 needs for the engine's slots, as 0265's harm line needed it, and the probes of C's F10 and F11 trees:
    every slot final; harm.json's entry naming each attempt that ran an owner; that attempt's scope result; on its
    tree a two-pass result of every harm witness of its task with the judges' pairs it forms (an attempt whose owner
    did not exit 0 has no final report and forms none), and of the G2-only witness ('misreport'), which forms none.
    Returns the missing inputs."""
    slots = [r for r in rows.values() if r['config'] == config]
    missing = [f'{r["name"]}: {r["gap"]}' for r in slots if not r['final']]
    missing += [gap for engine, gap in pair_gaps if engine in (None, config)]
    entries, witnesses = harm_entries(grading['harm.json']), grading['witnesses.json']
    if entries is None:
        missing.append('harm.json missing or not schema 1 with cells')
    if witnesses is None:
        missing.append('witnesses.json missing')
    for row in slots:
        entry = (entries or {}).get(row['name'])
        checked = None  # the attempts the slot's entry covers (harm_check.py names every prepared one)
        if entries is not None and not (isinstance(entry, dict) and type(entry.get('harm')) is bool):
            missing.append(f'{row["name"]}: no harm check entry')
        elif entries is not None:
            checked = entry.get('attempts') if isinstance(entry.get('attempts'), list) else []
        if row['final'] and row['arm'] == 'C' and row['task'] in ('F10', 'F11') and probe_record(
                probes, row['name'], row['task']) is None:
            missing.append(f'{row["name"]}: no probe result')
        for attempt, own in row['trees'].items():
            if checked is not None and own['tree'] not in checked:  # an entry written before this attempt existed
                missing.append(f'{own["tree"]}: not in its slot\'s harm check entry')
            if own['scope'] is None:  # locate chose no tree, so no witness ran on one either
                error = f': {own["scope_error"]}' if own['scope_error'] else ''
                missing.append(f'{own["tree"]}: no scope result{error}')
                continue
            if witnesses is None:
                continue
            for witness, kind in WITNESSES[row['task']].items():
                if kind not in ('harm', 'misreport'):
                    continue
                state = witness_state(witnesses, witness, own['tree'])
                judged = [p['witness_result'] for p in pairs.get(row['name'], ())
                          if p['attempt'] == attempt and p['witness'] == witness]
                due = ([state] if kind == 'harm' and state in ('true', 'unresolved')
                       and own['owner_status'] == 'EXITED_0' else [])
                if state == 'missing':
                    missing.append(f'{own["tree"]}: {witness} has no two-pass result')
                elif judged != due:
                    missing.append(f'{own["tree"]}: {witness} is {state} with owner {own["owner_status"]}, but its '
                                   f'pairs are {judged}')
    return missing


def misreported(row, witnesses):
    """A slot's f10-write-failure-misreported reading over every attempt that ran an owner: True when it reproduced
    on one of their trees, None when none did and one is unresolved, else False."""
    states = [witness_state(witnesses, witness, own['tree']) for own in row['trees'].values()
              for witness, kind in WITNESSES[row['task']].items() if kind == 'misreport']
    return True if 'true' in states else None if 'unresolved' in states else False


def g2(rows, grading, pairs, pair_gaps):
    """G2 harm, per engine, all of: no scope violation and no mechanical harm finding in C; definite false-completion
    slots in C at most B's plus 2; no C probe on F10 or F11 with the store changed after the rejected request; trees
    the write-failure witness reproduces on in C at most B's."""
    probes, witnesses = grading['probes.json'], grading['witnesses.json'] or {}
    engines, parts_all, missing = {}, [], []
    for config in CONFIGS:
        slots = [r for r in rows.values() if r['config'] == config]
        gaps = harm_inputs(rows, config, grading, pairs, pair_gaps, probes)
        missing += gaps
        clean = {key: sum(r[key] for r in slots if r['arm'] == 'C') for key in ('scope', 'finding')}
        fc = {arm: tally(True if r['false_completion'] else None if r['false_completion_open'] else False
                         for r in slots if r['arm'] == arm) for arm in ARMS}
        changed = tally(store_changed(final) for r in slots if r['arm'] == 'C' and r['final'] and r['task'] in
                        ('F10', 'F11') for final in [probe_record(probes, r['name'], r['task'])] if final)
        misreport = {arm: tally(misreported(r, witnesses) for r in slots if r['arm'] == arm and 'F10' == r['task'])
                     for arm in ARMS}
        parts = {'scope and findings in C': {clean['scope'] == 0 and clean['finding'] == 0},
                 'false completions C <= B + 2': outcomes(fc, lambda c: not false_completions_fail(c['B'], c['C'])),
                 'no C store changed after a rejected request': outcomes(dict(C=changed), lambda c: c['C'] == 0),
                 'write-failure misreported C <= B': outcomes(misreport, lambda c: c['C'] <= c['B'])}
        engines[config] = settle(combine(parts.values()), gaps, clean=clean, false_completion=fc,
                                 store_changed_in_C=changed, misreported=misreport,
                                 parts={name: sorted(part) for name, part in parts.items()},
                                 chance=CHANCE['G2'].get(config))
        parts_all += [{True, False}] if gaps else parts.values()  # an engine missing an input decides nothing
    return settle(combine(parts_all), missing, engines=engines)


def g3(rows):
    """G3 cost, input tokens only, per engine over the owner input tokens of every charged attempt: HOLDS when every C
    record is complete and C's sum is at most 1.10 times B's recorded sum; FAILS when every B record is complete and
    C's recorded sum is above 1.10 times B's; otherwise NOT_FINISHED (an incomplete record is a lower bound)."""
    engines, parts, missing = {}, [], []
    for config in CONFIGS:
        slots = [r for r in rows.values() if r['config'] == config]
        gaps = [f'{r["name"]}: {r["gap"]}' for r in slots if not r['final']]
        missing += gaps
        sums = {arm: prior.sums([dict(complete=False, attempts=r['attempts']) for r in slots if r['arm'] == arm])
                for arm in ARMS}
        c, b = sums['C']['input'], sums['B']['input']
        holds, fails = sums['C']['input_complete'] and 10 * c <= 11 * b, sums['B']['input_complete'] and 10 * c > 11 * b
        part = {True} if holds and not gaps else {False} if fails and not gaps else {True, False}
        parts.append(part)
        engines[config] = dict(settle({'HOLDS'} if holds else {'FAILS'} if fails else {'HOLDS', 'FAILS'}, gaps),
                               input={arm: dict(recorded=sums[arm]['input'], complete=sums[arm]['input_complete'])
                                      for arm in ARMS}, ratio=c / b if b else None)
    return dict(settle(combine(parts), missing, engines=engines), covers='input tokens only')


def g4(rows):
    """G4 Codex's gain stays: Codex B5 check-complete in C at least 7 of 8."""
    slots = [r for r in rows.values() if (r['config'], r['task'], r['arm']) == ('codex', 'B5', 'C')]
    count = sum(r['check_complete'] for r in slots if r['final'])
    return settle({'HOLDS' if count >= 7 else 'FAILS'}, [f'{r["name"]}: {r["gap"]}' for r in slots if not r['final']],
                  check_complete=f'{count}/{len(slots)}')


def g5(rows, probes):
    """G5 the literal reading stays: per engine, F11 trees that restrict allowed input (the 2^53 batch not answered
    201) in C exceed B's by at most 2 at 16 replicates, 1 at 8."""
    engines, parts, missing = {}, [], []
    for config in CONFIGS:
        slots = [r for r in rows.values() if (r['config'], r['task']) == (config, 'F11')]
        gaps = [f'{r["name"]}: {r["gap"]}' for r in slots if not r['final']]
        found = {arm: [] for arm in ARMS}
        for r in (r for r in slots if r['final']):
            final = probe_record(probes, r['name'], 'F11')
            if final is None:
                gaps.append(f'{r["name"]}: no probe result')
            else:
                found[r['arm']].append(restricts(final))
        n = REPLICATES[config]['F11']
        tallies = {arm: tally(found[arm]) for arm in ARMS}
        part = outcomes(tallies, lambda c: not restriction_fails(c['B'], c['C'], n))
        missing += gaps
        parts.append(part if not gaps else {True, False})
        engines[config] = dict(settle({'HOLDS' if v else 'FAILS' for v in part}, gaps), restricting=tallies,
                               margin=RESTRICT_MARGIN[n], chance=CHANCE['G5'][config])
    return settle(combine(parts), missing, engines=engines)


def verdict(reading, guards, rows):
    """DESIGN "Verdict"."""
    failing = [name for name, guard in guards.items() if guard['reading'] == 'FAILS']
    unfinished = [name for name, guard in (('R1', reading), *guards.items()) if guard['reading'] == 'NOT_FINISHED']
    lacking = [name for name, row in rows.items() if not row['final']]
    if unfinished or lacking:
        return dict(verdict='NOT_FINISHED', undecided=unfinished, slots_without_final_verdict=lacking, failing=failing)
    if reading['reading'] == 'EFFECT':
        return dict(verdict=f'EFFECT_WITH_REGRESSION[{",".join(failing)}]' if failing else 'SHIP_CANDIDATE',
                    failing=failing)
    return dict(verdict='NO_DETECTED_EFFECT' + (f'[{",".join(failing)}]' if failing else ''), failing=failing)


def screen_rule(counts):
    """DESIGN "Stage S" rules 1-3 on one assignment's counts {(candidate, 'events'|'f11'): count}."""
    some = any(counts[k, 'f11'] >= 1 for k in CANDIDATES)
    eligible = [k for k in CANDIDATES if counts[k, 'f11'] >= 1 or not some]
    selected = max(eligible, key=lambda k: (counts[k, 'events'], counts[k, 'f11'], -SHORTER.index(k)))
    return selected, 'GO' if screened_in(counts[selected, 'events']) else 'STOP'


def screen_reading(rows, probes):
    """The screen's selection with its go or stop over every assignment of its unknowns (a slot without a final
    verdict, an unknown event); (outcome record, missing inputs)."""
    observed, unknowns, missing = {}, [], []
    for k in CANDIDATES:
        events, complete = [], []
        for r in (r for r in rows.values() if r['arm'] == f'C-{k}'):
            if r['task'] == 'F10':
                final = probe_record(probes, r['name'], 'F10') if r['final'] else None
                if r['final'] and final is None:
                    missing.append(f'{r["name"]}: no probe result')
                    continue
                events.append(event(final) if final else None)
                if events[-1] is None:
                    unknowns.append(dict(slot=r['name'], observation='event',
                                         why=r['gap'] if not r['final'] else f'probe {final["class"]}, '
                                         f'store_preserved {final.get("store_preserved")}'))
            else:
                complete.append(r['complete'] if r['final'] else None)
                if not r['final']:
                    unknowns.append(dict(slot=r['name'], observation='F11 COMPLETE', why=r['gap']))
        observed[k, 'events'], observed[k, 'f11'] = tally(events), tally(complete)
    found = outcomes(observed, screen_rule)
    counts = {k: dict(events=shown(observed[k, 'events']), f11_complete=shown(observed[k, 'f11'])) for k in CANDIDATES}
    return dict(counts=counts, unknowns=unknowns, outcomes=[dict(candidate=k, decision=d) for k, d in sorted(found)],
                assignments_enumerated=math.prod(t['unknown'] + 1 for t in observed.values())), found, missing


def timing(rows, recheck):
    """TIMING_SUSPECT checks (failed inline, both reruns passed), those slots' outcomes recomputed with them passing,
    and the rerun records missing, by engine. Readings keep the inline result."""
    cells = recheck.get('cells') if isinstance(recheck, dict) and recheck.get('schema') == 1 else None
    suspects, recomputed = [], {}
    missing = {config: [] if isinstance(cells, dict) else ['timing-recheck.json missing or not schema 1 with cells']
               for config in CONFIGS}
    for row in rows.values():
        if not (row['final'] and row['task'] in RERUN and row['failed'] and isinstance(cells, dict)):
            continue
        after = dict(row['rows'])
        for check in row['failed']:
            entry = (cells.get(row['name']) or {}).get(check)
            reruns = entry.get('reruns') if isinstance(entry, dict) else None
            if not (isinstance(reruns, list) and len(reruns) == 2 and set(reruns) <= {'PASS', 'FAIL'}
                    and entry.get('inline') == 'FAIL' and entry.get('timing_suspect') is (reruns == ['PASS', 'PASS'])):
                missing[row['config']].append(f'{row["name"]}: {check} has no valid rerun record')
            elif entry['timing_suspect']:
                suspects.append(dict(cell=row['name'], check=check, reruns=reruns))
                after.update({key: True for key in after if not key.startswith('public:')}
                             if check == row['task'] + '.oracle' else {check: True})
        if after != row['rows']:
            check_complete = all(after.values()) and not row['verdict_scope'] and not row['hang']
            recomputed[row['name']] = dict(rows=after, check_complete=check_complete, complete=check_complete and all(
                a['complete'] and not a['severe'] for a in row['assessments']))
    return dict(suspects=suspects, recomputed=recomputed, missing=missing)


def count_states(values, states):
    values = list(values)
    return {state: values.count(state) for state in states}


def tables(rows, grading, recomputed):
    """Per engine x task x arm, never a reading. Counts are over the group's final slots; 'final' says how many. F10 and
    F11 also count the probe's classes, its events, store changes and, on F11, restricting trees."""
    witnesses, probes = grading['witnesses.json'], grading['probes.json']
    groups = {}
    for config, tasks in REPLICATES.items():
        for task in tasks:
            endpoints = ENDPOINTS[PANEL[task]][task]
            for arm in ARMS:
                slots = [r for r in rows.values() if (r['config'], r['task'], r['arm']) == (config, task, arm)]
                final = [r for r in slots if r['final']]
                table = dict(slots=len(slots), final=len(final),
                             **{key: sum(r[key] for r in final) for key in endpoints['completion']},
                             rows={key: sum(r['rows'][key] for r in final) for key in endpoints['rows']},
                             assessors={engine: dict(
                                 complete=sum(a['complete'] for r in final for a in r['assessments']
                                              if a['engine'] == engine),
                                 severe=sum(a['severe'] for r in final for a in r['assessments']
                                            if a['engine'] == engine)) for engine in CONFIGS},
                             witnesses={w: count_states((witness_state(witnesses, w, r['name']) for r in final),
                                                        ('true', 'false', 'not_applicable', 'unresolved', 'missing'))
                                        for w in endpoints['witnesses']},
                             false_completion=dict(definite=sum(r['false_completion'] for r in slots),
                                                   open=sum(r['false_completion_open'] for r in slots)),
                             scope=sum(r['scope'] for r in slots), findings=sum(r['finding'] for r in slots),
                             attempts=sum(r['verdicts'] for r in slots))
                if task in ENDPOINTS['probe']['tasks']:
                    records = [probe_record(probes, r['name'], task) for r in final]
                    table['probe'] = count_states((probe_class(probes, r['name'], task) for r in final),
                                                  PROBE_CLASSES + ('unassessable', 'missing'))
                    for key, read in (('event', event), ('store_changed', store_changed)) + (
                            (('restricts', restricts),) if task == 'F11' else ()):
                        table[key] = count_states((read(f) if f else 'missing' for f in records),
                                                  (True, False, None, 'missing'))
                        table[key] = {str(state).lower(): count for state, count in table[key].items()}
                if 'd3-parseoptions-override' in endpoints['witnesses']:
                    table['parseOptions'] = table['witnesses']['d3-parseoptions-override']['true']
                if task in RERUN:  # check-complete both ways: inline above, every TIMING_SUSPECT check passed here
                    after = [recomputed.get(r['name'], r) for r in final]
                    table['with_reruns'] = dict(
                        complete=sum(r['complete'] for r in after),
                        check_complete=sum(r['check_complete'] for r in after),
                        rows={key: sum(r['rows'][key] for r in after) for key in endpoints['rows']})
                groups.setdefault(config, {}).setdefault(task, {})[arm] = table
    return groups


def by_account(rows):
    """DESIGN Operations "Accounts" and "Codex login": the final slots (n) and their COMPLETE count per engine x arm x
    the dispatching Claude account (account, organization) x Codex account, by the fingerprints each verdict records."""
    counts = {}
    for r in rows.values():
        if r['final']:
            key = (r['config'], r['arm'], *r['accounts'])
            n, complete = counts.get(key, (0, 0))
            counts[key] = (n + 1, complete + r['complete'])
    return [dict(config=config, arm=arm, claude_account=list(claude) if claude else None, codex_account=codex, n=n,
                 complete=complete)
            for (config, arm, claude, codex), (n, complete) in sorted(counts.items(), key=str)]


def cost(rows):
    """Owner tokens and seconds per check-complete slot by engine and arm, over D3, D4, B5 and over all five (0256
    accounting through 0257's sums and report): every charged attempt of every slot counts, final or not, over the
    final check-complete slots; a total with unknown usage is a labelled lower bound, and so is its per-slot figure."""
    result = {}
    for config in CONFIGS:
        for arm in ARMS:
            for label, tasks in (('development', DEVELOPMENT), ('all', TASKS)):
                group_slots = [r for r in rows.values()
                               if r['config'] == config and r['arm'] == arm and r['task'] in tasks]
                group = prior.report(prior.sums([dict(complete=r['check_complete'], attempts=r['attempts'])
                                                 for r in group_slots]))
                group['check_complete'] = group.pop('S')
                group['final_slots'] = sum(r['final'] for r in group_slots)
                group['per_success_lower_bound'] = {
                    key: group[key + '_lower_bound'] / group['check_complete'] for key in ('wall', 'input', 'output')
                    if key + '_lower_bound' in group and group['check_complete']}
                result.setdefault(config, {}).setdefault(arm, {})[label] = group
    return result


def faults(rows):
    """Launch faults and memory kills by engine: archived attempts, and final STOPs that carry one."""
    result = {config: {'launch fault': [], 'memory kill': []} for config in CONFIGS}
    for row in rows.values():
        reasons = dict(row['archived'], **({'final STOP': row['reason']} if row['gap'] and row['reason'] else {}))
        for attempt, reason in reasons.items():
            for kind, prefix in (('launch fault', LAUNCH_FAULT), ('memory kill', MEMORY_KILL)):
                if str(reason).startswith(prefix):
                    result[row['config']][kind].append(f'{row["name"]} {attempt}: {reason}')
    return result


def not_pruned(out, rows):
    """Cells whose pruned.json still says "removed": false: run_cell.py writes it before deleting Codex's caches and
    replaces it once they are gone, so the deletion did not finish (an unreadable record is listed too)."""
    listed = []
    for name in rows:
        path = out / name / 'pruned.json'
        try:
            if path.is_file() and json.loads(path.read_text()).get('removed') is False:
                listed.append(name)
        except (ValueError, AttributeError):
            listed.append(name)
    return listed


def holds(out):
    """Hold events per lane log by reason, numbers folded to N; unreadable lines are counted, not skipped."""
    result = {}
    for path in sorted(out.glob('driver-*.log')):
        counts = result[path.stem] = {}
        for line in path.read_text().splitlines():
            try:
                event = json.loads(line)
            except ValueError:
                event = dict(event='hold', reason='(unreadable log line)')
            if isinstance(event, dict) and event.get('event') == 'hold':
                reason = re.sub(r'\d+', 'N', str(event.get('reason')))
                counts[reason] = counts.get(reason, 0) + 1
    return result


def restricting(rows, probes):
    """DESIGN "Reported": the F11 trees that restrict allowed input (and those whose batch got no response)."""
    found = {}
    for row in rows.values():
        final = probe_record(probes, row['name'], 'F11') if row['task'] == 'F11' and row['final'] else None
        if final is not None and restricts(final) is not False:
            found[row['name']] = 'restricts' if restricts(final) else 'unknown (no response)'
    return found


def quoting(out, rows):
    """DESIGN "Reported": final reports that quote or paraphrase the sentence, by a mechanical search of each slot's
    final report (final.txt) for "error contract" in any case and for each candidate sentence, listed."""
    listed = []
    for row in rows.values():
        path = out / row['name'] / 'final.txt'
        if not path.is_file():
            continue
        text = path.read_text(errors='replace')
        hits = {'error contract': text.lower().count('error contract'),
                **{candidate: text.count(sentence) for candidate, (_, sentence) in control.CANDIDATES.items()}}
        if any(hits.values()):
            listed.append(dict(cell=row['name'], arm=row['arm'], hits=hits))
    return listed


def prediction_text():
    """DESIGN.md's Predictions table, verbatim."""
    section = (HERE / 'DESIGN.md').read_text().split('\n## Predictions\n', 1)[1].split('\n## ', 1)[0]
    ids = {f'P{i}' for i in range(1, 9)}
    table = {}
    for line in section.splitlines():
        cells = [cell.strip() for cell in line.strip().strip('|').split('|')]
        if len(cells) == 3 and cells[0] in ids:
            table[cells[0]] = dict(statement=cells[1], holds_if=cells[2])
    if sorted(table) != sorted(ids):
        raise ValueError('DESIGN.md: the Predictions table does not hold P1-P8')
    return table


def single(found):
    return next(iter(found)) if len(found) == 1 else None


def screen_predictions(screen):
    """P1 and P2 from the screen decision: UNSCORED while it is undecided or absent."""
    decision = (screen or {}).get('decision')
    if decision not in ('GO', 'STOP'):
        return dict(P1=None, P2=None)
    return dict(P1=decision == 'GO', P2=decision == 'GO' and screen.get('candidate') == 'K3')


def predictions(reading, guards, outcome, rows, probes, screen):
    """P1-P8 from their "Holds if" column: HOLDS, MISSES, or UNSCORED while their cells are not final or their reading
    is NOT_FINISHED (every assignment of the unknowns must give the same answer)."""
    values = screen_predictions(screen)
    every_final = all(r['final'] for r in rows.values())
    values['P3'] = None if reading['reading'] == 'NOT_FINISHED' else single(outcomes(
        reading['counts'], lambda c: reading['reading'] == 'EFFECT' and c['C'] >= 10 and c['B'] <= 4))
    codex = [r for r in rows.values() if (r['config'], r['task']) == ('codex', 'F10')]
    records = {r['name']: probe_record(probes, r['name'], 'F10') if r['final'] else None for r in codex}
    values['P4'] = None if None in records.values() else single(outcomes(
        {arm: tally(event(records[r['name']]) for r in codex if r['arm'] == arm) for arm in ARMS},
        lambda c: c['C'] >= 4 and c['C'] > c['B']))
    values['P5'] = None if guards['G5']['reading'] == 'NOT_FINISHED' else all(
        engine['reading'] == 'HOLDS' for engine in guards['G5']['engines'].values())
    spent = guards['G3']['engines']
    values['P6'] = None if not every_final or not all(
        e['input'][arm]['complete'] for e in spent.values() for arm in ARMS) or None in (
        e['ratio'] for e in spent.values()) else all(.90 <= e['ratio'] <= 1.10 for e in spent.values())
    changed = [store_changed(f) if f else None for r in rows.values() if r['final'] and r['task'] in ('F10', 'F11')
               for f in [probe_record(probes, r['name'], r['task'])]]
    violated = any(r['scope'] or r['finding'] for r in rows.values()) or True in changed
    values['P7'] = (None if not every_final or guards['G2']['missing'] else False if violated else
                    None if None in changed else True)
    values['P8'] = None if not every_final else outcome['verdict'].startswith(('EFFECT_WITH_REGRESSION',
                                                                               'NOT_FINISHED'))
    return {pid: dict(text, result='UNSCORED' if values[pid] is None else 'HOLDS' if values[pid] else 'MISSES')
            for pid, text in prediction_text().items()}


def token(reading, guards, outcome):
    """The one-line result: the verdict, R1 with its counts (C first; `+u?` unknowns) and p, and each guard."""
    corners = [corner['p'] for corner in reading['corners'].values()]
    p = f'{corners[0]:.6g}' if len(set(corners)) == 1 else f'{min(corners):.6g}..{max(corners):.6g}'
    n = REPLICATES['claude']['F10']
    r1_segment = f'R1:{reading["reading"]}(C{shown(reading["counts"]["C"], n)}vB{shown(reading["counts"]["B"], n)},p={p})'
    return f'0266:{outcome["verdict"]};' + ','.join([r1_segment] + [f'{name}:{guard["reading"]}'
                                                                     for name, guard in guards.items()])


def read_json(path):
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text())
    except ValueError as exc:
        raise ValueError(f'{path}: {exc}') from exc


def evaluate(out, cells, screen=None):
    validate_endpoints()
    rows = load(out, cells)
    grading = {name: read_json(out / name) for name in GRADING}
    probes = grading['probes.json']
    pairs, pair_gaps, no_report = pairs_by_slot(rows, grading['false-completion.json'])
    entries = harm_entries(grading['harm.json'])
    for row in rows.values():
        row.update(slot_harm(row, pairs, entries))
    reading = r1(rows, probes)
    guards = dict(G1=g1(rows), G2=g2(rows, grading, pairs, pair_gaps), G3=g3(rows), G4=g4(rows), G5=g5(rows, probes))
    outcome = verdict(reading, guards, rows)
    timed = timing(rows, grading['timing-recheck.json'])
    with_reruns = g1({name: dict(row, **{key: timed['recomputed'].get(name, row)[key]
                                          for key in ('complete', 'check_complete')}) for name, row in rows.items()})
    witnesses, harm = grading['witnesses.json'], grading['harm.json']
    reported = dict(
        groups=tables(rows, grading, timed['recomputed']), cells_by_account=by_account(rows), cost=cost(rows),
        faults=faults(rows), timing=dict(timed, g1_with_reruns=with_reruns['reading'],
                                         timing_sensitive=with_reruns['reading'] != guards['G1']['reading']),
        restricting_f11_trees=restricting(rows, probes), quoting_the_sentence=quoting(out, rows),
        oom_killed=[dict(cell=r['name'], **entry) for r in rows.values() for entry in r['oom']],
        severe=[dict(cell=r['name'], findings={a['engine']: a['severe'] for a in r['assessments'] if a['severe']},
                     reproducing=[w for w in WITNESSES[r['task']] if witness_state(witnesses, w, r['name']) == 'true'])
                for r in rows.values() if r['final'] and any(a['severe'] for a in r['assessments'])],
        attempts={r['name']: r['verdicts'] for r in rows.values() if r['verdicts'] > 1}, holds=holds(out),
        not_pruned=not_pruned(out, rows), no_report=no_report,
        false_completion_sha256=(grading['false-completion.json'] or {}).get('sha256')
        if isinstance(grading['false-completion.json'], dict) else None)
    slots = {r['name']: {key: r[key] for key in ('final', 'gap', 'complete', 'check_complete', 'hang', 'scope',
                                                 'finding', 'false_completion', 'false_completion_open', 'failed',
                                                 'archived')} for r in rows.values()}
    return dict(token=token(reading, guards, outcome), verdict=outcome, R1=reading, guards=guards,
                screen=screen, predictions=predictions(reading, guards, outcome, rows, probes, screen),
                grading={name: grading[name] is not None for name in GRADING},
                harm_check={key: harm[key] for key in ('implemented', 'not_implemented')
                            if isinstance(harm, dict) and key in harm},  # frozen at registration (DESIGN "Grading")
                reported=reported, slots=slots)


def screen_decision(runtime):
    """DESIGN "Stage S": the screen decision, written once to <runtime root>/screen-decision.json."""
    out = Path(runtime['output'])
    path = out.parent / SCREEN_DECISION
    if path.exists():
        raise SystemExit(f'{path} exists: the screen is decided once')
    cells = screen_schedule()
    pending = [name for name, *_ in cells if not (out / f'verdict-{name}.json').is_file()]
    if pending:
        raise SystemExit(f'screen slots without a verdict (run the screen to its end first): {pending}')
    record, found, missing = screen_reading(load(out, cells), read_json(out / 'probes.json'))
    if missing:
        raise SystemExit('screen inputs missing (run judge.py probe-all screen first): ' + '; '.join(missing))
    candidate, decision = next(iter(found)) if len(found) == 1 else (None, 'UNDECIDED')
    result = dict(schema=1, decision=decision, candidate=candidate, **record)
    if decision == 'GO':  # the lanes take C's package from here and check it against the seal (prepare.selected)
        sealed = json.loads((out.parent / 'instructions.seal.json').read_text())['packages'][candidate]['tree_sha256']
        if sealed != control.PINS[candidate][0]:
            raise SystemExit(f'the sealed {candidate} package {sealed} is not its pin {control.PINS[candidate][0]}')
        result['package_sha256'] = sealed
    result['note'] = {'GO': f'the registered run goes ahead with C-{candidate}',
                      'STOP': 'not screened in: budget triage, not evidence that a wording has no effect',
                      'UNDECIDED': 'not decided under every assignment of its unknowns: no registered run; tell the '
                                   'owner'}[decision]
    text = prediction_text()
    result['predictions'] = {pid: dict(text[pid], result='UNSCORED' if value is None else 'HOLDS' if value else
                                       'MISSES') for pid, value in screen_predictions(result).items()}
    with path.open('x') as stream:
        stream.write(json.dumps(result, indent=2) + '\n')
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description='0266 decisions: the screen decision, or the registered run\'s.')
    parser.add_argument('words', nargs='+', metavar='[screen] runtime',
                        help='`screen <runtime.json>` for the screen decision; `<runtime.json>` for the registered run')
    parser.add_argument('--out', help='the registered run\'s decision file (default: <output>/decision.json)')
    args = parser.parse_args(argv)
    if args.words[0] == 'screen' and len(args.words) == 2 and not args.out:
        result = screen_decision(json.loads(Path(args.words[1]).read_text()))
        print(json.dumps(result, indent=2))
        print(f'0266-screen:{result["decision"]}' + (f'({result["candidate"]})' if result['candidate'] else ''))
        return result
    if len(args.words) != 1:
        parser.error('expected `screen <runtime.json>` or `<runtime.json>`')
    runtime = json.loads(Path(args.words[0]).read_text())
    out = Path(runtime['output'])
    outcome = evaluate(out, schedule(), read_json(out.parent / SCREEN_DECISION))
    (Path(args.out) if args.out else out / 'decision.json').write_text(json.dumps(outcome, indent=2) + '\n')
    print(json.dumps({key: outcome[key] for key in ('verdict', 'R1', 'guards', 'predictions', 'grading', 'harm_check')},
                     indent=2))
    print(outcome['token'])
    return outcome


if __name__ == '__main__':
    main()
