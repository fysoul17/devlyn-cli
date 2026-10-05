"""Operator summary (not apparatus): summary.py <cells.tsv>. One line per cell from its verdict, plus the SMOKE
checks §6 names that verdicts do not carry: I's review launches and any Bash timeout or backgrounding of them."""
import json
from pathlib import Path
import sys

OUT = Path.home() / '.local/share/nx01/0232-live/out'

for line in Path(sys.argv[1]).read_text().splitlines():
    if not line or line.startswith('#'):
        continue
    name, task, arm, config = line.split()[:4]
    path = OUT / f'verdict-{name}.json'
    if not path.exists():
        print(f'{name}: no verdict')
        continue
    v = json.loads(path.read_text())
    fields = dict(status=v.get('status'), reason=v.get('reason'), owner=v.get('owner_status'), s=v.get('owner_seconds'),
                  identity=(v.get('identity') or {}).get('status'), usage=v.get('usage'), input=v.get('input_tokens'),
                  output=v.get('output_tokens'), teardown=v.get('teardown'), trace_mb=round((v.get('trace_bytes') or 0) / 2**20, 1),
                  snapshot=(v.get('snapshot') or {}).get('kind'), public=v.get('product_check_pass'),
                  oracle=[r['status'] for r in v.get('oracle') or []], scope=len(v.get('scope_violations') or []))
    if arm == 'I':
        c = v.get('compliance') or {}
        reviews = sorted(p.name for p in (OUT / name / 'home/.devlyn/reviews').glob('*')) if (OUT / name).exists() else []
        stream = (OUT / name / 'run/stdout').read_text(errors='replace') if (OUT / name / 'run/stdout').exists() else ''
        fields.update(compliant=c.get('compliant'), reasons=c.get('reasons'), reviews=reviews,
                      timed_out=stream.count('Command timed out'), backgrounded=stream.count('moved to the background'))
    if arm == 'F':
        fields['obligations'] = (v.get('obligations') or {}).get('satisfied')
    print(name, json.dumps(fields))
