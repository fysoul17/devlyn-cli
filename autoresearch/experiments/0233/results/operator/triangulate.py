#!/usr/bin/env python3
"""Descriptive triangulation (not a registered test): 0232 A/I/F beside 0233 A/B/C on the shared tasks D3/D4/I0185.

Per (config, arm): cells, completions by task, total wall, input, output, per-success costs. Usage that is not COMPLETE
is flagged with '≥' (lower bound). 0233's own decision is decide.py's, not this table's.
"""
import glob
import json
import os
import sys

CC = os.path.expanduser('~/.local/share/nx01/core-continuation-20260912/autoresearch/experiments/0232/results/cells.md')
OUT = os.path.expanduser('~/.local/share/nx01/0233-live/out')
TASKS = ('D3', 'D4', 'I0185')


def rows_0232():
    for line in open(CC):
        c = [x.strip() for x in line.strip().strip('|').split('|')]
        if len(c) < 10 or not c[0].startswith('m'):
            continue
        yield dict(exp='0232', task=c[1], arm=c[2], config=c[3], complete=c[5] == 'COMPLETE', wall=float(c[6]),
                   input=int(c[7]), output=int(c[8]), usage=c[9])


def rows_0233():
    for f in sorted(glob.glob(os.path.join(OUT, 'verdict-d*.json'))):
        v = json.load(open(f))
        yield dict(exp='0233', task=v['task'], arm=v['arm'], config=v['config'], complete=v['status'] == 'COMPLETE',
                   wall=float(v['owner_seconds'] or 0), input=int(v['input_tokens'] or 0),
                   output=int(v['output_tokens'] or 0), usage=v['usage'])


def main():
    rows = [r for r in list(rows_0232()) + list(rows_0233()) if r['task'] in TASKS]
    groups = {}
    for r in rows:
        groups.setdefault((r['config'], r['exp'], r['arm']), []).append(r)
    print('| config | exp | arm | cells | done D3/D4/I0185 | wall s | input | output | wall/success | input/success | output/success |')
    print('|---|---|---|---|---|---|---|---|---|---|---|')
    for key in sorted(groups):
        g = groups[key]
        s = sum(r['complete'] for r in g)
        by = '/'.join(f"{sum(r['complete'] for r in g if r['task'] == t)}of{sum(1 for r in g if r['task'] == t)}" for t in TASKS)
        lb = '≥' if any(r['usage'] != 'COMPLETE' for r in g) else ''
        w, i, o = (sum(r[k] for r in g) for k in ('wall', 'input', 'output'))
        per = lambda x, p='': f'{p}{x / s:,.0f}' if s else '∞'
        print(f"| {key[0]} | {key[1]} | {key[2]} | {len(g)} | {s} ({by}) | {w:,.0f} | {lb}{i:,} | {lb}{o:,} | {per(w)} | {per(i, lb)} | {per(o, lb)} |")


if __name__ == '__main__':
    sys.exit(main())
