#!/usr/bin/env python3
"""
measure-static.py — archived static comparison helper for pre-cutover auto-resolve.

Archive note (2026-05-14): this helper reads the deleted
config/skills/devlyn:auto-resolve paths for historical v3-era comparisons. It
is not current solo<pair evidence. Use scripts/static-ab.sh for current prompt
load checks and npx devlyn-cli benchmark audit for pair evidence.

Usage:
    python3 measure-static.py --baseline <ref> --head <ref> [--out FILE]

Measures SKILL.md size, reference-file inventory, legacy-vs-structured artifact
references, and goal-driven XML adoption. Runs in <1 second. No subagent calls.

Output: JSON to stdout or --out file.
"""
import argparse, json, re, subprocess, sys

SKILL_PATH = 'config/skills/devlyn:auto-resolve/SKILL.md'
REF_FILES = [
    'build-gate.md', 'engine-routing.md', 'findings-schema.md',
    'pipeline-state.md', 'pipeline-routing.md',
]
REF_BASE = 'config/skills/devlyn:auto-resolve/references/'


def git_show(ref: str, path: str) -> str | None:
    try:
        return subprocess.check_output(['git', 'show', f'{ref}:{path}'], text=True, stderr=subprocess.DEVNULL)
    except subprocess.CalledProcessError:
        return None


def wc_lines(text: str | None) -> int:
    return len(text.splitlines()) if text else 0


def token_estimate(text: str | None) -> int:
    """Rough ~4 chars/token. Consistent for relative comparison, not for billing."""
    return len(text) // 4 if text else 0


def count_pattern(text: str | None, pattern: str) -> int:
    return len(re.findall(pattern, text)) if text else 0


def measure_ref(ref: str) -> dict:
    skill = git_show(ref, SKILL_PATH)
    refs = {f: git_show(ref, REF_BASE + f) for f in REF_FILES}
    total_lines = wc_lines(skill) + sum(wc_lines(c) for c in refs.values())
    return {
        'skill_lines': wc_lines(skill),
        'skill_tokens_est': token_estimate(skill),
        'references': {f: {'lines': wc_lines(c), 'exists': c is not None} for f, c in refs.items()},
        'total_orchestrator_context_lines': total_lines,
        'legacy_artifact_refs': count_pattern(skill, r'\.devlyn/(BUILD-GATE|EVAL-FINDINGS|BROWSER-RESULTS|CHALLENGE-FINDINGS|done-criteria|SPEC-CONTEXT)\.md'),
        'structured_artifact_refs': count_pattern(skill, r'findings\.jsonl|pipeline\.state\.json'),
        'goal_driven_xml_blocks': count_pattern(skill, r'<(goal|output_contract|quality_bar|harness_principles|engine_routing_convention|autonomy_contract)>'),
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--baseline', required=True)
    p.add_argument('--head', default='HEAD')
    p.add_argument('--out')
    args = p.parse_args()

    baseline = measure_ref(args.baseline)
    head = measure_ref(args.head)

    def delta(key):
        b, h = baseline.get(key), head.get(key)
        if isinstance(b, (int, float)) and isinstance(h, (int, float)):
            return h - b
        return None

    result = {
        'baseline_ref': args.baseline,
        'head_ref': args.head,
        'baseline': baseline,
        'head': head,
        'deltas': {k: delta(k) for k in ['skill_lines', 'skill_tokens_est', 'total_orchestrator_context_lines', 'legacy_artifact_refs', 'structured_artifact_refs', 'goal_driven_xml_blocks']},
    }
    out = json.dumps(result, indent=2)
    if args.out:
        with open(args.out, 'w') as f:
            f.write(out)
    else:
        print(out)


if __name__ == '__main__':
    main()
