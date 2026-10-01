#!/usr/bin/env python3
"""Read-only collection of 0228 replay outcomes for scoring (registration "Predicates"; 0227 facts() logic).

  collect.py facts <out.json> <attempt>...    per attempt: merged verdict, seats (authenticated, accepted, verdict),
                                              every finding of rank >= 1 with its merge acceptance
  collect.py pool <facts.json> <pool.json> <map.json> [--twins-lower]
                                              a pool of rank-2 findings masked of arm, token and attempt (random ids);
                                              with --twins-lower also every finding of any rank by a twin seat that
                                              has no rank-2 finding (labeling decides which of those are targets)

Nothing here writes outside the given output paths; attempt files are only read, after every judge process ended."""
import hashlib
import json
import os
import runpy
import secrets
import sys
from pathlib import Path

DEV = Path('/Users/Shared/devlyn-vr-0228-dev')
EVIDENCE = Path.home() / '.local/share/nx01/core-continuation-20260912/autoresearch/experiments/0227'


def jsonl(path):
    return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()] if path.is_file() else []


def canon(row):
    return json.dumps({k: v for k, v in row.items() if k != 'source'}, sort_keys=True)


def facts(attempt, rows, mapping):
    base = DEV / attempt
    arm, tok = base.relative_to(DEV).parts[:2]
    row = rows[tok]
    work = base / 'work'
    devlyn = work / '.devlyn'
    shared = base / 'product/config/skills/_shared'
    code = {name: runpy.run_path(str(shared / file)) for name, file in (
        ('auth', 'judge-role-evidence.py'), ('parser', 'judge-output-parser.py'))}
    try:
        state = json.loads((devlyn / 'pipeline.state.json').read_text())
    except (OSError, ValueError):
        state = {}
    verify = (state.get('phases') or {}).get('verify') or {}
    merged = jsonl(devlyn / 'verify-merged.findings.jsonl')
    seats, findings = {}, []
    previous = Path.cwd()
    os.chdir(work)
    try:
        for role, seat in row['seats'].items():
            stem = seat['stem']
            carrier_path = devlyn / f'{stem}.prompt.transport.json'
            carrier = json.loads(carrier_path.read_text()) if carrier_path.is_file() else {}
            try:
                authenticated = code['auth']['authenticate'](devlyn, state, role) == (
                    verify.get('role_evidence') or {}).get(role)
            except (IndexError, KeyError, OSError, TypeError, UnicodeError, ValueError, SystemExit):
                authenticated = False
            parsed, summary = [], {}
            if authenticated:
                try:
                    parsed, summary = code['parser']['collect_judge'](devlyn / (stem + '.stdout'))
                except (SystemExit, OSError, UnicodeError, ValueError) as exc:
                    summary, authenticated = {'verdict': None, 'error': str(exc)}, False
            source = 'judge' if role == 'primary_judge' else 'pair_judge'
            accepted = authenticated and all(any(canon(r) == canon(m) for m in merged) for r in parsed) \
                and (devlyn / 'verify-merged.findings.jsonl').is_file() \
                and (devlyn / ('verify.findings.jsonl' if source == 'judge' else 'verify.pair.findings.jsonl')).is_file() \
                and (verify.get('sub_verdicts') or {}).get(source) is not None
            for index, finding in enumerate(parsed):
                rank = code['parser']['finding_rank'](finding)
                if rank >= 1:
                    findings.append({'seat': role, 'engine': seat['engine'], 'index': index, 'rank': rank,
                                     'accepted_by_merge': accepted,
                                     **{k: finding.get(k) for k in ('severity', 'verdict_binding', 'rule_id', 'file',
                                                                    'line', 'message', 'id')}})
            seats[role] = {'engine': seat['engine'], 'completed': carrier.get('outcome') == 'exited'
                           and carrier.get('exit_code') == 0, 'authenticated': authenticated,
                           'accepted_by_merge': accepted, 'verdict': summary.get('verdict')}
    finally:
        os.chdir(previous)
    task, variant, orientation, rep = mapping[tok].split('|')
    return {'attempt': attempt, 'arm': arm, 'token': tok, 'task': task, 'variant': variant,
            'orientation': orientation, 'verdict': verify.get('verdict'), 'sub_verdicts': verify.get('sub_verdicts'),
            'seats': seats, 'findings': findings}


def main(argv):
    if argv[0] == 'facts':
        out, attempts = Path(argv[1]), argv[2:]
        rows = {r['token']: r for r in json.loads((EVIDENCE / 'manifest.json').read_text())['rounds']}
        mapping = json.loads((EVIDENCE / 'evidence/mapping.json').read_text())['tokens']
        result = [facts(attempt, rows, mapping) for attempt in attempts]
        out.write_text(json.dumps(result, indent=2) + '\n')
        print(json.dumps({'attempts': len(result), 'findings': sum(len(r['findings']) for r in result)}))
    elif argv[0] == 'pool':
        records = json.loads(Path(argv[1]).read_text())
        twins_lower = '--twins-lower' in argv
        pool, key = [], {}
        for record in records:
            rank2_seats = {f['seat'] for f in record['findings'] if f['rank'] == 2}
            for finding in record['findings']:
                lower = twins_lower and record['variant'] == 'twin' and finding['rank'] < 2 \
                    and finding['seat'] not in rank2_seats
                if finding['rank'] == 2 or lower:
                    fid = secrets.token_hex(6)
                    key[fid] = {'attempt': record['attempt'], 'seat': finding['seat'], 'index': finding['index']}
                    pool.append({'id': fid, 'task': record['task'], 'variant': record['variant'],
                                 'rank': finding['rank'],
                                 **{k: finding[k] for k in ('severity', 'verdict_binding', 'rule_id', 'file', 'line',
                                                            'message')}})
        pool.sort(key=lambda item: hashlib.sha256(item['id'].encode()).hexdigest())
        Path(argv[2]).write_text(json.dumps(pool, indent=2) + '\n')
        Path(argv[3]).write_text(json.dumps(key, indent=2) + '\n')
        os.chmod(argv[3], 0o600)
        print(json.dumps({'pool': len(pool)}))


if __name__ == '__main__':
    main(sys.argv[1:])
