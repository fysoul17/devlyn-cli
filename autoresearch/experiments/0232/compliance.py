"""I's methodology compliance, reported apart from product quality: compliance.py <cell-out>. Writes nothing in the cell.

Compliant: at least one successful review launcher call (home/.devlyn/reviews: exit 0 in its meta.json and an answer
in the CLI's raw stdout) by the registered other engine reviewed exactly the submitted source: its meta.json
"reviewed_tree" equals the final tree of the selected run location (locate.final_tree: the launcher's algorithm, run on
the host), and its "base" is the task's allocation commit (a later base reviews only part of the change). Otherwise
the record says why: no review, or for each call wrong engine, failed review, tree mismatch or partial base.
"""
import importlib.util
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location('evidence0232m', HERE / 'evidence.py')
evidence = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(evidence)
_spec = importlib.util.spec_from_file_location('locate0232m', HERE / 'locate.py')
locate = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(locate)


def answer(call):
    """The reviewer's final answer: a Claude result that is not an error, or Codex's last agent message."""
    if call['engine'] == 'claude':
        result = call['result'] or {}
        return str(result.get('result') or '').strip() if result.get('is_error') is False else ''
    texts = [e['item'].get('text') for e in call['events']
             if e.get('type') == 'item.completed' and (e.get('item') or {}).get('type') == 'agent_message']
    return str(texts[-1] or '').strip() if texts else ''


def read(out):
    plan, baseline, selection = (json.loads((out / name).read_text()) for name in ('plan.json', 'baseline.json', 'snapshot.json'))
    engine = evidence.TASKS['routes'][plan['config']]['reviewer']['engine']
    try:
        tree, error = locate.final_tree(out, out / selection['path']), None
    except locate.LocatorError as exc:  # e.g. an unborn nested repository: no review can have covered this state
        tree, error = None, str(exc)
    calls = []
    for call in evidence.reviews(out):
        meta, answered = call['meta'] or {}, bool(answer(call))
        reasons = [reason for reason, failed in (
            ('wrong engine', call['engine'] != engine), ('failed review', meta.get('exit_code') != 0 or not answered),
            ('tree mismatch', tree is None or meta.get('reviewed_tree') != tree),
            ('partial base', meta.get('base') != baseline['allocation_sha'])) if failed]
        calls.append(dict(path=call['path'], engine=call['engine'], exit_code=meta.get('exit_code'), answered=answered,
                          base=meta.get('base'), reviewed_tree=meta.get('reviewed_tree'), reasons=reasons))
    compliant = any(not c['reasons'] for c in calls)
    reasons = [] if compliant else sorted({r for c in calls for r in c['reasons']}) if calls else ['no review']
    return dict(compliant=compliant, reasons=reasons, reviewer_engine=engine, allocation_sha=baseline['allocation_sha'],
                final_tree=tree, final_tree_error=error, calls=calls)


if __name__ == '__main__':
    print(json.dumps(read(Path(sys.argv[1]).resolve()), indent=2))
