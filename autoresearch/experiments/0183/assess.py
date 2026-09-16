"""External CLI, scope, debris and actual pipeline evidence assessment."""
from pathlib import Path
import hashlib, json, shutil, subprocess, sys, tempfile, time

REPO=Path(__file__).resolve().parents[3]
EVIDENCE=REPO/'.devlyn/0183'
WORKS=Path('/Users/aipalm/.local/share/nx01/0183-participants')
SCRATCH=REPO/'.git/devlyn-completion/2137acb862ccbc4bb2ae8500/scratch'
KEYS=('lines','chars','words','tokens_c4','tokens_w13')

def heldout(case, code):
    with tempfile.TemporaryDirectory(prefix='external-cli-',dir=SCRATCH) as temp:
        root=Path(temp)/'source'; (root/'scripts').mkdir(parents=True)
        script=root/'scripts/skill-token-gauge.py';script.write_bytes(code)
        target=Path(temp)/'selected Ω' if case=='root' else root
        files={'config/skills/測定/SKILL.md':'# Unicode\nline two 雪\n',
               'config/skills/測定/references/nested/more.txt':'keep all reference files\n',
               'optional-skills/測定/SKILL.md':'# Other\r\n',
               'config/skills/skip/SKILL.md':'# Omit only when filtering\n',
               'config/skills/_shared/nested/help.md':'# Shared\n',
               'AGENTS.md':'one two three', 'CLAUDE.md':''}
        for path,body in files.items():
            p=target/path;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(body.encode())
        original_code=(EVIDENCE/'inputs'/case/'scripts/skill-token-gauge.py').read_bytes()
        original=root/'scripts/original.py';original.write_bytes(original_code)
        def cli(path, args=()):
            return subprocess.run([sys.executable,'-B',str(path),*args],capture_output=True,text=True,timeout=20)
        for flags in ([],['--json']):
            before=cli(original,flags);after=cli(script,flags)
            assert (after.returncode,after.stdout,after.stderr)==(before.returncode,before.stdout,before.stderr)
        args=['--root',str(target)] if case=='root' else ['--skill','測定']
        p=subprocess.run([sys.executable,'-B',str(script),'--json',*args],capture_output=True,text=True,timeout=20)
        assert p.returncode==0,p.stderr
        data=json.loads(p.stdout)
        if case=='root':
            (target/'scripts').mkdir(exist_ok=True)
            target_original=target/'scripts/original.py';target_original.write_bytes(original_code)
            for flags in ([],['--json']):
                before=cli(target_original,flags);after=cli(script,[*flags,*args])
                assert (after.returncode,after.stdout,after.stderr)==(before.returncode,before.stdout,before.stderr)
        else:
            baseline=json.loads(cli(original,['--json']).stdout)
            baseline['skills']=[s for s in baseline['skills'] if s['name']=='測定']
            groups=baseline['skills']+[baseline['root'],baseline['shared']]
            baseline['grand_total']={k:sum(g['totals'][k] for g in groups) for k in KEYS}
            assert data==baseline
        expected={path:body for path,body in files.items() if case=='root' or '/skip/' not in path}
        all_rows=[f for group in data['skills']+[data['shared'],data['root']] for f in group['files']]
        assert len(all_rows)==len(expected)
        assert {f['path'] for f in all_rows}==set(expected)
        for f in all_rows:
            text=expected[f['path']].replace('\r\n','\n').replace('\r','\n')
            measures=dict(lines=len(text.splitlines()),chars=len(text),words=len(text.split()),
                tokens_c4=len(text)//4,tokens_w13=round(len(text.split())*1.3))
            assert {k:f[k] for k in KEYS}==measures,(f,measures)
        assert data['grand_total']=={k:sum(f[k] for f in all_rows) for k in KEYS}
        return dict(pass_=True,files=len(all_rows),stdout=p.stdout,stderr=p.stderr)

def inspect(draw, case, arm):
    out=EVIDENCE/'runs'/draw;work=WORKS/draw
    launch=json.loads((out/'result.json').read_text())
    baseline=json.loads((out/'input.json').read_text())['baseline']
    seed=EVIDENCE/'inputs'/case
    changed=subprocess.check_output(['git','diff',baseline,'--name-only'],cwd=work,text=True).splitlines()
    new=subprocess.check_output(['git','ls-files','--others','--exclude-standard'],cwd=work,text=True).splitlines()
    scope=all(p in ('scripts/skill-token-gauge.py','tests/test_regression.py') for p in changed+new)
    preserved=all((work/p.relative_to(seed)).is_file() and p.read_bytes()==(work/p.relative_to(seed)).read_bytes()
        for p in seed.rglob('*') if p.is_file() and p.relative_to(seed).as_posix()!='scripts/skill-token-gauge.py')
    debris=[str(p.relative_to(work)) for p in work.rglob('*') if p.is_file()
            and not any(x in p.relative_to(work).parts for x in ('.git','.devlyn','.agents'))
            and (p.suffix=='.pyc' or any(x in p.parts for x in ('__pycache__','test-results','playwright-report')))]
    start=time.monotonic()
    with tempfile.TemporaryDirectory(prefix='external-acceptance-',dir=SCRATCH) as temp:
        copy=Path(temp)/'work';shutil.copytree(seed,copy)
        shutil.copyfile(work/'scripts/skill-token-gauge.py',copy/'scripts/skill-token-gauge.py')
        check=subprocess.run([sys.executable,'-B','-m','unittest','discover','-s','tests','-v'],cwd=copy,capture_output=True,text=True,timeout=60)
    try: extra=heldout(case,(work/'scripts/skill-token-gauge.py').read_bytes())
    except (AssertionError,ValueError,subprocess.SubprocessError) as exc: extra=dict(pass_=False,error=repr(exc))
    row=dict(draw=draw,case=case,arm=arm,native=launch,changed=changed,new=new,
             scope=scope,preserved=preserved,debris=debris,external_seconds=time.monotonic()-start,
             acceptance=dict(exit_code=check.returncode,stdout=check.stdout,stderr=check.stderr),heldout=extra)
    row['product_complete']=scope and preserved and not debris and check.returncode==0 and extra['pass_']
    # Lifecycle fidelity is independently adjudicated against receipts/raw sessions.
    row['archived_states']=[str(p) for p in (work/'.devlyn/runs').glob('*/pipeline.state.json')]
    row['pipeline_fidelity']='REQUIRES_ROOT_RECEIPT_REVIEW' if arm=='C' else 'not_applicable'
    return row

def main():
    registry=json.loads((EVIDENCE/'REGISTRATION.json').read_text())
    seals={}
    for row in registry['order']:
        work=WORKS/row['draw']
        assert (EVIDENCE/'runs'/row['draw']/'result.json').exists()
        seals[row['draw']]={str(p.relative_to(work)):hashlib.sha256(p.read_bytes()).hexdigest()
            for p in work.rglob('*') if p.is_file() and '.git' not in p.relative_to(work).parts}
    with (EVIDENCE/'SEALED-OUTPUTS.json').open('x') as stream:json.dump(seals,stream,indent=2)
    rows=[inspect(**row) for row in registry['order']]
    with (EVIDENCE/'ASSESSMENT.json').open('x') as stream:json.dump(rows,stream,indent=2)
    print(json.dumps([{k:r[k] for k in ('draw','product_complete','pipeline_fidelity','external_seconds')} for r in rows]))

if __name__=='__main__':main()
