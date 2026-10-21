"""Generate the pinned Codex model cache: models_cache.py <runtime.json> <out>."""
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import uuid

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location('models_cache_assess0233', HERE.parent / '0233/assess.py')
_assess = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_assess)
reap = _assess.reap


def command(runtime, home):
    name = 'devlyn-0256-cache-' + uuid.uuid4().hex
    return ['docker', 'run', '--name', name, '--rm', '--network', 'bridge', '--read-only',
            '--cap-drop', 'ALL', '--security-opt', 'no-new-privileges', '--tmpfs', '/tmp:rw,exec',
            '--tmpfs', '/home/probe/.codex/tmp:rw,nosuid,exec,uid=501,gid=501',
            '--mount', f'type=bind,src={home},dst=/home/probe', '--env', 'HOME=/home/probe',
            '--env', 'CODEX_HOME=/home/probe/.codex', runtime['image'], 'timeout', '120s',
            'codex', 'exec', '--ignore-user-config', '--ignore-rules', '--skip-git-repo-check',
            '-s', 'read-only', '-m', 'gpt-6-astra', '-c', 'model_reasoning_effort=low',
            '-C', '/tmp', 'Reply OK.']


def generate(runtime, out):
    out = Path(out)
    if out.exists():
        raise FileExistsError(out)
    with tempfile.TemporaryDirectory(prefix='0256-models-', dir=runtime['scratch']) as temp:
        home = Path(temp)
        codex_home = home / '.codex'
        codex_home.mkdir(mode=0o700)
        shutil.copyfile(Path(runtime['auth']) / 'codex.json', codex_home / 'auth.json')
        argv = command(runtime, home)
        try:
            subprocess.run(argv, capture_output=True, timeout=180)
        finally:
            reap(argv[argv.index('--name') + 1])
        cache = codex_home / 'models_cache.json'
        if not cache.is_file():
            raise RuntimeError('pinned Codex wrote no models cache')
        data = cache.read_bytes()
        with out.open('xb') as stream:
            stream.write(data)
    value = hashlib.sha256(data).hexdigest()
    print(value)
    return value


if __name__ == '__main__':
    generate(json.loads(Path(sys.argv[1]).read_text()), sys.argv[2])
