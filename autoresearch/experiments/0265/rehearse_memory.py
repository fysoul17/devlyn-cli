"""Q8 lane rehearsal and memory (DESIGN Qualification). Never dispatches models.

checks [--root DIR]: (a) two owner-shaped containers start together from the runtime image: 0237/cell-init-v1.py's
limits, read-only root and mount shape, no credential and no network. One runs D3's public checks and tsc on a
writable copy of commander's base tree, the other D4's public checks, mypy and pyright on click's. Every running
container, other sessions' included, is sampled with `docker stats` every 2 s. Writes <root>/q8-checks.json.

sample --out FILE [--interval 2] --until-file PATH [--root DIR]: during (b), the two lane drivers running
rehearsal.tsv, every interval records `docker stats --no-stream` for every running container and the Docker VM's
available memory, until PATH appears; then writes FILE with the samples and a summary: the smallest available memory,
the containers running then, and the peak per container name prefix (the name less its per-run uuid).

The VM's available memory is MemAvailable in /proc/meminfo read inside a container of ours (in checks, one of the two;
in sample, a small idle sampler container started for it): Docker Desktop's VM is not visible from macOS, `docker info`
gives only its MemTotal, and a container's /proc/meminfo is the VM kernel's own. MemAvailable, not MemFree, is the
kernel's estimate of what a new process can take without swapping (free memory plus reclaimable cache). One long-lived
sampler instead of a container per sample keeps the sampler's own start-up out of what it measures.

Only the containers and volumes created here are removed; a measurement file is never overwritten.
"""
import argparse
import datetime
import json
from pathlib import Path
import re
import shlex
import subprocess
import tempfile
import time
import uuid

HERE = Path(__file__).resolve().parent
ROOT = Path.home() / '.local/share/nx01/0265-live'
TASKS = {t['id']: t for t in json.loads((HERE.parent / '0233/tasks.json').read_text())['tasks']}
TYPE_CHECKS = {'D3': ['tsc -p tsconfig.js.json', 'tsc -p tsconfig.ts.json'],
               'D4': ['mypy src/click', 'pyright src/click']}
ENV = dict(HOME='/home/participant', CODEX_HOME='/home/participant/.codex', DISABLE_AUTOUPDATER='1',  # 0257/prepare.py
           PYTHONPATH='src:/control/python', GIT_CONFIG_GLOBAL='/dev/null', GIT_CONFIG_NOSYSTEM='1',
           CODEX_ROLLOUT_TRACE_ROOT='/cell/trace', MYPY_CACHE_DIR='/tmp/.mypy_cache',
           ENABLE_CLAUDEAI_MCP_SERVERS='false')
INTERVAL = 2
LIMIT = 1800
UNITS = {'B': 1, 'kB': 10 ** 3, 'MB': 10 ** 6, 'GB': 10 ** 9,
         'KiB': 2 ** 10, 'MiB': 2 ** 20, 'GiB': 2 ** 30, 'TiB': 2 ** 40}
STEP = re.compile(r'^Q6-STEP (\d+) (\d+) (\d+) (\d+)$', re.M)


def docker(*args, timeout=120):
    return subprocess.run(['docker', *args], check=True, capture_output=True, text=True, timeout=timeout).stdout.strip()


def size(text):
    """`docker stats` MemUsage's used part, e.g. '1.5GiB / 4GiB' -> bytes."""
    number, unit = re.fullmatch(r'([\d.]+)\s*([A-Za-z]+)', text.split('/')[0].strip()).groups()
    return round(float(number) * UNITS[unit])


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def script(commands):
    return '\n'.join(f'start=$(date +%s); sh -c {shlex.quote(c)}; code=$?; echo "Q6-STEP {i} $code $start $(date +%s)"'
                     for i, c in enumerate(commands))


def steps(commands, log):
    found = {int(i): dict(exit_code=int(code), seconds=int(end) - int(start))
             for i, code, start, end in STEP.findall(log)}
    return [dict(command=c, **found.get(i, dict(exit_code=None, seconds=None))) for i, c in enumerate(commands)]


def create(task, runtime, temp):
    """An owner-shaped container (0237/cell-init-v1.py) over a writable clone of the task's base tree."""
    spec = TASKS[task]
    cell, home, harness = temp / task / 'cell', temp / task / 'home', temp / task / 'harness'
    for path in (cell / 'trace', home / '.codex', home / '.claude', harness):
        path.mkdir(parents=True)
    work = cell / 'work'
    subprocess.run(['git', 'clone', '--no-hardlinks', '--quiet', str(Path(runtime['sources']) / spec['source']),
                    str(work)], check=True)
    subprocess.run(['git', '-C', str(work), 'checkout', '-q', '-B', 'main', spec['base_sha']], check=True)
    name, volume = 'devlyn-0265-q6-' + uuid.uuid4().hex, 'devlyn-0265-q6-tmp-' + uuid.uuid4().hex
    commands = spec['public_checks'] + TYPE_CHECKS[task]
    mounts = [(cell, '/cell', False), (home, '/home/participant', False),
              (Path(runtime['control']) / 'public', '/control', True), (harness, '/harness', True)]
    argv = ['create', '--init', '--name', name, '--label', 'devlyn.task=0265-q6', '--network', 'none',
            '--cap-drop', 'ALL', '--security-opt', 'no-new-privileges', '--security-opt', 'seccomp=unconfined',
            '--read-only', '--restart=no', '--pids-limit', '256', '--memory', '4g', '--cpus', '2',
            '--tmpfs', '/home/participant/.codex/tmp:rw,nosuid,exec,uid=501,gid=501', '-w', '/cell/work',
            '--mount', f'type=volume,src={volume},dst=/tmp']
    for src, dst, readonly in mounts:
        argv += ['--mount', f'type=bind,src={src},dst={dst}' + (',readonly' if readonly else '')]
    for key, value in ENV.items():
        argv += ['--env', f'{key}={value}']
    argv += [runtime['image'], 'sh', '-c', script(commands)]
    return dict(name=name, volume=volume, commands=commands, argv=argv)


def stats():
    """Memory used by every running container, by name."""
    rows = [json.loads(line) for line in docker('stats', '--no-stream', '--format', '{{json .}}').splitlines() if line]
    return {row['Name']: size(row['MemUsage']) for row in rows}


def available(names):
    """The Docker VM's MemAvailable in bytes, read inside the first of our containers that answers; None if none."""
    for name in names:
        try:
            meminfo = docker('exec', name, 'cat', '/proc/meminfo', timeout=30)
            return int(re.search(r'^MemAvailable:\s+(\d+) kB$', meminfo, re.M).group(1)) * 1024
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, AttributeError):
            continue
    return None


def sample(ours):
    containers = stats()
    return dict(at=now(), containers=containers, total=sum(containers.values()),
                ours=sum(v for k, v in containers.items() if k in ours), vm_available=available(ours))


def running(name):
    return json.loads(docker('inspect', name))[0]['State']['Running']


def rehearse(root):
    root = Path(root).expanduser().resolve()
    runtime = json.loads((root / 'runtime-smoke.json').read_text())
    target = root / 'q8-checks.json'
    if target.exists():
        raise FileExistsError(f'{target} exists: a rehearsal is a measurement and is never overwritten')
    mem_total = int(docker('info', '--format', '{{.MemTotal}}'))
    created, volumes = [], []
    with tempfile.TemporaryDirectory(prefix='q6-', dir=runtime['scratch']) as temp:
        try:
            plans = {task: create(task, runtime, Path(temp)) for task in ('D3', 'D4')}
            for plan in plans.values():
                volumes.append(plan['volume'])
                docker('volume', 'create', '--label', 'devlyn.task=0265-q6', plan['volume'])
                created.append(plan['name'])
                docker(*plan['argv'])
            started = time.monotonic()
            for plan in plans.values():
                docker('start', plan['name'])
            ours, samples, timed_out = set(created), [], False
            while any(running(name) for name in created):
                tick = time.monotonic()
                samples.append(dict(seconds=round(tick - started, 1), **sample(ours)))
                if tick - started > LIMIT:
                    timed_out = True
                    for name in created:
                        subprocess.run(['docker', 'kill', name], capture_output=True)
                    break
                time.sleep(max(0.0, INTERVAL - (time.monotonic() - tick)))
            results = {}
            for task, plan in plans.items():
                state = json.loads(docker('inspect', plan['name']))[0]['State']
                log = subprocess.run(['docker', 'logs', plan['name']], stdout=subprocess.PIPE,
                                     stderr=subprocess.STDOUT, text=True).stdout
                results[task] = dict(name=plan['name'], exit_code=state['ExitCode'], oom_killed=state['OOMKilled'],
                                     steps=steps(plan['commands'], log), log_tail=log[-4000:])
        finally:
            for name in created:
                subprocess.run(['docker', 'rm', '-f', name], capture_output=True)
            for volume in volumes:
                subprocess.run(['docker', 'volume', 'rm', volume], capture_output=True)
    if not samples:
        raise RuntimeError('both containers finished before the first sample')
    peak = max(samples, key=lambda s: s['total'])
    record = dict(schema=1, image=runtime['image'], interval_seconds=INTERVAL, mem_total=mem_total,
                  timed_out=timed_out, containers=results, samples=samples,
                  peak_ours=max(s['ours'] for s in samples), peak_total=peak['total'],
                  free_at_peak=mem_total - peak['total'], vm_available_at_peak=peak['vm_available'],
                  min_vm_available=min((s['vm_available'] for s in samples if s['vm_available'] is not None),
                                       default=None))
    with target.open('x') as stream:
        stream.write(json.dumps(record, indent=1) + '\n')
    return record


def prefix(name):
    """A container's name less its per-run uuid: devlyn-0231-assess-<32 hex> -> devlyn-0231-assess."""
    return re.sub(r'-[0-9a-f]{32}$', '', name)


def summary(samples):
    """The smallest VM available memory with the containers running then, and per name prefix the peak of its
    containers' sum within one sample and its largest single container."""
    measured = [s for s in samples if s['vm_available'] is not None]
    low = min(measured, key=lambda s: s['vm_available'], default=None)
    peaks = {}
    for s in samples:
        sums = {}
        for name, used in (s.get('containers') or {}).items():
            sums[prefix(name)] = sums.get(prefix(name), 0) + used
            entry = peaks.setdefault(prefix(name), dict(peak=0, largest=0))
            entry['largest'] = max(entry['largest'], used)
        for group, used in sums.items():
            peaks[group]['peak'] = max(peaks[group]['peak'], used)
    return dict(sample_count=len(samples), samples_without_available=len(samples) - len(measured),
                samples_without_stats=sum('containers' not in s for s in samples),
                min_vm_available=low and low['vm_available'], min_at=low and low['at'],
                running_at_min=low and low.get('containers'), peak_by_prefix=dict(sorted(peaks.items())))


def watch(root, out, until, interval=INTERVAL):
    """Sample until `until` appears; the record is written however the loop ends, and the sampler is removed."""
    runtime = json.loads((Path(root).expanduser() / 'runtime-smoke.json').read_text())
    out, until = Path(out), Path(until)
    if out.exists():
        raise FileExistsError(f'{out} exists: a rehearsal is a measurement and is never overwritten')
    if until.exists():
        raise FileExistsError(f'{until} exists already: the sampler would stop before its first sample')
    mem_total = int(docker('info', '--format', '{{.MemTotal}}'))
    name, samples, stopped, started = 'devlyn-0265-q8-sampler-' + uuid.uuid4().hex, [], 'until-file', time.monotonic()
    try:
        docker('run', '-d', '--rm', '--init', '--name', name, '--label', 'devlyn.task=0265-q8', '--network', 'none',
               '--read-only', '--cap-drop', 'ALL', '--security-opt', 'no-new-privileges', '--memory', '64m',
               '--pids-limit', '16', runtime['image'], 'sleep', 'infinity')
        while not until.exists():
            tick = time.monotonic()
            record = dict(at=now(), seconds=round(tick - started, 1))
            try:
                record['containers'] = stats()
            except (subprocess.SubprocessError, ValueError, KeyError, AttributeError) as exc:  # a gap, recorded
                detail = getattr(exc, 'stderr', None)  # bytes on a timeout, even when the call asked for text
                detail = detail.decode(errors='replace') if isinstance(detail, bytes) else detail
                record['stats_error'] = ' '.join(filter(None, (f'{type(exc).__name__}: {exc}', (detail or '').strip())))
            record['vm_available'] = available([name])
            samples.append(record)
            time.sleep(max(0.0, interval - (time.monotonic() - tick)))
    except BaseException as exc:
        stopped = f'{type(exc).__name__}: {exc}'
        raise
    finally:
        subprocess.run(['docker', 'rm', '-f', name], capture_output=True)
        result = dict(schema=1, image=runtime['image'], interval_seconds=interval, until_file=str(until),
                      mem_total=mem_total, sampler=name, stopped=stopped, **summary(samples), samples=samples)
        with out.open('x') as stream:
            stream.write(json.dumps(result, indent=1) + '\n')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    modes = parser.add_subparsers(dest='mode', required=True)
    modes.add_parser('checks', help='(a) D3 and D4 checks in two owner-shaped containers at once')
    sampler = modes.add_parser('sample', help='(b) sample memory until a file appears')
    sampler.add_argument('--out', required=True)
    sampler.add_argument('--interval', type=float, default=INTERVAL)
    sampler.add_argument('--until-file', required=True)
    for mode in modes.choices.values():
        mode.add_argument('--root', default=str(ROOT))
    args = parser.parse_args()
    gib = 2 ** 30
    if args.mode == 'checks':
        result = rehearse(args.root)
        print(json.dumps({key: round(result[key] / gib, 3) if isinstance(result[key], int) else result[key]
                          for key in ('mem_total', 'peak_ours', 'peak_total', 'free_at_peak', 'vm_available_at_peak',
                                      'min_vm_available')}))
        print(json.dumps({task: [(s['command'], s['exit_code'], s['seconds']) for s in r['steps']] + [r['oom_killed']]
                          for task, r in result['containers'].items()}))
    else:
        result = watch(args.root, args.out, args.until_file, args.interval)
        print(json.dumps(dict({key: result[key] for key in ('sample_count', 'samples_without_available',
                                                            'samples_without_stats', 'min_at', 'running_at_min')},
                              min_vm_available_gib=result['min_vm_available'] and round(
                                  result['min_vm_available'] / gib, 3),
                              peak_by_prefix_gib={k: {key: round(v / gib, 3) for key, v in p.items()}
                                                  for k, p in result['peak_by_prefix'].items()})))
