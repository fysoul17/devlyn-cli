"""Reuse the frozen0197 continuation design on a new, separately admitted task."""
from pathlib import Path
import importlib.util
import os

REPO = Path(__file__).resolve().parents[3]
E = REPO / '.devlyn/0198'
WORKS = REPO.parent / '0198-participants'
REL = Path('config/skills/_shared/resolve-bootstrap.py')


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


runner = module('runner0197_reused', REPO / 'autoresearch/experiments/0197/run.py')
runner.E, runner.WORKS, runner.REL = E, WORKS, REL
runner.ORDER = [('binding-1', ['S', 'F']), ('binding-2', ['F', 'S'])]
native, prior = runner.native, runner.prior
native.E = E
native.SCRATCH = REPO / '.git/devlyn-completion/bed944925305d19fa5e49678/scratch'
original_execute = native.controller.execute


def isolated_execute(plan, out):
    settings = dict(GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM='1', GIT_TEMPLATE_DIR='')
    before = {key: os.environ.get(key) for key in settings}
    os.environ.update(settings)
    try:
        return original_execute(plan, out)
    finally:
        for key, value in before.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


native.controller.execute = isolated_execute
registered = runner.registered
original_packet = runner.packet


def packet(work):
    text = original_packet(work).replace('\nORIGINAL TASK-COMPLETE\n', '\nORIGINAL BOOTSTRAP\n').replace('\nCURRENT TASK-COMPLETE\n', '\nCURRENT BOOTSTRAP\n')
    producer = (E / 'input/config/skills/_shared/task-complete.py').read_text().splitlines()
    return text + '\nUNCHANGED RECEIPT PRODUCER allocate/complete excerpt\n' + '\n'.join(producer[177:225] + producer[598:633])


runner.packet = packet

if __name__ == '__main__':
    runner.launch()
