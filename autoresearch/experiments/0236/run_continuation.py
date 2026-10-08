"""Run one 0236 continuation end to end: run_continuation.py <runtime.json> <name> <unit> <F|G>.

Resumes a sealed 0235 Claude cell's own session for one added user message (registration 0236 §3) on an immutable
copy of the cell's end state, then runs the unchanged 0235 post-run pipeline. 0235 code is imported, never edited.
After an assessor fault, `0235/run_cell.py --regrade <runtime.json> <name>` regrades the preserved continuation.

Exit 0 = verdict recorded, 3 = not dispatched (preflight), 2 = STOP: a source cell that fails verification, a frozen
message that no longer matches its source, a resumed session that is not the source session or does not extend its
transcript, or any 0235 STOP.
"""
import datetime
import hashlib
import importlib.util
import json
from pathlib import Path
import os
import shutil
import stat
import subprocess
import sys

HERE = Path(__file__).resolve().parent
EXP = HERE.parent


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


rc = load('run_cell0236', EXP / '0235/run_cell.py')
messages = load('messages0236', HERE / 'messages.py')
cell_run, usage, locate, check, quota, diagnostics = rc.cell_run, rc.usage, rc.locate, rc.check, rc.quota, rc.diagnostics
evidence = usage.evidence
digest = rc.digest
# 0235's audit refreshed the stat cache of .git/index after sealing (registration 0236 §10); nothing else may differ.
ALLOWED_DRIFT = {'cell/work/.git/index'}
EVIDENCE_ROOTS = ('run', 'cell', 'tmp', 'home')
# /tmp of the source end state restored into the new cell's /tmp volume: root-owned sticky directory as the image's
# /tmp, contents owned by the participant (USER 501:501) that wrote them.
SEED = ('set -o pipefail; tar -C /src -cf - . | tar -C /dst -xpf - && chown -R 501:501 /dst && chown 0:0 /dst '
        '&& chmod 1777 /dst')


class SourceError(Exception):
    """The source cell or its frozen message cannot be trusted: nothing is dispatched."""


def files(root, names):
    """sha256 of every regular file under root/<name>, keyed as 0235 seal_after_teardown keys them. Read only."""
    found = {}
    for name in names:
        for path in sorted(p for p in (root / name).rglob('*') if p.is_file() and not p.is_symlink()):
            found[str(path.relative_to(root))] = digest(path)
    return found


def init_event(stdout):
    return next((e for e in evidence.lines(stdout) if e.get('type') == 'system' and e.get('subtype') == 'init'), None)


def environment(init):
    """What a resumed session loads besides its transcript: route, tools, skills, MCP servers and plugins."""
    return dict(model=init.get('model'), claude_code_version=init.get('claude_code_version'),
                permission_mode=init.get('permissionMode'), tools=sorted(init.get('tools') or []),
                skills=sorted(init.get('skills') or []), agents=sorted(init.get('agents') or []),
                mcp_servers=sorted((s.get('name'), s.get('status')) for s in init.get('mcp_servers') or []),
                plugins=sorted(p.get('name') for p in init.get('plugins') or []))


def verify_source(src, image):
    """The source cell as sealed: a non-STOP verdict, its evidence manifest matching the files except exactly the
    allowed drift (recorded), and the image it ran on. Returns the origin record."""
    verdict_path = src.parent / f'verdict-{src.name}.json'
    try:
        verdict = json.loads(verdict_path.read_text())
        manifest = json.loads((src / 'evidence.manifest.json').read_text())
        seal = json.loads((src / 'seal.json').read_text())
    except (OSError, ValueError) as exc:
        raise SourceError(f'{src.name}: unreadable source record: {exc}') from exc
    if verdict.get('status') in (None, 'STOP'):
        raise SourceError(f'{src.name}: source verdict is {verdict.get("status")}')
    if digest(src / 'evidence.manifest.json') != verdict.get('evidence_manifest_sha256') or manifest.get('failures'):
        raise SourceError(f'{src.name}: evidence manifest does not match its verdict')
    current = files(src, EVIDENCE_ROOTS)
    drift = sorted(k for k in manifest['files'].keys() | current.keys() if manifest['files'].get(k) != current.get(k))
    if set(drift) - ALLOWED_DRIFT:
        raise SourceError(f'{src.name}: evidence changed since sealing: {sorted(set(drift) - ALLOWED_DRIFT)[:5]}')
    if seal.get('image') != image:
        raise SourceError(f'{src.name}: sealed on image {seal.get("image")}, runtime image is {image}')
    init = init_event(src / 'run/stdout')
    if not init or not init.get('session_id'):
        raise SourceError(f'{src.name}: no init session id')
    session = init['session_id']
    transcript = Path('home/.claude/projects/-cell-work') / f'{session}.jsonl'
    states = [e for e in evidence.lines(src / transcript) if e.get('type') == 'cost-state' and e.get('sessionId') == session]
    if not states or not isinstance(states[-1].get('modelUsage'), dict):
        raise SourceError(f'{src.name}: transcript has no cost-state for session {session}')
    assessors = {}
    for engine in messages.ENGINES:
        result = json.loads((src / 'assessment' / engine / 'result.json').read_text())
        assessors[engine] = dict(seconds=result['seconds'], usage=result['usage'], exit_code=result['exit_code'],
                                 complete=result['complete'])
    return dict(source=src.name, source_dir=str(src), verdict_sha256=digest(verdict_path),
                manifest_sha256=verdict['evidence_manifest_sha256'], manifest_drift=drift, session=session,
                transcript=str(transcript), transcript_sha256=current[str(transcript)],
                transcript_bytes=(src / transcript).stat().st_size, owner_status=verdict['owner_status'],
                owner_seconds=verdict['owner_seconds'], usage=verdict['usage'], input_tokens=verdict['input_tokens'],
                output_tokens=verdict['output_tokens'], cost_state=states[-1]['modelUsage'], assessors=assessors,
                status=verdict['status'], init=environment(init))


def frozen_message(source_output, unit, arm):
    """The frozen message file, which must still equal the message generated from the source's raw assessor output."""
    path = messages.frozen(arm, unit)
    try:
        text = path.read_text()
        expected = messages.message(source_output, unit, arm)
    except (OSError, ValueError, KeyError, IndexError) as exc:
        raise SourceError(f'message {path.name}: {exc}') from exc
    if text != expected:
        raise SourceError(f'frozen message {path.name} differs from its source')
    return text


def copy_entry(source, target):
    """shutil.copy2, except that a named pipe (left in /tmp by FIFO tests) is recreated with its mode and times."""
    mode = os.lstat(source).st_mode
    if not stat.S_ISFIFO(mode):
        return shutil.copy2(source, target)
    os.mkfifo(target, stat.S_IMODE(mode))
    shutil.copystat(source, target)
    return target


def build(src, out, origin, message):
    """The new cell: original baseline, prompt and harness byte-for-byte; the source end state (cell, home) copied
    with symlinks kept; the source /tmp copied to tmp.seed and restored into the volume at launch, so tmp/ holds only
    what the continuation's /tmp contained at teardown. Returns the plan."""
    out.mkdir(mode=0o700)
    for name in ('baseline.json', 'prompt.txt'):
        shutil.copyfile(src / name, out / name)
    shutil.copytree(src / 'harness', out / 'harness', symlinks=True)
    for name, target in (('cell', 'cell'), ('home', 'home'), ('tmp', 'tmp.seed')):
        shutil.copytree(src / name, out / target, symlinks=True, copy_function=copy_entry)
    (out / 'tmp').mkdir()
    copied = {('tmp/' + k[len('tmp.seed/'):] if k.startswith('tmp.seed/') else k): v
              for k, v in files(out, ('harness', 'cell', 'home', 'tmp.seed')).items()}
    expected = files(src, ('harness', 'cell', 'home', 'tmp'))
    if copied != expected or any(digest(out / n) != digest(src / n) for n in ('baseline.json', 'prompt.txt')):
        raise SourceError(f'{src.name}: the copy differs from the source')
    (out / 'continuation.txt').write_text(message)
    (out / 'origin.json').write_text(json.dumps(origin, indent=2))
    plan = json.loads((src / 'plan.json').read_text())
    plan.update(name=out.name, cell=str(out / 'cell'), tmp=str(out / 'tmp'), home=str(out / 'home'),
                harness=str(out / 'harness'),
                argv=['claude', '-p', '--resume', origin['session'], '--model', plan['model'], '--effort', plan['effort'],
                      '--permission-mode', 'bypassPermissions', '--output-format', 'stream-json', '--verbose', message])
    (out / 'plan.json').write_text(json.dumps(plan, indent=1))
    return plan


def seeding(docker, seed, image, volumes):
    """0235 cell.run's docker call, plus: right after it creates the /tmp volume (recorded in volumes), restore the
    source /tmp into it. A failed restore raises, so no owner starts on an empty /tmp."""
    def call(*args, **kwargs):
        result = docker(*args, **kwargs)
        if args[:2] == ('volume', 'create'):
            volumes.append(args[-1])
            docker('run', '--rm', '--network', 'none', '--user', '0',
                   '--mount', f'type=bind,src={seed},dst=/src,readonly', '--mount', f'type=volume,src={args[-1]},dst=/dst',
                   '--entrypoint', 'bash', image, '-c', SEED, timeout=600)
        return result
    return call


def discard(docker, volumes):
    """Remove the /tmp volumes of a launch that failed before its teardown (each holds a copy of the source /tmp; one
    already removed is no error). Returns the removal failures."""
    failures = []
    for volume in volumes:
        try:
            docker('volume', 'rm', '--force', volume)
        except (OSError, subprocess.SubprocessError) as exc:
            failures.append(f'{volume}: {exc}')
    return failures


def session_check(out, origin):
    """Fail closed unless the continuation resumed the source session and only appended to its transcript."""
    init = init_event(out / 'run/stdout')
    if not init:
        return None, 'continuation emitted no init event'
    env = dict(source=origin['init'], continuation=environment(init))
    env['same'] = env['source'] == env['continuation']
    if init.get('session_id') != origin['session']:
        return env, f'resumed session {init.get("session_id")} is not the source session {origin["session"]}'
    if not (out / origin['transcript']).is_file():
        return env, 'the continuation transcript is missing'
    before = (Path(origin['source_dir']) / origin['transcript']).read_bytes()
    after = (out / origin['transcript']).read_bytes()
    if hashlib.sha256(before).hexdigest() != origin['transcript_sha256']:
        return env, 'source transcript changed since verification'
    if not after.startswith(before) or len(after) == len(before):
        return env, 'the source transcript is not a strict byte prefix of the continuation transcript'
    return env, None


def appended_messages(out, origin):
    """Assistant messages of the source session (sidechains included) appended after the source copy of every
    transcript file, keyed by message id (last copy wins, as evidence.transcripts reads them)."""
    found, gaps = {}, []
    projects, source = out / 'home/.claude/projects', Path(origin['source_dir'])
    for path in sorted(projects.rglob('*.jsonl')):
        relative = path.relative_to(out)
        data = path.read_bytes()
        old = (source / relative).read_bytes() if (source / relative).is_file() else b''
        if not data.startswith(old):
            gaps.append(f'{relative}: source content was rewritten')
            continue
        seen = {message_of(e).get('id') for e in map(parse, old.decode(errors='replace').splitlines())}
        for event in map(parse, data[len(old):].decode(errors='replace').splitlines()):
            message = message_of(event)
            if (not event or event.get('type') != 'assistant' or event.get('isApiErrorMessage')
                    or message.get('model') == '<synthetic>' or event.get('sessionId') != origin['session']):
                continue
            if message.get('id') in seen:
                gaps.append(f'{relative}: source message {message["id"]} written again')
            elif message.get('usage') and message.get('id'):
                found[message['id']] = dict(model=str(message.get('model')).split('[')[0], usage=message['usage'])
    return found, gaps


def parse(line):
    try:
        value = json.loads(line)
    except ValueError:
        return None
    return value if isinstance(value, dict) else None


def message_of(event):
    message = (event or {}).get('message')
    return message if isinstance(message, dict) else {}


def turn_usage(out, origin, session):
    """Turn usage = the final owner result's modelUsage minus the source cost-state, per model and counter. COMPLETE
    only when it equals the sum over the appended transcript messages, the source and session totals are COMPLETE,
    and the cell has no usage outside the owner session."""
    gaps = []
    results = [e for e in evidence.lines(out / 'run/stdout') if e.get('type') == 'result']
    final = (results[-1].get('modelUsage') if results else None) or {}
    if not final:
        gaps.append('owner result without usage')
    turn, owner_input, owner_output = {}, 0, 0
    for model in sorted(final.keys() | origin['cost_state'].keys()):
        now, then = final.get(model), origin['cost_state'].get(model)
        row = {}
        for key, name in usage.RESULT.items():
            a, b = (now or {}).get(name, None if now else 0), (then or {}).get(name, None if then else 0)
            if type(a) is not int or type(b) is not int:
                gaps.append(f'{model}: counter {name} missing')
                continue
            row[key] = a - b
            if row[key] < 0:
                gaps.append(f'{model}: {name} fell from {b} to {a}')
        if now:
            owner_input += sum((now.get(usage.RESULT[k]) or 0) for k in ('input', 'cache_read', 'cache_write'))
            owner_output += now.get('outputTokens') or 0
        turn[model.split('[')[0]] = row
    appended, transcript_gaps = appended_messages(out, origin)
    gaps += transcript_gaps
    summed = {}
    for message in appended.values():
        row = summed.setdefault(message['model'], dict.fromkeys(usage.TRANSCRIPT, 0))
        for key, name in usage.TRANSCRIPT.items():
            value = message['usage'].get(name)
            if type(value) is not int:
                gaps.append(f'transcript message lacks {name}')
                continue
            row[key] += value
    if {m: r for m, r in turn.items() if any(r.values())} != summed:
        gaps.append(f'turn usage {turn} disagrees with the appended transcript {summed}')
    if origin['usage'] != 'COMPLETE':
        gaps.append(f'source usage {origin["usage"]}')
    if session.get('completeness') != 'COMPLETE':
        gaps.append(f'session usage {session.get("completeness")}')
    elif (session['input_tokens'], session['output_tokens']) != (owner_input, owner_output):
        gaps.append('usage outside the owner session')
    rows = [r for r in turn.values() if len(r) == len(usage.RESULT)]
    known = not gaps
    return dict(completeness='COMPLETE' if known else 'UNKNOWN', gaps=gaps, per_model=turn, transcript=summed,
                input_tokens=sum(r['input'] + r['cache_read'] + r['cache_write'] for r in rows) if known else None,
                output_tokens=sum(r['output'] for r in rows) if known else None,
                uncached_input_tokens=sum(r['input'] for r in rows) if known else None,
                cache_read_tokens=sum(r['cache_read'] for r in rows) if known else None,
                cache_write_tokens=sum(r['cache_write'] for r in rows) if known else None)


def apparatus_hashes():
    found = {'0236/' + str(p.relative_to(HERE)): digest(p) for p in sorted(HERE.rglob('*'))
             if p.is_file() and '__pycache__' not in p.parts}
    found |= {'0235/' + p.name: digest(p) for p in sorted((EXP / '0235').glob('*.py'))}
    return found | {'0235/tasks.json': digest(EXP / '0235/tasks.json'), '0232/common.txt': digest(EXP / '0232/common.txt')}


def stop(verdict_path, record, reason):
    return rc.write_verdict(verdict_path, dict(record, status='STOP', reason=reason))


def run(runtime_path, name, unit, arm):
    runtime = json.loads(Path(runtime_path).read_text())
    output = Path(runtime['output'])
    verdict_path = output / f'verdict-{name}.json'
    record = dict(cell=name, continuation_of=unit, arm=arm)
    venue, blocked = rc.preflight(runtime)
    if blocked:  # not a verdict: the continuation never ran and must be dispatched later
        (output / f'not-dispatched-{name}.json').write_text(json.dumps(dict(reason=blocked), indent=2))
        return 3
    if not rc.control_unchanged(runtime):
        return stop(verdict_path, record, 'control changed')
    src, out = Path(runtime['source_output']) / unit, output / name
    try:
        origin = verify_source(src, runtime['image'])
        message = frozen_message(runtime['source_output'], unit, arm)
        plan = build(src, out, origin, message)
    except (SourceError, OSError) as exc:
        return stop(verdict_path, record, f'source: {exc}')
    record.update(task=plan['task'], config=plan['config'])
    (out / 'seal.json').write_text(json.dumps(dict(
        sealed_at=datetime.datetime.now(datetime.timezone.utc).isoformat(), venue=venue, image=runtime['image'],
        source_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=HERE, text=True).strip(),
        apparatus=apparatus_hashes(),
        cell={n: digest(out / n) for n in ('plan.json', 'prompt.txt', 'baseline.json', 'continuation.txt', 'origin.json')},
        control_manifest_sha256=digest(runtime['control'] + '.manifest.json'), origin=origin), indent=2))
    docker, volumes = cell_run.docker, []
    cell_run.docker = seeding(docker, out / 'tmp.seed', plan['image'], volumes)
    try:
        owner = cell_run.run(out, runtime)
    except (OSError, subprocess.SubprocessError) as exc:  # cell.run raised: volume create, /tmp restore or launch
        shutil.rmtree(Path(runtime['scratch']) / 'credentials' / name, ignore_errors=True)
        failures = discard(docker, volumes)
        return stop(verdict_path, record, f'launch failed: {type(exc).__name__}: {exc}'
                    + (f'; /tmp volume not removed: {"; ".join(failures)}' if failures else ''))
    sealed, collection_failures = rc.seal_after_teardown(out)
    if collection_failures:
        record.update(owner_status=owner['owner_status'], teardown=owner['teardown'])
        return stop(verdict_path, record, 'evidence collection failed: ' + '; '.join(collection_failures[:3]))
    try:
        session = usage.record(out)
    except (OSError, ValueError, KeyError, TypeError) as exc:  # usage is recorded, never a stop
        session = dict(completeness=f'UNKNOWN ({type(exc).__name__}: {exc})', input_tokens=None, output_tokens=None)
    environment_record, resumed = session_check(out, origin) if owner['teardown'] == 'CLEAN' else (None, None)
    try:
        turn = turn_usage(out, origin, session) if not resumed else dict(completeness='UNKNOWN', gaps=[resumed])
    except (OSError, ValueError, KeyError, TypeError) as exc:
        turn = dict(completeness=f'UNKNOWN ({type(exc).__name__}: {exc})')
    (out / 'turn_usage.json').write_text(json.dumps(turn, indent=2))
    limits = quota.classify(out)
    trace_bytes = sum(p.stat().st_size for p in (out / 'cell/trace').rglob('*') if p.is_file())
    record.update(owner_status=owner['owner_status'], owner_seconds=owner['seconds'], teardown=owner['teardown'],
                  identity=owner['identity'], environment=environment_record,
                  session_usage=session['completeness'], session_input_tokens=session['input_tokens'],
                  session_output_tokens=session['output_tokens'], turn_usage=turn['completeness'],
                  turn_input_tokens=turn.get('input_tokens'), turn_output_tokens=turn.get('output_tokens'),
                  turn_uncached_input_tokens=turn.get('uncached_input_tokens'),
                  turn_cache_read_tokens=turn.get('cache_read_tokens'), turn_cache_write_tokens=turn.get('cache_write_tokens'),
                  turn_seconds=owner['seconds'], cumulative_seconds=origin['owner_seconds'] + owner['seconds'],
                  origin_sha256=digest(out / 'origin.json'), quota=limits, trace_bytes=trace_bytes,
                  evidence_manifest_sha256=sealed, collection_failures=collection_failures)
    try:
        record['diagnostics'] = diagnostics.record(out)
    except (OSError, ValueError, TypeError, KeyError) as exc:
        record['diagnostics'] = dict(status='UNKNOWN', error=f'{type(exc).__name__}: {exc}')
    baseline = json.loads((out / 'baseline.json').read_text())
    reason = ('teardown failed: ' + str(owner.get('teardown_error')) if owner['teardown'] != 'CLEAN' else
              'session: ' + resumed if resumed else
              'harness changed' if not rc.harness_unchanged(out, baseline) else
              'shared account fault during execution: ' + ', '.join(sorted({h['kind'] for h in limits['execution']}))
              if limits['execution'] else
              'model identity ' + owner['identity']['status'].lower()
              if owner['identity']['status'] in ('MISMATCH', 'UNVERIFIED', 'UNKNOWN') else None)
    if not reason:
        try:
            record['snapshot'] = locate.locate(out)
            before, after = locate.packet.tree(src / 'snapshot'), locate.packet.tree(out / 'snapshot')
            record['files_changed'] = sorted(n for n in before.keys() | after.keys() if before.get(n) != after.get(n))
            record['tree_unchanged'] = not record['files_changed']
            checks = check.check(out, runtime)
        except locate.LocatorError as exc:
            reason = 'locator: ' + str(exc)
        except check.NoVerdict as exc:
            reason = 'evaluator produced no verdict: ' + str(exc)
    if reason:
        return stop(verdict_path, record, reason)
    return rc.write_verdict(verdict_path, rc.grade(out, runtime, record, checks))


if __name__ == '__main__':
    if len(sys.argv) != 5 or sys.argv[4] not in ('F', 'G'):
        raise SystemExit(__doc__)
    sys.exit(run(*sys.argv[1:5]))
