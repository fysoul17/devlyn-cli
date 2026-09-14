"""Bounded research entry; preserve observation gaps without restarting the task."""
import base64, datetime, hashlib, json, os, signal, stat, subprocess, time

def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()

def put(path, data):
    with path.open("x") as stream:
        json.dump(data, stream, indent=2)
        stream.write("\n")

def seal(path):
    return {"path": str(path.absolute()), "resolved": str(path.resolve()),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "mode": stat.S_IMODE(path.stat().st_mode), "bytes": path.stat().st_size,
        "symlink": os.readlink(path) if path.is_symlink() else None}


def process_table(timeout):
    # Same native ps fields/identity as quality-speed-pilot-r0/run-cell.py:38–49.
    raw = subprocess.run(['/bin/ps', 'ax', '-o', 'pid=,ppid=,pgid=,stat=,lstart='],
        stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, check=True, timeout=timeout)
    rows = {}
    for line in raw.stdout.splitlines():
        fields = line.split(None, 8)
        if len(fields) == 9 and all(x.isdigit() for x in fields[:3]):
            pid, ppid, pgid = map(int, fields[:3])
            rows[pid] = {'pid': pid, 'ppid': ppid, 'pgid': pgid,
                'state': fields[3], 'identity': ' '.join(fields[4:9])}
    return rows


def execute(plan, out):
    bounds = plan['bounds']
    if bounds != {'native_seconds': 1800, 'wrapper_seconds': 1810, 'post_return_quiet_seconds': 15,
                  'term_seconds': 10, 'kill_reap_seconds': 5, 'overall_seconds': 1830}:
        raise ValueError('Unexpected ordinary-entry bounds')
    remembered, events, owned = {}, [], {}
    process, error, wrapper_return, quiet_at = None, None, None, None
    observed_quiet = False
    observation_timeouts = 0
    start = time.monotonic()
    hard_deadline = start + bounds['overall_seconds']

    def remaining():
        value = hard_deadline - time.monotonic()
        if value <= 0:
            raise TimeoutError('Overall1830s controller deadline reached')
        return value

    with (out / 'owned-processes.jsonl').open('x') as census, (out / 'stdout').open('xb') as stdout, (out / 'stderr').open('xb') as stderr:
        def snapshot(deadline):
            nonlocal observation_timeouts
            # A failed sample is not an empty process table. Keep its raw bytes,
            # retry within the existing quiet budget, and fail if it stays blind.
            deadline = min(deadline, time.monotonic() + bounds['post_return_quiet_seconds'])
            while True:
                budget = min(remaining(), deadline - time.monotonic())
                if budget <= 0:
                    raise TimeoutError('Process observation deadline reached')
                try:
                    return process_table(min(2, budget))
                except subprocess.TimeoutExpired as exc:
                    observation_timeouts += 1
                    census.write(json.dumps({'at': now(), 'event': 'process_observation_timeout',
                        'error': repr(exc), 'stdout_base64': base64.b64encode(exc.output or b'').decode(),
                        'stderr_base64': base64.b64encode(exc.stderr or b'').decode()}) + '\n')
                    census.flush()
                    if time.monotonic() >= deadline:
                        raise

        def observe(deadline):
            table = snapshot(deadline)
            ids = {pid for pid, row in table.items() if pid in remembered and remembered[pid]['identity'] == row['identity']}
            if process is not None and process.poll() is None and process.pid in table:
                ids.add(process.pid)
            while True:
                expanded = ids | {pid for pid, row in table.items() if row['ppid'] in ids}
                if expanded == ids:
                    break
                ids = expanded
            ids.discard(os.getpid())
            for pid in ids:
                remembered[pid] = table[pid]
            rows = {pid: table[pid] for pid in ids if not table[pid]['state'].startswith('Z')}
            census.write(json.dumps({'at': now(), 'owned': list(rows.values())}) + '\n')
            census.flush()
            return rows

        def send(rows, number):
            current = snapshot(hard_deadline)
            for pid, row in rows.items():
                if pid in current and current[pid]['identity'] == row['identity']:
                    try:
                        os.kill(pid, number)
                        events.append({'at': now(), **row, 'signal': number})
                    except ProcessLookupError:
                        events.append({'at': now(), 'pid': pid, 'signal': number, 'already_exited': True})

        try:
            process = subprocess.Popen(plan['argv'], cwd=plan['work'], stdin=subprocess.DEVNULL,
                stdout=stdout, stderr=stderr, start_new_session=True)
            put(out / 'process.json', {'pid': process.pid, 'at': now(), 'argv': plan['argv'], 'cwd': plan['work']})
            observe_until = start + bounds['wrapper_seconds']
            while time.monotonic() < min(observe_until, hard_deadline):
                owned = observe(observe_until)
                if process.poll() is not None:
                    if wrapper_return is None:
                        wrapper_return = time.monotonic() - start
                        observe_until = min(observe_until, time.monotonic() + bounds['post_return_quiet_seconds'])
                    if not owned:
                        observed_quiet, quiet_at = True, now()
                        break
                time.sleep(min(1, remaining(), max(0, observe_until - time.monotonic())))
            if not observed_quiet:
                error = 'Observed owned set did not become quiet within the registered wrapper/quiet interval'
        except (OSError, ValueError, subprocess.SubprocessError) as exc:
            error = repr(exc)
        cleanup_start = time.monotonic()
        try:
            owned = observe(hard_deadline)
            if owned:
                leaders = {pid: row for pid, row in owned.items() if row['ppid'] not in owned}
                send(leaders, signal.SIGTERM)
                until = min(hard_deadline, time.monotonic() + bounds['term_seconds'])
                while owned and time.monotonic() < until:
                    time.sleep(min(.2, remaining(), max(0, until - time.monotonic())))
                    try:
                        owned = observe(until)
                    except (TimeoutError, subprocess.TimeoutExpired):
                        # Grace expired; KILL still requires a fresh identity check.
                        break
                if owned:
                    send(owned, signal.SIGKILL)
            reap_until = min(hard_deadline, time.monotonic() + bounds['kill_reap_seconds'])
            if process is not None:
                process.wait(timeout=max(0, reap_until - time.monotonic()))
            owned = observe(reap_until)
            while owned and time.monotonic() < reap_until:
                time.sleep(min(.2, max(0, reap_until - time.monotonic())))
                if time.monotonic() < reap_until:
                    owned = observe(reap_until)
            final_owned_quiet = not owned
        except (OSError, ValueError, subprocess.SubprocessError) as exc:
            error = (error + '; ' if error else '') + repr(exc)
            final_owned_quiet = None
    return {'at': now(), 'exit_code': process.returncode if process else None, 'error': error,
        'wrapper_return_seconds': wrapper_return, 'controller_seconds': time.monotonic() - start,
        'cleanup_seconds': time.monotonic() - cleanup_start, 'bounds': bounds,
        'observation_timeouts': observation_timeouts, 'observed_quiet_before_cleanup': observed_quiet, 'observed_quiet_at': quiet_at,
        'owned_writers_quiescent': final_owned_quiet, 'owned_survivors_last_observed': list(owned.values()),
        'owned_processes': list(remembered.values()), 'cleanup_signals': events,
        'stdout': seal(out / 'stdout'), 'stderr': seal(out / 'stderr'), 'census': seal(out / 'owned-processes.jsonl'),
        'scope': 'Observed descendant set retained across reparent/setsid; unobserved fast detached descendants and other services are not certified.',
        'task_acceptance': 'NOT_ASSESSED; CLI exit/owned quiet is not a pipeline verdict', 'whole_run_output_tokens': None}
