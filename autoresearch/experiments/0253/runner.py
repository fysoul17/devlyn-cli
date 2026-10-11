"""Prospective native API body capture; existing accounting gates are unchanged."""
import importlib.util
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('runner0251_native_bodies', HERE.parent / '0251/runner.py')
legacy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(legacy)
read, write, digest = legacy.read, legacy.write, legacy.digest

CAPTURE_ENV = {
    'CLAUDE_CODE_ENABLE_TELEMETRY': '1',
    'OTEL_METRICS_EXPORTER': 'none',
    'OTEL_LOGS_EXPORTER': 'none',
    'OTEL_TRACES_EXPORTER': 'none',
    'OTEL_LOG_RAW_API_BODIES': 'file:/home/participant/.claude/api-bodies',
}


class Runner(legacy.Runner):
    def inputs(self):
        return dict(super().inputs(), **{str(Path(__file__)): digest(Path(__file__))})

    def prepare(self, name, task, arm, config):
        out = super().prepare(name, task, arm, config)
        if config == 'claude':
            (out / 'home/.claude/api-bodies').mkdir(mode=0o700)
            plan = read(out / 'plan.json')
            if any(key.startswith('OTEL_') or key == 'CLAUDE_CODE_ENABLE_TELEMETRY'
                   for key in plan['env']):
                raise ValueError('competing telemetry configuration in prepared plan')
            plan['env'].update(CAPTURE_ENV)
            write(out / 'plan.json', plan)
            seal = read(out / 'seal.json')
            seal['prepared']['plan.json'] = digest(out / 'plan.json')
            write(out / 'seal.json', seal)
            self.unchanged(out)
        return out
