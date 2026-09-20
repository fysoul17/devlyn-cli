"""0193 two-arm experiment, reusing the frozen native transport without resolve."""
from pathlib import Path
import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile

R=Path(__file__).resolve().parents[3]; H=Path(__file__).resolve().parent
E=R/'.devlyn/0193'; S=R/'.git/devlyn-completion/c790c43ce8f80f4b411cac89/scratch'
W=R.parent/'0193-participants'


def module(path):
    spec=importlib.util.spec_from_file_location('loaded_'+path.stem,path)
    value=importlib.util.module_from_spec(spec); spec.loader.exec_module(value); return value


def put(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x') as stream: json.dump(value,stream,indent=2); stream.write('\n')


def hashes(root):
    return {str(p.relative_to(root)):dict(mode=p.lstat().st_mode & 0o777,
        value='symlink:'+str(p.readlink()) if p.is_symlink() else hashlib.sha256(p.read_bytes()).hexdigest())
        for p in root.rglob('*') if (p.is_symlink() or p.is_file()) and '.git' not in p.relative_to(root).parts}


def prepare():
    seed=E/'inputs/root'; package=seed/'package'; package.mkdir(parents=True)
    for name in ('role-config.py','platform-support.py','resolve-bootstrap.py','judge-role-evidence.py'):
        shutil.copy2(R/'config/skills/_shared'/name,package/name)
    shutil.copytree(R/'config/skills/_shared/adapters',package/'adapters')
    (seed/'tests').mkdir(); shutil.copyfile(H/'test_acceptance.py',seed/'tests/test_acceptance.py')
    shutil.copyfile(H/'request.md',seed/'spec.md')
    (seed/'.gitignore').write_text('.devlyn/\n.agents/\n__pycache__/\n*.pyc\n')
    put(seed/'spec.expected.json',dict(required_files=['package/role-config.py'],
        forbidden_files=['spec.md','spec.expected.json','.gitignore','tests/test_acceptance.py',
                         *[str(p.relative_to(seed)) for p in package.rglob('*') if p.is_file() and p.name!='role-config.py']],
        verification_commands=[dict(cmd='/opt/homebrew/bin/python3 -B -m unittest discover -s tests -v',exit_code=0,timeout_sec=90),
                               dict(cmd='/opt/homebrew/bin/python3 -B package/role-config.py --self-test',exit_code=0,timeout_sec=90)]))
    shutil.copyfile(Path.home()/'.codex/models_cache.json',E/'models_cache.json')


def calibrate():
    source=(E/'inputs/root/package/role-config.py').read_text()
    old='''    if optional and not path.exists():
        return {}, {"path": str(path.absolute()), "sha256": None}
    try:
        raw = path.read_bytes()'''
    new='''    try:
        if optional:
            try:
                path.lstat()
            except FileNotFoundError:
                return {}, {"path": str(path.absolute()), "sha256": None}
        raw = path.read_bytes()'''
    assert source.count(old)==1
    reference=source.replace(old,new)
    assert reference.count('path.lstat()')==1 and reference.count('        if optional:\n')==1
    variants=dict(original=source,reference=reference,
        reference_open=reference.replace('        raw = path.read_bytes()\n        value = validate', '        with open(path, "rb") as handle:\n            raw = handle.read()\n        value = validate'),
        follows_links=reference.replace('path.lstat()','path.stat()'),
        catches_all_oserror=reference.replace('except FileNotFoundError:\n                return {},','except OSError:\n                return {},'),
        rejects_valid_links=reference.replace('        if optional:\n','        if path.is_symlink():\n            fail(f"cannot read role configuration {path}")\n        if optional:\n'),
        requires_optional=reference.replace('        if optional:\n','        if False:\n'))
    checker=module(H/'check.py'); results=[]
    for name,content in variants.items():
        with tempfile.TemporaryDirectory(dir=S) as temporary:
            base=Path(temporary); package=base/'package'; shutil.copytree(E/'inputs/root/package',package)
            (package/'role-config.py').write_text(content)
            checks=checker.check(package,base)
        failed={c['check'] for c in checks if not c['pass_']}
        bad_ops=('optional','status','dispatch','edit','clear')
        expected={
            'original':{k+'/'+o for k in ('dangling','loop','parent-file') for o in bad_ops}
                |{'io/13/optional','io/5/optional','cli/status','cli/edit','cli/clear'},
            'reference':set(),
            'reference_open':set(),
            'follows_links':{'dangling/'+o for o in bad_ops}|{'cli/status','cli/edit','cli/clear'},
            'catches_all_oserror':{'parent-file/'+o for o in bad_ops}|{'io/13/optional','io/5/optional'},
            'rejects_valid_links':{'valid-link/read-binding-edit'},
            'requires_optional':{'missing/False','missing/True'},
        }[name]
        results.append(dict(variant=name,checks=checks,expected_failures=sorted(expected)))
        assert failed==expected,(name,sorted(failed-expected),sorted(expected-failed),checks)
    put(E/'CALIBRATION.json',results); (E/'reference.py').write_text(reference)
    print(json.dumps([{r['variant']:sum(c['pass_'] for c in r['checks'])} for r in results]))


def freeze():
    paths=[*[p for p in H.glob('*') if p.is_file()],*[p for p in (E/'inputs').rglob('*') if p.is_file()],E/'models_cache.json',E/'CALIBRATION.json',E/'reference.py',E/'REPRODUCTION.json',E/'CALIBRATION-SUPPORT.json',
        R/'.devlyn/0179/catalog-setting.txt',R/'autoresearch/experiments/0179/AGENTS.candidate.md',
        R/'autoresearch/experiments/0191/launch.py',R/'autoresearch/scripts/comparison-controller.py',
        R/'config/skills/_shared/run-bounded.py',R/'config/skills/_shared/task-complete.py',R/'config/skills/_shared/platform-support.py']
    assert all(p.is_file() for p in paths), 'Missing frozen input'
    put(E/'REGISTRATION.json',dict(version=subprocess.check_output(['codex','--version'],text=True).strip(),
        order=[dict(draw=f'{i:02}-{arm}',arm=arm,case='root') for i,arm in enumerate('ABBA',1)],
        source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip(),
        sha256={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}))


def run():
    launch=module(R/'autoresearch/experiments/0191/launch.py')
    launch.EVIDENCE,launch.SCRATCH,launch.WORKS=E,S,W
    registry=json.loads((E/'REGISTRATION.json').read_text())
    for row in registry['order']:
        out=E/'runs'/row['draw']; assert not out.exists(),'No rerolls'
        previous=dict(os.environ)
        try:
            assert subprocess.check_output(['codex','--version'],text=True).strip()==registry['version']
            os.environ['TMPDIR']=str(W/row['draw']); sys.argv=['launch.py',row['draw'],row['arm'],row['case']]
            launch.main()
        finally:
            os.environ.clear(); os.environ.update(previous)
        put(out/'sealed.json',hashes(W/row['draw']))
        result=json.loads((out/'result.json').read_text())
        assert not result['error'] and result['owned_writers_quiescent'],result
        events=[json.loads(line) for line in (out/'stdout').read_text().splitlines() if line.strip()]
        if result['exit_code']!=124:
            assert any(e.get('type')=='turn.completed' for e in events),'Missing native completion; stop'


if __name__=='__main__':
    {'prepare':prepare,'calibrate':calibrate,'freeze':freeze,'run':run}[sys.argv[1]]()
