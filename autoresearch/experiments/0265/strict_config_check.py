"""DESIGN Q3, Codex config honoured: strict_config_check.py <runtime.json>. No model call.

The 0265 config.toml (prepare.codex_config, the file both arms get) must load under the pinned Codex's
--strict-config (allowed); the same file plus one unknown top-level key and one unknown [features] key must fail at
config load (violating). Both run raw in the cell image as `codex --strict-config debug prompt-input "Reply OK."`,
offline and with no credential. When that form does not take the flag, or accepts the violating file, nothing is
concluded: the two `codex exec --strict-config` commands (one model call each, the orchestrator's decision) are
printed with their config homes kept, and are not run.

Exit 0 PASS, 1 FAIL, 3 undecided.
"""
import importlib.util
import json
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import uuid

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location('prepare0265s', HERE / 'prepare.py')
prepare = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(prepare)
UNKNOWN = ('zz_unknown_top_0265', 'zz_unknown_feature_0265')
PROMPT = 'Reply OK.'
SMOKE_TREE = HERE.parents[2] / 'autoresearch/experiments/0222/smoke/repo'


def configs():
    """(allowed, violating) config.toml texts."""
    allowed = prepare.codex_config(prepare.TASKS['routes']['codex']['owner'])
    if allowed.count('[features]\n') != 1:
        raise ValueError('expected one [features] table')
    return allowed, f'{UNKNOWN[0]} = true\n' + allowed.replace('[features]\n', f'[features]\n{UNKNOWN[1]} = true\n')


def codex_home(folder, text, models_cache):
    (folder / '.codex').mkdir(parents=True)
    (folder / '.codex/config.toml').write_text(text)
    if models_cache:
        shutil.copyfile(models_cache, folder / '.codex/models_cache.json')
    return folder


def docker_argv(image, home, name, command, extra=()):
    return ['docker', 'run', '--name', name, '--rm', '--read-only', '--cap-drop', 'ALL',
            '--security-opt', 'no-new-privileges', '--tmpfs', '/tmp:rw,exec',
            '--tmpfs', '/home/probe/.codex/tmp:rw,nosuid,exec,uid=501,gid=501',
            '--mount', f'type=bind,src={home},dst=/home/probe', '--env', 'HOME=/home/probe',
            '--env', 'CODEX_HOME=/home/probe/.codex', *extra, image, 'timeout', '120s', *command]


def run(argv):
    """(exit code or None on timeout, stdout, stderr) of one docker command."""
    try:
        done = subprocess.run(argv, capture_output=True, text=True, timeout=180)
    except subprocess.TimeoutExpired:
        return None, '', 'timed out after 180 s'
    return done.returncode, done.stdout, done.stderr


def decide(allowed, violating):
    """The (code, stdout, stderr) of each debug run -> (PASS | FAIL | UNDECIDED, why)."""
    for _, _, err in (allowed, violating):
        # clap's refusal, or Codex 0.164.0's own: "Error: `--strict-config` is not supported for `codex debug`".
        if re.search(r'(unexpected argument|unrecognized|not supported).*--strict-config'
                     r'|--strict-config.*not supported', err):
            return 'UNDECIDED', 'this Codex form does not take --strict-config: ' + err.strip()[-500:]
    if allowed[0] != 0:
        return 'FAIL', f'the 0265 config.toml does not load (exit {allowed[0]}): {allowed[2].strip()[-2000:]}'
    if violating[0] == 0:
        return 'UNDECIDED', 'debug prompt-input accepted the violating file, so it does not apply --strict-config'
    named = [key for key in UNKNOWN if key in violating[1] + violating[2]]
    if not named:
        return 'FAIL', (f'the violating file failed for another reason (exit {violating[0]}): '
                        f'{violating[2].strip()[-2000:]}')
    return 'PASS', f'the 0265 file loads; the violating file fails at config load naming {named}'


def exec_commands(runtime, texts):
    """The two model-call commands an orchestrator may run instead; their config homes are kept for it."""
    keep = Path(tempfile.mkdtemp(prefix='strict-config-exec-', dir=runtime['scratch']))
    commands = []
    for label, text in zip(('allowed', 'violating'), texts):
        home = codex_home(keep / label, text, runtime.get('models_cache'))
        (home / '.codex/auth.json').touch()  # mount target only; the login is bind-mounted read-only
        commands.append(shlex.join(docker_argv(
            runtime['image'], home, f'devlyn-0265-strict-{label}-<uuid>',
            ['codex', 'exec', '--strict-config', '--json', '--skip-git-repo-check', PROMPT],
            ['--network', 'bridge', '--mount', f'type=bind,src={Path(runtime["auth"]) / "codex.json"},'
             f'dst=/home/probe/.codex/auth.json,readonly',
             '--mount', f'type=bind,src={SMOKE_TREE},dst=/cell/work,readonly', '-w', '/cell/work'])))
    return commands


def main(runtime_path, runner=run):
    runtime = json.loads(Path(runtime_path).read_text())
    texts = configs()
    results = []
    with tempfile.TemporaryDirectory(prefix='strict-config-', dir=runtime['scratch']) as temp:
        for label, text in zip(('allowed', 'violating'), texts):
            home = codex_home(Path(temp) / label, text, runtime.get('models_cache'))
            name = 'devlyn-0265-strict-' + uuid.uuid4().hex
            result = runner(docker_argv(runtime['image'], home, name,
                                        ['codex', '--strict-config', 'debug', 'prompt-input', PROMPT],
                                        ['--network', 'none', '-w', '/tmp']))
            if result[0] is None:
                runner(['docker', 'rm', '-f', name])
            results.append(result)
    status, why = decide(*results)
    print(f'{status}: {why}')
    if status == 'UNDECIDED':
        print('Not run (one model call each, the orchestrator decides):')
        for command in exec_commands(runtime, texts):
            print(command)
    return {'PASS': 0, 'FAIL': 1, 'UNDECIDED': 3}[status]


if __name__ == '__main__':
    sys.exit(main(sys.argv[1]))
