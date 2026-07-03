#!/usr/bin/env python3
"""skill-token-gauge.py — per-skill prompt-token cost gauge.

Zero-dependency approximation: no tokenizer is vendored, so every file gets
two independent estimates — chars/4 and words*1.3 — printed side by side
instead of one number dressed up as exact.

Scope: SKILL.md (cold-start cost) + references/** (progressive-disclosure
cost) for every skill directory (one containing a top-level SKILL.md) under
config/skills/ and optional-skills/, plus config/skills/_shared/**/*.md and
the root CLAUDE.md / AGENTS.md.

A gauge, not a gate: reports current cost, does not compare, threshold, or
fail. See scripts/static-ab.sh for before/after delta checks.

Usage:
    python3 scripts/skill-token-gauge.py [--json]
"""
import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILL_BASES = ['config/skills', 'optional-skills']
SHARED_DIR = 'config/skills/_shared'
ROOT_DOCS = ['CLAUDE.md', 'AGENTS.md']
METHOD = 'tokens_c4 = chars/4, tokens_w13 = words*1.3 (both approximations; no tokenizer vendored)'


def measure(path: Path) -> dict:
    text = path.read_text(encoding='utf-8', errors='replace')
    return {
        'lines': len(text.splitlines()),
        'chars': len(text),
        'words': len(text.split()),
        'tokens_c4': len(text) // 4,
        'tokens_w13': round(len(text.split()) * 1.3),
    }


def sum_totals(files: list[dict]) -> dict:
    keys = ['lines', 'chars', 'words', 'tokens_c4', 'tokens_w13']
    return {k: sum(f[k] for f in files) for k in keys}


def rel(path: Path) -> str:
    return str(path.relative_to(REPO_ROOT))


def collect_skills() -> list[dict]:
    skills = []
    for base in SKILL_BASES:
        base_dir = REPO_ROOT / base
        if not base_dir.is_dir():
            continue
        for skill_dir in sorted(base_dir.iterdir()):
            skill_md = skill_dir / 'SKILL.md'
            if not skill_dir.is_dir() or not skill_md.is_file():
                continue
            files = [{'path': rel(skill_md), 'role': 'cold_start', **measure(skill_md)}]
            refs_dir = skill_dir / 'references'
            if refs_dir.is_dir():
                for ref_file in sorted(p for p in refs_dir.rglob('*') if p.is_file()):
                    files.append({'path': rel(ref_file), 'role': 'reference', **measure(ref_file)})
            skills.append({'name': skill_dir.name, 'base': base, 'files': files, 'totals': sum_totals(files)})
    return skills


def collect_shared() -> dict:
    shared_dir = REPO_ROOT / SHARED_DIR
    files = []
    if shared_dir.is_dir():
        for md_file in sorted(shared_dir.rglob('*.md')):
            files.append({'path': rel(md_file), 'role': 'shared', **measure(md_file)})
    return {'files': files, 'totals': sum_totals(files)}


def collect_root() -> dict:
    files = []
    for name in ROOT_DOCS:
        doc = REPO_ROOT / name
        if doc.is_file():
            files.append({'path': rel(doc), 'role': 'root', **measure(doc)})
    return {'files': files, 'totals': sum_totals(files)}


def display_path(file_path: str, group_prefix: str) -> str:
    return file_path[len(group_prefix):] if file_path.startswith(group_prefix) else file_path


def print_table(skills: list[dict], shared: dict, root: dict, grand_total: dict) -> None:
    groups = [(s['name'], f"{s['base']}/{s['name']}/", s['files'], s['totals']) for s in skills]
    groups.append(('_shared', f'{SHARED_DIR}/', shared['files'], shared['totals']))
    groups.append(('(root)', '', root['files'], root['totals']))

    rows = [('SKILL', 'FILE', 'ROLE', 'LINES', 'CHARS', 'TOK≈c/4', 'TOK≈w*1.3')]
    for label, prefix, files, totals in groups:
        for f in files:
            rows.append((label, display_path(f['path'], prefix), f['role'], f['lines'], f['chars'], f['tokens_c4'], f['tokens_w13']))
        rows.append((label, 'SUBTOTAL', '', totals['lines'], totals['chars'], totals['tokens_c4'], totals['tokens_w13']))
    rows.append(('GRAND TOTAL', '', '', grand_total['lines'], grand_total['chars'], grand_total['tokens_c4'], grand_total['tokens_w13']))

    widths = [max(len(str(row[i])) for row in rows) for i in range(7)]
    fmt = '  '.join(f'{{:<{w}}}' if i < 3 else f'{{:>{w}}}' for i, w in enumerate(widths))

    print(f'# {METHOD}')
    print()
    print(fmt.format(*rows[0]))
    print(fmt.format(*['-' * w for w in widths]))
    prev_label = None
    for row in rows[1:-1]:
        if prev_label is not None and row[0] != prev_label:
            print()
        print(fmt.format(*row))
        prev_label = row[0]
    print()
    print(fmt.format(*rows[-1]))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--json', action='store_true', help='emit JSON instead of the stdout table')
    args = parser.parse_args()

    skills = collect_skills()
    shared = collect_shared()
    root = collect_root()
    all_files = [f for s in skills for f in s['files']] + shared['files'] + root['files']
    grand_total = sum_totals(all_files)

    if args.json:
        json.dump({'method': METHOD, 'skills': skills, 'shared': shared, 'root': root, 'grand_total': grand_total}, sys.stdout, indent=2)
        print()
    else:
        print_table(skills, shared, root, grand_total)


if __name__ == '__main__':
    main()
