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
import shutil
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location('locate0231', HERE / 'locate.py')
locate = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(locate)
_spec = importlib.util.spec_from_file_location('packet0222o', HERE.parent / '0222/packet.py')
packet = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(packet)
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


def files_of(root, names):
    """packet.tree of the named files under root (read as bytes; nothing executes)."""
    with tempfile.TemporaryDirectory() as temp:
        for name in names:
            source, target = root / name, Path(temp) / name
            if source.is_symlink() or source.is_file():
                target.parent.mkdir(parents=True, exist_ok=True)
                target.symlink_to(source.readlink()) if source.is_symlink() else shutil.copy2(source, target)
        return packet.tree(Path(temp))


def head_tree(out, root):
    """The task tree's HEAD commit and its tracked content, read with exec-free host Git."""
    anchor = out / 'cell/work'
    gitdir = None if root == anchor else next((d for d in (anchor / '.git/worktrees').iterdir()
                                               if locate.host(out, (d / 'gitdir').read_text().strip()) == root / '.git'), None)
    command = ['git', *locate.SAFE] + (['--git-dir', str(gitdir)] if gitdir else ['-C', str(anchor)])
    head = subprocess.run([*command, 'rev-parse', 'HEAD'], capture_output=True, text=True, env=locate.ENV).stdout.strip()
    with tempfile.TemporaryDirectory() as temp:
        return head, packet.tree(locate.raw_tree(command, head, Path(temp)))


def live_layout(archive, root, temp):
    """The pre-archive layout the frozen helpers expect: the task's files with the run's records as its .devlyn."""
    work = Path(temp) / 'work'
    shutil.copytree(root, work, symlinks=True, ignore=lambda folder, names: [n for n in names if n in ('.git', '.devlyn')
                                                                             and Path(folder) == root])
    shutil.copytree(archive, work / '.devlyn', symlinks=True)
    return work / '.devlyn'


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


def frozen(plan):
    """The arm's own helpers from the frozen control tree: never code a participant could have rewritten."""
    return Path(plan['control']).parent / 'packages' / plan['arm'] / 'package/config/skills/_shared'


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


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None


def carriers(archive, root, state, verify, sub, merge):
    """The final VERIFY round's own records, by binding and content:
    - the dispatch record matches state's binding, names this run, round and seal, dispatches the primary judge and
      either dispatches the pair or records the automatic skip;
    - each dispatched judge's role evidence and every artifact it lists match state's bindings; its prompt and argv
      match the dispatch record; its evidence names this run, round and role with a clean observed call; its capture
      declares a verdict no better than the recorded sub-verdict;
    - MECHANICAL's verdict, derived with the arm's frozen merge helpers from its findings and evidence, is no better
      than recorded, and the merged verdict is the worst sub-verdict."""
    round_, problems = verify.get('round', 0), []

    def parsed(path):
        try:
            return json.loads(path.read_text())
        except (OSError, ValueError):
            problems.append(f'{path.name} missing or unparseable')
            return None
    binding = verify.get('dispatch') or {}
    dispatch_file = archive / Path(str(binding.get('path', ''))).name
    if sha(dispatch_file) != binding.get('sha256'):
        problems.append('dispatch record does not match its state binding')
    dispatch = parsed(dispatch_file) or {}
    if (dispatch.get('run_id'), dispatch.get('round')) != (state.get('run_id'), round_):
        problems.append('dispatch record names another run or round')
    if dispatch.get('source_seal_sha256') != sha(archive / 'source-seal.json'):
        problems.append('dispatch record is bound to another seal')
    roles = dispatch.get('roles') or {}
    if (roles.get('primary_judge') or {}).get('decision') != 'dispatch':
        problems.append('primary judge was not dispatched')
    pair = roles.get('pair_judge') or {}
    if not (pair.get('decision') == 'dispatch' or (pair.get('decision') == 'skip' and pair.get('reason') == AUTO_SKIP)):
        problems.append('pair judge neither dispatched nor automatically skipped')
    bound_evidence = verify.get('role_evidence') or {}
    for role in ('primary_judge', 'pair_judge'):
        entry = roles.get(role) or {}
        if entry.get('decision') != 'dispatch':
            continue
        engine, stem, bound = entry.get('engine'), f'{entry.get("engine")}-judge.r{round_}', bound_evidence.get(role) or {}
        evidence_file = archive / f'{stem}.role-evidence.json'
        if not bound or sha(evidence_file) != bound.get('sha256'):
            problems.append(f'{role} role evidence does not match its state binding')
        for artifact in bound.get('artifacts', ()):
            if sha(archive / Path(artifact['path']).name) != artifact['sha256']:
                problems.append(f'{role} artifact {Path(artifact["path"]).name} does not match its binding')
        if sha(archive / f'{stem}.prompt') != entry.get('prompt_sha256'):
            problems.append(f'{role} prompt does not match its dispatched digest')
        if parsed(archive / f'{stem}.argv.json') != entry.get('argv'):
            problems.append(f'{role} argv does not match the dispatch record')
        evidence = parsed(evidence_file) or {}
        if ((evidence.get('run_id'), evidence.get('round'), evidence.get('role')) != (state.get('run_id'), round_, role)
                or evidence.get('exit_code') != 0 or not evidence.get('model_observed')):
            problems.append(f'{role} role evidence does not bind this run, round and a clean observed call')
        verdict = declared(engine, archive / (stem + ('.output.json' if engine == 'claude' else '.stdout')))
        recorded = sub.get('judge' if role == 'primary_judge' else role)
        if verdict is None or recorded not in RANK or RANK[recorded] < RANK[verdict]:
            problems.append(f'{role} capture declares {verdict}, recorded {recorded}')
    derived = 'PASS'
    if not (archive / 'spec-verify.results.json').is_file():
        problems.append('MECHANICAL results are missing')
    try:
        for line in (archive / 'verify-mechanical.findings.jsonl').read_text().splitlines():
            if not line.strip():
                continue
            item = merge['loads_strict_json'](line)
            if not (isinstance(item, dict) and isinstance(item.get('id'), str) and isinstance(item.get('severity'), str)):
                raise ValueError(f'malformed MECHANICAL finding {line[:80]!r}')
            derived = merge['worse'](derived, merge['RANK_VERDICT'][merge['finding_rank'](item)])
        with tempfile.TemporaryDirectory() as temp:
            devlyn = live_layout(archive, root, temp)
            if merge['mechanical_evidence_violation'](devlyn) is not None:
                derived = 'BLOCKED'
            outcome = merge['mechanical_evidence_outcome'](devlyn)
            if outcome is not None:
                derived = merge['worse'](derived, outcome['verdict'])
    except (OSError, ValueError, KeyError, TypeError) as exc:
        problems.append(f'MECHANICAL evidence cannot be derived: {exc}')
    if sub.get('mechanical') not in RANK or RANK[sub['mechanical']] < RANK.get(derived, 3):
        problems.append(f'MECHANICAL derives {derived}, recorded {sub.get("mechanical")}')
    worst = max((sub.get(k) for k in ('mechanical', 'judge', 'pair_judge') if sub.get(k)), key=lambda v: RANK.get(v, 3), default=None)
    summary = parsed(archive / 'verify-merge.summary.json') or {}
    if verify.get('verdict') != worst or summary.get('verdict') != worst:
        problems.append(f'merged verdict is not the worst sub-verdict ({worst})')
    return not problems, problems


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
    checks['round_carriers'], missing = carriers(archive, root, state, verify, sub,
                                                 runpy.run_path(str(frozen(plan) / 'verify-merge-findings.py')))
    final_verdict = (phases.get('final_report') or {}).get('verdict')
    allowed = {verify.get('verdict')} | ({'BLOCKED:repair-budget-exhausted'} if verify.get('verdict') == 'NEEDS_WORK' else set())
    checks['final_verdict_derived'] = final_verdict in allowed
    binding = verify.get('source_seal') or {}
    seal_path = archive / 'source-seal.json'
    seal = json.loads(seal_path.read_text()).get('seal') if seal_path.is_file() else None
    raw = seal_path.read_bytes() if seal_path.is_file() else b''
    checks['seal_bound'] = (binding.get('path') == '.devlyn/source-seal.json' and isinstance(seal, dict)
                            and binding.get('sha256') == hashlib.sha256(raw).hexdigest() and binding.get('bytes') == len(raw))
    if selection['kind'] == 'accepted':  # an accepted commit is immutable: its seal must name exactly that commit
        checks['seal_head_is_final_source'] = isinstance(seal, dict) and seal.get('head') == selection['sha']
    else:  # no change after the seal: Git's view of the tree equals its HEAD commit, compared without running Git status
        head, committed = head_tree(out, root)
        current = files_of(root, locate.tree_files(out, root))
        checks['seal_head_is_final_source'] = isinstance(seal, dict) and seal.get('head') == head and current == committed
    tools = frozen(plan)
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
