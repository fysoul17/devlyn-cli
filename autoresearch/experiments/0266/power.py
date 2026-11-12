"""The chance and power figures of DESIGN "Interpretation limits" and "Stage S", recomputed through decide.py's own
rules (effect, completion_fails, false_completions_fail, restriction_fails, screened_in) and its CHANCE table. Run:
python3 power.py.

Rates are 0265's harness arm (B, devlyn-cli 4.3.30) as RESULT.md reports it, a sizing aid, never evidence about 4.3.31:
with no true difference both arms are drawn at that rate. Every figure is exact, by enumerating the binomial outcomes
of each arm. Each line prints the computed value beside DESIGN's, as DESIGN prints it, and says DIFFERS when the two
disagree by more than half a unit of DESIGN's last decimal.
"""
import importlib.util
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('decide0266', HERE / 'decide.py')
decide = importlib.util.module_from_spec(spec)
spec.loader.exec_module(decide)

# 0265 harness arm (B) COMPLETE rates per engine x task (0265 results/decision.json, 8 slots each).
COMPLETE = {('claude', 'D3'): 4 / 8, ('claude', 'D4'): 3 / 8, ('claude', 'B5'): 8 / 8, ('claude', 'F10'): 1 / 8,
            ('claude', 'F11'): 6 / 8, ('codex', 'B5'): 8 / 8, ('codex', 'F10'): 7 / 8, ('codex', 'F11'): 2 / 8,
            ('codex', 'D3'): 7 / 8}
# DESIGN "Interpretation limits": the G1 cells it names, as printed.
G1_QUOTED = {('claude', 'D3'): '0.105', ('claude', 'D4'): '0.097', ('claude', 'F11'): '0.075',
             ('claude', 'F10'): '0.030', ('codex', 'F11'): '0.072', ('codex', 'D3'): '0.028', ('codex', 'F10'): '0.028'}


def pmf(n, p):
    return [math.comb(n, k) * p**k * (1 - p)**(n - k) for k in range(n + 1)]


def chance(rule, n, p_b, p_c=None):
    """P(rule(b, c)) with b ~ Bin(n, p_b) and c ~ Bin(n, p_c), p_c = p_b when no difference."""
    b_pmf, c_pmf = pmf(n, p_b), pmf(n, p_b if p_c is None else p_c)
    return sum(b_pmf[b] * c_pmf[c] for b in range(n + 1) for c in range(n + 1) if rule(b, c))


def g1_cell(config, task):
    n = decide.REPLICATES[config][task]
    return chance(lambda b, c: decide.completion_fails(b, c, n), n, COMPLETE[config, task])


def figures():
    """(label, computed, DESIGN's figure as printed or None) for every figure DESIGN quotes."""
    rows = []
    cells = {key: g1_cell(*key) for key in COMPLETE}
    for key, value in cells.items():
        rows.append((f'G1 COMPLETE comparison fails by chance, {key[0]} {key[1]} (decide.CHANCE {decide.CHANCE["G1"][key]})',
                     value, G1_QUOTED.get(key, '0.0' if value == 0 else None)))
    rows.append(('G1 fails in at least one of its nine cells by chance (DESIGN: about 36%)',
                 1 - math.prod(1 - value for value in cells.values()), '0.36'))
    for config, rate, quoted in (('claude', .25, '0.15'), ('codex', .90, '0.10'), ('codex', .75, '0.19')):
        n = decide.REPLICATES[config]['F11']
        rows.append((f'G5 fails by chance, {config} at a restricting rate of {rate}',
                     chance(lambda b, c: decide.restriction_fails(b, c, n), n, rate), quoted))
    # Not a DESIGN figure: 0266's probe on 0265's archived codex F11 trees (2026-11-12) read 0 of 16 restricting.
    rows.append(('G5 fails by chance, codex at the rate 0266\'s probe read on 0265\'s codex F11 trees (0 of 16)',
                 chance(lambda b, c: decide.restriction_fails(b, c, 8), 8, 0.0), None))
    n = decide.REPLICATES['claude']['D4']
    rows.append(("G2's false-completion count fails by chance, claude D4 at 0.6 (DESIGN: about 10%)",
                 chance(decide.false_completions_fail, n, .6), '0.10'))
    n = decide.REPLICATES['claude']['F10']
    for rate, quoted in ((.5, '0.63'), (.6, '0.83'), (.75, '0.98')):
        rows.append((f"R1's power, B at 0.125, C at {rate}",
                     chance(lambda b, c: decide.effect(b, c, n), n, .125, rate), quoted))
    rows += [('R1: 8 v 2 one-sided p (rejects)', decide.fisher(2, 8, n, 'upper'), '0.027'),
             ('R1: 7 v 2 one-sided p (does not)', decide.fisher(2, 7, n, 'upper'), '0.057')]
    for rate, quoted in ((.5, '0.69'), (.11, '0.06')):
        rows.append((f'Stage S bar: a wording at a true event rate of {rate} passes 2 of 4',
                     sum(p for k, p in enumerate(pmf(decide.SCREEN_TASKS['F10'], rate)) if decide.screened_in(k)),
                     quoted))
    return rows


def differs(computed, quoted):
    """More than half a unit of the quoted figure's last decimal apart."""
    return abs(computed - float(quoted)) > 5 * 10.0 ** -(len(quoted.split('.')[1]) + 1) + 1e-12


def main():
    count = 0
    for label, computed, quoted in figures():
        flag = '' if quoted is None else f' (DESIGN {quoted}) ' + ('DIFFERS' if differs(computed, quoted) else 'ok')
        count += flag.endswith('DIFFERS')
        print(f'{label}: {computed:.4f}{flag}')
    print(f'{count} figure(s) differ from DESIGN by more than its rounding')
    return count


if __name__ == '__main__':
    main()
