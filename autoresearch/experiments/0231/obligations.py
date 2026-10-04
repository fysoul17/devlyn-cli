"""Obligation meter (0225:137; 0231 "Metrics"): obligations.py <cell-out>. Binding for the candidate, reported for
the control. Keyed on obligations, never on phase names:

- VERIFY's final round reviewed the final source: completed, its MECHANICAL evidence and primary judge returned
  review verdicts, and the pair judge did too unless it was skipped automatically for an unavailable engine;
- the MECHANICAL seal is bound and its head is the final source, with no change after it;
- FINAL_REPORT completed, its report digest is bound, and the arm's own terminal-claim check is CLEAN.

The report digest and the terminal classification use the arm's own installed functions (they define those encodings);
everything else is read here.
"""
import hashlib
import importlib.util
import json
from pathlib import Path
import runpy
import subprocess
import sys

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location('locate0231', HERE / 'locate.py')
locate = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(locate)
REVIEWED = {'PASS', 'PASS_WITH_ISSUES', 'NEEDS_WORK'}
AUTO_SKIP = 'auto_pair_other_engine_unavailable'


def task_root(out):
    selection = json.loads((out / 'snapshot.json').read_text())
    if selection['kind'] == 'anchor':
        return out / 'cell/work'
    if selection['kind'] == 'worktree':
        return out / selection['path']
    receipt = json.loads((out / selection['receipt']).read_text())
    return locate.host(out, receipt['worktree'])


def git(out, root, *args):
    """Git in the anchor or in a linked worktree whose .git file names a container path."""
    anchor = out / 'cell/work'
    if root == anchor:
        command = ['git', '-C', str(root), *args]
    else:
        gitdir = next((d for d in (anchor / '.git/worktrees').iterdir()
                       if locate.host(out, (d / 'gitdir').read_text().strip()) == root / '.git'), None)
        if gitdir is None:
            return None
        command = ['git', '--git-dir', str(gitdir), '--work-tree', str(root), *args]
    done = subprocess.run(command, capture_output=True, text=True)
    return done.stdout.strip() if done.returncode == 0 else None


def final_state(root):
    """The final invocation: the newest of the archived runs and the live state. A newer live run that never archived
    has not finished its report, so it is the final invocation and it is unfinished."""
    candidates = []
    for path in root.glob('.devlyn/runs/*/pipeline.state.json'):
        candidates.append((json.loads(path.read_text()).get('started_at') or '', path.parent, True))
    live = root / '.devlyn/pipeline.state.json'
    if live.is_file():
        candidates.append((json.loads(live.read_text()).get('started_at') or '', root / '.devlyn', False))
    if not candidates:
        return None, None, False
    _, folder, archived = max(candidates, key=lambda c: (c[0], c[2]))
    return folder, json.loads((folder / 'pipeline.state.json').read_text()), archived


def carriers(archive, round_, sub):
    """The final VERIFY round's own records: MECHANICAL evidence, the dispatch record, each dispatched judge's prompt,
    argv, role evidence and capture, and a merge summary that agrees with the recorded sub-verdicts."""
    missing = [name for name in ('spec-verify.results.json', 'verify-mechanical.findings.jsonl', 'verify-merge.summary.json',
                                 f'verify-judge.r{round_}.dispatch.json') if not (archive / name).is_file()]
    if missing:
        return False, missing
    dispatch = json.loads((archive / f'verify-judge.r{round_}.dispatch.json').read_text())
    for role, entry in (dispatch.get('roles') or {}).items():
        if entry.get('decision') != 'dispatch':
            continue
        stem = f'{entry.get("engine")}-judge.r{round_}'
        capture = '.output.json' if entry.get('engine') == 'claude' else '.stdout'
        missing += [stem + suffix for suffix in ('.prompt', '.argv.json', '.role-evidence.json', capture)
                    if not (archive / (stem + suffix)).is_file()]
    summary = json.loads((archive / 'verify-merge.summary.json').read_text())
    agrees = {k: v for k, v in (summary.get('source_verdicts') or {}).items() if k in sub} == sub
    return not missing and agrees, missing + ([] if agrees else ['merge summary disagrees with sub-verdicts'])


def shared(root):
    return next((d for d in (root / '.claude/skills/_shared', root / '.agents/skills/_shared') if d.is_dir()), None)


def pair_skipped(archive, round_):
    for path in archive.glob(f'verify-judge.r{round_}.dispatch.json'):
        roles = (json.loads(path.read_text()).get('roles') or {})
        pair = roles.get('pair_judge') or {}
        return pair.get('decision') == 'skip' and pair.get('reason') == AUTO_SKIP
    return False


def meter(out):
    plan = json.loads((out / 'plan.json').read_text())
    root = task_root(out)
    archive, state, archived = final_state(root)
    checks = {}
    if state is None:
        return dict(binding=plan['arm'] == 'candidate', satisfied=False, checks=dict(state_present=False))
    phases = state.get('phases') or {}
    verify, final = phases.get('verify') or {}, phases.get('final_report') or {}
    sub = verify.get('sub_verdicts') or {}
    checks['archived'] = archived
    checks['verify_reviewed'] = bool(verify.get('completed_at')) and verify.get('verdict') in REVIEWED
    checks['mechanical_reviewed'] = sub.get('mechanical') in REVIEWED
    checks['primary_judge_reviewed'] = sub.get('judge') in REVIEWED
    checks['pair_judge_reviewed'] = sub.get('pair_judge') in REVIEWED or pair_skipped(archive, verify.get('round', 0))
    checks['round_carriers'], missing = carriers(archive, verify.get('round', 0), sub)
    binding = verify.get('source_seal') or {}
    seal_path = archive / 'source-seal.json'
    seal = json.loads(seal_path.read_text()).get('seal') if seal_path.is_file() else None
    raw = seal_path.read_bytes() if seal_path.is_file() else b''
    checks['seal_bound'] = (binding.get('path') == '.devlyn/source-seal.json' and isinstance(seal, dict)
                            and binding.get('sha256') == hashlib.sha256(raw).hexdigest() and binding.get('bytes') == len(raw))
    head = git(out, root, 'rev-parse', 'HEAD')
    dirty = git(out, root, 'status', '--porcelain', '--untracked-files=all')
    checks['seal_head_is_final_source'] = isinstance(seal, dict) and seal.get('head') == head and dirty == ''
    tools = shared(root)
    try:
        digest = runpy.run_path(str(tools / 'state-phase-write.py'))['final_report_digest'](
            state, archive, str(archive / 'final-report.md'))
        checks['report_bound'] = bool(final.get('completed_at')) and final.get('output_sha256') == digest
    except (SystemExit, ValueError, OSError, KeyError, TypeError):
        checks['report_bound'] = False
    try:
        classifier = runpy.run_path(str(tools / 'terminal-claim-check.py'))['classify_state_bytes']
        state_file = archive / 'pipeline.state.json'
        classification, _ = classifier(root, state_file, state_file.read_bytes(), archived=archived)
        checks['terminal_clean'] = classification.status == 'CLEAN'
    except (SystemExit, ValueError, OSError, KeyError, TypeError, AttributeError):
        checks['terminal_clean'] = False
    return dict(binding=plan['arm'] == 'candidate', satisfied=all(checks.values()), checks=checks, missing=missing,
                run_id=state.get('run_id'), verify_verdict=verify.get('verdict'), final_verdict=final.get('verdict'),
                sub_verdicts=sub, phases=sorted(phases))


if __name__ == '__main__':
    print(json.dumps(meter(Path(sys.argv[1]).resolve()), indent=2))
