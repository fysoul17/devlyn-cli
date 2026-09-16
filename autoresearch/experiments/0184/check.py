"""Actual-CLI checks. No participant receives this file or its results."""
from pathlib import Path
import json,os,shutil,subprocess,sys,tempfile,time

REPO=Path(__file__).resolve().parents[3]
HERE=Path(__file__).resolve().parent
EVIDENCE=REPO/'.devlyn/0184'
SCRATCH=REPO/'.git/devlyn-completion/500627caa6c42463728dd5e5/scratch'
REL=Path('benchmark/auto-resolve/scripts/collect-swebench-predictions.py')

def check(case,code):
    started=time.monotonic();results=[]
    def scenario(label,body):
        try:
            with tempfile.TemporaryDirectory(prefix='oracle-',dir=SCRATCH) as temp:
                root=Path(temp);script=root/'collector.py';script.write_bytes(code)
                shutil.copyfile(EVIDENCE/'source/pair_evidence_contract.py',root/'pair_evidence_contract.py')
                patches=root/'patches';patches.mkdir();out=root/'predictions.jsonl'
                def add(instance,text,name='patch.diff'):
                    path=patches/instance/name;path.parent.mkdir(parents=True,exist_ok=True)
                    path.write_bytes(text if isinstance(text,bytes) else text.encode());return path
                def cli(*args,limited=False):
                    cmd=[sys.executable,'-B',str(script),'--patch-root',str(patches),'--model-name','model Ω','--out',str(out),*args]
                    if limited:
                        cmd=[sys.executable,'-B','-c','import resource,signal,runpy,sys; resource.setrlimit(resource.RLIMIT_FSIZE,(1024,1024)); signal.signal(signal.SIGXFSZ,signal.SIG_IGN); sys.argv=sys.argv[1:]; runpy.run_path(sys.argv[0],run_name="__main__")',*cmd[2:]]
                    return subprocess.run(cmd,capture_output=True,text=True,timeout=20,cwd=root,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'})
                body(root,patches,out,add,cli)
            results.append(dict(name=label,passed=True))
        except (AssertionError,ValueError,OSError,subprocess.SubprocessError) as exc:
            results.append(dict(name=label,passed=False,error=repr(exc)))
    def success(root,patches,out,add,cli):
        add('b','B Ω\r\n');add('a','A\n');add('z','  ')
        original=root/'original.py';original.write_bytes((EVIDENCE/'source/collector.py').read_bytes())
        before=subprocess.run([sys.executable,'-B',str(original),'--patch-root',str(patches),'--model-name','model Ω','--out',str(out),'--allow-empty'],capture_output=True,text=True,timeout=20)
        expected=out.read_bytes();after=cli('--allow-empty')
        assert (after.returncode,after.stdout,after.stderr)==(before.returncode,before.stdout,before.stderr),(after.returncode,after.stderr)
        assert out.read_bytes()==expected
        ids=root/'ids.jsonl';ids.write_text(json.dumps({'instance_id':'b'})+'\n')
        p=cli('--instances-jsonl',str(ids));assert p.returncode==0,p.stderr
        assert [json.loads(x)['instance_id'] for x in out.read_text().splitlines()]==['b']
    scenario('unchanged-success-order-schema-filter-and-empty-accounting',success)
    if case=='literal':
        for name in ('literal[ab]*?.diff',' --雪.patch ','--dash.patch'):
            def literal(root,patches,out,add,cli,name=name):
                add('b','B',name);add('a','A',name);add('noise','wrong','literalax.diff')
                (patches/'directory'/name).mkdir(parents=True)
                add('nested/child','nested',name)
                p=cli('--patch-name='+name);assert p.returncode==0,p.stderr
                rows=[json.loads(x) for x in out.read_text().splitlines()]
                assert [(r['instance_id'],r['model_patch']) for r in rows]==[('a','A'),('b','B')],rows
                assert json.loads(p.stdout)['patch_name']==name
                ids=root/'ids.jsonl';ids.write_text('{"instance_id":"b"}\n')
                p=cli('--patch-name='+name,'--instances-jsonl',str(ids));assert p.returncode==0,p.stderr
                assert json.loads(out.read_text())['instance_id']=='b'
            scenario('literal-name-'+repr(name),literal)
        for name in ('','.','..','../patch.diff','sub/file','sub\\file'):
            def invalid(root,patches,out,add,cli,name=name):
                add('a','A');out.write_bytes(b'KEEP')
                p=cli('--patch-name='+name)
                assert p.returncode==2 and not p.stdout and p.stderr,(p.returncode,p.stdout,p.stderr)
                assert out.read_bytes()==b'KEEP'
            scenario('reject-name-'+repr(name),invalid)
    elif case=='atomic':
        for mode in ('late-empty','late-utf8','all-skipped','write-error'):
            for exists in (False,True):
                def failure(root,patches,out,add,cli,mode=mode,exists=exists):
                    add('a','A' if mode!='all-skipped' else '')
                    add('b', {'late-empty':' ', 'late-utf8':b'\xff', 'all-skipped':' ', 'write-error':'X'*8192}[mode])
                    if exists:out.write_bytes(b'ORIGINAL\x00BYTES')
                    before={str(p.relative_to(root)):p.read_bytes() for p in root.rglob('*') if p.is_file()}
                    p=cli(*(['--allow-empty'] if mode=='all-skipped' else []),limited=mode=='write-error')
                    assert p.returncode==1 and not p.stdout and p.stderr and 'Traceback' not in p.stderr,(p.returncode,p.stdout,p.stderr)
                    assert out.exists()==exists
                    if exists:assert out.read_bytes()==b'ORIGINAL\x00BYTES'
                    after={str(p.relative_to(root)):p.read_bytes() for p in root.rglob('*') if p.is_file()}
                    assert after==before,'input change or leftover temporary file'
                scenario(mode+('-existing' if exists else '-absent'),failure)
        def atomic_publication(root,patches,out,add,cli):
            add('a','new patch');out.write_bytes(b'OLD')
            alias=root/'old-inode';os.link(out,alias)
            p=cli();assert p.returncode==0,p.stderr
            assert alias.read_bytes()==b'OLD','publication overwrote the original destination inode'
            assert json.loads(out.read_text())['model_patch']=='new patch'
        scenario('atomic-replacement-preserves-old-inode',atomic_publication)
        def publish_error(root,patches,out,add,cli):
            add('a','A');out.mkdir();(out/'keep').write_bytes(b'KEEP')
            before={str(p.relative_to(root)):p.read_bytes() for p in root.rglob('*') if p.is_file()}
            p=cli();assert p.returncode==1 and not p.stdout and p.stderr and 'Traceback' not in p.stderr,p.stderr
            assert before=={str(p.relative_to(root)):p.read_bytes() for p in root.rglob('*') if p.is_file()}
        scenario('publication-error-cleanup',publish_error)
    else:raise ValueError(case)
    return dict(case=case,passed=all(r['passed'] for r in results),seconds=time.monotonic()-started,checks=results)

if __name__=='__main__':print(json.dumps(check(sys.argv[1],Path(sys.argv[2]).read_bytes()),indent=2))
