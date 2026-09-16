"""Frozen external checks for two observed real-source failures; no model calls."""
from pathlib import Path
import json, os, re, shutil, subprocess, sys, tempfile, time

BASE = Path(__file__).resolve().parents[3] / '.devlyn/0182/cases'

def run(argv, cwd, env=None):
    start = time.monotonic()
    try:
        p = subprocess.run(argv, cwd=cwd, env=env, capture_output=True, text=True, timeout=30)
    except subprocess.TimeoutExpired as error:
        return {'exit': None, 'stdout': (error.stdout or b'').decode(errors='replace'), 'stderr': (error.stderr or b'').decode(errors='replace'), 'seconds': time.monotonic()-start, 'error': 'timeout'}
    return {'exit': p.returncode, 'stdout': p.stdout, 'stderr': p.stderr, 'seconds': time.monotonic()-start}

def score(case, work):
    work = Path(work).resolve()
    checks = []
    def check(name, ok, raw):
        checks.append({'name': name, 'pass': bool(ok), 'raw': raw})
    allowed = 'bin/devlyn.js' if case == 'description' else 'scripts/static-ab.sh'
    for p in sorted((BASE/case/'seed').rglob('*')):
        if p.is_file() and str(p.relative_to(BASE/case/'seed')) != allowed:
            relative = p.relative_to(BASE/case/'seed')
            check('preserve:'+str(relative), (work/relative).is_file() and p.read_bytes()==(work/relative).read_bytes(), {})
    if case == 'description':
        pairs = [
            ('real apostrophe', "---\nname: test\ndescription: Extract a verifiable spec from a user's idea by driving the conversation with focused questions.\n---\n", "Extract a verifiable spec from a user's idea by driving the conversation with focused questions."[:70]),
            ('plain double quotes', '---\ndescription: Show "quoted" paths and user\'s settings\n---\n', 'Show "quoted" paths and user\'s settings'),
            ('single quoted', "---\ndescription: 'It''s a \"useful\" tool' # omitted\n---\n", 'It\'s a "useful" tool'),
            ('double quoted', '---\ndescription: "A \\"quoted\\" C:\\\\tools path" # omitted\n---\n', 'A "quoted" C:\\tools path'),
            ('empty fallback', '---\ndescription:   \npurpose: Useful purpose\n---\n# Title\n', 'Useful purpose'),
            ('empty skips key', '---\ndescription:\nname: WRONG\n---\n# Right title\n', 'Right title'),
            ('purpose quotes', '---\npurpose: Keep the user\'s "intent"\n---\n', 'Keep the user\'s "intent"'),
            ('priority', 'Plain first sentence\ndescription: Other\n# Title\n', 'Plain first sentence'),
            ('description priority', '---\npurpose: purpose\ndescription: description\n---\n# title\n','description'),
            ('template fallback', '---\ndescription: {placeholder}\npurpose: Useful\n---\n', 'Useful'),
            ('title', '# Heading\nbody\n','Heading'),
            ('excluded title', '# [placeholder]\n',''),
            ('limit', '---\ndescription: '+('a'*90)+'\n---\n','a'*70),
            ('crlf', '---\r\ndescription: It\'s preserved\r\n---\r\n', "It's preserved"),
        ]
        with tempfile.TemporaryDirectory() as t:
            d=Path(t); (d/'bin').mkdir(); shutil.copyfile(work/'bin/devlyn.js',d/'bin/devlyn.js'); shutil.copyfile(work/'package.json',d/'package.json')
            cases=[]
            for i,(name,content,expected) in enumerate(pairs):
                label=f'case{i:02}';p=d/'config/skills'/label/'SKILL.md';p.parent.mkdir(parents=True);p.write_text(content);cases.append({'name':name,'label':label,'expected':expected})
            raw=run(['node','bin/devlyn.js','list'],d)
            check('description CLI runtime',raw['exit']==0,raw)
            clean=re.sub(r'\x1b\[[0-9;]*m','',raw['stdout'])
            lines=clean.splitlines()
            for row in cases:
                marker='  '+row['label']
                indices=[i for i,line in enumerate(lines) if line==marker]
                actual=None
                if len(indices)==1:
                    i=indices[0];actual=lines[i+1][5:] if i+1<len(lines) and lines[i+1].startswith('     ') else ''
                check(row['name'],actual==row['expected'],{**row,'actual':actual})
        raw=run(['node', '--check','bin/devlyn.js'],work);check('node syntax',raw['exit']==0,raw)
    else:
        with tempfile.TemporaryDirectory(prefix='static-ab-') as t:
            d=Path(t);(d/'scripts').mkdir();(d/'scripts/static-ab.sh').write_bytes((work/allowed).read_bytes())
            subprocess.run(['git','init','-q',str(d)],check=True)
            def commit(words):
                (d/'CLAUDE.md').write_text('word '*words+'\n')
                subprocess.run(['git','add','CLAUDE.md'],cwd=d,check=True)
                subprocess.run(['git','-c','user.name=Test','-c','user.email=t@local','commit','-qm','baseline','--allow-empty'],cwd=d,check=True)
            def invoke(value, words):
                (d/'CLAUDE.md').write_text('word '*words+'\n');env=dict(os.environ);env.pop('DEVLYN_STATIC_AB_MAX_GROWTH_PCT',None)
                if value is not None:env['DEVLYN_STATIC_AB_MAX_GROWTH_PCT']=value
                return run(['bash','scripts/static-ab.sh'],d,env)
            commit(0)
            for value in ['', 'abc','1+1','-1',' 15','15 ','.5','1.','1e2','NaN','Infinity','9'*400,'1; print 123']:
                raw=invoke(value,4)
                check('reject:'+repr(value),raw['exit']==2 and not re.search(r'^file\s+lines\(A\)',raw['stdout'],re.M) and re.search(r'number|numeric|decimal|threshold|DEVLYN_STATIC_AB_MAX_GROWTH_PCT',raw['stderr'],re.I),raw)
            raw=invoke('15',4)
            check('zero baseline growth',raw['exit']==0 and re.search(r'undefined|not defined|n/a|not applicable',raw['stdout']+raw['stderr'],re.I) and re.search(r'⚠|warn',raw['stdout']+raw['stderr'],re.I),raw)
            raw=invoke('15',0);check('zero unchanged',raw['exit']==0 and 'did NOT grow' in raw['stdout'],raw)
            commit(1000)
            for value in [None,'0','15','0.5','001.50']:
                raw=invoke(value,1000);check('valid:'+str(value),raw['exit']==0 and 'did NOT grow' in raw['stdout'],raw)
            raw=invoke('15',1100);check('within',raw['exit']==0 and 'within limit' in raw['stdout'],raw)
            raw=invoke('15',1200);check('over',raw['exit']==0 and '⚠' in raw['stdout'],raw)
            raw=invoke('0.09',1001);check('unrounded comparison',raw['exit']==0 and 'within limit' in raw['stdout'],raw)
            raw=invoke('0',999);check('shrink',raw['exit']==0 and 'did NOT grow' in raw['stdout'],raw)
            raw=invoke('15',1000);check('preserved totals',all(x in raw['stdout'] for x in ['TOTAL','words','tokens≈','CLAUDE.md','1300']),raw)
            seed_script=(BASE/'static/seed/scripts/static-ab.sh').read_text()
            files=[line.strip() for line in seed_script.split('FILES=(\n',1)[1].split('\n)',1)[0].splitlines() if line.strip()]
            for name in files:
                path=d/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text('word '*10+'\n')
            subprocess.run(['git','add',*files],cwd=d,check=True)
            subprocess.run(['git','-c','user.name=Test','-c','user.email=t@local','commit','-qm','all measured files'],cwd=d,check=True)
            changed=files[-1];(d/changed).write_text('word '*20+'\n')
            raw=run(['bash','scripts/static-ab.sh'],d,{**os.environ,'DEVLYN_STATIC_AB_MAX_GROWTH_PCT':'0'})
            before=len(files)*10;after=before+10
            check('all files measured',raw['exit']==0 and all(name in raw['stdout'] for name in files) and re.search(r'^words\s+'+str(before)+r'\s+'+str(after)+r'\s+10$',raw['stdout'],re.M) and re.search(r'^tokens≈\s+'+str(int(before*1.3))+r'\s+'+str(int(after*1.3))+r'\s+13$',raw['stdout'],re.M),raw)

    return {'case':case,'checks':checks,'mechanical_success':all(x['pass'] for x in checks),'seconds':sum(x['raw'].get('seconds',0) for x in checks)}

if __name__=='__main__':
    print(json.dumps(score(sys.argv[1],Path(sys.argv[2])),indent=2))
