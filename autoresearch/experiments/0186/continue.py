"""Authorized completion of the sealed repair; old censored comparison is immutable."""
from pathlib import Path
import datetime,hashlib,importlib.util,json,math,os,sys,time
R=Path(__file__).resolve().parents[3];H=Path(__file__).resolve().parent;E=R/'.devlyn/0186-continuation'
W=R.parent/'0186-participants/instructions-2-B-continuation'
S=R/'.git/devlyn-completion/de61a898ff4784dd683ba8ef/scratch'
spec=importlib.util.spec_from_file_location('native',R/'autoresearch/experiments/0184/native.py');native=importlib.util.module_from_spec(spec);spec.loader.exec_module(native)
native.E=E;native.SCRATCH=S

def seal():return {str(p.relative_to(W)):hashlib.sha256(p.read_bytes()).hexdigest() for d in ('bin','tests') for p in (W/d).rglob('*') if p.is_file()}
def packet():
 parts=[(H/'review.md').read_text()]
 for title,p in [('REQUEST',W/'spec.md'),('EXPECTED',W/'spec.expected.json'),('ORIGINAL',R/'.devlyn/0186/source/original.js'),('CURRENT',W/'bin/devlyn.js')]:parts.append('\n'+title+'\n'+p.read_text())
 for p in sorted((W/'tests').glob('*.js')):parts.append('\n'+str(p.relative_to(W))+'\n'+p.read_text())
 return '\n'.join(parts)
def main():
 reg=json.loads((E/'REGISTRATION.json').read_text())
 for p,h in reg['inputs'].items():assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==h,p
 start=time.monotonic();steps=[];verdict='INCOMPLETE';error=None
 try:
  for i in range(3):
   remaining=math.floor(1800-(time.monotonic()-start));assert remaining>0,'continuation budget exhausted'
   answer,meta=native.invoke('review-'+str(i),packet(),review=True,budget=min(600,remaining));steps.append({'step':'review-'+str(i),'meta':meta})
   text=answer.strip()
   if text.startswith('```'):text='\n'.join(text.splitlines()[1:-1])
   review=json.loads(text);assert isinstance(review,dict) and isinstance(review.get('findings'),list)
   assert all(isinstance(f,dict) and f.get('severity') in ('HIGH','MEDIUM','LOW') and all(isinstance(f.get(k),str) and f[k] for k in ('file','problem')) for f in review['findings'])
   native.put(E/('review-'+str(i)+'.json'),review)
   if not review['findings']:verdict='REVIEW_CLEAN';break
   if i==2:verdict='REVIEW_EXHAUSTED';break
   (W/'.devlyn').mkdir(exist_ok=True);(W/'.devlyn/review.txt').write_text(answer)
   prompt='Read AGENTS.md, spec.md and spec.expected.json. Finish this retained implementation directly. Read .devlyn/review.txt, validate every claim and repair substantiated in-scope defects only. Preserve all supplied inputs, unrelated bytes and the allocated branch. Run required checks and meaningful regressions, scoped cleanup and recheck. No resolve, new agents, network task operations, dependencies, publication or user/global changes. The outer owner owns delivery. Do not allocate again. Do not access research/sibling/prior results outside this checkout. Return one terminal outcome.'
   remaining=math.floor(1800-(time.monotonic()-start));assert remaining>0,'continuation budget exhausted'
   os.environ['TMPDIR']=json.loads((E/'ownership.json').read_text())['scratch']
   answer,meta=native.invoke('repair-'+str(i),prompt,work=W,budget=remaining);steps.append({'step':'repair-'+str(i),'meta':meta})
   native.put(E/('product-after-repair-'+str(i)+'.json'),seal())
 except Exception as exc:error=repr(exc)
 native.put(E/'SEALED-PRODUCT.json',seal());native.put(E/'RESULT.json',{'verdict':verdict,'error':error,'seconds':time.monotonic()-start,'steps':steps,'percentage_parking_disabled_by_user':True})
 print(json.dumps({'verdict':verdict,'error':error,'seconds':time.monotonic()-start}),flush=True)
if __name__=='__main__':main()
