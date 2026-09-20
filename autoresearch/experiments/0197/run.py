"""Registered serial native generation, continued/fresh review and fresh repair."""
from pathlib import Path
import hashlib
import importlib.util
import json
import shutil

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
E = REPO / '.devlyn/0197'
WORKS = REPO.parent / '0197-participants'
REL = Path('config/skills/_shared/task-complete.py')


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


native = module('native0197', HERE / 'native.py')
prior = module('runner0184', REPO / 'autoresearch/experiments/0184/run.py')
assert 'Independently review' in prior.REVIEW_PROMPT and 'You do not receive other reviews or execution results.' in prior.REVIEW_PROMPT
BASE_PROMPT = prior.BASE_PROMPT
REVIEW_PROMPT = prior.REVIEW_PROMPT.replace('Independently review', 'Review').replace('You do not receive other reviews or execution results.', 'No additional execution results or other reviews are supplied in this packet.')
REPAIR_PROMPT = prior.REPAIR_PROMPT
ORDER = [('history-1', ['S', 'F']), ('history-2', ['F', 'S'])]


def registered():
    registration = json.loads((E / 'REGISTRATION.json').read_text())
    for name, digest in registration['sha256'].items():
        assert hashlib.sha256(Path(name).read_bytes()).hexdigest() == digest, name


def packet(work):
    parts = [REVIEW_PROMPT, '\nREQUEST\n' + (E / 'input/spec.md').read_text(), '\nORIGINAL TASK-COMPLETE\n' + (E / 'input' / REL).read_text(), '\nCURRENT TASK-COMPLETE\n' + (work / REL).read_text(), '\nCURRENT ARCHIVE SUPPORT\n' + (work / REL.with_name('archive_run.py')).read_text(), '\nSUPPLIED CHECKS\n' + (E / 'input/tests/test_smoke.py').read_text()]
    added = work / 'tests/test_regression.py'
    if added.exists():
        parts += ['\nADDED CHECKS\n' + added.read_text()]
    baseline = prior.seal(E / 'input')
    current = prior.seal(work)
    already = {str(REL), str(REL.with_name('archive_run.py')), 'tests/test_regression.py'}
    for relative in sorted(set(current) | set(baseline)):
        if relative in already or relative.startswith('.devlyn/') or current.get(relative) == baseline.get(relative):
            continue
        path = work / relative
        parts.append('\nADDITIONAL CHANGED FILE ' + relative + '\n' + (path.read_text(errors='replace') if path.exists() else '[DELETED]'))
    return '\n'.join(parts)


def launch():
    registered()
    WORKS.mkdir(exist_ok=True)
    initial = {}
    for name, arms in ORDER:
        registered()
        work = WORKS / (name + '-initial')
        saved = E / (name + '.initial.json')
        if saved.exists():
            info = json.loads(saved.read_text())
            assert prior.seal(work) == info['seal']
            initial[name] = info
            continue
        if work.exists():
            raise RuntimeError('Interrupted initial requires inspection: ' + name)
        shutil.copytree(E / 'input', work)
        info = dict(work=str(work), **prior.init_work(work, name + '-initial'))
        answer, meta = native.invoke(name + '-initial', BASE_PROMPT, work)
        info.update(seal=prior.seal(work), thread=meta['threads'][0], home=meta['home'])
        native.put(E / (name + '.initial.json'), info)
        initial[name] = info
    if not (E / 'INITIAL-SEALED.json').exists():
        native.put(E / 'INITIAL-SEALED.json', initial)
    finals = {}
    for name, arms in ORDER:
        source = Path(initial[name]['work'])
        assert prior.seal(source) == initial[name]['seal']
        prompt = packet(source)
        for arm in arms:
            registered()
            draw = name + '-' + arm
            work = WORKS / draw
            saved = E / (draw + '.sealed.json')
            if saved.exists():
                finals[draw] = json.loads(saved.read_text())
                assert prior.seal(work) == finals[draw]
                continue
            if work.exists():
                raise RuntimeError('Interrupted branch requires inspection; never reroll: ' + draw)
            shutil.copytree(source, work, ignore=shutil.ignore_patterns('.git', '.devlyn'))
            native.put(E / (draw + '.branch.json'), dict(initial=name, arm=arm, work=str(work), **prior.init_work(work, draw)))
            answer, meta = native.invoke(draw + '-review', prompt, source,
                home=Path(initial[name]['home']) if arm == 'S' else None,
                resume=initial[name]['thread'] if arm == 'S' else None, review=True, budget=600)
            assert prior.seal(source) == initial[name]['seal'], 'review mutated initial source'
            try:
                text = answer.strip()
                if text.startswith('```'):
                    text = '\n'.join(text.splitlines()[1:-1])
                parsed = json.loads(text)
                valid = isinstance(parsed, dict) and isinstance(parsed.get('findings'), list) and all(isinstance(f, dict) and f.get('severity') in ('HIGH', 'MEDIUM', 'LOW') and all(isinstance(f.get(k), str) and f[k] for k in ('file', 'problem')) for f in parsed['findings'])
            except ValueError:
                parsed, valid = None, False
            native.put(E / (draw + '.review.json'), dict(structure_valid=valid, parsed=parsed, no_tool_events=meta['tool_events'] == 0))
            (work / '.devlyn').mkdir(exist_ok=True)
            (work / '.devlyn/review.txt').write_text(answer)
            native.invoke(draw + '-repair', REPAIR_PROMPT, work)
            finals[draw] = prior.seal(work)
            native.put(E / (draw + '.sealed.json'), finals[draw])
    native.put(E / 'FINAL-SEALED.json', finals)
    print('Two initial products and four repaired products sealed; external assessment pending.', flush=True)


if __name__ == '__main__':
    launch()
