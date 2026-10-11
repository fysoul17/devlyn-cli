"""Stage new single-peer inputs through unchanged 0238 verification and isolation."""
import importlib.util
from pathlib import Path

EXPERIMENT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location('stage0238_single_peer', EXPERIMENT.parent / '0238/results/stage.py')
legacy = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(legacy)
legacy.EXPERIMENT = EXPERIMENT
base_stage = legacy.stage


def stage(args):
    runtime = base_stage(args)
    path = runtime.parent / 'staging.json'
    record = legacy.read(path)
    record['stage_adapter_sha256'] = legacy.sha(Path(__file__))
    legacy.write(path, record)
    return runtime


if __name__ == '__main__':
    legacy.stage = stage
    legacy.main()
