"""Power, size and interval figures DESIGN quotes ("Why r3" 1-2, "Strongest counter", "Decision" 1-3), recomputed
through decide.py's own Fisher test and Wilson-MOVER interval. Run: python3 power.py (about 15 s).

Truths are 0257's observed rates, a sizing aid, never evidence about 4.3.30. Every figure is exact, by enumerating
the binomial outcomes of each arm (the 16-replicate completion line too: at most 1.4 million interval evaluations).
Each line prints the computed value beside DESIGN's, as DESIGN prints it, and says DIFFERS when the two disagree by
more than half a unit of DESIGN's last decimal.
"""
import importlib.util
import itertools
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('decide0265', HERE / 'decide.py')
decide = importlib.util.module_from_spec(spec)
spec.loader.exec_module(decide)

RATES = {  # 0257 COMPLETE rates (A, B), 16 slots per arm and task (0257 RESULT.md; I0185 completed none)
    'claude': {'D3': (10 / 16, 5 / 16), 'D4': (6 / 16, 5 / 16), 'I0185': (0.0, 0.0), 'B5': (14 / 16, 16 / 16)},
    'codex': {'D3': (15 / 16, 12 / 16), 'D4': (16 / 16, 16 / 16), 'I0185': (0.0, 0.0), 'B5': (5 / 16, 16 / 16)},
}
PANELS = (('D3', 'D4', 'B5'), ('D3', 'D4', 'I0185', 'B5'))


def pmf(n, p):
    return [math.comb(n, k) * p**k * (1 - p)**(n - k) for k in range(n + 1)]


def test_power(p_a, p_b, n, alpha, adverse):
    """P(decide.fisher(a, b, n, adverse) <= alpha) with a ~ Bin(n, p_a), b ~ Bin(n, p_b)."""
    a_pmf, b_pmf = pmf(n, p_a), pmf(n, p_b)
    return sum(a_pmf[a] * b_pmf[b] for a in range(n + 1) for b in range(n + 1)
               if a_pmf[a] and b_pmf[b] and decide.fisher(a, b, n, adverse) <= alpha)


def line(rates, n):
    """Exact P(B_BETTER) and P(B_WORSE) of decide.sign_interval, n slots per arm and task."""
    outcomes = [[(a, b, pa * pb) for a, pa in enumerate(pmf(n, rate_a)) if pa for b, pb in enumerate(pmf(n, rate_b))
                 if pb] for rate_a, rate_b in rates.values()]
    better = worse = 0.0
    for combo in itertools.product(*outcomes):
        result = decide.sign_interval({task: dict(A=a, B=b) for task, (a, b, _) in zip(rates, combo)}, n)
        probability = math.prod(p for _, _, p in combo)
        better += probability * (result['reading'] == 'B_BETTER')
        worse += probability * (result['reading'] == 'B_WORSE')
    return dict(better=better, worse=worse)


def every_task(a, b):
    """decide.sign_interval with the same counts, a of 8 in A and b of 8 in B, on D3, D4 and B5."""
    return decide.sign_interval({task: dict(A=a, B=b) for task in decide.DEVELOPMENT}, decide.N)


def pooled(engine, tasks):
    """No difference: both arms at the task's pooled 0257 rate."""
    return {task: (sum(RATES[engine][task]) / 2,) * 2 for task in tasks}


def threshold(n=decide.N, alpha=.025):
    """For each higher count, the largest lower count whose one-sided p is at most alpha (None when none is)."""
    return {high: max((low for low in range(high + 1) if decide.fisher(low, high, n, 'upper') <= alpha), default=None)
            for high in range(n, -1, -1)}


def figures():
    """(label, computed, DESIGN's figure as printed or None) for every figure DESIGN quotes."""
    rows = []
    for engine, quoted in (('claude', {16: ('0.12', '0.14'), 8: ('0.06', '0.11')}),
                           ('codex', {16: ('0.58', '0.63'), 8: ('0.20', '0.22')})):
        for n, ends in quoted.items():
            for tasks, value in zip((PANELS[1], PANELS[0]), ends):
                result = line({task: RATES[engine][task] for task in tasks}, n)
                rows.append((f'Why r3 1: {engine} D over {"+".join(tasks)} reads a difference, {n} per arm',
                             result['better'] + result['worse'], value))
    for alpha, r1, drift, gap, halved in ((.025, '0.78', '0.89', '0.39', '0.14'),
                                          (.05, '0.93', '0.97', '0.49', '0.25')):
        rows += [(f'Decision 1: R1 at 0257 rates (A 5/16, B 1.00), single test at {alpha}',
                  test_power(5 / 16, 1.0, decide.N, alpha, 'upper'), r1),
                 (f'Decision 1: R2 at 0257 rates (A 1.00, B 0), single test at {alpha}',
                  test_power(1.0, 0.0, decide.N, alpha, 'lower'), '1.00'),
                 (f'Decision 1: R2 with B drifted to 0.25, single test at {alpha}',
                  test_power(1.0, .25, decide.N, alpha, 'lower'), drift),
                 (f'Decision 1 / counter: a 0.50 gap (0.90 vs 0.40), R1 direction, single test at {alpha}',
                  test_power(.40, .90, decide.N, alpha, 'upper'), gap),
                 (f'Decision 1 / counter: a 0.50 gap (0.90 vs 0.40), R2 direction, single test at {alpha}',
                  test_power(.90, .40, decide.N, alpha, 'lower'), gap),
                 (f"Decision 1 / counter: R1's gap halved (A 0.56, B 0.90), single test at {alpha}",
                  test_power(.56, .90, decide.N, alpha, 'upper'), halved)]
    rows.append(('Decision 1: 8 v 4 one-sided p', decide.fisher(4, 8, decide.N, 'upper'), '0.038'))
    middle = every_task(4, 4)
    rows.append(('Decision 2: half-width at mid rates, 4/8 v 4/8 on every task (DESIGN: about)',
                 (middle['hi'] - middle['lo']) / 2, '0.21'))
    for b, quoted in ((5, ('0.25', '-0.01', '0.44')), (6, ('0.375', '0.11', '0.55'))):
        result = every_task(3, b)
        rows += [(f'Decision 2 / counter: {b}/8 v 3/8 on every task, {key} (reads {result["reading"]})', result[key],
                  value) for key, value in zip(('D', 'lo', 'hi'), quoted)]
    for engine, null in (('claude', '0.03'), ('codex', '0.01')):
        none = line(pooled(engine, PANELS[0]), decide.N)
        rows += [(f'Decision 2: {engine} false B_BETTER with no difference', none['better'], null),
                 (f'Decision 2: {engine} false B_WORSE with no difference', none['worse'], null)]
    harm_n = decide.N * len(decide.TASKS)
    for rate, value in ((.05, '0.007'), (.10, None), (.18, None), (.30, '0.031')):
        rows.append((f'Decision 3: harm line size at a common rate of {rate:.2f} (DESIGN: 0.007-0.031)',
                     test_power(rate, rate, harm_n, .05, 'upper'), value))
    for a, b, value in ((.10, .35, '0.81'), (.10, .40, '0.92'), (.18, .45, '0.78')):
        rows.append((f'Decision 3 / counter: harm line power {a:.2f} -> {b:.2f}',
                     test_power(a, b, harm_n, .05, 'upper'), value))
    return rows


def differs(computed, quoted):
    """More than half a unit of the quoted figure's last decimal apart."""
    return abs(computed - float(quoted)) > 5 * 10.0 ** -(len(quoted.split('.')[1]) + 1) + 1e-12


def main():
    print('Decision 1: p <= 0.025 at 8 v 8 needs (higher v at most lower):',
          ', '.join(f'{high} v {low}' for high, low in threshold().items() if low is not None),
          '(DESIGN: 8 v 3, 7 v 2, 6 v 1, 5 v 0)')
    count = 0
    for label, computed, quoted in figures():
        flag = '' if quoted is None else f' (DESIGN {quoted}) ' + ('DIFFERS' if differs(computed, quoted) else 'ok')
        count += flag.endswith('DIFFERS')
        print(f'{label}: {computed:.4f}{flag}')
    print(f'{count} figure(s) differ from DESIGN by more than its rounding')
    return count


if __name__ == '__main__':
    main()
