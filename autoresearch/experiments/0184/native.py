"""Bounded native participants with disposable configs and raw transport evidence."""
from pathlib import Path
import datetime,hashlib,importlib.util,json,os,shutil,subprocess,tempfile

REPO=Path(__file__).resolve().parents[3];E=REPO/'.devlyn/0184'
SCRATCH=REPO/'.git/devlyn-completion/500627caa6c42463728dd5e5/scratch'
spec=importlib.util.spec_from_file_location('controller',REPO/'autoresearch/scripts/comparison-controller.py')
controller=importlib.util.module_from_spec(spec);spec.loader.exec_module(controller)

def put(path,obj):
    with path.open('x') as stream:json.dump(obj,stream,indent=2)

def invoke(run_id,prompt,work=None,engine='codex',review=False,budget=1200):
    out=E/'runs'/run_id;out.mkdir(parents=True,exist_ok=False);(out/'prompt.txt').write_text(prompt)
    previous=dict(os.environ)
    with tempfile.TemporaryDirectory(prefix=run_id+'-',dir=SCRATCH) as temporary:
        home=Path(temporary);neutral=home/'neutral';neutral.mkdir();cwd=neutral if review else work
        env={k:previous[k] for k in ('HOME','PATH','TMPDIR','LANG','LC_ALL','TERM','SHELL','USER','LOGNAME') if k in previous}
        env['PYTHONDONTWRITEBYTECODE']='1'
        common=[]
        if engine=='codex':
            for name in ('auth.json','models_cache.json'):
                src=Path('/Users/aipalm/.codex')/name if name=='auth.json' else E/name
                shutil.copyfile(src,home/name);(home/name).chmod(0o600)
            selector=(E/'catalog-setting.txt').read_text().strip()
            (home/'config.toml').write_text('model="gpt-6-astra"\nmodel_reasoning_effort="high"\nweb_search="disabled"\nproject_doc_max_bytes=0\n'+selector+'\n[features]\nmulti_agent=false\napps=false\nplugins=false\nhooks=false\nskill_search=false\nskip_host_skill_discovery=true\n')
            env['CODEX_HOME']=str(home)
            common=['--config','model_reasoning_effort="high"','--config','project_doc_max_bytes=0','--config','web_search="disabled"','--config',selector]
            for feature in ('multi_agent','apps','plugins','hooks','skill_search'):common+=['--disable',feature]
            common+=['--enable','skip_host_skill_discovery']
            native=[shutil.which('codex'),'exec','--ignore-user-config','--strict-config','--ignore-rules','--ephemeral','--sandbox','read-only' if review else 'danger-full-access','--model','gpt-6-astra',*common,'--skip-git-repo-check','--json','--color','never','-']
            render=subprocess.run([shutil.which('codex'),'--config','model="gpt-6-astra"','--config','sandbox_mode="read-only"' if review else 'sandbox_mode="danger-full-access"',*common,'debug','prompt-input',prompt],cwd=cwd,env=env,capture_output=True,timeout=30,check=True)
            (out/'render.json').write_bytes(render.stdout);(out/'render.stderr').write_bytes(render.stderr)
            for message in json.loads(render.stdout):
                for block in message.get('content',[]):
                    text=block.get('text','');assert 'Persistent Memory' not in text and '(file: ' not in text
        elif engine=='fable':
            native=[shutil.which('claude'),'-p','--model','claude-fable-5-1','--effort','high','--tools','','--disable-slash-commands','--permission-mode','dontAsk','--setting-sources','','--strict-mcp-config','--mcp-config','{"mcpServers":{}}','--no-session-persistence','--output-format','stream-json','--verbose']
        else:raise ValueError(engine)
        argv=['/opt/homebrew/bin/python3','-B',str(REPO/'config/skills/_shared/run-bounded.py'),str(budget),'--stdin-file',str(out/'prompt.txt'),'--record-transport','--',*native]
        plan=dict(work=str(cwd),argv=argv,bounds=dict(native_seconds=1800,wrapper_seconds=1810,post_return_quiet_seconds=15,term_seconds=10,kill_reap_seconds=5,overall_seconds=1830))
        put(out/'launch-plan.json',plan)
        put(out/'input.json',dict(engine=engine,review=review,started_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),prompt_sha256=hashlib.sha256(prompt.encode()).hexdigest()))
        try:
            os.environ.clear();os.environ.update(env)
            result=controller.execute(plan,out);put(out/'result.json',result)
        finally:os.environ.clear();os.environ.update(previous)
    events=[]
    for line in (out/'stdout').read_text(errors='replace').splitlines():
        try:event=json.loads(line)
        except ValueError:continue
        if isinstance(event,dict):events.append(event)
    if engine=='codex':
        messages=[e['item']['text'] for e in events if e.get('type')=='item.completed' and e.get('item',{}).get('type')=='agent_message']
        calls=[e['item'] for e in events if e.get('type')=='item.completed' and e.get('item',{}).get('type') not in ('agent_message','reasoning','todo_list','error')]
        usage=[e['usage'] for e in events if e.get('type')=='turn.completed' and 'usage' in e]
        meta=dict(native_errors=[e['item'] for e in events if e.get('item',{}).get('type')=='error'],usage=usage,requested_model='gpt-6-astra',requested_effort='high',tool_events=len(calls))
    else:
        terminal=[e for e in events if e.get('type')=='result'];messages=[e.get('result','') for e in terminal]
        calls=[c for e in events for c in e.get('message',{}).get('content',[]) if isinstance(c,dict) and c.get('type')=='tool_use']
        meta=dict(native_results=terminal,init=[e for e in events if e.get('type')=='system' and e.get('subtype')=='init'],requested_model='claude-fable-5-1',requested_effort='high',tool_events=len(calls))
        assert terminal and not any(e.get('is_error') for e in terminal),'Fable native error'
        assert meta['init'] and all(e.get('model')=='claude-fable-5-1' and not e.get('tools') and not e.get('mcp_servers') and not e.get('plugins') for e in meta['init']),'Fable role/isolation mismatch'
        assert any('claude-fable-5-1' in e.get('modelUsage',{}) for e in terminal),'Missing Fable model usage'
    answer=messages[-1] if messages else ''
    (out/'answer.txt').write_text(answer);meta.update(native_home_removed=not home.exists(),seconds=result['wrapper_return_seconds'],exit_code=result['exit_code'],quiescent=result['owned_writers_quiescent'],error=result['error'])
    put(out/'telemetry.json',meta)
    print(json.dumps(dict(run=run_id,seconds=meta['seconds'],exit_code=meta['exit_code'],tool_events=meta['tool_events'],quiescent=meta['quiescent'])),flush=True)
    if result['error'] or not result['owned_writers_quiescent'] or result['exit_code']!=0 or not answer:
        raise RuntimeError('Native run did not return a usable quiescent result: '+run_id)
    if review and calls:raise RuntimeError('Review no-tool fidelity failed: '+run_id)
    return answer,meta
