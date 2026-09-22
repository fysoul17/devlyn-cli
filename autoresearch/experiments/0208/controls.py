"""Zero-model live accounting + private PID namespace termination controls.

Requires an already present Bun image, pinned by sha256 ID. No image pull,
Docker socket, host PID mode, privileged container or model credentials.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import time
import uuid

from accounting import AccountingError, Rollouts
from test_accounting import event, meta, tokens, usage


def docker(*args, timeout=5):
    return subprocess.run(['docker', *args], capture_output=True, text=True,
                          check=True, timeout=timeout).stdout.strip()


def require(condition, evidence):
    if not condition:
        raise ValueError(evidence)


def control(image, scratch, case):
    name = 'devlyn-0208-' + uuid.uuid4().hex
    record = dict(case=case, container=name, image=image, model_calls=0)
    with tempfile.TemporaryDirectory(dir=scratch) as tmp:
        work = Path(tmp).resolve()
        logs = work / 'sessions'; logs.mkdir()
        rows = [('owner', meta('owner')), ('owner', event('task_started', turn_id='owner-1'))]
        if case != 'silent':
            rows += [('child', meta('child', 'owner')), ('child', event('task_started', turn_id='child-1')),
                     ('grandchild', meta('grandchild', 'child')),
                     ('grandchild', event('task_started', turn_id='grandchild-1'))]
            rows += [(sid, usage(100, 10)) for sid in ('owner', 'child', 'grandchild')]
        if case == 'input': rows.append(('grandchild', usage(900, 10, usage(100, 10)['payload']['info']['total_token_usage'])))
        if case == 'output': rows.append(('grandchild', usage(100, 90, usage(100, 10)['payload']['info']['total_token_usage'])))
        if case == 'calls':
            for sid in ('c2', 'c3', 'c4'):
                rows += [(sid, meta(sid, 'grandchild')), (sid, event('task_started', turn_id=sid + '-1'))]
        # sh exits after backgrounding setsid; the sleeper is reparented to PID1.
        # The real child ignores TERM and outlives both launching shells.
        (work / 'launch.sh').write_text('''#!/bin/sh
sh -c 'setsid sh /work/child.sh </dev/null >/dev/null 2>&1 &'
exec bun /work/fixture.js
''')
        (work / 'child.sh').write_text('''#!/bin/sh
echo $$ > /work/child.pid
trap '' TERM
while :; do sleep 1; done
''')
        script = '''import {appendFileSync,writeFileSync} from 'node:fs';
while (!await Bun.file('/work/child.pid').exists()) await Bun.sleep(5);
writeFileSync('/work/ready', 'ready');
while (!await Bun.file('/work/go').exists()) await Bun.sleep(5);
const rows = ROWS;
for (const [sid,row] of rows) {
  appendFileSync('/work/sessions/'+sid+'.jsonl', JSON.stringify(row)+'\\n');
  await Bun.sleep(60);
}
setInterval(()=>{},1000);
'''.replace('ROWS', json.dumps(rows))
        (work / 'fixture.js').write_text(script)
        created, start = False, None
        try:
            cid = docker('create', '--name', name, '--label', 'devlyn.control=' + name,
                         '--network', 'none', '--read-only', '--cap-drop', 'ALL',
                         '--security-opt', 'no-new-privileges', '--pids-limit', '32',
                         '--restart=no', '--mount', f'type=bind,src={work},dst=/work',
                         image, 'sh', '/work/launch.sh')
            created = True; record['container_id'] = cid
            config = json.loads(docker('inspect', cid))[0]
            host = config['HostConfig']
            require(not host['Privileged'] and host['PidMode'] == '', host)
            require(host['RestartPolicy']['Name'] == 'no' and host['NetworkMode'] == 'none', host)
            require(len(config['Mounts']) == 1 and config['Mounts'][0]['Destination'] == '/work', config['Mounts'])
            require(host['ReadonlyRootfs'] and host['PidsLimit'] == 32 and host['CapDrop'] == ['ALL'] and
                    host['SecurityOpt'] == ['no-new-privileges'], host)
            record['host_config'] = {k: host[k] for k in ('Privileged', 'PidMode', 'RestartPolicy', 'NetworkMode', 'CapDrop', 'SecurityOpt', 'ReadonlyRootfs', 'PidsLimit')}
            # Wall includes dispatch, accounting, checks, kill and stopped proof.
            start = time.monotonic(); deadline = start + 10
            def remaining():
                return max(.001, min(2, deadline - time.monotonic()))
            docker('start', cid, timeout=remaining())
            while not (work / 'ready').exists():
                if time.monotonic() >= deadline - 3: raise TimeoutError('fixture not ready')
                time.sleep(.02)
            pid = int((work / 'child.pid').read_text())
            # All evidence is inside the namespace, not host ps visibility.
            raw = docker('exec', cid, 'cat', f'/proc/{pid}/stat', timeout=remaining())
            fields = raw[raw.rindex(')') + 2:].split()
            require(int(fields[1]) == 1 and int(fields[3]) == pid, raw)
            record['detached_child_stat'] = raw
            meter = Rollouts(logs, 'owner', input_limit=1000, output_limit=100,
                             dispatch_limit=5, stale_seconds=1.5, started=time.monotonic())
            (work / 'go').write_text('go')
            emission_start = time.monotonic()
            observations = []
            reason = None
            while time.monotonic() < deadline - 3:
                observed = time.monotonic()
                try:
                    value = meter.poll(observed)
                    if not observations or value != observations[-1]['value']:
                        observations.append(dict(seconds=observed - start, value=value))
                    if value['exceeded']:
                        reason = 'BUDGET_EXCEEDED'; break
                except AccountingError as exc:
                    reason = str(exc); break
                time.sleep(.02)
            if reason is None: reason = 'WALL_RESERVE'
            record.update(reason=reason, observations=observations, stop_requested_seconds=time.monotonic() - start)
            docker('kill', '--signal', 'KILL', cid, timeout=remaining())
            state = json.loads(docker('inspect', '--format', '{{json .State}}', cid, timeout=remaining()))
            require(state['Running'] is False and state['Pid'] == 0, state)
            record['stopped_state'] = state
            probe = subprocess.run(['docker', 'exec', cid, 'test', '-e', f'/proc/{pid}'],
                                   capture_output=True, text=True, timeout=remaining())
            require(probe.returncode != 0 and 'is not running' in probe.stderr, str(probe))
            record['after_exec'] = dict(exit_code=probe.returncode, stderr=probe.stderr)
            record['quiescent_seconds'] = time.monotonic() - start
            require(record['quiescent_seconds'] < 10, record['quiescent_seconds'])
            require(reason.startswith('stale active usage') if case == 'silent' else reason == 'BUDGET_EXCEEDED', reason)
            record['fixture_logs'] = {p.name: p.read_text() for p in logs.iterdir()}
            expected = dict(input=(1100, 30, 3), output=(300, 110, 3), calls=(300, 30, 6), silent=(0, 0, 1))[case]
            final = observations[-1]['value']
            require(final['totals'] == tokens(expected[0], expected[1]) and
                    final['dispatches'] == expected[2], final)
            for sid in {sid for sid, _ in rows}:
                written = [json.loads(line) for line in record['fixture_logs'][sid + '.jsonl'].splitlines()]
                require(written == [row for key, row in rows if key == sid], written)
            if case == 'silent':
                require(record['stop_requested_seconds'] >= emission_start - start + 1.5, record)
            record['status'] = 'PASS_NON_MODEL_CONTROL'
        except Exception as exc:
            record.update(status='FAIL', error=repr(exc))
            if created:
                try:
                    capture = subprocess.run(['docker', 'logs', name], capture_output=True,
                                             text=True, timeout=5)
                    record['container_logs'] = dict(exit_code=capture.returncode,
                                                    stdout=capture.stdout, stderr=capture.stderr)
                except (OSError, subprocess.SubprocessError) as log_error:
                    record['log_capture_error'] = repr(log_error)
        finally:
            # Even a timed-out create may have created the uniquely named object.
            # Recovery is reported separately; it cannot turn a missed wall into PASS.
            if created:
                docker('rm', '-f', cid)
            else:
                lookup = subprocess.run(['docker', 'inspect', name], capture_output=True, text=True, timeout=5)
                if lookup.returncode == 0:
                    found = json.loads(lookup.stdout)[0]
                    if found['Config']['Labels'].get('devlyn.control') != name:
                        raise RuntimeError('container ownership mismatch')
                    docker('rm', '-f', name)
                elif 'No such object' not in lookup.stderr:
                    raise RuntimeError('cannot establish container absence: ' + lookup.stderr)
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--image', required=True)
    parser.add_argument('--scratch', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if not args.image.startswith('sha256:'):
        parser.error('use an inspected local image ID, never a mutable tag')
    # Open before side effects: do not rerun controls if evidence already exists.
    with args.output.open('x') as stream:
        for case in ('input', 'output', 'calls', 'silent'):
            try:
                record = control(args.image, args.scratch, case)
            except Exception as exc:
                stream.write(json.dumps(dict(case=case, status='FAIL', error=repr(exc))) + '\n')
                stream.flush()
                raise
            record['source_sha256'] = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                                       for p in Path(__file__).parent.glob('*.py')}
            stream.write(json.dumps(record) + '\n'); stream.flush()
            if record['status'] == 'FAIL':
                raise RuntimeError(record)
            print(case, record['status'], round(record['quiescent_seconds'], 3))


if __name__ == '__main__':
    main()
