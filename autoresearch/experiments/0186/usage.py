"""Read account limits without inference; retain only non-identifying counters."""
import datetime
import json
from pathlib import Path
import selectors
import subprocess
import time

EVIDENCE = Path(__file__).resolve().parents[3] / '.devlyn/0186'

def read():
    process = subprocess.Popen(['codex', 'app-server', '--stdio'], stdin=subprocess.PIPE,
                               stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
    selector = selectors.DefaultSelector()
    selector.register(process.stdout, selectors.EVENT_READ)
    def send(payload):
        process.stdin.write(json.dumps(payload) + '\n')
        process.stdin.flush()
    try:
        send({'id': 1, 'method': 'initialize', 'params': {
            'clientInfo': {'name': 'devlyn-usage-observer', 'version': '1.0'}}})
        deadline = time.monotonic() + 25
        while time.monotonic() < deadline:
            if not selector.select(1):
                continue
            line = process.stdout.readline()
            if not line:
                raise RuntimeError('usage observer exited before result')
            response = json.loads(line)
            if response.get('id') == 1:
                if 'error' in response:
                    raise RuntimeError(response['error'])
                send({'method': 'initialized', 'params': {}})
                send({'id': 2, 'method': 'account/rateLimits/read', 'params': {}})
            elif response.get('id') == 2:
                if 'error' in response:
                    raise RuntimeError(response['error'])
                limits = response['result']['rateLimitsByLimitId']['codex']
                windows = {name: limits[name] for name in ('primary', 'secondary') if limits.get(name)}
                if not windows:
                    raise RuntimeError('no account windows available')
                remaining = min(100 - window['usedPercent'] for window in windows.values())
                row = dict(observed_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                           windows=windows, remaining_percent=remaining, park=remaining <= 15)
                EVIDENCE.mkdir(exist_ok=True)
                with (EVIDENCE / 'usage-observations.jsonl').open('a') as stream:
                    stream.write(json.dumps(row) + '\n')
                return row
        raise TimeoutError('usage observation timed out')
    finally:
        selector.close()
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()

if __name__ == '__main__':
    result = read()
    print(json.dumps(result))
    raise SystemExit(75 if result['park'] else 0)
