"""0183 native transport with installer-equivalent stamping; full resolve is condition C."""
from pathlib import Path
import argparse, datetime, hashlib, json, os, shutil, subprocess, sys, tempfile, time

REPO = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
EVIDENCE = REPO / '.devlyn/0183'
SCRATCH = REPO / '.git/devlyn-completion/2137acb862ccbc4bb2ae8500/scratch'
WORKS = Path('/Users/aipalm/.local/share/nx01/0183-participants')
sys.path.insert(0, str(REPO / 'autoresearch/scripts'))
import importlib.util
module_spec = importlib.util.spec_from_file_location('controller', REPO / 'autoresearch/scripts/comparison-controller.py')
controller = importlib.util.module_from_spec(module_spec)
module_spec.loader.exec_module(controller)

def put(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x') as stream:
        json.dump(obj, stream, indent=2)
        stream.write('\n')

def run(argv, cwd=None, **kw):
    return subprocess.run(argv, cwd=cwd, check=True, capture_output=True, **kw)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('draw')
    parser.add_argument('arm', choices=['A', 'B', 'C'])
    parser.add_argument('case', choices=['probe', 'root', 'filter'])
    args = parser.parse_args()
    if args.case != 'probe':
        registry = json.loads((EVIDENCE / 'REGISTRATION.json').read_text())
        for name, digest in registry['sha256'].items():
            assert hashlib.sha256(Path(name).read_bytes()).hexdigest() == digest, name
        index = next(i for i, row in enumerate(registry['order']) if row['draw'] == args.draw)
        assert registry['order'][index] == dict(draw=args.draw, arm=args.arm, case=args.case)
        assert all((EVIDENCE/'runs'/row['draw']/'result.json').exists() for row in registry['order'][:index])
        assert not any((EVIDENCE/'runs'/row['draw']).exists() for row in registry['order'][index:])
    out = EVIDENCE / 'runs' / args.draw
    out.mkdir(parents=True, exist_ok=False)
    work = WORKS / args.draw
    shutil.copytree(EVIDENCE / 'inputs' / args.case, work)
    if args.arm == 'B':
        shutil.copyfile(REPO/'autoresearch/experiments/0179/AGENTS.candidate.md', work/'AGENTS.md')
    elif args.arm == 'C':
        shutil.copyfile(REPO/'AGENTS.md', work/'AGENTS.md')
        for name in ('_shared', 'devlyn:resolve'):
            shutil.copytree(REPO/'config/skills'/name, work/'.agents/skills'/name)
        skill = work/'.agents/skills/devlyn:resolve/SKILL.md'
        # Match the actual installer's assignment-only stamp; keep sentinel guards literal.
        for folder in (work/'.agents/skills/_shared', skill.parent):
            for document in folder.rglob('*.md'):
                document.write_text(document.read_text().replace(
                    '${CLAUDE_SKILL_DIR:-__DEVLYN_SKILL_DIR__}',
                    '${CLAUDE_SKILL_DIR:-' + str(skill.parent) + '}'))
    run(['git','init','-q','-b','main',str(work)])
    run(['git','remote','add','origin','https://github.com/fysoul17/devlyn-cli.git'], work)
    run(['git','config','user.name','Research'], work)
    run(['git','config','user.email','research@localhost'], work)
    run(['git','add','.'], work)
    run(['git','commit','-qm','committed original source and owner inputs'], work)
    allocation = json.loads(run([sys.executable,str(REPO/'config/skills/_shared/task-complete.py'),
        'allocate','--repo',str(work),'--task',args.draw,'--branch','task/'+args.draw,
        '--repository','fysoul17/devlyn-cli','--remote','origin','--base',
        run(['git','branch','--show-current'],work,text=True).stdout.strip()], work,text=True).stdout)
    put(out/'ownership.json', allocation)
    native_selector = (REPO/'.devlyn/0179/catalog-setting.txt').read_text().strip()
    (work/'.devlyn/task-inputs').mkdir(parents=True,exist_ok=True)
    (work/'.devlyn/task-inputs/native-options.txt').write_text(native_selector+'\n')
    prompt = ('Complete the task in spec.md; read it and spec.expected.json fully. '
        'Preserve supplied requirements/checks and all unrelated files. Use the supplied Python interpreter; '
        'no dependencies or network task operations are needed. Local experiment commits only; '
        'no push/publication or user/global changes. The outer owner already allocated this task branch '
        'and handles delivery; do not allocate again. Return after one terminal outcome, no outer restart. '
        'Files outside this checkout are outside the task except installed executables, native auth/model metadata '
        'and your ownership receipt '+allocation['receipt']+'. No research, sibling task or prior-result access. ')
    if args.arm == 'B':
        prompt += 'Read and follow AGENTS.md. '
    elif args.arm == 'C':
        prompt += ('Read AGENTS.md and '+str(skill)+'. Execute complete canonical /devlyn:resolve '
            '--spec spec.md --no-pair --no-risk-probes. All core phases, independent same-model primary verification, internal repair, '
            'final reporting and archive are mandatory; no phase bypass. Request gpt-6-astra/high for '
            'Codex parent, PLAN, IMPLEMENT, BUILD_GATE, CLEANUP and primary JUDGE. No OTHER model is part of '
            'this run. Each Codex child must include one --config argument with the exact line in '
            '.devlyn/task-inputs/native-options.txt; this disables host skill cards while retaining the '
            'explicitly provided canonical bodies. Keep all canonical monitored-wrapper, sandbox, '
            'prompt and receipt contracts. Local-only delivery remains the outer owner responsibility. ')
    (out/'prompt.txt').write_text(prompt)
    baseline = run(['git','rev-parse','HEAD'],work,text=True).stdout.strip()
    common = ['--config','model_reasoning_effort="high"','--config','project_doc_max_bytes=0',
              '--config','web_search="disabled"','--config',native_selector]
    for feature in ('multi_agent','apps','plugins','hooks','skill_search'):
        common += ['--disable', feature]
    common += ['--enable','skip_host_skill_discovery']
    with tempfile.TemporaryDirectory(prefix=args.draw+'-',dir=SCRATCH) as temp:
        home = Path(temp)
        for name in ('auth.json','models_cache.json'):
            src = Path('/Users/aipalm/.codex')/name if name=='auth.json' else EVIDENCE/name
            shutil.copyfile(src, home/name)
            (home/name).chmod(0o600)
        # Child processes get the same native defaults without personal configuration.
        (home/'config.toml').write_text('model = "gpt-6-astra"\nmodel_reasoning_effort = "high"\n'
            'web_search = "disabled"\nproject_doc_max_bytes = 0\n'+native_selector+'\n'
            '[features]\nmulti_agent = false\napps = false\nplugins = false\nhooks = false\n'
            'skill_search = false\nskip_host_skill_discovery = true\n')
        env = {k:os.environ[k] for k in ('HOME','PATH','TMPDIR','LANG','LC_ALL','TERM','SHELL','USER','LOGNAME') if k in os.environ}
        env['CODEX_HOME'] = str(home)
        os.environ.clear()
        os.environ.update(env)
        rendered=run(['codex','--config','model="gpt-6-astra"','--config',
            'sandbox_mode="danger-full-access"',*common,'debug','prompt-input',prompt],work,timeout=30)
        (out/'render.json').write_bytes(rendered.stdout)
        (out/'render.stderr').write_bytes(rendered.stderr)
        for message in json.loads(rendered.stdout):
            for block in message.get('content',[]):
                text=block.get('text','')
                assert 'Persistent Memory' not in text and '(file: ' not in text
        argv = [sys.executable,str(REPO/'config/skills/_shared/run-bounded.py'),'1800','--stdin-file',
                str(out/'prompt.txt'),'--',shutil.which('codex'),'exec','--ignore-user-config','--strict-config',
                '--ignore-rules','--ephemeral','--sandbox','danger-full-access','--model','gpt-6-astra',
                *common,'--json','--color','never','-']
        plan = dict(work=str(work), argv=argv, bounds=dict(native_seconds=1800,wrapper_seconds=1810,
             post_return_quiet_seconds=15,term_seconds=10,kill_reap_seconds=5,overall_seconds=1830))
        put(out/'launch-plan.json', plan)
        put(out/'input.json',dict(arm=args.arm,case=args.case,baseline=baseline,
             version=run(['codex','--version'],text=True).stdout.strip(),
             started_at=datetime.datetime.now(datetime.timezone.utc).isoformat()))
        result = controller.execute(plan,out)
        put(out/'result.json',result)
    (out/'diff.patch').write_bytes(run(['git','diff',baseline,'--binary'],work).stdout)
    (out/'status.txt').write_bytes(run(['git','status','--short'],work).stdout)
    print(json.dumps(dict(draw=args.draw,exit_code=result['exit_code'],
        seconds=result['wrapper_return_seconds'],error=result['error'],
        quiescent=result['owned_writers_quiescent'],native_home_removed=not home.exists())),flush=True)

if __name__ == '__main__':
    main()
