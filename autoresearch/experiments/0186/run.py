"""Reuse qualified native transports; add only the focused review/repair treatment."""
from pathlib import Path
import argparse, hashlib, importlib.util, json, math, os, shutil, sys, time
R=Path(__file__).resolve().parents[3]; H=Path(__file__).resolve().parent; E=R/'.devlyn/0186'
SCRATCH=R/'.git/devlyn-completion/de61a898ff4784dd683ba8ef/scratch'; WORKS=R.parent/'0186-participants'
sys.path.insert(0,str(H))
import usage

def module(name,p):
 s=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
launch=module('launch0185',R/'autoresearch/experiments/0185/launch.py')
native=module('native0184',R/'autoresearch/experiments/0184/native.py')
for m in (launch,native):m.EVIDENCE=E;m.E=E;m.SCRATCH=SCRATCH;m.WORKS=WORKS

def put(p,obj):
 p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('x') as f:json.dump(obj,f,indent=2)

def packet(work):
 parts=[(H/'review.md').read_text()]
 for title,p in [('REQUEST',work/'spec.md'),('EXPECTED',work/'spec.expected.json'),('ORIGINAL',E/'source/original.js'),('CURRENT',work/'bin/devlyn.js')]:
  parts.append('\n'+title+'\n'+p.read_text())
 for p in sorted((work/'tests').glob('*.js')):parts.append('\n'+str(p.relative_to(work))+'\n'+p.read_text())
 return '\n'.join(parts)

def main():
 args=argparse.ArgumentParser();args.add_argument('draw');a=args.parse_args()
 registry=json.loads((E/'REGISTRATION.json').read_text())
 row=next(r for r in registry['order'] if r['draw']==a.draw)
 out=E/'runs'/a.draw; work=WORKS/a.draw
 previous=dict(os.environ); started=time.monotonic()
 try:
  sys.argv=['launch.py',a.draw,row['arm'],'install'];launch.main()
 finally:os.environ.clear();os.environ.update(previous)
 result=json.loads((out/'result.json').read_text())
 if row['arm']=='C':return
 (out/'result.json').rename(out/'initial-result.json')
 (out/'sealed-product.json').rename(out/'initial-sealed-product.json')
 initial=out/'initial-product';shutil.copytree(work/'bin',initial/'bin');shutil.copytree(work/'tests',initial/'tests');shutil.copyfile(work/'package.json',initial/'package.json')
 steps=[];quota=result.get('quota_parking');workflow='INCOMPLETE'
 base_process_table=native.controller.process_table; next_check=0
 def observe(timeout):
  nonlocal quota,next_check
  if time.monotonic()>=next_check:
   next_check=time.monotonic()+30
   try:q=usage.read()
   except Exception as exc:quota={'observer_error':repr(exc)};raise OSError('PARKED: quota unavailable') from exc
   if q['park']:quota=q;raise OSError('PARKED: quota reserve')
  return base_process_table(timeout)
 def call(suffix,prompt,review=False):
  nonlocal quota
  q=usage.read()
  if q['park']:quota=q;raise RuntimeError('PARKED: quota reserve')
  budget=math.floor(1800-(time.monotonic()-started))
  if budget<1:raise RuntimeError('composite 1800s budget exhausted')
  if review:budget=min(600,budget)
  native.controller.process_table=observe
  try:answer,meta=native.invoke(a.draw+'-'+suffix,prompt,work=None if review else work,review=review,budget=budget)
  finally:native.controller.process_table=base_process_table
  steps.append({'step':suffix,'meta':meta});return answer
 try:
  if quota or result['error'] or result['exit_code']!=0 or not result['owned_writers_quiescent']:raise RuntimeError('initial run incomplete')
  for i in range(3):
   answer=call('review-'+str(i),packet(work),True)
   text=answer.strip()
   if text.startswith('```'):text='\n'.join(text.splitlines()[1:-1])
   parsed=json.loads(text)
   assert isinstance(parsed,dict) and isinstance(parsed.get('findings'),list)
   assert all(isinstance(f,dict) and f.get('severity') in ('HIGH','MEDIUM','LOW') and all(isinstance(f.get(k),str) and f[k] for k in ('file','problem')) for f in parsed['findings'])
   put(out/('review-'+str(i)+'.json'),parsed)
   if not parsed['findings']:workflow='REVIEW_CLEAN';break
   if i==2:workflow='REVIEW_EXHAUSTED';break
   (work/'.devlyn/focused-review.txt').write_text(answer)
   prompt=(out/'prompt.txt').read_text()+' Do not invoke resolve or new agents. Read .devlyn/focused-review.txt. Validate every finding against the request and actual source; repair substantiated in-scope defects, reject unsupported claims with evidence. Run required checks and scoped cleanup after changes. Preserve all supplied inputs. The review is evidence, not permission to expand scope.'
   call('repair-'+str(i),prompt)
 except Exception as exc:result['focused_error']=repr(exc)
 result.update(quota_parking=quota,focused_workflow=workflow,focused_steps=steps,initial_wrapper_return_seconds=result['wrapper_return_seconds'],composite_seconds=time.monotonic()-started)
 result['wrapper_return_seconds']=result['composite_seconds']
 # Underlying per-step controllers seal quiescence before returning, including stop paths.
 step_results=[json.loads(p.read_text()) for p in (E/'runs').glob(a.draw+'-*/result.json')]
 result['owned_writers_quiescent']=result['owned_writers_quiescent'] and all(x['owned_writers_quiescent'] for x in step_results)
 put(out/'result.json',result)
 put(out/'sealed-product.json',{str(p.relative_to(work)):hashlib.sha256(p.read_bytes()).hexdigest() for folder in ('bin','tests') for p in (work/folder).rglob('*') if p.is_file()})
 (out/'final-diff.patch').write_bytes(launch.run(['git','diff',json.loads((out/'input.json').read_text())['baseline'],'--binary'],work).stdout)
 print(json.dumps({'draw':a.draw,'workflow':workflow,'seconds':result['composite_seconds'],'quota':quota}),flush=True)
if __name__=='__main__':main()
