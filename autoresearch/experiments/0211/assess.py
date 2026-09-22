"""One blinded static assessment after a locally sealed cell; no repair feedback."""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def assess(cell, runtime_path):
    runtime = json.loads(runtime_path.read_text())
    sealed = json.loads((cell / 'local-seal.json').read_text())
    if not sealed['eligible_for_assessment']:
        raise ValueError('cell is not sealed for assessment')
    out = cell / 'assessment'
    out.mkdir(exist_ok=False)
    call = out / '.devlyn/reviews/call-1'
    call.mkdir(parents=True)
    packet = module('packet', HERE.parent / '0205/review.py')
    before, prompt = packet.packet(cell / 'work')
    prompt = prompt.replace('This is exposed regression material, not blind research.',
                            'This is blinded outcome assessment. No arm label is supplied.')
    prompt = ('Assess the complete caller contract, source, regressions and actual checks. '
              'Return JSON with complete:boolean, findings with severity and concrete witnesses, '
              'and limitations. No tools or repairs. Do not infer an arm from coding style.\n' + prompt)
    prompt += '\nROOT DETERMINISTIC CHECKS\n' + (cell / 'checks.json').read_text()
    prompt = prompt.replace(str(cell), '/sealed-cell')
    prompt = '\n'.join(line for line in prompt.splitlines()
                       if 'duration_ms:' not in line and '# duration_ms ' not in line)
    (call / 'prompt.txt').write_text(prompt)
    argv = [sys.executable, '-B', str(ROOT / 'config/skills/_shared/run-bounded.py'), '230',
            '--stdin-file', str(call / 'prompt.txt'), '--', 'claude', '-p',
            '--model', 'claude-fable-5-1', '--effort', 'medium', '--tools', '',
            '--disable-slash-commands', '--permission-mode', 'dontAsk',
            '--setting-sources', '', '--strict-mcp-config', '--mcp-config', '{"mcpServers":{}}',
            '--no-session-persistence', '--output-format', 'stream-json', '--verbose']
    record = dict(argv=argv, started_at=time.time(), source_sha256=before,
                  prompt_sha256=packet.digest(call / 'prompt.txt'))
    (call / 'started.json').write_text(json.dumps(record, indent=2))
    start = time.monotonic()
    with tempfile.TemporaryDirectory(prefix='assessment-', dir=runtime['scratch']) as temp:
        home = Path(temp)
        (home / '.claude').mkdir()
        shutil.copyfile(Path(runtime['auth']) / 'claude.json', home / '.claude/.credentials.json')
        (home / '.claude/.credentials.json').chmod(0o600)
        env = {k: os.environ[k] for k in ('PATH', 'LANG', 'LC_ALL') if k in os.environ}
        env.update(HOME=temp, CLAUDE_CONFIG_DIR=str(home / '.claude'), TMPDIR=temp,
                   CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC='1', CLAUDE_CODE_MAX_RETRIES='0')
        with (call / 'stdout').open('xb') as stdout, (call / 'stderr').open('xb') as stderr:
            result = subprocess.run(argv, cwd=home, env=env, stdout=stdout, stderr=stderr)
    record.update(exit_code=result.returncode, seconds=time.monotonic()-start,
                  source_unchanged=before == {n: packet.digest(cell / 'work' / n) for n in before})
    (call / 'result.json').write_text(json.dumps(record, indent=2))
    controller = module('controller', HERE.parent / '0210/native_cell.py')
    usage, pending = controller.reviews(out)
    if pending or usage['calls'] != 1 or usage['input_tokens'] > 400000 or usage['output_tokens'] > 8000:
        raise ValueError('assessment accounting/observed target failure; stop screen')
    events = [json.loads(line) for line in (call / 'stdout').read_text().splitlines() if line.strip()]
    answer = next(e['result'] for e in events if e.get('type') == 'result')
    (out / 'answer.txt').write_text(answer)
    (out / 'usage.json').write_text(json.dumps(usage, indent=2))
    print(answer)


if __name__ == '__main__':
    assess(Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve())
