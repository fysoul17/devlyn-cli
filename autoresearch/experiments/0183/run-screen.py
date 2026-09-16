"""Sequential registered draws; a contract/infrastructure failure stops the screen."""
from pathlib import Path
import json, subprocess, sys

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[2]
EVIDENCE=REPO/'.devlyn/0183'
registry=json.loads((EVIDENCE/'REGISTRATION.json').read_text())
for row in registry['order']:
    subprocess.run([sys.executable,str(HERE/'launch.py'),row['draw'],row['arm'],row['case']],check=True)
    result=json.loads((EVIDENCE/'runs'/row['draw']/'result.json').read_text())
    if result['error'] or not result['owned_writers_quiescent']:
        raise SystemExit('STOP: infrastructure/owned-process result requires inspection: '+row['draw'])
    if row['arm']=='C':
        work=Path('/Users/aipalm/.local/share/nx01/0183-participants')/row['draw']
        archived=list((work/'.devlyn/runs').glob('*/pipeline.state.json'))
        if not archived:
            raise SystemExit('STOP: actual full control did not archive; preserve and inspect: '+row['draw'])
print('All registered draws returned; sealed external assessment has not run.',flush=True)
