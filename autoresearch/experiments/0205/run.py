"""Fixed three-cell follow-up; sources/evidence are retained and never rerolled."""
from pathlib import Path
import hashlib
import json
import os
import shutil
import stat
import subprocess
import sys
import time

R = Path(__file__).resolve().parents[3]
E = R / '.devlyn/0205'
W = R.parent / '0205-participants'
B = 'config/skills/_shared/resolve-bootstrap.py'


def seal(root):
    result = {}
    for p in sorted(root.rglob('*')):
        rel = p.relative_to(root)
        if {'.git', '.devlyn'} & set(rel.parts):
            continue
        s = p.lstat()
        if p.is_symlink():
            result[str(rel)] = ['link', os.readlink(p)]
        elif p.is_file():
            result[str(rel)] = ['file', stat.S_IMODE(s.st_mode), hashlib.sha256(p.read_bytes()).hexdigest()]
        elif p.is_dir():
            result[str(rel)] = ['dir', stat.S_IMODE(s.st_mode)]
    return result


def put(path, value):
    with path.open('x') as f:
        json.dump(value, f, ensure_ascii=False, indent=2)
        f.write('\n')


def prepare():
    W.mkdir(exist_ok=False)
    turns = json.loads((R / '.devlyn/0187-intent/REGISTRATION.json').read_text())['turns']
    configs = [
        dict(name='binding', source=str(R.parent / '0204-participant'), allowed=[B, 'tests/test_regression.py'],
             review_files=['spec.md', B, 'tests/test_smoke.py', 'tests/test_regression.py', 'config/skills/_shared/task-complete.py'],
             request=(R.parent / '0204-participant/spec.md').read_text(), original_context='',
             finding='Historical Fable0204 final review: base_branch removeprefix returns refs/tags/t for HEAD->refs/tags/t. '
                     'A real branch named refs/tags/t (refs/heads/refs/tags/t) has the same string, so its receipt is wrongly bound. '
                     'Reproduce with actual Git and a matching receipt before repair. Non-branch HEAD must not bind a branch receipt. '
                     'Only repair this demonstrated finding; inherited Windows junction finding stays unexecuted/open.',
             checks='python3 -B -m unittest discover -s tests; python3 -B config/skills/_shared/resolve-bootstrap.py --self-test. '
                    'Add actual-Git symbolic-HEAD regression for all three modes, retain branch/tag and NBSP controls.'),
        dict(name='rollback', source=str(R.parent / '0185-participants/install-1-C'),
             allowed=['bin/devlyn.js', 'tests/regression*.js'],
             review_files=['spec.md', 'bin/devlyn.js', 'tests/acceptance.js', 'tests/support.js'],
             request=(R / 'autoresearch/experiments/0185/request.md').read_text(), original_context='',
             finding='Root0185 post-seal counterexample: .devlyn/0185/replay-absence.js injects failure on the second publication '
                     'then reenters at removal of initially absent skills directory. Lock was already released; contender succeeds '
                     'and corrupts restoration. Run the copied .devlyn/replay-absence.js before repair, assert failed AND contender '
                     'actually triggered. Keep exclusion through every rollback shared-path operation. Repair only this lifecycle defect.',
             checks='node --test tests/acceptance.js; node --test .devlyn/heldout.js; '
                    'node .devlyn/replay-absence.js bin/devlyn.js; '
                    'node .devlyn/replay.js bin/devlyn.js release; node .devlyn/replay.js bin/devlyn.js alias; '
                    'node .devlyn/replay-terminal.js bin/devlyn.js alias. Replay scripts return JSON: exit0 alone is not PASS; passed must be true.'),
        dict(name='scope', source=str(R / '.devlyn/0187-other/inputs/x1'), allowed=['palette.py', 'tests/test_regression.py'],
             review_files=['palette.py','adapters.py','tests/test_acceptance.py','tests/test_regression.py','tests/native_bridge_check.py'],
             request='\n\n'.join(turns[:3]), original_context=(R / '.devlyn/0187-intent/seed/palette.py').read_text(),
             finding=(R / '.devlyn/0187-other/x1-other-review.json').read_text(),
             checks='python3 -B -m unittest discover -s tests; python3 -B tests/native_bridge_check.py. '
                    'Also verify dynamic advertised commands/order/fields and unknown-engine compatibility. '
                    'Bridge77 is UNAVAILABLE, never PASS. Include small mutation checks for false Claude-only/drop-model advice '
                    'inside checkout only; preserve originals. Do not follow the fourth historical handoff turn; it is not supplied.')]
    for c in configs:
        source = Path(c['source']); work = W / c['name']; out = E / c['name']
        out.mkdir(exist_ok=False)
        before = seal(source)
        shutil.copytree(source, work, ignore=shutil.ignore_patterns('.git','.devlyn','__pycache__','.agents'))
        # Existing policy files stay as immutable source, but native project-doc loading is disabled.
        subprocess.run(['git','init','-q','-b','conformance'],cwd=work,check=True)
        subprocess.run(['git','add','.'],cwd=work,check=True)
        subprocess.run(['git','-c','user.name=Conformance','-c','user.email=conformance@local','commit','-qm','exposed input'],cwd=work,check=True)
        evidence = work / '.devlyn'; evidence.mkdir(); (evidence / 'tmp').mkdir()
        if c['name']=='rollback':
            for name in ('replay-absence.js','replay.js','replay-terminal.js'):
                text=(R / '.devlyn/0185' / name).read_text().replace("require('../../autoresearch/experiments/0185/support')", "require('../tests/support')")
                (evidence/name).write_text(text)
            shutil.copyfile(R/'autoresearch/experiments/0185/heldout.js', evidence/'heldout.js')
            p=evidence/'heldout.js';p.write_text(p.read_text().replace("require('./support')", "require('../tests/support')"))
        put(evidence / 'caller.json', c)
        put(out / 'input.json', dict(config=c, source_seal=before, participant_seal=seal(work)))
        prompt = (R / 'autoresearch/experiments/0204/owner.md').read_text() + f'''

CALLER CONTEXT:0205 exposed {c['name']} follow-up. Selected Codex owner gpt-6-astra/high.
Work only in {work}, including all temporary experiments; TMPDIR points to .devlyn/tmp.
Read .devlyn/caller.json: original request, context, known finding, allowed files and checks.
This new diagnostic does not revise prior results. Source, spec, caller inputs, supplied
checks, AGENTS/CLAUDE and external helper are immutable. No weakening existing assertions.
No network, commits, branches, publication, external writes or sibling-answer access.
Only permitted model call is the one final static review below; no resolve/delegates.
Reproduce the supplied actionable finding BEFORE editing; save exact commands, stdout,
stderr, exit codes and source hashes under .devlyn/red. Make the smallest in-scope repair,
add necessary regressions, run every supplied check and save raw results in
.devlyn/checks-final. Preserve explicit user scope over generic advice or false findings.
No required check may be silently omitted. Report unavailable integrations accurately.
Then call exactly once:
python3 -B {R}/autoresearch/experiments/0205/review.py {work}
This actual Fable5.1 review has240s bound within your1200s total wall budget. The helper
reads original request/source/checks without historical reviewer advice. It may write only
its own evidence output. Any unavailable/error route blocks visibly; no retry/substitution.
Do not change source after that final review; new findings stay unresolved. At end inspect
tracked/staged/untracked files and task-created caches/temp data. Remove only your disposable
test debris, retain source/recovery/raw evidence. Write .devlyn/owner-result.json with final
hashes, per-obligation results, red/recheck paths, findings and limitations. Never claim global
PASS from a narrower witness. Historical Windows or integration limits remain explicit.
'''
        (out/'prompt.txt').write_text(prompt)
    put(E/'registration.json', dict(order=[c['name'] for c in configs], bound=1200,
        model='gpt-6-astra',effort='high', review_model='claude-fable-5-1',review_effort='medium',
        source_sha256={str(p.relative_to(R)):hashlib.sha256(p.read_bytes()).hexdigest()
            for p in [Path(__file__),R/'autoresearch/experiments/0205/review.py',R/'autoresearch/experiments/0205/PROTOCOL.md',R/'autoresearch/experiments/0204/owner.md']}))


def run(name):
    registration = 'registration.json' if name == 'binding' else 'registration-followup.json'
    reg=json.loads((E/registration).read_text())
    assert name in reg['order']
    for p,h in reg['source_sha256'].items():
        assert hashlib.sha256((R/p).read_bytes()).hexdigest()==h,p
    work=W/name;out=E/name
    argv=[sys.executable,'-B',str(R/'config/skills/_shared/run-bounded.py'),'1200',
        '--stdin-file',str(out/'prompt.txt'),'--record-transport','--',shutil.which('codex'),'exec',
        '--ignore-user-config','--strict-config','--ignore-rules','--model','gpt-6-astra',
        '-c','model_reasoning_effort="high"','-c','project_doc_max_bytes=0','-c','web_search="disabled"',
        '-c',(R/'.devlyn/0179/catalog-setting.txt').read_text().strip(),'-s','danger-full-access','--skip-git-repo-check','--json']
    for feature in ('multi_agent','apps','plugins','hooks','skill_search'):
        argv+=['--disable',feature]
    argv+=['--enable','skip_host_skill_discovery','-']
    env={k:os.environ[k] for k in ('HOME','PATH','LANG','LC_ALL','TERM','SHELL','USER','LOGNAME') if k in os.environ}
    env.update(TMPDIR=str(work/'.devlyn/tmp'),PYTHONDONTWRITEBYTECODE='1',GIT_CONFIG_GLOBAL=os.devnull,GIT_CONFIG_NOSYSTEM='1',GIT_TEMPLATE_DIR='')
    put(out/'started.json',dict(argv=argv,cwd=str(work),started_at=time.time(),prompt_sha256=hashlib.sha256((out/'prompt.txt').read_bytes()).hexdigest()))
    start=time.monotonic()
    with (out/'stdout').open('xb') as stdout,(out/'stderr').open('xb') as stderr:
        result=subprocess.run(argv,cwd=work,env=env,stdout=stdout,stderr=stderr)
    put(out/'result.json',dict(exit_code=result.returncode,seconds=time.monotonic()-start,files=seal(work)))
    print(name,result.returncode,flush=True)


if __name__=='__main__':
    prepare() if sys.argv[1]=='prepare' else run(sys.argv[1])
