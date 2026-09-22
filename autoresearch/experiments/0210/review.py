"""One static Fable call using the existing 0205 evidence packet and bounded runner."""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time

spec = importlib.util.spec_from_file_location('packet', '/control/autoresearch/experiments/0205/review.py')
packet = importlib.util.module_from_spec(spec)
spec.loader.exec_module(packet)
work = Path('/work')
root = work / '.devlyn/reviews'
root.mkdir(exist_ok=True)
number = len(list(root.glob('call-*'))) + 1
if number > 2:
    raise SystemExit('Review pool exhausted; no model dispatched')
staging = root / f'.call-{number}.pending'
staging.mkdir()
started_at = time.time()
(staging / 'started.json').write_text(json.dumps({'started_at': started_at, 'stage': 'packet'}))
out = root / f'call-{number}'
staging.rename(out)
before, prompt = packet.packet(work)
(out / 'prompt.txt').write_text(prompt)
argv = ['python3', '-B', '/control/run-bounded.py', '230', '--stdin-file',
        str(out / 'prompt.txt'), '--', 'claude', '-p', '--model', 'claude-fable-5-1',
        '--effort', 'medium', '--tools', '', '--disable-slash-commands',
        '--permission-mode', 'dontAsk', '--setting-sources', '', '--strict-mcp-config',
        '--mcp-config', '{"mcpServers":{}}', '--no-session-persistence',
        '--output-format', 'stream-json', '--verbose']
record = dict(started_at=started_at, argv=argv, source_sha256=before, prompt_sha256=packet.digest(out / 'prompt.txt'))
(out / 'started.tmp').write_text(json.dumps(record, indent=2))
(out / 'started.tmp').replace(out / 'started.json')
start = time.monotonic()
with tempfile.TemporaryDirectory(prefix='fable-') as tmp:
    home = Path(tmp)
    (home / '.claude').mkdir()
    shutil.copyfile('/credentials/claude.json', home / '.claude/.credentials.json')
    (home / '.claude/.credentials.json').chmod(0o600)
    env = {key: os.environ[key] for key in ('PATH', 'LANG', 'LC_ALL') if key in os.environ}
    env.update(HOME=tmp, CLAUDE_CONFIG_DIR=str(home / '.claude'), TMPDIR=tmp,
               CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC='1', CLAUDE_CODE_MAX_RETRIES='0')
    with (out / 'stdout').open('xb') as stdout, (out / 'stderr').open('xb') as stderr:
        result = subprocess.run(argv, cwd=home, env=env, stdout=stdout, stderr=stderr)
record.update(exit_code=result.returncode, seconds=time.monotonic()-start,
              source_unchanged=before == {name: packet.digest(work / name) for name in before})
(out / 'result.tmp').write_text(json.dumps(record, indent=2))
(out / 'result.tmp').replace(out / 'result.json')
if result.returncode or record['seconds'] > 240 or not record['source_unchanged']:
    raise SystemExit('Review failed/deadline/source change; stop, no retry')
events = [json.loads(line) for line in (out / 'stdout').read_text().split('\n') if line.strip()]
results = [event for event in events if event.get('type') == 'result']
if (len(results) != 1 or results[0].get('is_error') or
        set(results[0].get('modelUsage', {})) != {'claude-fable-5-1'}):
    raise SystemExit('Missing successful Fable identity/usage; stop')
if any(item.get('type') == 'tool_use' for event in events
       for item in event.get('message', {}).get('content', [])):
    raise SystemExit('Unexpected reviewer tool invocation; stop')
(out / 'answer.txt').write_text(results[0]['result'])
print(results[0]['result'])
