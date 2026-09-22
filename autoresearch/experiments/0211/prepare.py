"""Materialize one registered cell; does not dispatch models or schedule cells."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prepare(index, runtime_path):
    runtime = json.loads(runtime_path.read_text())
    registration = json.loads((HERE.parent / '0206/tasks.json').read_text())
    entry = registration['cells'][index]
    task = next(t for t in registration['tasks'] if t['id'] == entry['task'])
    name = f"{index + 1:02d}-{task['id']}-{entry['repetition']}-{entry['arm']}"
    out = Path(runtime['output']) / name
    out.mkdir(parents=True, exist_ok=False)
    source = Path(runtime['sources']) / ('commander' if task['id'] in ('D1', 'D3') else 'click')
    work = out / 'work'
    subprocess.run(['git', 'clone', '--no-hardlinks', '--quiet', str(source), str(work)], check=True)
    subprocess.run(['git', 'checkout', '--quiet', '--detach', task['base_sha']], cwd=work, check=True)
    subprocess.run(['git', 'remote', 'remove', 'origin'], cwd=work, check=True)
    if subprocess.check_output(['git', 'status', '--porcelain'], cwd=work):
        raise ValueError('non-clean registered source')
    (work / '.devlyn').mkdir()
    issue = Path(runtime['sources']) / (task['id'] + '-issue.json')
    if digest(issue) != task['issue_snapshot_sha256']:
        raise ValueError('issue changed')
    review_files = sorted({str(p.relative_to(work)) for pattern in task['allowed']
                           for p in work.glob(pattern) if p.is_file()})
    caller = dict(request=task['request'] + '\n\nREQUIREMENTS\n' + '\n'.join(task['obligations']),
                  allowed=task['allowed'], review_files=review_files,
                  original_context=issue.read_text(), public_checks=task['public_checks'])
    (work / '.devlyn/caller.json').write_text(json.dumps(caller, indent=2))
    home = out / 'home'
    (home / '.codex').mkdir(parents=True)
    (home / '.codex/config.toml').write_bytes((HERE / 'codex.toml').read_bytes())
    prompt = (HERE / 'common.txt').read_text() + '\n\nCALLER CONTRACT\n' + json.dumps(caller, indent=2)
    prompt += (f"\nObserved whole-cell targets, including all descendants and teardown: "
               f"{task['wall_seconds']} seconds, {task['input_tokens']} cache-inclusive INPUT, "
               f"{task['output_tokens']} OUTPUT including reasoning once, 5 model invocations.\n")
    if entry['arm'] == 'B':
        candidate = HERE.parent / '0204/owner.md'
        if digest(candidate) != registration['candidate_sha256']:
            raise ValueError('candidate changed')
        prompt += '\n\n' + candidate.read_text()
    elif entry['arm'] == 'C':
        prompt += ('\nAn independent final review is mandatory. Repair actionable findings with '
                   'executed evidence, then obtain fresh review after any source repair. '
                   'Use the same two-review/four-descendant pool; unresolved findings after '
                   'the second review mean PRODUCT_INCOMPLETE.\n')
    (out / 'prompt.txt').write_text(prompt)
    argv = ['env', 'PYTHONPATH=/work/src:/control/python',
            'PATH=/control/less/usr/bin:/opt/codex/bin:/opt/codex/codex-path:/usr/local/bin:/usr/local/sbin:/usr/sbin:/usr/bin:/sbin:/bin',
            'codex', 'exec', '--strict-config', '--ignore-rules', '--json',
            '--skip-git-repo-check', '-C', '/work', prompt]
    plan = dict(work=str(work), home=str(home), control=runtime['control'], auth=runtime['auth'],
                image=runtime['image'], network='bridge', argv=argv,
                wall_seconds=task['wall_seconds'], input_tokens=task['input_tokens'],
                output_tokens=task['output_tokens'], model_calls=5, model='gpt-6-astra', effort='high')
    (out / 'plan.json').write_text(json.dumps(plan, indent=2))
    protected = {str(p.relative_to(work)): digest(p) for p in work.rglob('*')
                 if p.is_file() and '.git' not in p.relative_to(work).parts}
    (out / 'baseline.json').write_text(json.dumps(dict(entry=entry, task=task,
        files=protected, prompt_sha256=digest(out / 'prompt.txt'),
        config_sha256=digest(home / '.codex/config.toml')), indent=2))
    print(out)


if __name__ == '__main__':
    prepare(int(sys.argv[1]), Path(sys.argv[2]).resolve())
