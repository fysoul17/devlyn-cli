"""Reuse frozen research machinery with a separate registry and fresh roots."""
from pathlib import Path
import importlib.util, json, sys

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[3]
EVIDENCE=REPO/'.devlyn/0183-followup'
WORKS=Path('/Users/aipalm/.local/share/nx01/0183-followup-participants')

def module(name):
    path=HERE.parent/(name+'.py')
    spec=importlib.util.spec_from_file_location('followup_'+name,path)
    loaded=importlib.util.module_from_spec(spec);spec.loader.exec_module(loaded)
    loaded.EVIDENCE=EVIDENCE;loaded.WORKS=WORKS
    return loaded

def main():
    action=sys.argv[1]
    if action=='launch':
        launch=module('launch');registry=json.loads((EVIDENCE/'REGISTRATION.json').read_text())
        for row in registry['order']:
            sys.argv=['launch.py',row['draw'],row['arm'],row['case']]
            launch.main()
            result=json.loads((EVIDENCE/'runs'/row['draw']/'result.json').read_text())
            if result['error'] or not result['owned_writers_quiescent']:
                raise SystemExit('STOP: external process/observation failure: '+row['draw'])
        print('All six follow-up draws returned; assessment pending.',flush=True)
    elif action=='assess':module('assess').main()
    elif action=='telemetry':
        telemetry=module('telemetry');registry=json.loads((EVIDENCE/'REGISTRATION.json').read_text())
        rows=[telemetry.collect(row['draw']) for row in registry['order']]
        with (EVIDENCE/'TELEMETRY.json').open('x') as stream:json.dump(rows,stream,indent=2)
        print('Recorded parent/child telemetry with completeness flags')
    else:raise SystemExit('expected launch|assess|telemetry')

if __name__=='__main__':main()
