"""Show this cell's observed usage: the root controller's accounting calculation over the same data.

Advisory only. Calls still in flight are not yet counted; compare with the targets in your instructions.
"""
import argparse
import importlib.util
import json
import math
from pathlib import Path
import time

argparse.ArgumentParser(description=__doc__).parse_args()
spec = importlib.util.spec_from_file_location(
    'native_cell', '/control/autoresearch/experiments/0210/native_cell.py')
cell = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cell)
sessions = Path.home() / '.codex/sessions'
roots = [json.loads(path.open().readline())['payload'] for path in sessions.rglob('*.jsonl')]
owner = [meta['id'] for meta in roots if meta.get('source') == 'exec']
if len(owner) != 1:
    raise SystemExit('cannot identify the single owner session; usage unknown')
now = time.monotonic()
native = cell.accounting.Rollouts(sessions, owner[0], input_limit=math.inf, output_limit=math.inf,
                                  dispatch_limit=math.inf, stale_seconds=math.inf, started=now).poll(now)
review, pending = cell.reviews(Path('/work'))
print(json.dumps(dict(
    observed_input_tokens_cache_inclusive=native['totals']['input_tokens'] + review['input_tokens'],
    observed_output_tokens=native['totals']['output_tokens'] + review['output_tokens'],
    model_invocations=native['dispatches'] + review['calls'],
    reviews_started=review['calls'], reviews_pending=len(pending)), indent=2))
