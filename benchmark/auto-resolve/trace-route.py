#!/usr/bin/env python3
"""
trace-route.py — Simulate PHASE 0.5 Stage A + PHASE 1.4 Stage B decisions on a test case.

Does NOT execute a real pipeline. Runs the orchestrator's routing logic against
a test case's spec/task and compares the decision against `expected.json`.

This validates the routing LOGIC is correct without spending subagent tokens
on a real pipeline.

Usage:
    python3 trace-route.py --test-case T1-trivial
    python3 trace-route.py --test-case T2-standard --verbose
    python3 trace-route.py --all
"""
import argparse, json, pathlib, re, sys

RISK_KEYWORDS = [
    'auth', 'login', 'session', 'token', 'secret', 'password', 'crypto',
    'api', 'env', 'permission', 'access', 'database', 'migration', 'payment',
]

PHASES_PER_ROUTE = {
    'fast':     ['build', 'build_gate', 'evaluate', 'final_report'],
    'standard': ['build', 'build_gate', 'evaluate', 'critic', 'docs', 'final_report'],
    'strict':   ['build', 'build_gate', 'evaluate', 'critic', 'docs', 'final_report'],
}
# v3.4+ collapsed SIMPLIFY/REVIEW/CHALLENGE/SECURITY into a single CRITIC phase
# with design + security sub-passes. CRITIC security sub-pass is delegated to
# the native Claude Code `security-review` skill. Route difference between
# standard and strict is the team flag in BUILD, not the phase list.


def load_test_case(name):
    d = pathlib.Path(__file__).parent / 'test-cases' / name
    if not d.exists():
        print(f"ERROR: test case directory not found: {d}", file=sys.stderr)
        sys.exit(1)
    result = {'name': name, 'dir': str(d)}
    result['task'] = (d / 'task.txt').read_text().strip() if (d / 'task.txt').exists() else ''
    result['spec'] = (d / 'spec.md').read_text() if (d / 'spec.md').exists() else None
    result['expected'] = json.loads((d / 'expected.json').read_text()) if (d / 'expected.json').exists() else None
    return result


def parse_spec_frontmatter(spec_text):
    """Extract YAML frontmatter fields from spec content (first --- block)."""
    if not spec_text or not spec_text.startswith('---\n'):
        return {}
    end = spec_text.find('\n---\n', 4)
    if end < 0:
        return {}
    block = spec_text[4:end]
    out = {}
    for line in block.splitlines():
        m = re.match(r'^([a-z_-]+):\s*"?([^"]*)"?$', line.strip())
        if m:
            out[m.group(1)] = m.group(2).strip()
    return out


def has_web_files(diff_files):
    """Check if any file is web-relevant (for browser validate forcing)."""
    patterns = [r'\.tsx$', r'\.jsx$', r'\.vue$', r'\.svelte$', r'\.css$', r'\.html$', r'page\.', r'layout\.', r'route\.']
    return any(re.search(p, f) for f in diff_files for p in patterns)


def stage_a(tc):
    """Decision order: user override > risk keyword > spec complexity > generated defers."""
    user_route = tc['expected'].get('user_route')  # simulate --route flag from test fixture
    reasons = []

    if user_route in ('fast', 'standard', 'strict'):
        return {'selected': user_route, 'user_override': True,
                'reasons': [f'user explicit override: --route {user_route}']}

    source_body = tc['spec'] if tc['spec'] else tc['task']
    body_lower = source_body.lower() if source_body else ''
    hits = [k for k in RISK_KEYWORDS if k in body_lower]
    if hits:
        return {'selected': 'strict', 'user_override': False,
                'reasons': [f'risk keyword hit: {hits[:3]}' + ('...' if len(hits) > 3 else '')]}

    if tc['spec'] is None:
        return {'selected': 'standard', 'user_override': False,
                'reasons': ['source.type=generated; complexity deferred to Stage B post-BUILD']}

    fm = parse_spec_frontmatter(tc['spec'])
    complexity = fm.get('complexity', 'medium')
    route_map = {'low': 'fast', 'medium': 'standard', 'high': 'strict'}
    return {'selected': route_map.get(complexity, 'standard'), 'user_override': False,
            'reasons': [f'spec.complexity={complexity}', '0 risk keywords']}


def stage_b(current_route, user_override, diff_signals):
    """Post-BUILD escalation. Never de-escalates. Skipped on user_override."""
    if user_override:
        return {'at': None, 'escalated_from': None, 'reasons': []}
    tier = {'fast': 0, 'standard': 1, 'strict': 2}
    rev = {v: k for k, v in tier.items()}
    cur = tier[current_route]
    new = cur
    reasons = []
    if diff_signals.get('risk_in_diff'):
        reasons.append(f"risk in diff content: {diff_signals['risk_in_diff']}")
        new = max(new, 2)
    if diff_signals.get('cross_boundary'):
        reasons.append('cross-boundary changes')
        new = min(max(new, cur + 1), 2)
    if diff_signals.get('diff_files', 0) > 10:
        reasons.append(f"diff_files={diff_signals['diff_files']} > 10")
        new = min(max(new, cur + 1), 2)
    if diff_signals.get('diff_lines', 0) > 400:
        reasons.append(f"diff_lines={diff_signals['diff_lines']} > 400")
        new = min(max(new, cur + 1), 2)
    if (diff_signals.get('api_surface') or diff_signals.get('tests_absent')) and cur == 0:
        if diff_signals.get('api_surface'):
            reasons.append('api surface touched')
        if diff_signals.get('tests_absent'):
            reasons.append('tests absent for new code')
        new = max(new, 1)
    if new > cur:
        return {'at': '<simulated>', 'escalated_from': current_route,
                'reasons': reasons, 'selected': rev[new]}
    return {'at': None, 'escalated_from': None, 'reasons': []}


def phase_list_for(route, has_web):
    phases = list(PHASES_PER_ROUTE[route])
    if has_web:
        phases.insert(2, 'browser_validate')
    return phases


def trace(tc, verbose=False):
    a = stage_a(tc)
    signals = tc['expected'].get('stage_b_signals', {})
    b = stage_b(a['selected'], a['user_override'], signals)
    final_route = b.get('selected', a['selected'])
    web = has_web_files(tc['expected'].get('diff_files', []))
    phases = phase_list_for(final_route, web)

    result = {
        'test_case': tc['name'],
        'stage_a': a,
        'stage_b': b,
        'final_route': final_route,
        'has_web_files': web,
        'phase_list': phases,
    }

    expected = tc['expected']
    mismatches = []
    if expected.get('final_route') and expected['final_route'] != final_route:
        mismatches.append(f"route: expected {expected['final_route']}, got {final_route}")
    if expected.get('expected_phases'):
        if sorted(expected['expected_phases']) != sorted(phases):
            mismatches.append(f"phases: expected {expected['expected_phases']}, got {phases}")
    if expected.get('stage_a_override') is not None and expected['stage_a_override'] != a['user_override']:
        mismatches.append(f"stage_a user_override: expected {expected['stage_a_override']}, got {a['user_override']}")

    result['match'] = not mismatches
    result['mismatches'] = mismatches
    return result


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--test-case')
    p.add_argument('--all', action='store_true')
    p.add_argument('--verbose', action='store_true')
    args = p.parse_args()

    if args.all:
        tc_dir = pathlib.Path(__file__).parent / 'test-cases'
        cases = sorted([d.name for d in tc_dir.iterdir() if d.is_dir()])
    elif args.test_case:
        cases = [args.test_case]
    else:
        p.error('specify --test-case or --all')

    results = []
    for name in cases:
        tc = load_test_case(name)
        r = trace(tc, verbose=args.verbose)
        results.append(r)

    summary = {'runs': len(results), 'match': sum(1 for r in results if r['match']), 'mismatch': sum(1 for r in results if not r['match'])}
    print(json.dumps({'summary': summary, 'results': results}, indent=2))
    sys.exit(0 if summary['mismatch'] == 0 else 1)


if __name__ == '__main__':
    main()
