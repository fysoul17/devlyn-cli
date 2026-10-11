#!/usr/bin/env python3
"""One awaited, read-only peer call; prospective shared-helper candidate.

Records an attempt before dispatch and the untouched native streams afterwards.
Receipts describe requested execution; native evidence must establish what ran.
"""
from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import os
from pathlib import Path
import runpy
import subprocess
import sys
import tempfile
import time
import uuid


def write(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n', encoding='utf-8')


def answer(engine, capture):
    """Recognize one native terminal success; requested identity is not evidence."""
    text = capture.read_text(encoding='utf-8')
    if engine == 'claude':
        result = json.loads(text)
        if result.get('type') != 'result' or result.get('is_error') is not False:
            raise ValueError('Claude returned no successful result')
        value = result.get('result')
    else:
        rows = [json.loads(line) for line in text.splitlines() if line.strip()]
        if (sum(row.get('type') == 'turn.completed' for row in rows) != 1
                or any(row.get('type') in ('turn.failed', 'error') for row in rows)):
            raise ValueError('Codex returned no successful completed turn')
        messages = [row['item'].get('text') for row in rows if row.get('type') == 'item.completed'
                    and isinstance(row.get('item'), dict) and row['item'].get('type') == 'agent_message']
        value = messages[-1] if messages else None
    if not isinstance(value, str) or not value.strip():
        raise ValueError('native result has no final answer')
    return value


def source_identity(repo):
    """HEAD and tracked/nonignored contents, including symlink targets and modes."""
    def git(*args):
        return subprocess.check_output(['git', '-C', str(repo), *args])
    root = Path(os.fsdecode(git('rev-parse', '--show-toplevel').rstrip(b'\n'))).resolve()
    if root != repo:
        raise ValueError('--repo must name the checkout root')
    files = {}
    for raw in sorted(set(git('ls-files', '-z', '--cached', '--others', '--exclude-standard').split(b'\0')) - {b''}):
        name = os.fsdecode(raw)
        path = repo / name
        if path.is_symlink():
            content = os.fsencode(os.readlink(path))
        elif path.is_file():
            content = path.read_bytes()
        elif not path.exists():
            files[name] = None  # tracked deletion is part of the candidate
            continue
        else:
            raise ValueError('unsupported source entry: ' + name)
        files[name] = [path.lstat().st_mode, hashlib.sha256(content).hexdigest()]
    return dict(head=git('rev-parse', 'HEAD').decode().strip(), files=files)


def argv_for(engine, model, effort, repo, prompt, resume=None):
    if engine == 'claude':
        return ['claude', '-p', '--model', model, '--effort', effort,
                '--permission-mode', 'dontAsk', '--tools', 'Read,Grep,Glob',
                '--strict-mcp-config', '--mcp-config', '{"mcpServers":{}}',
                '--output-format', 'json',
                *(['--resume', resume] if resume else ['--session-id', str(uuid.uuid4())]), prompt]
    if engine == 'codex':
        # Config overrides also apply to resume, whose CLI has no -s/-C switches.
        return ['codex', 'exec', *(['resume'] if resume else []), '--json', '--skip-git-repo-check',
                '-m', model, '-c', 'model_reasoning_effort=' + json.dumps(effort),
                '-c', 'sandbox_mode="read-only"', '-c', 'approval_policy="never"',
                '-c', 'agents.enabled=false',
                '-c', 'features.multi_agent_v2.enabled=false',
                '-c', 'projects.' + json.dumps(str(repo)) + '.trust_level="trusted"',
                *([resume] if resume else []), prompt]
    raise ValueError('unknown peer engine')


@contextlib.contextmanager
def capture_process(repo, stdout, stderr):
    """The dedicated helper redirects inherited fds for the shared process boundary."""
    previous, descriptors = Path.cwd(), [os.dup(1), os.dup(2)]
    try:
        sys.stdout.flush()
        sys.stderr.flush()
        os.dup2(stdout.fileno(), 1)
        os.dup2(stderr.fileno(), 2)
        os.chdir(repo)
        yield
    finally:
        sys.stdout.flush()
        sys.stderr.flush()
        os.chdir(previous)
        for target, saved in zip((1, 2), descriptors):
            os.dup2(saved, target)
            os.close(saved)


def run(args):
    repo = Path(args.repo).resolve()
    if args.watchdog_seconds <= 0:
        raise ValueError('watchdog must be positive')
    # The helper owns custody; caller scratch may disappear after this call.
    records = repo / '.devlyn' / 'pair'
    if records.resolve() != records:
        raise ValueError('peer records must not traverse symlinks')
    if subprocess.run(['git', '-C', str(repo), 'check-ignore', '-q', '--no-index',
                       str(records) + '/'], capture_output=True).returncode != 0:
        raise ValueError('.devlyn/pair must be Git-ignored')
    prompt = Path(args.prompt).read_text(encoding='utf-8')
    before = source_identity(repo)
    records.mkdir(parents=True, exist_ok=True)
    out = Path(tempfile.mkdtemp(prefix='peer-', dir=records))
    stamp = time.time_ns()
    capture = 'peer' + str(stamp) + ('.json' if args.engine == 'claude' else '.jsonl')
    argv = argv_for(args.engine, args.model, args.effort, repo, prompt, args.resume)
    write(out / 'attempt.json', dict(schema='devlyn-peer-v1', engine=args.engine,
          model=args.model, effort=args.effort, repo=str(repo), resume=args.resume,
          source_before=before, prompt_sha256=hashlib.sha256(prompt.encode()).hexdigest(),
          argv=argv, capture=capture, started_ns=stamp, watchdog_seconds=args.watchdog_seconds))
    started, status, code, error = time.monotonic(), 'NOT_STARTED', None, None
    final_answer = None
    try:
        platform = runpy.run_path(str(Path(__file__).with_name('platform-support.py')))
        with (out / capture).open('xb') as stdout, (out / 'stderr').open('xb') as stderr, open(os.devnull, 'rb') as stdin:
            status = 'RUNNING'
            with capture_process(repo, stdout, stderr):
                code = platform['run_process'](platform['native_argv'](argv, repo), stdin,
                                               args.watchdog_seconds, heartbeat=30)
            status = 'TIMEOUT' if code == 124 else 'EXITED'
            if code == 0:
                try:
                    value = answer(args.engine, out / capture)
                    final_answer = out / 'finalanswer.txt'
                    final_answer.write_text(value + '\n', encoding='utf-8')
                except (ValueError, UnicodeError, AttributeError, TypeError) as exc:
                    status, error = 'NATIVE_FAILED', str(exc)
    except BaseException as exc:
        status, error = 'INTERRUPTED' if isinstance(exc, (KeyboardInterrupt, SystemExit)) else 'FAILED', str(exc)
        raise
    finally:
        try:
            after = source_identity(repo)
            stable = before == after
        except (OSError, ValueError, subprocess.SubprocessError) as exc:
            after, stable, error = None, False, str(exc)
        write(out / 'completion.json', dict(schema='devlyn-peer-v1', status=status, exit_code=code,
              error=error, ended_ns=time.time_ns(), seconds=time.monotonic() - started,
              source_after=after, source_unchanged=stable,
              final_answer=str(final_answer) if final_answer else None))
    print(json.dumps(dict(receipt=str(out), status=status, exit_code=code, source_unchanged=stable,
                          final_answer=str(final_answer) if final_answer else None)))
    return 0 if status == 'EXITED' and code == 0 and stable else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--engine', choices=('claude', 'codex'), required=True)
    for key in ('model', 'effort', 'repo', 'prompt'):
        parser.add_argument('--' + key, required=True)
    parser.add_argument('--resume')
    parser.add_argument('--watchdog-seconds', type=int, required=True)
    return run(parser.parse_args())


if __name__ == '__main__':
    sys.exit(main())
