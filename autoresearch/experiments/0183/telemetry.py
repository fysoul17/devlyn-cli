"""Count each native thread once, retaining absent completion counters as unknown."""
from pathlib import Path
import json

REPO=Path(__file__).resolve().parents[3]
EVIDENCE=REPO/'.devlyn/0183'
WORKS=Path('/Users/aipalm/.local/share/nx01/0183-participants')

def collect(draw):
    work=WORKS/draw
    arm=json.loads((EVIDENCE/'runs'/draw/'input.json').read_text())['arm']
    paths=[EVIDENCE/'runs'/draw/'stdout']
    paths += [p for p in (work/'.devlyn').rglob('*') if p.is_file() and
              (p.suffix in ('.jsonl','.stdout') or p.name.endswith('-judge.stdout'))]
    threads={}
    for path in paths:
        tid=None;counts=[]
        for line in path.read_text(errors='replace').splitlines():
            try: event=json.loads(line)
            except json.JSONDecodeError:continue
            if not isinstance(event,dict):continue
            if event.get('type')=='thread.started':tid=event.get('thread_id')
            if event.get('type')=='turn.completed' and isinstance(event.get('usage'),dict):
                counts.append(event['usage'])
        if tid:
            item=dict(thread=tid,path=str(path),turns=counts)
            if tid not in threads or len(counts)>len(threads[tid]['turns']):threads[tid]=item
    keys=sorted({key for t in threads.values() for c in t['turns'] for key in c})
    # A canonical non-JSON judge capture may have no structured usage. Its absence
    # must not turn the observed subset into a whole-run counter claim.
    expected_minimum=6 if arm=='C' else 1
    return dict(draw=draw,threads=list(threads.values()),expected_minimum_threads=expected_minimum,
                whole_run_counters_complete=len(threads)>=expected_minimum and all(t['turns'] for t in threads.values()),
                counters={key:sum(c.get(key,0) for t in threads.values() for c in t['turns']) for key in keys},
                dollars=None,scope='Observed native parent and child thread completion counters; duplicate captures deduplicated by thread id.')

if __name__=='__main__':
    registry=json.loads((EVIDENCE/'REGISTRATION.json').read_text())
    rows=[collect(row['draw']) for row in registry['order']]
    with (EVIDENCE/'TELEMETRY.json').open('x') as stream:json.dump(rows,stream,indent=2)
    print(json.dumps(rows))
