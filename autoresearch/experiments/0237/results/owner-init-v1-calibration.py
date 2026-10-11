"""One model-free real-container probe through the new owner run boundary.

Uses only freshly written dummy credential placeholders; never calls preflight.
Run once after a retained prospective prediction, with a fresh destination.
"""
import importlib.util
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location('init_calibration_runner', HERE / 'runner-init-v1.py')
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)
IMAGE = 'sha256:0f472bb41685b7daa5923d51d31983f4b3c70053dd773fdf712bd0dcd6d87998'

PROBE = '''import json, os, signal, time
from pathlib import Path

signal.alarm(15)
def read(path):
    return Path(path).read_text().strip()

report = {
    'pid1_comm': read('/proc/1/comm'),
    'pid1_cmdline': Path('/proc/1/cmdline').read_bytes().replace(b'\\0', b' ').decode().strip(),
    'caller_pid': os.getpid(), 'caller_ppid': os.getppid(),
    'caller_cmdline': Path('/proc/self/cmdline').read_bytes().replace(b'\\0', b' ').decode().strip(),
    'pids_max': read('/sys/fs/cgroup/pids.max'),
    'pids_before': int(read('/sys/fs/cgroup/pids.current')),
    'memory_max': read('/sys/fs/cgroup/memory.max'),
    'cpu_max': read('/sys/fs/cgroup/cpu.max'),
}
read_end, write_end = os.pipe()
intermediate = os.fork()
if intermediate == 0:
    os.close(read_end)
    orphan = os.fork()
    if orphan == 0:
        os.close(write_end)
        deadline = time.monotonic() + 5
        while os.getppid() != 1 and time.monotonic() < deadline:
            time.sleep(0.01)
        Path('/tmp/orphan-child.json').write_text(json.dumps({
            'pid': os.getpid(), 'ppid_before_exit': os.getppid(),
            'pids_while_adopted': int(read('/sys/fs/cgroup/pids.current')),
        }))
        os._exit(0)
    os.write(write_end, str(orphan).encode())
    os.close(write_end)
    os._exit(0)
os.close(write_end)
orphan = int(os.read(read_end, 100))
os.close(read_end)
_, intermediate_status = os.waitpid(intermediate, 0)
report['intermediate_exit'] = os.waitstatus_to_exitcode(intermediate_status)
report['orphan_pid'] = orphan
deadline = time.monotonic() + 5
while Path('/proc', str(orphan)).exists() and time.monotonic() < deadline:
    time.sleep(0.01)
report['orphan_report'] = json.loads(Path('/tmp/orphan-child.json').read_text())
report['orphan_proc_absent'] = not Path('/proc', str(orphan)).exists()
report['pids_after'] = int(read('/sys/fs/cgroup/pids.current'))
quota, period = map(int, report['cpu_max'].split())
report['passed'] = (report['caller_pid'] != 1 and report['caller_ppid'] == 1
                    and report['orphan_report']['ppid_before_exit'] == 1
                    and report['orphan_proc_absent'] and report['intermediate_exit'] == 0
                    and report['pids_after'] <= report['pids_before']
                    and report['pids_max'] == '256' and report['memory_max'] == '4294967296'
                    and quota == 2 * period)
print(json.dumps(report, sort_keys=True), flush=True)
raise SystemExit(0 if report['passed'] else 1)
'''


def main():
    root = Path(sys.argv[1]).resolve()
    root.mkdir(mode=0o700, exist_ok=False)
    control, out = root / 'control', root / 'cell-out'
    for name in ('public', 'oracle', 'packages'):
        (control / name).mkdir(parents=True)
    runner.frozen.write(str(control) + '.manifest.json', dict(manifests={name: {} for name in ('public', 'oracle', 'packages')}))
    auth = root / 'dummy-auth'
    auth.mkdir(mode=0o700)
    for name in ('claude.json', 'codex.json'):
        path = auth / name
        path.write_text('{"model_free_dummy_placeholder":true}\n')
        path.chmod(0o600)
    for name in ('cell/work', 'cell/trace', 'home/.claude', 'home/.codex', 'harness', 'tmp'):
        (out / name).mkdir(parents=True)
    (out / 'cell/probe.py').write_text(PROBE)
    runtime_path = root / 'runtime.json'
    runtime = dict(image=IMAGE, control=str(control), output=str(root / 'out'), auth=str(auth),
                   scratch=str(root / 'scratch'), phase='smoke', tasks_file=str(HERE / 'tasks-confirmation-max.json'))
    runner.frozen.write(runtime_path, runtime)
    app = runner.Runner(runtime_path)
    plan = dict(name='owner-init-v1-model-free', task='MODEL-FREE-ORPHAN-PROBE', arm='A', config='claude',
                engine='claude', model=app.tasks['routes']['claude']['owner']['model'],
                effort=app.tasks['routes']['claude']['owner']['effort'], wall_seconds=5400,
                image=IMAGE, cell=str(out / 'cell'), home=str(out / 'home'), harness=str(out / 'harness'),
                tmp=str(out / 'tmp'), control=str(control / 'public'),
                env={'HOME': '/home/participant', 'CODEX_HOME': '/home/participant/.codex'},
                argv=['python3', '-B', '/cell/probe.py'])
    runner.frozen.write(out / 'plan.json', plan)
    before = app.inputs()
    runner.frozen.write(root / 'inputs-before.json', before)
    result = app.frame.cell_run.run(out, runtime)
    after = app.inputs()
    runner.frozen.write(root / 'inputs-after.json', after)
    probe = json.loads((out / 'run/stdout').read_text())
    started = runner.frozen.read(out / 'run/started.json')
    summary = dict(scope='MODEL_FREE_ACTUAL_OWNER_BOUNDARY', root=str(root), result=result,
                   probe=probe, inputs_unchanged=before == after,
                   recorded_argv_equal=started['create_argv'] == result['create_argv'],
                   dummy_credential_cleanup=not (root / 'scratch/credentials'/plan['name']).exists())
    runner.frozen.write(root / 'summary.json', summary)
    print(json.dumps(summary, sort_keys=True))
    return 0 if (probe['passed'] and result['owner_status'] == 'EXITED_0'
                 and result['teardown'] == 'CLEAN' and before == after
                 and summary['recorded_argv_equal'] and summary['dummy_credential_cleanup']) else 1


if __name__ == '__main__':
    sys.exit(main())
