"""Materialize one cell: prepare.py <runtime.json> <name> <task> <arm> <config>. Never dispatches models."""
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys

HERE = Path(__file__).resolve().parent
TASKS = json.loads((HERE / 'tasks.json').read_text())
_spec = importlib.util.spec_from_file_location('packet0222', HERE / 'packet.py')
packet = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(packet)
REVIEW = ('Before finishing, obtain an independent review with `python3 /control/review.py`; it sends the request, '
          'allowed files, your diff and any files you put under /work/.devlyn/checks-final to a reviewer without '
          'tools. Reproduce and repair actionable findings, rerun affected checks, and obtain a fresh review after '
          'any source change.')
INSTALL = {'claude': ['-y'], 'codex': ['agents', 'codex']}
SKILL = '/home/participant/.codex/skills/devlyn:resolve/SKILL.md'


def git(work, *args):
    return subprocess.run(['git', *args], cwd=work, check=True, capture_output=True, text=True).stdout.strip()


def source(task, runtime, work):
    if 'source_dir' in task:
        shutil.copytree(HERE.parents[2] / task['source_dir'], work)
        if packet.content(packet.tree(work)) != task['source_sha256']:
            raise ValueError(task['id'] + ' registered inputs changed')
        git(work, 'init', '-q', '-b', 'main')
    else:
        subprocess.run(['git', 'clone', '--no-hardlinks', '--quiet', str(Path(runtime['sources']) / task['source']),
                        str(work)], check=True)
        git(work, 'checkout', '-q', '-B', 'main', task['base_sha'])
        git(work, 'remote', 'remove', 'origin')
    for key, value in (('user.name', 'Participant'), ('user.email', 'participant@localhost'), ('commit.gpgsign', 'false')):
        git(work, 'config', key, value)
    if 'source_dir' in task:
        git(work, 'add', '-A')
        git(work, 'commit', '-qm', 'registered inputs')
    with (work / '.git/info/exclude').open('a') as exclude:
        exclude.write('.devlyn/\n')


def install(runtime, work, home, config):
    """Arm F: the published 3.2.1 installer, offline, in the cell image; its output becomes the baseline."""
    subprocess.run(['docker', 'run', '--rm', '--network', 'none', '--cap-drop', 'ALL',
                    '--security-opt', 'no-new-privileges', '--env', 'HOME=/home/participant', '-w', '/work',
                    '--mount', f'type=bind,src={work},dst=/work', '--mount', f'type=bind,src={home},dst=/home/participant',
                    '--mount', f'type=bind,src={runtime["control"]},dst=/control,readonly', runtime['image'],
                    'node', '/control/devlyn-cli/package/bin/devlyn.js', *INSTALL[config]],
                   check=True, capture_output=True, timeout=300)
    git(work, 'add', '-A')
    git(work, 'commit', '-qm', 'install devlyn-cli 3.2.1')


def codex_toml(owner):
    return (f'model = "{owner["model"]}"\nmodel_reasoning_effort = "{owner["effort"]}"\n'
            'approval_policy = "never"\nsandbox_mode = "danger-full-access"\nweb_search = "disabled"\n'
            '[features]\nrollout_budget = false\napps = false\nplugins = false\nhooks = false\nshell_snapshot = false\n'
            '[features.multi_agent_v2]\nenabled = true\nexpose_spawn_agent_model_overrides = false\n'
            f'[agents]\ndefault_subagent_model = "{owner.get("child_model", owner["model"])}"\n'
            f'default_subagent_reasoning_effort = "{owner.get("child_effort", owner["effort"])}"\n'
            'max_concurrent_threads_per_session = 4\n[projects."/work"]\ntrust_level = "trusted"\n')


def prepare(runtime, name, task_id, arm, config):
    task = next(t for t in TASKS['tasks'] if t['id'] == task_id)
    route = TASKS['routes'][config]
    if arm not in ('A', 'C', 'F'):
        raise ValueError("arm must be A, C or F; B' binds its candidate package in Session 5")
    out = Path(runtime['output']) / name
    out.mkdir(parents=True, exist_ok=False)
    work, home = out / 'work', out / 'home'
    source(task, runtime, work)
    (home / '.codex').mkdir(parents=True)
    (home / '.claude').mkdir()
    if config == 'codex':
        (home / '.codex/config.toml').write_text(codex_toml(route['owner']))
    if arm == 'F':
        install(runtime, work, home, config)
        (work / '.devlyn').mkdir()
        (work / '.devlyn/engines.json').write_text(json.dumps(dict(roles=route['F_roles']), indent=2) + '\n')
    # task-complete accepts only a GitHub remote; the cell has no push credentials.
    git(work, 'remote', 'add', 'origin', f'https://github.com/{task["repository"]}.git')
    if git(work, 'status', '--porcelain', '--untracked-files=all'):
        raise ValueError('baseline is not clean')
    issue = Path(runtime['sources']) / f'{task_id}-issue.json'
    if 'issue_snapshot_sha256' in task and hashlib.sha256(issue.read_bytes()).hexdigest() != task['issue_snapshot_sha256']:
        raise ValueError(task_id + ' issue snapshot changed')
    request = task['request'] + ('\n\nREQUIREMENTS\n' + '\n'.join(task['obligations']) if task['obligations'] else '')
    caller = dict(request=request, allowed=task['allowed'], public_checks=task['public_checks'],
                  review_files=sorted(n for n in packet.tree(work) if packet.allowed(n, task['allowed'])),
                  original_context=issue.read_text() if 'issue_snapshot_sha256' in task else '',
                  base_sha=git(work, 'rev-parse', 'HEAD'))
    (work / '.devlyn').mkdir(exist_ok=True)
    (work / '.devlyn/caller.json').write_text(json.dumps(caller, indent=2))
    common = (HERE / 'common.txt').read_text()
    if arm == 'F':
        goal = (request + '\n\nALLOWED PATHS\n' + '\n'.join(task['allowed']) + '\n\nPUBLIC CHECKS\n'
                + '\n'.join(task['public_checks']) + '\n\nCONSTRAINTS\n' + common.replace('There is no later repair turn. ', '')
                + 'Local-only: do not push or open a pull request.\n')
        (work / '.devlyn/goal.txt').write_text(goal)
        prompt = ('/devlyn:resolve --goal-file .devlyn/goal.txt' if config == 'claude' else
                  f'Read {SKILL} and execute /devlyn:resolve --goal-file .devlyn/goal.txt')
    else:
        prompt = common + '\nCALLER CONTRACT\n' + json.dumps(caller, indent=2) + ('\n\n' + REVIEW if arm == 'C' else '')
    (out / 'prompt.txt').write_text(prompt)
    owner = route['owner']
    env = dict(HOME='/home/participant', CODEX_HOME='/home/participant/.codex', DISABLE_AUTOUPDATER='1',
               PYTHONPATH='/work/src:/control/python', GIT_CONFIG_GLOBAL='/dev/null', GIT_CONFIG_NOSYSTEM='1')
    if arm == 'C':
        reviewer = route['reviewer']
        env['DEVLYN_REVIEWER'] = ':'.join((reviewer['engine'], reviewer['model'], reviewer['effort']))
    argv = (['claude', '-p', '--model', owner['model'], '--effort', owner['effort'], '--permission-mode',
             'bypassPermissions', '--output-format', 'stream-json', '--verbose', prompt] if config == 'claude' else
            ['codex', 'exec', '--strict-config', '--json', '--skip-git-repo-check', '-C', '/work', prompt])
    plan = dict(name=name, task=task_id, arm=arm, config=config, engine=owner['engine'], model=owner['model'],
                effort=owner['effort'], wall_seconds=TASKS['watchdog_seconds']['owner'], image=runtime['image'],
                work=str(work), home=str(home), control=runtime['control'], auth=runtime['auth'], env=env, argv=argv)
    (out / 'plan.json').write_text(json.dumps(plan, indent=2))
    digest = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
    (out / 'baseline.json').write_text(json.dumps(dict(
        task=task_id, arm=arm, config=config, files=packet.tree(work), prompt_sha256=digest(out / 'prompt.txt'),
        caller_sha256=digest(work / '.devlyn/caller.json'),
        prepare_sha256=digest(Path(__file__)), tasks_sha256=digest(HERE / 'tasks.json')), indent=2))
    return out


if __name__ == '__main__':
    print(prepare(json.loads(Path(sys.argv[1]).read_text()), *sys.argv[2:6]))
