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
    """Where the selected product's runs live: the anchor, the linked worktree, or for an accepted commit its
    worktree or, after cleanup, the receipt's custody copy."""
    selection = json.loads((out / 'snapshot.json').read_text())
    if selection['kind'] == 'anchor':
        return out / 'cell/work', selection
    if selection['kind'] == 'worktree':
        return out / selection['path'], selection
    receipt_path = out / selection['receipt']
    worktree = locate.host(out, json.loads(receipt_path.read_text()).get('worktree', ''))
    return (worktree if worktree and (worktree / '.devlyn').is_dir() else receipt_path.parent / 'custody'), selection


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


RANK = {'PASS': 0, 'PASS_WITH_ISSUES': 1, 'NEEDS_WORK': 2, 'BLOCKED': 3}


def declared(engine, capture):
    """The verdict a judge's own capture declares, or None when the capture is empty or unparseable."""
    text = capture.read_text(errors='replace') if capture.is_file() else ''
    if engine == 'claude':
        try:
            envelope = json.loads(text)
        except ValueError:
            return None
        if not isinstance(envelope, dict) or envelope.get('type') != 'result' or envelope.get('is_error'):
            return None
        structured = envelope.get('structured_output')
        text = structured.get('verdict', '') if isinstance(structured, dict) else str(envelope.get('result', ''))
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return lines[-1] if lines and lines[-1] in RANK else None


def carriers(archive, state, verify, sub):
    """The final VERIFY round's own records, by content: MECHANICAL results and findings parse; the dispatch record
    names this run and round and the bound seal; each dispatched judge's prompt matches its dispatched digest, its
    role evidence names this run, round and role with a clean exit, and its capture declares a verdict no worse than
    the recorded sub-verdict."""
    round_, problems = verify.get('round', 0), []

    def parsed(name):
        try:
            return json.loads((archive / name).read_text())
        except (OSError, ValueError):
            problems.append(f'{name} missing or unparseable')
            return None
    results = parsed('spec-verify.results.json')
    if not (isinstance(results, dict) and isinstance(results.get('commands'), list)):
        problems.append('MECHANICAL results lack their commands')
    try:
        for line in (archive / 'verify-mechanical.findings.jsonl').read_text().splitlines():
            if line.strip() and not isinstance(json.loads(line), dict):
                raise ValueError
    except (OSError, ValueError):
        problems.append('MECHANICAL findings missing or unparseable')
    dispatch = parsed(f'verify-judge.r{round_}.dispatch.json') or {}
    seal_raw = (archive / 'source-seal.json').read_bytes() if (archive / 'source-seal.json').is_file() else b''
    if (dispatch.get('run_id'), dispatch.get('round')) != (state.get('run_id'), round_):
        problems.append('dispatch record names another run or round')
    if dispatch.get('source_seal_sha256') != hashlib.sha256(seal_raw).hexdigest():
        problems.append('dispatch record is bound to another seal')
    for role, entry in (dispatch.get('roles') or {}).items():
        if entry.get('decision') != 'dispatch':
            continue
        engine, stem = entry.get('engine'), f'{entry.get("engine")}-judge.r{round_}'
        prompt = archive / (stem + '.prompt')
        if not prompt.is_file() or hashlib.sha256(prompt.read_bytes()).hexdigest() != entry.get('prompt_sha256'):
            problems.append(f'{role} prompt does not match its dispatched digest')
        evidence = parsed(stem + '.role-evidence.json') or {}
        if ((evidence.get('run_id'), evidence.get('round'), evidence.get('role')) != (state.get('run_id'), round_, role)
                or evidence.get('exit_code') != 0 or not evidence.get('model_observed')):
            problems.append(f'{role} role evidence does not bind this run, round and a clean observed call')
        verdict = declared(engine, archive / (stem + ('.output.json' if engine == 'claude' else '.stdout')))
        recorded = sub.get('judge' if role == 'primary_judge' else role)
        if verdict is None or recorded not in RANK or RANK[recorded] < RANK[verdict]:
            problems.append(f'{role} capture declares {verdict}, recorded {recorded}')
    summary = parsed('verify-merge.summary.json') or {}
    if {k: v for k, v in (summary.get('source_verdicts') or {}).items() if k in sub} != sub:
        problems.append('merge summary disagrees with sub-verdicts')
    return not problems, problems


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
    root, selection = task_root(out)
    archive, state, archived = final_state(root)
    if selection['kind'] == 'accepted':  # the accepted run itself, wherever it is kept
        receipt = json.loads((out / selection['receipt']).read_text())
        folder = root / '.devlyn/runs' / str((receipt.get('acceptance') or {}).get('run_id'))
        archive, state, archived = ((folder, json.loads((folder / 'pipeline.state.json').read_text()), True)
                                    if (folder / 'pipeline.state.json').is_file() else (None, None, False))
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
    checks['round_carriers'], missing = carriers(archive, state, verify, sub)
    binding = verify.get('source_seal') or {}
    seal_path = archive / 'source-seal.json'
    seal = json.loads(seal_path.read_text()).get('seal') if seal_path.is_file() else None
    raw = seal_path.read_bytes() if seal_path.is_file() else b''
    checks['seal_bound'] = (binding.get('path') == '.devlyn/source-seal.json' and isinstance(seal, dict)
                            and binding.get('sha256') == hashlib.sha256(raw).hexdigest() and binding.get('bytes') == len(raw))
    if selection['kind'] == 'accepted':  # an accepted commit is immutable: its seal must name exactly that commit
        checks['seal_head_is_final_source'] = isinstance(seal, dict) and seal.get('head') == selection['sha']
    else:
        head = git(out, root, 'rev-parse', 'HEAD')
        dirty = git(out, root, 'status', '--porcelain', '--untracked-files=all')
        checks['seal_head_is_final_source'] = isinstance(seal, dict) and seal.get('head') == head and dirty == ''
    tools = shared(out / 'cell/work') or shared(root)  # the installed package is committed in the anchor's baseline
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
