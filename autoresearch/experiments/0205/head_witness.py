"""Actual allocator plus symbolic non-branch HEAD; no participant test reuse."""
from pathlib import Path
import importlib.util
import json
import sys
import tempfile

R = Path(__file__).resolve().parents[3]
spec = importlib.util.spec_from_file_location('check0198', R / 'autoresearch/experiments/0198/check.py')
c = importlib.util.module_from_spec(spec)
spec.loader.exec_module(c)


def check(product, scratch):
    for ref in ('refs/tags/t', 'refs/remotes/upstream/main', 'refs/notes/x'):
        for terminal in (False, True):
            for mode in (['small','task'], ['--spec','spec.md'], ['--spec','spec.md','--verify-only','HEAD']):
                with tempfile.TemporaryDirectory(prefix='head-',dir=scratch) as tmp:
                    work=Path(tmp)
                    c.git(work,'init','-qb','main')
                    c.git(work,'config','user.name','Fixture')
                    c.git(work,'config','user.email','fixture@local')
                    (work/'spec.md').write_text('# Witness\nPreserve source.\n')
                    c.write(work/'spec.expected.json',{'verification_commands':[{'cmd':'python3 -B -c "assert True"'}]})
                    c.git(work,'add','.')
                    c.git(work,'commit','-qm','fixture')
                    c.git(work,'remote','add','origin','https://github.com/fysoul17/devlyn-cli.git')
                    allocation=c.command([sys.executable,'-B',c.PRODUCER,'allocate','--repo',work,'--task','HEAD witness','--branch',ref,'--repository','fysoul17/devlyn-cli','--base','main'],work)
                    if allocation['exit_code']:
                        raise RuntimeError(allocation)
                    receipt=Path(json.loads(allocation['stdout'])['receipt'])
                    data=json.loads(receipt.read_text())
                    if terminal:
                        data['status']='COMPLETE';c.write(receipt,data)
                    c.git(work,'update-ref',ref,'HEAD')
                    c.git(work,'symbolic-ref','HEAD',ref)
                    if c.git(work,'symbolic-ref','HEAD')!=ref:
                        raise RuntimeError('HEAD did not select counterexample')
                    (work/'.git/devlyn-bootstrap.lock').touch()
                    before=c.snapshot(work)
                    run=c.command([sys.executable,'-B',product/c.REL,*mode],work)
                    after=c.snapshot(work)
                    p=work/'.devlyn/pipeline.state.json'
                    try:
                        output=json.loads(run['stdout'])
                        state=json.loads(p.read_text()) if p.exists() else None
                        valid=isinstance(output,dict) and isinstance(state,dict)
                    except ValueError:
                        output=state=None;valid=False
                    kept={k:v for k,v in after.items() if k!='.devlyn' and not k.startswith('.devlyn/')}==before
                    passed=run['exit_code']==0 and valid and output.get('ok') is True and state.get('task') is None and state.get('base_ref',{}).get('branch') is None and kept
                    yield dict(ref=ref,terminal=terminal,mode=mode,passed=passed,preserved=kept,allocation=allocation,run=run,state=state)


if __name__=='__main__':
    product,scratch,target=map(Path,sys.argv[1:])
    with target.open('x') as f:
        rows=[]
        try:
            for row in check(product.resolve(),scratch.resolve()):
                rows.append(row)
        finally:
            json.dump(dict(product=str(product),rows=rows),f,indent=2)
    print(json.dumps({'passed':sum(r['passed'] for r in rows),'total':len(rows)}))
    raise SystemExit(not all(r['passed'] for r in rows))
