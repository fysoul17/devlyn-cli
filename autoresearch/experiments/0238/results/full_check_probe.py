"""Offline calibration; run from repo root. No model/credential/network use."""
import datetime
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import traceback

HERE=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('runner0238cal',HERE/'runner.py')
r=importlib.util.module_from_spec(spec);spec.loader.exec_module(r)
name=sys.argv[1]
result_dir=HERE/'results'/name;result_dir.mkdir(exist_ok=False)
prediction=sys.argv[2]
r.write(result_dir/'prediction.json',dict(at=datetime.datetime.now(datetime.timezone.utc).isoformat(),prediction=prediction))
root=Path(tempfile.mkdtemp(prefix='0238-full-check-',dir='/Users/aipalm/.local/share/nx01/0237-live'))
control=root/'control';control.mkdir()
old=Path('/Users/aipalm/.local/share/nx01/0237-live/control-discovery')
for tree in ('public','oracle'):
 shutil.copytree(old/tree,control/tree,symlinks=True)
(control/'packages').mkdir()
for relative in ('0234/oracle.js','0234/fixture_oracle.js','0238/f23_precision.py'):
 dst=control/'oracle/experiments'/relative;dst.parent.mkdir(parents=True,exist_ok=True)
 shutil.copyfile(HERE.parent/relative,dst)
r.write(str(control)+'.manifest.json',dict(manifests={name:{str(p.relative_to(control/name)):r.digest(p) for p in (control/name).rglob('*') if p.is_file()} for name in ('public','oracle','packages')}))
runtime=root/'runtime.json'
shutil.copyfile(HERE/'tasks-draft.json',root/'tasks.json')
r.write(runtime,dict(tasks_file=str(root/'tasks.json'),image='sha256:0f472bb41685b7daa5923d51d31983f4b3c70053dd773fdf712bd0dcd6d87998',
 control=str(control),phase='smoke',output=str(root/'out'),auth=str(root/'unused-auth'),sources=str(root/'unused-sources')))
app=r.Runner(runtime)
results=[]
for label in ('noop','positive','deleted'):
 positive=label=='positive'
 out=app.prepare(label,'F23','A','codex')
 if positive:
  work=out/'cell/work'
  for file in (HERE/'calibration/F23/exact-time').rglob('*'):
   if file.is_file():
    shutil.copyfile(file,work/file.relative_to(HERE/'calibration/F23/exact-time'))
  app.frame.prepare.git(work,'add','bin/cli.js','tests/cli.test.js')
  app.frame.prepare.git(work,'commit','-qm','offline positive control')
 if label=='deleted':
  work=out/'cell/work'
  (work/'bin/cli.js').unlink()
  app.frame.prepare.git(work,'add','-u','bin/cli.js')
  app.frame.prepare.git(work,'commit','-qm','offline deleted-product negative control')
 selection=app.frame.locate.locate(out)
 app.unchanged(out)
 raw=[]; original=app.frame.check.in_image
 def captured(*args):
  value=original(*args);raw.append(value);return value
 app.frame.check.in_image=captured
 result=dict(case=label,out=str(out),selection=selection)
 try:
  result['checks']=app.frame.check.check(out,app.runtime)
 except Exception as exc:
  result['error']=str(exc);result['traceback']=traceback.format_exc()
 finally:
  app.frame.check.in_image=original
 result['delivery']=r.delivery.check(out,selection,app.frame.locate,app.packet)
 with tempfile.TemporaryDirectory() as tmp:
  review=app.frame.assess.review_tree(out,Path(tmp))
  before,prompt=app.frame.assess.packet.packet(review)
  caller=r.read(out/'harness/caller.json')
  result['assessment_binding']=dict(tasks_same=app.frame.assess.TASKS is app.tasks,
    original_request_present=caller['request'] in prompt,source_names=sorted(before),
    selected_source_same={key:app.packet.digest(out/'snapshot'/key) for key in before}==before)
 r.write(result_dir/(label+'-raw.json'),raw)
 r.write(result_dir/(label+'.json'),result)
 results.append(result)
 if positive:
  machinery=original(app.runtime,out/'snapshot',['python3','-B',
    '/control/autoresearch/experiments/0238/f23_precision.py','/cell/work','--node','/missing-evaluator-node'])
  r.write(result_dir/'missing-interpreter-raw.json',machinery)
  assert machinery['exit_code']==2 and json.loads(machinery['stdout'])['status']=='STOP',machinery
r.write(result_dir/'summary.json',dict(retained_root=str(root),results=results))
print(json.dumps(dict(retained_root=str(root),results=results),indent=2))
