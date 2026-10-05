"""Dual blinded assessment of one sealed 0231 cell: assess.py <cell-out> <runtime.json>. Record only.

0222's packet and prompt, built on the selected snapshot laid over the allocation commit (so its diff and untracked
list are the product's), and run on the image's pinned CLIs instead of the host's.
"""
import importlib.util
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import time
import uuid

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location('assess0222', HERE.parent / '0222/assess.py')
base = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(base)
TASKS, packet, events = base.TASKS, base.packet, base.events


def review_tree(out, temp):
    """The snapshot as a working tree of a clone at the allocation commit, with the caller contract in .devlyn. Every
    tracked file goes first, so the snapshot's own files and symlinks (a symlink cannot be copied over an existing
    one) and its deletions are exactly what remains."""
    baseline = json.loads((out / 'baseline.json').read_text())
    work = temp / 'work'
    subprocess.run(['git', 'clone', '-q', '--shared', '--no-checkout', str(out / 'cell/work'), str(work)], check=True)
    subprocess.run(['git', '-C', str(work), 'checkout', '-q', '--detach', baseline['allocation_sha']], check=True)
    for name in subprocess.check_output(['git', 'ls-files', '-z'], cwd=work, text=True).split('\0'):
        if name:
            (work / name).unlink()
    shutil.copytree(out / 'snapshot', work, symlinks=True, dirs_exist_ok=True)
    (work / '.devlyn').mkdir(exist_ok=True)
    shutil.copyfile(out / 'harness/caller.json', work / '.devlyn/caller.json')
    return work


def reap(name):
    """Remove a named container and prove it is gone; any uncertainty is an evaluator STOP, never silence."""
    removed = subprocess.run(['docker', 'rm', '-f', name], capture_output=True, text=True, timeout=60)
    probe = subprocess.run(['docker', 'inspect', name], capture_output=True, text=True, timeout=60)
    gone = probe.returncode != 0 and 'No such object' in probe.stderr
    if not gone or (removed.returncode != 0 and 'No such container' not in removed.stderr):
        raise RuntimeError(f'cannot prove container {name} is gone: {removed.stderr.strip()} {probe.stderr.strip()}')


def valid(answer):
    """The assessor's JSON verdict, or None when it is not one: complete must be a boolean and findings a list of
    objects with a string severity. An invalid answer is no verdict (an evaluator STOP), never complete:false."""
    try:
        parsed = json.loads(re.search(r'\{.*\}', answer or '', re.S).group(0))
    except (AttributeError, ValueError):
        return None
    findings = parsed.get('findings') if isinstance(parsed, dict) else None
    if (not isinstance(parsed, dict) or not isinstance(parsed.get('complete'), bool) or not isinstance(findings, list)
            or not all(isinstance(f, dict) and isinstance(f.get('severity'), str) for f in findings)):
        return None
    return parsed


def one(out, runtime, route, prompt):
    record_dir = out / 'assessment' / route['engine']
    record_dir.mkdir(parents=True, exist_ok=False)
    (record_dir / 'prompt.txt').write_text(prompt)
    seconds_limit = TASKS['watchdog_seconds']['assessor']
    with tempfile.TemporaryDirectory(prefix='assess-', dir=runtime['scratch']) as temp:
        home = Path(temp) / 'home'
        home.mkdir()
        env = ['--env', 'HOME=/home/assessor', '--env', 'TMPDIR=/tmp']
        if route['engine'] == 'claude':
            (home / '.claude').mkdir()
            shutil.copyfile(Path(runtime['auth']) / 'claude.json', home / '.claude/.credentials.json')
            env += ['--env', 'CLAUDE_CONFIG_DIR=/home/assessor/.claude', '--env', 'CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1']
            command = ['claude', '-p', '--model', route['model'], '--effort', route['effort'], '--tools', '',
                       '--disable-slash-commands', '--permission-mode', 'dontAsk', '--setting-sources', '',
                       '--strict-mcp-config', '--mcp-config', '{"mcpServers":{}}', '--no-session-persistence',
                       '--output-format', 'stream-json', '--verbose']
        else:
            (home / '.codex').mkdir()
            shutil.copyfile(Path(runtime['auth']) / 'codex.json', home / '.codex/auth.json')
            env += ['--env', 'CODEX_HOME=/home/assessor/.codex']
            command = ['codex', 'exec', '--json', '--ignore-user-config', '--ignore-rules', '--skip-git-repo-check',
                       '--sandbox', 'read-only', '-m', route['model'], '-c',
                       f'model_reasoning_effort="{route["effort"]}"', '-C', '/tmp', '-']
        name = 'devlyn-0231-assess-' + uuid.uuid4().hex
        argv = ['docker', 'run', '--name', name, '--rm', '-i', '--network', 'bridge', '--read-only', '--cap-drop', 'ALL',
                '--security-opt', 'no-new-privileges', '--tmpfs', '/tmp:rw,nosuid,exec',
                '--tmpfs', '/home/assessor/.codex/tmp:rw,nosuid,exec,uid=501,gid=501',
                '--mount', f'type=bind,src={home},dst=/home/assessor', *env, runtime['image'],
                'timeout', '--kill-after=5s', f'{seconds_limit}s', *command]
        start = time.monotonic()
        try:
            with (record_dir / 'prompt.txt').open('rb') as stdin, (record_dir / 'stdout').open('xb') as stdout, \
                    (record_dir / 'stderr').open('xb') as stderr:
                result = subprocess.run(argv, stdin=stdin, stdout=stdout, stderr=stderr, timeout=seconds_limit + 60)
            exit_code = result.returncode
        except subprocess.TimeoutExpired:
            exit_code = None
        finally:
            reap(name)
        seconds = time.monotonic() - start
        if route['engine'] == 'codex' and (home / '.codex/sessions').exists():
            shutil.copytree(home / '.codex/sessions', record_dir / 'sessions')
    stream = events(record_dir / 'stdout')
    if route['engine'] == 'claude':
        final = [e for e in stream if e.get('type') == 'result']
        answer = final[-1].get('result') if final else None
        usage = final[-1].get('modelUsage') if final else None
    else:
        texts = [e['item'].get('text') for e in stream
                 if e.get('type') == 'item.completed' and e['item'].get('type') == 'agent_message']
        answer = texts[-1] if texts else None
        turns = [e['usage'] for e in stream if e.get('type') == 'turn.completed']
        usage = turns[-1] if turns else None
    parsed = valid(answer)
    severe = [f for f in (parsed or {}).get('findings', []) if str(f.get('severity', '')).lower() in ('high', 'critical')]
    record = dict(route=route, exit_code=exit_code, seconds=seconds, usage=usage or 'UNKNOWN',
                  complete=None if parsed is None else parsed['complete'], severe=len(severe), severe_findings=severe)
    (record_dir / 'result.json').write_text(json.dumps(record, indent=2))
    return record


def assess(out, runtime):
    with tempfile.TemporaryDirectory(prefix='review-', dir=runtime['scratch']) as temp:
        work = review_tree(out, Path(temp))
        before, prompt = packet.packet(work)
        prompt = prompt.replace('This is exposed regression material, not blind research.',
                                'This is blinded outcome assessment. No arm label is supplied.')
        prompt = ('Assess the complete caller contract, source, regressions and actual checks. '
                  'Return JSON with complete:boolean, findings with severity and concrete witnesses, '
                  'and limitations. No tools or repairs. Do not infer an arm from coding style.\n' + prompt)
        prompt += '\nROOT DETERMINISTIC CHECKS\n' + (out / 'checks.json').read_text()
        prompt = prompt.replace(str(work), '/sealed-cell/work').replace(str(out), '/sealed-cell')
        records = [one(out, runtime, route, prompt) for route in TASKS['assessors']]
        if before != {n: packet.digest(work / n) for n in before}:
            raise RuntimeError('sealed source changed during assessment')
    return records


if __name__ == '__main__':
    print(json.dumps(assess(Path(sys.argv[1]).resolve(), json.loads(Path(sys.argv[2]).read_text()))))
