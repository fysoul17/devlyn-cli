"""Artifact-only filesystem/API/CLI oracle; never reads participant explanations."""
from pathlib import Path
import builtins
from contextlib import ExitStack
import errno
import hashlib
import io
import json
import os
import runpy
import subprocess
import sys
import tempfile
from unittest.mock import patch


def check(package, fixtures):
    try:
        module = runpy.run_path(str(package / 'role-config.py'))
    except (Exception, SystemExit) as exc:
        return [dict(check='artifact/import', pass_=False, error=repr(exc))]
    rows = []

    def trial(label, action):
        try:
            with tempfile.TemporaryDirectory(dir=fixtures) as temporary:
                action(Path(temporary))
            rows.append(dict(check=label, pass_=True))
        except (Exception, SystemExit) as exc:
            rows.append(dict(check=label, pass_=False, error=repr(exc)))

    def blocked(action, path):
        try:
            action()
        except ValueError as exc:
            assert 'BLOCKED:invalid-engine-config' in str(exc), str(exc)
            assert str(path) in str(exc), str(exc)
        else:
            raise AssertionError('configuration error silently accepted')

    def bad_entry(work, kind, operation):
        folder = work / '.devlyn'; folder.mkdir()
        path = folder / 'engines.json'
        if kind == 'dangling': path.symlink_to('lost.json')
        elif kind == 'loop': path.symlink_to(path.name)
        elif kind == 'directory': path.mkdir(); (path / 'keep').write_bytes(b'untouched')
        elif kind == 'parent-file': folder.rmdir(); folder.write_bytes(b'untouched')
        sentinel = work / 'unrelated'; sentinel.write_bytes(b'keep')
        def snapshot():
            return {str(p.relative_to(work)): (('link',str(p.readlink())) if p.is_symlink()
                    else ('dir',) if p.is_dir() else ('file',p.read_bytes(),p.stat().st_mode))
                    for p in work.rglob('*')}
        before = snapshot()
        actions = {
            'optional': lambda: module['read_config'](path, optional=True),
            'required': lambda: module['read_config'](path),
            'status': lambda: module['resolve'](work,'claude',for_status=True,available=lambda _: True),
            'dispatch': lambda: module['resolve'](work,'claude',flag_engine='codex',no_pair=True,available=lambda _: True),
            'edit': lambda: module['edit'](work,'worker','{"engine":"codex"}'),
            'clear': lambda: module['edit'](work,'clear',None),
        }
        try: blocked(actions[operation], path)
        finally: assert snapshot() == before, 'rejected configuration changed filesystem'

    for kind in ('dangling','loop','directory','parent-file'):
        for operation in ('optional','required','status','dispatch','edit','clear'):
            trial(kind+'/'+operation, lambda w,k=kind,o=operation: bad_entry(w,k,o))

    def missing(work, parent):
        if parent: (work / '.devlyn').mkdir()
        path=work/'.devlyn/engines.json'
        config, source=module['read_config'](path,optional=True)
        assert config == {} and source == dict(path=str(path.absolute()),sha256=None)
        blocked(lambda: module['read_config'](path),path)
        assert module['resolve'](work,'codex',available=lambda _:True)['legacy_engine']=='codex'
        module['edit'](work,'worker','{"engine":"codex"}')
        assert json.loads(path.read_bytes()) == {'roles':{'worker':{'engine':'codex'}}}
        module['edit'](work,'clear',None); assert not path.exists()
    for parent in (False,True): trial('missing/'+str(parent),lambda w,p=parent: missing(w,p))

    def valid_link(work):
        folder=work/'.devlyn'; folder.mkdir(); path=folder/'engines.json'
        target=work/'shared.json'; raw=b'{"executor":"claude","custom":7}\n'; target.write_bytes(raw)
        target.chmod(0o640); path.symlink_to(target)
        value,source=module['read_config'](path,optional=True)
        assert value==json.loads(raw) and source==dict(path=str(target.resolve()),sha256=hashlib.sha256(raw).hexdigest())
        assert module['resolve'](work,'codex',available=lambda _:True)['legacy_engine']=='claude'
        module['edit'](work,'worker','{"engine":"codex"}')
        assert not path.is_symlink() and target.read_bytes()==raw
        assert json.loads(path.read_bytes())=={'executor':'claude','custom':7,'roles':{'worker':{'engine':'codex'}}}
        assert path.stat().st_mode & 0o777 == target.stat().st_mode & 0o777
        assert sorted(p.name for p in folder.iterdir())==['engines.json']
    trial('valid-link/read-binding-edit',valid_link)

    def io_error(work, number, operation):
        (work/'.devlyn').mkdir(); path=work/'.devlyn/engines.json'; path.write_bytes(b'{"executor":"codex"}')
        calls=[]
        def injected(original, label):
            def access(p,*a,**kw):
                if isinstance(p,(str,bytes,os.PathLike)) and os.fsdecode(p)==str(path):
                    calls.append(label)
                    raise OSError(number,'controlled config access error',str(p))
                return original(p,*a,**kw)
            return access
        with ExitStack() as patches:
            for owner,attribute in ((os,'stat'),(os,'lstat'),(os,'open'),(io,'open'),(builtins,'open')):
                patches.enter_context(patch.object(owner,attribute,injected(getattr(owner,attribute),attribute)))
            blocked(lambda: module['read_config'](path,optional=operation=='optional'),path)
        assert calls and path.read_bytes()==b'{"executor":"codex"}'
    for number in (errno.EACCES,errno.EIO):
        for operation in ('optional','required'):
            trial('io/'+str(number)+'/'+operation,lambda w,n=number,o=operation: io_error(w,n,o))

    def cli(work, operation):
        (work/'.devlyn').mkdir(); path=work/'.devlyn/engines.json'; path.symlink_to('lost.json')
        extra={'status':[], 'edit':['--set-role','worker','--value','{"engine":"codex"}'],
               'clear':['--set-role','clear'], 'explicit':['--role-config',str(path)]}[operation]
        result=subprocess.run([sys.executable,'-B',str(package/'role-config.py'),'--workdir',str(work),*extra],capture_output=True,text=True,timeout=20)
        assert result.returncode==1 and not result.stdout and 'BLOCKED:invalid-engine-config' in result.stderr and str(path) in result.stderr,(result.returncode,result.stdout,result.stderr)
        assert 'Traceback' not in result.stderr and path.is_symlink() and str(path.readlink())=='lost.json'
        assert sorted(p.name for p in path.parent.iterdir())==['engines.json']
    for operation in ('status','edit','clear','explicit'): trial('cli/'+operation,lambda w,o=operation: cli(w,o))
    return rows
