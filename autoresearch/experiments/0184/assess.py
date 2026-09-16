"""Assess only after all planned outputs are sealed; no feedback to participants."""
from pathlib import Path
import hashlib,importlib.util,json,subprocess,sys,tempfile,shutil,time

HERE=Path(__file__).resolve().parent;REPO=HERE.parents[2];E=REPO/'.devlyn/0184';WORKS=REPO.parent/'0184-participants'
spec=importlib.util.spec_from_file_location('check',HERE/'check.py');check=importlib.util.module_from_spec(spec);spec.loader.exec_module(check)
REL=check.REL;SCRATCH=check.SCRATCH

def assess(name,case,expected_seal):
    work=WORKS/name;seed=E/'inputs'/case
    for path,digest in expected_seal.items():assert hashlib.sha256((work/path).read_bytes()).hexdigest()==digest,(name,path)
    supplied_preserved=all((work/p.relative_to(seed)).is_file() and p.read_bytes()==(work/p.relative_to(seed)).read_bytes() for p in seed.rglob('*') if p.is_file() and p.relative_to(seed)!=REL)
    baseline=json.loads((E/(name.replace('-initial','')+'.initial.json' if name.endswith('-initial') else name+'.branch.json')).read_text())['baseline']
    changed=subprocess.check_output(['git','diff',baseline,'--name-only'],cwd=work,text=True).splitlines()
    new=subprocess.check_output(['git','ls-files','--others','--exclude-standard'],cwd=work,text=True).splitlines()
    allowed={str(p.relative_to(seed)) for p in seed.rglob('*')}|{'tests/test_regression.py'}
    extras=[str(p.relative_to(work)) for p in work.rglob('*') if not any(x in p.relative_to(work).parts for x in ('.git','.devlyn')) and str(p.relative_to(work)) not in allowed]
    scope=not extras and all(p in (str(REL),'tests/test_regression.py') for p in changed+new)
    debris=[str(p.relative_to(work)) for p in work.rglob('*') if p.is_file() and not any(x in p.relative_to(work).parts for x in ('.git','.devlyn')) and (p.suffix=='.pyc' or '__pycache__' in p.parts)]
    cli=check.check(case,(work/REL).read_bytes())
    start=time.monotonic()
    with tempfile.TemporaryDirectory(prefix='supplied-',dir=SCRATCH) as temp:
        copy=Path(temp)/'work';shutil.copytree(seed,copy);shutil.copyfile(work/REL,copy/REL)
        smoke=subprocess.run([sys.executable,'-B','-m','unittest','discover','-s','tests','-v'],cwd=copy,capture_output=True,text=True,timeout=30)
    review=None
    if not name.endswith('-initial'):
        review=json.loads((E/(name+'.review.json')).read_text())
    return dict(draw=name,case=case,source_sha256=hashlib.sha256((work/REL).read_bytes()).hexdigest(),changed=changed,new=new,unexpected_paths=extras,scope=scope,supplied_preserved=supplied_preserved,debris=debris,cli=cli,smoke=dict(exit_code=smoke.returncode,stdout=smoke.stdout,stderr=smoke.stderr,seconds=time.monotonic()-start),review=review,product_complete=bool(scope and supplied_preserved and not debris and cli['passed'] and smoke.returncode==0),pipeline_fidelity=review is None or review['structure_valid'] and review['no_tool_events'])

def main():
    registry=json.loads((E/'REGISTRATION.json').read_text())
    for path,digest in registry['sha256'].items():assert hashlib.sha256(Path(path).read_bytes()).hexdigest()==digest,path
    initial=json.loads((E/'INITIAL-SEALED.json').read_text());final=json.loads((E/'FINAL-SEALED.json').read_text())
    assert len(initial)==4 and len(final)==8
    rows=[assess(name+'-initial',info['case'],info['seal']) for name,info in initial.items()]
    rows += [assess(name,json.loads((E/(name+'.branch.json')).read_text())['case'],sealed) for name,sealed in final.items()]
    with (E/'ASSESSMENT.json').open('x') as f:json.dump(rows,f,indent=2)
    print(json.dumps([{k:r[k] for k in ('draw','product_complete','pipeline_fidelity')} for r in rows]))
if __name__=='__main__':main()
