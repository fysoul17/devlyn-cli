"""0226 frozen VERIFY recall screen. Commands: prepare, run --pr N,
redispatch --cause FILE --audit FILE --tokens TOKEN..., score, pool, check, join, self-test.

The committed, pushed Astra audit is JSON with reviewer="Astra",
genuine_registered_fault=true, cause_sha256, stop_evidence_sha256 and the
sorted affected_bundle. The evidence digest hashes the registered stop rows
as JSON with sorted keys. An unaudited stop remains final for scoring.
Join separately requires committed audit.json: reviewer="Astra", labels keyed
by finding id with kind, match, clause_source and reproduced_on_own_tree, and
reads keyed by ambiguous-read id with allowed or excluded verdicts.

Only prepare's Claude instruction probe and run/redispatch invoke a model. The
candidate is always the archived 22616b57 config/skills tree, never this
repository's working config/skills tree.
"""
from __future__ import annotations

import hashlib
from functools import cache
import io
import json
import os
from pathlib import Path
import re
import runpy
import shlex
import shutil
import signal
import stat
import subprocess
import sys
import tarfile
import tempfile
import time
from contextlib import contextmanager
from datetime import datetime, timezone

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
ROOT = Path('/Users/Shared/devlyn-vr')
PRIVATE = ROOT / 'private'
SHARED = ROOT / 'product/config/skills/_shared'
VERIFY_BODY = ROOT / 'product/config/skills/devlyn:resolve/references/phases/verify.md'
FROZEN = HERE / 'manifest.json'
CANDIDATE = '22616b57'
CONTRACT = 'autoresearch/iterations/0226-verify-recall-screen.md'
CLAUDE_SOURCE = Path.home() / '.local/share/claude/versions/2.1.281'
CLAUDE = ROOT / 'bin/claude'
CODEX = Path('/Users/Shared/devlyn-0225-codex-0.156.1/node_modules/.bin/codex')
MODELS_CACHE = Path.home() / '.local/share/nx01/0225-replay/homes/s6-04-r0/.codex/models_cache.json'
CODEX_SHIM = f'''#!/bin/sh
case "$CODEX_HOME" in */.codex) ;; *) echo "0226 codex shim: CODEX_HOME must end in /.codex" >&2; exit 97 ;; esac
HOME="${{CODEX_HOME%/.codex}}" exec {CODEX} "$@"
'''
DISCOVERED = ('CLAUDE.md', 'CLAUDE.local.md', '.claude/CLAUDE.md', '.claude/rules', 'AGENTS.md',
              '.claude', '.agents', '.codex')
INPUT_BLOCKERS = ('verify-input-invalid', 'verify-mechanical-evidence-invalid', 'verify-merge-required-source-missing',
                  'verify.state.', 'verify-pair-trigger', 'verify-dispatch-invalid', 'verify-state-changed',
                  'verify-not-open', 'verify-already-supervised')
BLOCKS = ('claude-1', 'codex-1', 'codex-2', 'claude-2')
STAMP = '2026-09-28T00:00:00Z'
CHILD: list[subprocess.Popen] = []
STOP: list[int] = []
INFRA_CLASSES = frozenset({'usage/rate-limit', 'capacity/overloaded', 'network',
                           'authentication', 'cli-binary-crash'})
DRIFT_CLASSES = frozenset({'manifest-drift', 'driver-drift', 'product-drift', 'node-drift',
                           'runtime-drift', 'toolchain-drift', 'mapping-drift', 'order-drift',
                           'sealed-input-drift',
                           'home-drift', 'account-drift', 'dispatch-drift'})
FIX_CLASSES = INFRA_CLASSES | DRIFT_CLASSES | {'instruction-load'}


class Fault(Exception):
    def __init__(self, kind, message):
        super().__init__(message)
        self.kind = kind


def guard(condition, kind, message):
    if not condition:
        raise Fault(kind, message)


def observed(kind, action):
    try:
        return action()
    except (SystemExit, OSError, ValueError, KeyError) as exc:
        raise Fault(kind, str(exc)) from exc


def fail(message):
    raise SystemExit(message)


def require(condition, message):
    if not condition:
        fail(message)


def sha256(raw):
    return hashlib.sha256(raw).hexdigest()


def now():
    return datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00', 'Z')


def dump(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + '\n', encoding='utf-8')


def load(path):
    return json.loads(path.read_text(encoding='utf-8'))


def minimal_env(path):
    env = {name: os.environ[name] for name in ('HOME', 'USER', 'LOGNAME', 'SHELL', 'TMPDIR', 'LANG') if name in os.environ}
    return {**env, 'PATH': os.pathsep.join(map(str, path)), 'GIT_CONFIG_GLOBAL': '/dev/null',
            'GIT_CONFIG_NOSYSTEM': '1', 'GIT_OPTIONAL_LOCKS': '0', 'DISABLE_AUTOUPDATER': '1'}


def git(cwd, *args):
    return git_raw(cwd, *args).decode().strip()


def git_raw(cwd, *args, env=None):
    proc = subprocess.run(['git', *args], cwd=cwd, env=env or minimal_env(['/opt/homebrew/bin', '/usr/bin', '/bin']),
                          capture_output=True)
    require(proc.returncode == 0, f'git {" ".join(args)}: {proc.stderr.decode(errors="replace")}')
    return proc.stdout


@contextmanager
def environment(env, cwd):
    saved, previous = dict(os.environ), Path.cwd()
    os.environ.clear()
    os.environ.update(env)
    os.chdir(cwd)
    try:
        yield
    finally:
        os.chdir(previous)
        os.environ.clear()
        os.environ.update(saved)


@cache
def modules():
    require((SHARED / 'verify-judges.py').is_file(), f'candidate product absent: {SHARED}')
    return {name: runpy.run_path(str(SHARED / file)) for name, file in (
        ('role', 'role-config.py'), ('render', 'phase-prompt-render.py'),
        ('merge', 'verify-merge-findings.py'), ('auth', 'judge-role-evidence.py'),
        ('judges', 'verify-judges.py'), ('parser', 'judge-output-parser.py'))}


def product():
    paths = [p for p in SHARED.rglob('*') if p.is_file() and '__pycache__' not in p.parts] + [VERIFY_BODY]
    require(all(p.is_file() for p in paths) and VERIFY_BODY.is_file(), 'candidate rubric is missing')
    return {str(p.relative_to(ROOT / 'product')): sha256(p.read_bytes()) for p in sorted(paths)}


def inventory(root):
    rows = []
    for folder, dirs, files in os.walk(root):
        dirs.sort()
        for name in files + [d for d in dirs if (Path(folder) / d).is_symlink()]:
            path = Path(folder) / name
            raw = os.readlink(path).encode() if path.is_symlink() else path.read_bytes()
            rows.append([str(path.relative_to(root)), len(raw), sha256(raw)])
    return sorted(rows)


def digest_inventory(root):
    rows = inventory(root)
    return {'files': len(rows), 'sha256': sha256(json.dumps(rows, separators=(',', ':')).encode())}


def sealed_inventory():
    outputs = {'score.json', 'pool.jsonl', 'pool-map.json', 'result.json'}
    rows = [row for row in inventory(PRIVATE) if row[0] not in outputs
            and not row[0].startswith('checks/')]
    return {'files': len(rows), 'sha256': sha256(json.dumps(rows, separators=(',', ':')).encode())}


def task_files():
    corpus = PRIVATE / 'corpus'
    require(corpus.is_dir(), f'missing private corpus: {corpus}')
    tasks = sorted(p.name for p in corpus.iterdir() if p.is_dir())
    require(len(tasks) == 8, 'corpus must contain exactly eight tasks')
    for task in tasks:
        require(re.fullmatch(r'[CJ][1-4]', task) is not None, f'noncanonical task id: {task}')
        require(load(corpus / task / 'task.json')['repo'] == ('cachetools' if task.startswith('C') else 'joi'),
                f'{task}: task id and repository disagree')
        for name in ('task.json', 'spec.md', 'spec.expected.json', 'reference.patch', 'twin.patch', 'calibration.json'):
            require((corpus / task / name).is_file(), f'{task}: missing {name}')
        require((corpus / task / 'hidden').is_dir(), f'{task}: missing hidden oracle')
    for repo in ('cachetools', 'joi'):
        source = PRIVATE / 'repos' / repo
        require(source.is_dir(), f'{repo}: pinned clone missing')
        forbidden = {'CLAUDE.md', 'CLAUDE.local.md', 'AGENTS.md', '.claude', '.agents', '.codex'}
        found = []
        for folder, dirs, files in os.walk(source):
            dirs[:] = [name for name in dirs if name != '.git']
            found.extend(str((Path(folder) / name).relative_to(source)) for name in dirs + files if name in forbidden)
        require(not found, f'{repo}: agent instructions in pinned clone: {found}')
    return tasks


def internal_id(task, variant, orientation, rep):
    return f'{task}|{variant}|{orientation}|{rep}'


def ordered_ids(tasks):
    require(len(tasks) == 8, 'order requires eight tasks')
    return [internal_id(task, variant, block.rsplit('-', 1)[0], int(block[-1]))
            for block in BLOCKS for task, variant in sorted(
                ((task, variant) for task in tasks for variant in ('reference', 'twin')),
                key=lambda pair: sha256(f'{block}|{pair[0]}|{pair[1]}'.encode()))]


def token(salt, rid):
    return sha256(salt + rid.encode())[:12]


def slug(salt, task):
    return 'change-' + sha256(salt + task.encode())[:8]


def order_digest(order):
    return sha256(json.dumps(order, separators=(',', ':')).encode())


def private_order(manifest=None):
    data = load(PRIVATE / 'mapping.json')
    mapping = data.get('tokens') if isinstance(data, dict) else None
    if not isinstance(mapping, dict) or not all(isinstance(tok, str) and isinstance(rid, str)
                                                 for tok, rid in mapping.items()):
        raise ValueError('invalid private mapping')
    tasks = sorted({rid.split('|')[0] for rid in mapping.values()})
    reverse = {rid: tok for tok, rid in mapping.items()}
    require(len(reverse) == 64 and (manifest is None or set(mapping) == {row['token'] for row in manifest['rounds']}),
            'private mapping and manifest rounds disagree')
    return [reverse[rid] for rid in ordered_ids(tasks)]


def account_ids():
    codex = load(Path.home() / '.codex/auth.json')['tokens']['account_id']
    claude = load(Path.home() / '.claude.json')['oauthAccount']['accountUuid']
    require(isinstance(codex, str) and codex and isinstance(claude, str) and claude,
            'Codex or Claude account id missing')
    return {'codex': codex, 'claude': claude}


def account_hashes():
    return {engine: sha256(value.encode()) for engine, value in account_ids().items()}


def identity(mapping, tok):
    require(tok in mapping['tokens'], f'unknown token {tok}')
    task, variant, orientation, rep = mapping['tokens'][tok].split('|')
    return task, variant, orientation, int(rep)


def discovery(work):
    return sorted(str(folder / name) for folder in (work, *work.parents) for name in DISCOVERED
                  if (folder / name).exists())


def node_bin():
    path = ROOT / 'toolchains/joi/node-bin'
    node = path / 'node'
    require(node.is_file() and os.access(node, os.X_OK), f'Node 22 missing: {node}')
    version = subprocess.run([str(node), '--version'], capture_output=True, text=True)
    require(version.returncode == 0 and re.fullmatch(r'v22\.\d+\.\d+', version.stdout.strip()),
            f'Node 22 required at {node}')
    return path


def round_env(tok, work, repo, *, stub=False):
    tool = ROOT / 'toolchains' / repo
    first = tool / 'venv/bin' if repo == 'cachetools' else node_bin()
    require(first.is_dir(), f'{repo} toolchain missing: {first}')
    env = minimal_env([ROOT / ('dry/bin' if stub else 'bin'), first, '/opt/homebrew/bin', '/usr/bin', '/bin',
                       '/usr/sbin', '/sbin'])
    env['CODEX_HOME'] = str(ROOT / ('dry/codex-home' if stub else f'homes/{tok}/.codex'))
    if repo == 'cachetools':
        env['PYTHONPATH'] = str(work / 'src')
        env['PYRIGHT_PYTHON_CACHE_DIR'] = str(tool / 'pyright-cache')
    return env


def runtime(repo):
    home = ROOT / 'runtime-home/.codex'
    home.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(MODELS_CACHE, home / 'models_cache.json')
    env = round_env('runtime', ROOT, repo)
    env['CODEX_HOME'] = str(home)
    with environment(env, ROOT):
        versions = {}
        for engine in ('claude', 'codex'):
            proc = subprocess.run([engine, '--version'], capture_output=True, text=True)
            require(proc.returncode == 0, f'{engine} --version failed: {proc.stderr}')
            versions[engine] = proc.stdout.strip()
        resolved = {name: str(Path(shutil.which(name)).resolve()) for name in
                    ('claude', 'codex', 'node', 'bash', 'python3', 'git')}
    entry = CODEX.resolve()
    native = entry.parents[1].parent / 'codex-darwin-arm64/vendor/aarch64-apple-darwin/bin/codex'
    require(native.is_file(), f'Codex vendored native binary missing: {native}')
    shutil.rmtree(home / 'tmp', ignore_errors=True)
    return {'versions': versions, 'resolved': resolved, 'python': sys.executable,
            'node_sha256': sha256(Path(resolved['node']).read_bytes()),
            'python3_sha256': sha256(Path(resolved['python3']).read_bytes()),
            'codex': str(entry), 'codex_entry_sha256': sha256(entry.read_bytes()),
            'codex_native': str(native.resolve()), 'codex_native_sha256': sha256(native.read_bytes()),
            'claude_sha256': sha256(CLAUDE.read_bytes()),
            'codex_shim_sha256': sha256((ROOT / 'bin/codex').read_bytes())}


def extract_archive(repo, sha, destination, prefix=None):
    raw = git_raw(repo, 'archive', '--format=tar', sha, *( [prefix] if prefix else []))
    destination.mkdir(parents=True, exist_ok=True)
    with tarfile.open(fileobj=io.BytesIO(raw)) as archive:
        archive.extractall(destination, filter='data')


def git_tree_hash(folder):
    """Hash an extracted tree with Git's object format without writing to .git."""
    body = bytearray()
    paths = sorted(folder.iterdir(), key=lambda path: os.fsencode(path.name) +
                   (b'/' if path.is_dir() and not path.is_symlink() else b''))
    for path in paths:
        if path.is_symlink():
            mode, raw = b'120000', os.fsencode(os.readlink(path))
            kind = b'blob'
        elif path.is_dir():
            mode, raw = b'40000', None
            kind = b'tree'
        else:
            mode, raw = b'100755' if path.stat().st_mode & 0o111 else b'100644', path.read_bytes()
            kind = b'blob'
        digest = (bytes.fromhex(git_tree_hash(path)) if raw is None else
                  hashlib.sha1(kind + b' ' + str(len(raw)).encode() + b'\0' + raw).digest())
        body.extend(mode + b' ' + os.fsencode(path.name) + b'\0' + digest)
    return hashlib.sha1(b'tree ' + str(len(body)).encode() + b'\0' + body).hexdigest()


def commit(work, message):
    env = minimal_env(['/opt/homebrew/bin', '/usr/bin', '/bin'])
    env.update(GIT_AUTHOR_NAME='dev', GIT_AUTHOR_EMAIL='dev@example.invalid',
               GIT_COMMITTER_NAME='dev', GIT_COMMITTER_EMAIL='dev@example.invalid',
               GIT_AUTHOR_DATE=STAMP, GIT_COMMITTER_DATE=STAMP)
    git_raw(work, '-c', 'core.logAllRefUpdates=false', 'add', '-A', env=env)
    git_raw(work, '-c', 'core.logAllRefUpdates=false', 'commit', '-qm', message, env=env)
    return git(work, 'rev-parse', 'HEAD')


def source_data(task):
    path = PRIVATE / 'corpus' / task
    info = load(path / 'task.json')
    require(set(info) == {'repo', 'sha'} and info['repo'] in ('cachetools', 'joi')
            and re.fullmatch(r'[0-9a-f]{40}', info['sha']) is not None, f'{task}: invalid task.json')
    repo = PRIVATE / 'repos' / info['repo']
    require(repo.is_dir() and git(repo, 'rev-parse', info['sha'] + '^{commit}') == info['sha']
            and git(repo, 'rev-parse', 'HEAD') == info['sha'],
            f'{task}: pinned repository SHA unavailable')
    return path, info, repo


def rewrite_spec(raw, name):
    lines = raw.splitlines(keepends=True)
    matches = [i for i, line in enumerate(lines) if re.fullmatch(rb'id:[ \t]*[^\r\n]+\r?\n?', line)]
    closing = next((i for i, line in enumerate(lines[1:], 1) if line.strip() == b'---'), None)
    require(len(matches) == 1 and lines[0].strip() == b'---' and closing is not None
            and 0 < matches[0] < closing,
            'spec.md requires a unique frontmatter id line')
    require(re.search(rb'(?<![A-Za-z0-9_])(?:C[1-4]|J[1-4])(?![A-Za-z0-9_])',
                      b''.join(lines[closing + 1:])) is None,
            'spec.md body still contains a task id')
    lines[matches[0]] = f'id: {name}\n'.encode()
    return b''.join(lines)


def materialize(tok, task, variant, orientation, task_slug, work, *, apparatus=True):
    corpus, info, repo = source_data(task)
    work.mkdir(parents=True)
    git(work, 'init', '-q', '-b', 'main')
    git(work, 'config', 'core.logAllRefUpdates', 'false')
    exclude = work / '.git/info/exclude'
    exclude.write_text('.devlyn/\n' + ('node_modules\n' if info['repo'] == 'joi' else ''), encoding='utf-8')
    extract_archive(repo, info['sha'], work)
    spec_dir = work / 'docs/specs' / task_slug
    spec_dir.mkdir(parents=True, exist_ok=True)
    spec = rewrite_spec((corpus / 'spec.md').read_bytes(), task_slug)
    (spec_dir / 'spec.md').write_bytes(spec)
    shutil.copyfile(corpus / 'spec.expected.json', spec_dir / 'spec.expected.json')
    base = commit(work, 'base')
    if variant != 'base':
        git_raw(work, 'apply', '--index', str(corpus / (variant + '.patch')))
        head = commit(work, 'change')
    else:
        head = base
    require(not git(work, 'status', '--porcelain', '--untracked-files=all'), f'{tok}: dirty materialized copy')
    changed = sorted(git(work, 'diff', '--name-only', base, head).splitlines()) if variant != 'base' else []
    require(not any((work / '.git' / name).exists() for name in ('logs', 'ORIG_HEAD', 'FETCH_HEAD'))
            and not git(work, 'remote'), f'{tok}: materialized Git metadata leaks history')
    if info['repo'] == 'joi':
        link = work / 'node_modules'
        link.symlink_to(ROOT / 'toolchains/joi/node_modules', target_is_directory=True)
    if variant == 'base' or not apparatus:
        return dict(base=base, head=head, changed=changed, repo=info['repo'])
    devlyn = work / '.devlyn'
    devlyn.mkdir()
    (devlyn / 'plan.md').write_text('<!-- devlyn:authorized-surface -->\n## Files to touch\n```json\n'
                                     + json.dumps({'authorized_surface': changed}) + '\n```\n', encoding='utf-8')
    roles = ({'primary_judge': {'engine': 'claude', 'model': 'claude-opus-5-5'},
              'pair_judge': {'engine': 'codex', 'model': 'gpt-6-astra', 'effort': 'high'}}
             if orientation == 'claude' else
             {'primary_judge': {'engine': 'codex', 'model': 'gpt-6-astra', 'effort': 'high'},
              'pair_judge': {'engine': 'claude', 'model': 'claude-opus-5-5'}})
    product_code = modules()
    role = product_code['role']
    (devlyn / 'engines.json').write_bytes(role['encoded']({'roles': roles}))
    with environment(round_env(tok, work, info['repo']), work):
        resolution = role['resolve'](work, orientation, available=lambda engine: engine in ('claude', 'codex'))
    state = {'version': '3.0', 'run_id': 'rs-20260928T000000Z-' + tok, 'engine': orientation,
             'mode': 'spec', 'base_ref': {'sha': base}, 'pair_verify': False,
             'source': {'type': 'spec', 'spec_path': str((spec_dir / 'spec.md').relative_to(work)),
                        'spec_sha256': sha256(spec)},
             'risk_profile': {'high_risk': False, 'risk_probes_enabled': False,
                              'pair_default_enabled': True, 'reasons': []},
             'rounds': {'global': 0, 'max_rounds': 2}, 'role_resolution': resolution,
             'verify': {'coverage_failed': False, 'pair_trigger': None},
             'phases': {'verify': {'engine': orientation, 'round': 0, 'started_at': STAMP,
                                   'completed_at': None, 'verdict': None, 'sub_verdicts': None}}}
    (devlyn / 'pipeline.state.json').write_bytes(role['encoded'](state))
    env = round_env(tok, work, info['repo'])
    env.update(SPEC_VERIFY_PHASE='verify_mechanical', SPEC_VERIFY_FINDINGS_FILE='verify-mechanical.findings.jsonl',
               SPEC_VERIFY_FINDING_PREFIX='VERIFY-MECH')
    proc = subprocess.run(['python3', str(SHARED / 'spec-verify-check.py'), '--include-risk-probes'],
                          cwd=work, env=env, capture_output=True, text=True)
    require(proc.returncode == 0, f'{tok}: MECHANICAL failed ({proc.returncode}): {proc.stderr}\n{proc.stdout}')
    with environment(round_env(tok, work, info['repo']), work):
        findings, verdict = product_code['merge']['mechanical_source'](devlyn)
    require(verdict == 'PASS' and not findings, f'{tok}: MECHANICAL {verdict}: {findings}')
    return dict(base=base, head=head, changed=changed, repo=info['repo'])


def preflight(tok, work, repo):
    code = modules()
    devlyn = work / '.devlyn'
    state = code['role']['loads']((devlyn / 'pipeline.state.json').read_bytes())
    with environment(round_env(tok, work, repo), work):
        resolution = code['role']['snapshot'](state)
        require(resolution['sha256'] == state['role_resolution']['sha256'], f'{tok}: role resolution drift')
        _, mechanical = code['merge']['mechanical_source'](devlyn)
        require(mechanical == 'PASS', f'{tok}: MECHANICAL {mechanical}')
        reasons = code['merge']['outcome_independent_reasons'](devlyn)
        snapshot = code['render']['build_verify_snapshot'](devlyn, state)
        header, _, rest = snapshot.partition(b'\n')
        label, _, length = header.partition(b' ')
        metadata = json.loads(rest[:int(length)])
        require(label == b'metadata' and metadata['head_sha'] == git(work, 'rev-parse', 'HEAD')
                and metadata['round'] == 0, f'{tok}: snapshot identity mismatch')
        seats, prompts = {}, {}
        for role in code['judges']['ROLES']:
            entry = code['judges']['decide'](state, resolution, role, False)
            require(entry['decision'] == 'dispatch', f'{tok} {role}: {entry}')
            prompt = code['render']['render_verify'](role, entry['engine'], snapshot)
            argv, extra = code['judges']['launch_argv'](devlyn, entry)
            seats[role] = {'engine': entry['engine'], 'model': entry['model_requested'],
                           'effort': entry['effort'], 'requested_effort': resolution['roles'][role]['effort_requested'],
                           'channel': entry['channel'], 'stem': entry['stem'],
                           'prompt_sha256': sha256(prompt), 'argv_sha256': sha256(code['role']['encoded'](argv)),
                           'environment': extra}
            prompts[role] = prompt
    require('pair.default' in reasons, f'{tok}: pair trigger lacks pair.default: {reasons}')
    return {'snapshot_sha256': sha256(snapshot), 'snapshot_bytes': len(snapshot), 'reasons': reasons,
            'seats': seats, 'prompts': prompts}


def label_scan(prompts, base_content, rid, corpus_names):
    labels = [b'twin', b'mutant', b'reference.patch', b'0226', b'corpus', b'oracle', b'devlyn-0226', rid.encode()]
    labels.extend(name.encode() for name in corpus_names)
    labels.extend(f'{prefix}{n}'.encode() for prefix in ('C', 'J') for n in range(1, 5))
    for prompt in prompts:
        for label in labels:
            pattern = rb'(?<![A-Za-z0-9])' + re.escape(label) + rb'(?![A-Za-z0-9])'
            if re.search(pattern, base_content) is None and re.search(pattern, prompt):
                fail(f'label scan: forbidden {label!r} in rendered prompt')


def base_content(work, base):
    raw = git_raw(work, 'archive', '--format=tar', base)
    with tarfile.open(fileobj=io.BytesIO(raw)) as archive:
        return b'\n'.join(member.name.encode() + b'\n' + archive.extractfile(member).read()
                          for member in archive if member.isfile())


def dry_run(tok, work, repo, reasons):
    dry = ROOT / 'dry' / tok
    shutil.copytree(work, dry, symlinks=True)
    stubs = ROOT / 'dry/stubs' / tok
    (stubs / 'barrier').mkdir(parents=True)
    env = round_env(tok, dry, repo, stub=True)
    env.update(STUB_DIR=str(stubs), STUB_BARRIER='1')
    proc = subprocess.run([sys.executable, str(SHARED / 'verify-judges.py'), '--devlyn-dir', str(dry / '.devlyn')],
                          cwd=dry, env=env, capture_output=True, text=True)
    require(proc.returncode == 0, f'{tok}: dry run failed rc={proc.returncode}\n{proc.stdout}\n{proc.stderr[-4000:]}')
    summary = json.loads(proc.stdout)
    carriers = [load(dry / '.devlyn' / f'{engine}-judge.r0.prompt.transport.json')
                for engine in ('claude', 'codex')]
    record = load(dry / '.devlyn/verify-judge.r0.dispatch.json')
    require(summary['verdict'] == 'PASS'
            and summary['source_verdicts'] == {'mechanical': 'PASS', 'judge': 'PASS', 'pair_judge': 'PASS'}
            and all(c['outcome'] == 'exited' and c['exit_code'] == 0 for c in carriers)
            and min(c['ended_at'] for c in carriers) > max(c['started_at'] for c in carriers)
            and record['pair_trigger'] == {'eligible': True, 'reasons': reasons, 'skipped_reason': None},
            f'{tok}: stub dry-run contract failed: {summary}')
    return {'verdict': 'PASS', 'source_verdicts': summary['source_verdicts'],
            'carriers': [{'outcome': c['outcome'], 'exit_code': c['exit_code']} for c in carriers],
            'overlap': True}


def transcript(session):
    found = list((Path.home() / '.claude/projects').glob(f'*/{session}.jsonl'))
    require(len(found) == 1, f'Claude transcript missing or ambiguous for {session}')
    return found[0]


def attachments(path, work):
    files = []
    for line in path.read_text(encoding='utf-8').splitlines():
        attachment = json.loads(line).get('attachment') or {}
        if attachment.get('type') == 'instructions':
            files.extend(entry['path'] for entry in attachment.get('files', []))
    return sorted(str(Path(path).relative_to(work)) if Path(path).is_relative_to(work) else path for path in files)


def instructions(tok, repo):
    dry = ROOT / 'dry' / tok
    devlyn = dry / '.devlyn'
    code = modules()
    state = code['role']['loads']((devlyn / 'pipeline.state.json').read_bytes())
    env = round_env(tok, dry, repo)
    with environment(env, dry):
        resolution = code['role']['snapshot'](state)
        role = next(role for role in code['judges']['ROLES'] if resolution['roles'][role]['engine'] == 'claude')
        argv, _ = code['judges']['launch_argv'](devlyn, code['judges']['decide'](state, resolution, role, False))
    argv = argv[argv.index('--') + 1:]
    argv[argv.index('--model') + 1] = 'claude-sonnet-5'
    destination = ROOT / 'transcripts' / tok / 'probe'
    try:
        proc = subprocess.run(argv, cwd=dry, env=env, input='Reply with exactly: OK',
                              capture_output=True, text=True, timeout=300)
        require(proc.returncode == 0, f'{tok}: Claude instruction probe failed: {proc.stderr}')
        session = json.loads(proc.stdout)['session_id']
        source = transcript(session)
    finally:
        project = (source.parent if 'source' in locals() else Path.home() / '.claude/projects' /
                   ('-' + str(dry).strip('/').replace('/', '-')))
        if project.is_dir():
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(project), str(destination))
    files = attachments(destination / source.name, dry)
    require(files == [], f'{tok}: Claude loaded instruction files: {files}')
    return {'files': files}


def pristine(tok, work):
    dest = PRIVATE / 'pristine'
    dest.mkdir(exist_ok=True)
    for suffix, path in (('.tar', work), ('.home.tar', ROOT / 'homes' / tok)):
        with tarfile.open(dest / (tok + suffix), 'w') as archive:
            archive.add(path, arcname=path.name, recursive=True,
                        filter=lambda member: None if suffix == '.tar' and
                        member.name == 'work/node_modules' else member)
    return {**{suffix: sha256((dest / (tok + suffix)).read_bytes()) for suffix in ('.tar', '.home.tar')},
            'work_inventory': digest_inventory(work),
            'home_inventory': digest_inventory(ROOT / 'homes' / tok)}


def prepare():
    require(ROOT.is_dir() and stat.S_IMODE(ROOT.stat().st_mode) == 0o700,
            f'{ROOT} must exist with mode 0700 and a staged private corpus')
    require(not Path('/Users/Shared/devlyn-0226').exists(), 'author/implementer root was not moved to private/workspaces')
    require((PRIVATE / 'workspaces').is_dir(), 'private/workspaces is missing')
    require(not (ROOT / 'manifest.json').exists(), 'prepare runs once; manifest already exists')
    for name in ('bin', 'product', 'dry', 'rounds', 'homes', 'transcripts', 'runtime-home'):
        shutil.rmtree(ROOT / name, ignore_errors=True)
    for name in ('salt', 'mapping.json'):
        (PRIVATE / name).unlink(missing_ok=True)
    shutil.rmtree(PRIVATE / 'pristine', ignore_errors=True)
    require(not ROOT.is_relative_to(Path.home()), 'ROOT must be outside HOME')
    for parent in (ROOT, *ROOT.parents):
        if parent == Path('/'):
            break
        require(not any((parent / name).exists() for name in DISCOVERED),
                f'instruction or agent file in ancestor {parent}')
    tasks = task_files()
    require((ROOT / 'toolchains/cachetools/venv/bin/python3').is_file()
            and (ROOT / 'toolchains/cachetools/pyright-cache').is_dir()
            and (ROOT / 'toolchains/joi/node_modules').is_dir(), 'toolchains are not provisioned')
    python_bin = ROOT / 'toolchains/cachetools/venv/bin'
    python_version = subprocess.run([str(python_bin / 'python3'), '--version'], capture_output=True, text=True)
    require(python_version.returncode == 0 and python_version.stdout.startswith('Python 3.13.'),
            f'cachetools needs Python 3.13, found {python_version.stdout.strip()!r}')
    for tool in ('pytest', 'ruff', 'pyright'):
        require((python_bin / tool).is_file(), f'cachetools toolchain missing {tool}')
    coverage = subprocess.run([str(python_bin / 'python3'), '-c', 'import pytest_cov'], capture_output=True, text=True)
    require(coverage.returncode == 0, f'cachetools toolchain missing pytest-cov: {coverage.stderr}')
    node_bin()
    tree_hash = git(REPO, 'rev-parse', CANDIDATE + ':config/skills')
    extract_archive(REPO, CANDIDATE, ROOT / 'product', 'config/skills')
    extracted_tree = git_tree_hash(ROOT / 'product/config/skills')
    require(extracted_tree == tree_hash, f'candidate extraction tree mismatch {extracted_tree} != {tree_hash}')
    code = modules()
    (ROOT / 'bin').mkdir()
    shutil.copyfile(CLAUDE_SOURCE, CLAUDE)
    CLAUDE.chmod(0o500)
    (ROOT / 'bin/codex').write_text(CODEX_SHIM, encoding='utf-8')
    (ROOT / 'bin/codex').chmod(0o500)
    codex_version = subprocess.run([str(CODEX), '--version'], capture_output=True, text=True).stdout.split()[-1]
    require(load(MODELS_CACHE)['client_version'] == codex_version, 'Codex cache version differs from pinned CLI')
    salt = os.urandom(32)
    (PRIVATE / 'salt').write_bytes(salt)
    order_ids = ordered_ids(tasks)
    order = [token(salt, rid) for rid in order_ids]
    require(len(set(order)) == 64, 'token collision')
    mapping = {'tokens': dict(zip(order, order_ids)), 'slugs': {slug(salt, task): task for task in tasks}}
    dump(PRIVATE / 'mapping.json', mapping)
    (ROOT / 'dry/bin').mkdir(parents=True)
    for engine in ('claude', 'codex'):
        path = ROOT / 'dry/bin' / engine
        path.write_text(code['judges']['STUB'], encoding='utf-8')
        path.chmod(0o755)
    (ROOT / 'dry/codex-home').mkdir()
    dump(ROOT / 'dry/codex-home/models_cache.json', {'client_version': '9.9.9', 'models': [
        {'slug': 'gpt-6-astra', 'supported_reasoning_levels': [{'effort': 'medium'}, {'effort': 'high'}]}]})
    rounds = []
    changed_by_task = {}
    for tok in order:
        task, variant, orientation, rep = identity(mapping, tok)
        work = ROOT / 'rounds' / tok / 'work'
        home = ROOT / 'homes' / tok / '.codex'
        home.mkdir(parents=True)
        shutil.copyfile(MODELS_CACHE, home / 'models_cache.json')
        material = materialize(tok, task, variant, orientation, slug(salt, task), work)
        changed_by_task.setdefault(task, {})[variant] = material['changed']
        if set(changed_by_task[task]) == {'reference', 'twin'}:
            require(changed_by_task[task]['reference'] == changed_by_task[task]['twin'],
                    f'{task}: twin changed-file set differs from reference')
        checks = preflight(tok, work, material['repo'])
        shutil.rmtree(home / 'tmp', ignore_errors=True)
        corpus_names = [p.name for p in (PRIVATE / 'corpus' / task).rglob('*') if p.is_file()]
        label_scan(checks.pop('prompts').values(), base_content(work, material['base']),
                   mapping['tokens'][tok], corpus_names)
        saved = pristine(tok, work)
        dry = dry_run(tok, work, material['repo'], checks['reasons'])
        probe = instructions(tok, material['repo'])
        require(discovery(work) == [] and discovery(ROOT / 'dry' / tok) == [],
                f'{tok}: instruction discovery is not empty')
        rounds.append({'token': tok, 'run_id': 'rs-20260928T000000Z-' + tok,
                       'base': material['base'], 'head': material['head'], 'repo': material['repo'],
                       'span_sha256': sha256(git_raw(work, 'diff', material['base'], material['head'])),
                       'verify_started_at': STAMP, 'work': str(work),
                       'resolution_sha256': load(work / '.devlyn/pipeline.state.json')['role_resolution']['sha256'],
                       'env': round_env(tok, work, material['repo']),
                       'models_cache_sha256': sha256((home / 'models_cache.json').read_bytes()),
                       'dry_run': dry, 'claude_instructions': probe, 'discovery': [], 'pristine': saved,
                       **checks})
        print(f'[0226] prepared {len(rounds)}/64', file=sys.stderr, flush=True)
    toolchains = {repo: digest_inventory(ROOT / 'toolchains' / repo) for repo in ('cachetools', 'joi')}
    corpus_files = inventory(PRIVATE / 'corpus')
    repo_shas = {repo: sorted({load(PRIVATE / 'corpus' / task / 'task.json')['sha'] for task in tasks
                               if load(PRIVATE / 'corpus' / task / 'task.json')['repo'] == repo})
                 for repo in ('cachetools', 'joi')}
    sealed = sealed_inventory()
    manifest = {'schema': 1, 'contract': CONTRACT, 'repo_head': git(REPO, 'rev-parse', 'HEAD'),
                'candidate_commit': CANDIDATE, 'candidate_tree': tree_hash, 'product_sha256': product(),
                'driver_sha256': sha256(Path(__file__).read_bytes()),
                'runtime': {repo: runtime(repo) for repo in ('cachetools', 'joi')},
                'accounts': account_hashes(),
                'node_bin': str(node_bin()), 'toolchains': toolchains,
                'order_sha256': order_digest(order), 'rounds': sorted(rounds, key=lambda row: row['token']),
                'corpus_files': corpus_files, 'repo_pins': repo_shas,
                'salt_sha256': sha256(salt), 'mapping_sha256': sha256((PRIVATE / 'mapping.json').read_bytes()),
                'sealed_inputs': sealed}
    require(all(digest_inventory(ROOT / 'homes' / row['token']) == row['pristine']['home_inventory']
                for row in rounds), 'runtime changed a round home after pristine capture')
    dump(ROOT / 'manifest.json', manifest)
    print(f'[0226] manifest sha256 {sha256((ROOT / "manifest.json").read_bytes())}', file=sys.stderr)


def frozen(*, calls=True):
    manifest = observed('manifest-drift', lambda: load(ROOT / 'manifest.json'))
    committed = subprocess.run(['git', 'show', f'HEAD:{FROZEN.relative_to(REPO)}'], cwd=REPO, capture_output=True)
    guard(committed.returncode == 0 and committed.stdout == observed(
              'manifest-drift', lambda: (ROOT / 'manifest.json').read_bytes()),
          'manifest-drift', 'manifest is not committed byte for byte at HEAD')
    guard(observed('driver-drift', lambda: sha256(Path(__file__).read_bytes())) == manifest['driver_sha256'],
          'driver-drift', 'driver changed after freeze')
    guard(observed('product-drift', lambda: git(REPO, 'rev-parse', CANDIDATE + ':config/skills')) == manifest['candidate_tree']
          and observed('product-drift', lambda: git_tree_hash(ROOT / 'product/config/skills')) == manifest['candidate_tree']
          and observed('product-drift', product) == manifest['product_sha256'],
          'product-drift', 'candidate product changed after freeze')
    if calls:
        guard(str(observed('node-drift', node_bin)) == manifest['node_bin'], 'node-drift',
              'Node 22 directory changed after freeze')
        for repo in ('cachetools', 'joi'):
            guard(observed('runtime-drift', lambda: runtime(repo)) == manifest['runtime'][repo], 'runtime-drift',
                  f'{repo} judge runtime changed after freeze')
        guard(observed('toolchain-drift', lambda: digest_inventory(ROOT / 'toolchains/cachetools')) ==
              manifest['toolchains']['cachetools'] and
              observed('toolchain-drift', lambda: digest_inventory(ROOT / 'toolchains/joi')) ==
              manifest['toolchains']['joi'],
              'toolchain-drift', 'toolchain changed after freeze')
    guard(observed('mapping-drift', lambda: sha256((PRIVATE / 'salt').read_bytes())) == manifest['salt_sha256']
          and observed('mapping-drift', lambda: sha256((PRIVATE / 'mapping.json').read_bytes())) == manifest['mapping_sha256'],
          'mapping-drift', 'opaque mapping changed after freeze')
    guard(order_digest(observed('mapping-drift', lambda: private_order(manifest))) == manifest['order_sha256'],
          'order-drift', 'private round order changed')
    return manifest


def gh(*args):
    proc = subprocess.run(['gh', *args], cwd=REPO, capture_output=True, text=True)
    require(proc.returncode == 0, f'gh {" ".join(args)} failed: {proc.stderr.strip()}')
    return proc.stdout


def timeline_intact(timeline, freeze_head):
    committed = [item for item in timeline if item.get('event') == 'committed']
    return (len(committed) == 1 and committed[0].get('sha') == freeze_head
            and not any(item.get('event') in ('head_ref_force_pushed', 'head_ref_restored',
                                             'head_ref_deleted', 'head_ref_changed') for item in timeline))


def witness(pr, *, observation, first_started=None):
    manifest = frozen(calls=False)
    head = git(REPO, 'rev-parse', 'HEAD')
    view_raw = gh('pr', 'view', str(pr), '--json', 'headRefOid,headRefName,createdAt,commits')
    view = json.loads(view_raw)
    branch = view['headRefName']
    remote_raw = git(REPO, 'ls-remote', 'origin', 'refs/heads/' + branch)
    repo_name = json.loads(gh('repo', 'view', '--json', 'nameWithOwner'))['nameWithOwner']
    timeline_raw = gh('api', f'repos/{repo_name}/issues/{pr}/timeline', '--paginate', '--slurp',
                      '-H', 'Accept: application/vnd.github+json')
    timeline = [item for page in json.loads(timeline_raw) for item in page]
    previous = load(ROOT / 'witness.json') if (ROOT / 'witness.json').is_file() else None
    require(previous is None or previous['pr'] == pr, 'witness PR number changed')
    freeze_head = previous['freeze_head'] if previous else head
    started = first_started or (previous or {}).get('first_started')
    record = {'checked_at': now(), 'observation': observation, 'pr': pr, 'head': view['headRefOid'],
              'freeze_head': freeze_head, 'local_head': head, 'first_started': started,
              'branch': branch, 'view': view_raw, 'timeline': timeline_raw, 'ls_remote': remote_raw,
              'manifest_sha256': sha256((ROOT / 'manifest.json').read_bytes()),
              'candidate_tree': manifest['candidate_tree']}
    with (ROOT / 'witness.jsonl').open('a', encoding='utf-8') as handle:
        handle.write(json.dumps(record, sort_keys=True) + '\n')
    require(view['headRefOid'] == freeze_head and remote_raw.split()[0] == freeze_head,
            'PR head or origin branch differs from the freeze commit')
    require([item.get('oid') for item in view['commits']] == [freeze_head]
            and git(REPO, 'merge-base', 'main', freeze_head) == git(REPO, 'rev-parse', freeze_head + '^'),
            'PR must contain exactly the freeze commit')
    require(timeline_intact(timeline, freeze_head), 'PR timeline records a head change')
    if started:
        require(view['createdAt'] < started, 'PR was created after the first seat started')
    dump(ROOT / 'witness.json', record)
    return record


@contextmanager
def sealed(tok, repo):
    """Expose only this round, its HOME, the candidate, shims and its toolchain."""
    hidden = [p for p in ROOT.iterdir() if p.name not in ('rounds', 'homes', 'bin', 'product', 'toolchains')]
    hidden += [p for folder in ('rounds', 'homes') for p in (ROOT / folder).iterdir() if p.name != tok]
    hidden += [p for p in (ROOT / 'toolchains').iterdir() if p.name != repo]
    search = [ROOT, ROOT / 'rounds', ROOT / 'homes', ROOT / 'toolchains']
    modes = {p: stat.S_IMODE(p.lstat().st_mode) for p in hidden + search}
    try:
        for path in hidden:
            path.chmod(0)
        for path in search:
            path.chmod(0o100)
        yield
    finally:
        for path in search + hidden:
            path.chmod(modes[path])


def forward(signum, _frame):
    STOP.append(signum)
    if CHILD and CHILD[0].poll() is None:
        CHILD[0].send_signal(signal.SIGTERM)


def cli_lines(stderr, engine, prompt=None):
    if engine == 'claude':
        return [line for line in stderr.splitlines() if re.match(r'^\[claude-code:[^]]+\]', line)]
    _, separator, stream = stderr.partition('\nuser\n')
    if separator and prompt is not None and stream.startswith(prompt):
        stderr = stderr[:len(stderr) - len(stream)] + stream[len(prompt):]
    return stderr.splitlines()


def classify_infra(seats):
    """Pure frozen classifier. Callers pass no judge-authored result text."""
    patterns = (
        ('usage/rate-limit', re.compile(r'(?i)(?:\b429\b|usage limit|rate limit)')),
        ('capacity/overloaded', re.compile(r'(?i)(?:\b5\d\d\b|at capacity|overloaded)')),
        ('network', re.compile(r'(?i)(?:stream disconnected|ECONNRESET|ENOTFOUND|ETIMEDOUT|network error)')),
        ('authentication', re.compile(r'(?i)(?:\b401\b|\b403\b|login|Unauthorized)')),
    )
    classes = set()
    for seat in seats:
        carrier = seat.get('carrier') or {}
        if carrier.get('outcome') == 'exited' and carrier.get('exit_code') == 0:
            continue
        envelope = seat.get('envelope') or {}
        engine = seat.get('engine', 'codex')
        parts = cli_lines(seat.get('stderr', ''), engine, seat.get('prompt'))
        if engine == 'claude':
            parts += [str(envelope.get(k, '')) for k in ('is_error', 'api_error_status', 'terminal_reason')]
        text = '\n'.join(parts)
        for kind, pattern in patterns:
            if pattern.search(text):
                classes.add(kind)
        exit_code = carrier.get('exit_code')
        if carrier.get('outcome') == 'exited' and isinstance(exit_code, int) and (
                exit_code < 0 or 129 <= exit_code <= 159):
            classes.add('cli-binary-crash')
    return sorted(classes)


def load_envelope(path):
    if not path.is_file() or not path.stat().st_size:
        return {}
    try:
        value = load(path)
    except (ValueError, UnicodeError):
        return {}
    return value if isinstance(value, dict) else {}


def stop_round(tok, classes):
    classes = sorted(set(classes))
    guard(classes and set(classes) <= FIX_CLASSES | {'affected-bundle'}, 'driver-error',
          f'{tok}: unregistered stop class: {classes}')
    stops = ROOT / 'stops.jsonl'
    count = 1 + sum(1 for line in stops.read_text().splitlines() if json.loads(line)['token'] == tok) if stops.exists() else 1
    missing = [folder for folder in ('rounds', 'homes') if not (ROOT / folder / tok).exists()]
    with stops.open('a', encoding='utf-8') as handle:
        handle.write(json.dumps({'token': tok, 'class': classes[0], 'classes': classes,
                                 'missing': missing, 'time': now(), 'stop': count}, sort_keys=True) + '\n')
    return ROOT / 'rounds' / tok


def final_fault(tok, classes, message):
    classes = sorted(set(classes))
    dump(ROOT / 'rounds' / tok / f'{tok}.driver-error.json',
         {'classes': classes, 'message': message, 'time': now()})
    with (ROOT / 'stops.jsonl').open('a', encoding='utf-8') as handle:
        handle.write(json.dumps({'token': tok, 'class': classes[0], 'classes': classes,
                                 'final': True, 'time': now()}, sort_keys=True) + '\n')


def classified(tok, folder, classes):
    dump(folder / f'{tok}.classified.json', {'classes': sorted(set(classes)), 'time': now()})


def atomic_dump(path, data):
    with tempfile.NamedTemporaryFile('w', encoding='utf-8', dir=path.parent, delete=False) as handle:
        temporary = Path(handle.name)
        json.dump(data, handle, indent=2, sort_keys=True)
        handle.write('\n')
        handle.flush()
        os.fsync(handle.fileno())
    try:
        os.replace(temporary, path)
        descriptor = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
    finally:
        temporary.unlink(missing_ok=True)


def finish_intent(requested=None):
    path = ROOT / 'redispatch-intent.json'
    if not path.is_file():
        return
    intent = load(path)
    require(isinstance(intent['tokens'], list) and isinstance(intent.get('stop_numbers'), dict)
            and set(intent['stop_numbers']) == set(intent['tokens'])
            and all(isinstance(number, int) and number >= 0 for number in intent['stop_numbers'].values()),
            'invalid redispatch intent')
    completed = {tok for tok, number in intent['stop_numbers'].items()
                 if (ROOT / 'rounds' / f'{tok}.stop-{number}').is_dir()
                 and (ROOT / 'rounds' / tok / f'{tok}.classified.json').is_file()}
    if requested is not None and len(completed) != len(intent['tokens']):
        require(set(intent['tokens']) <= set(requested),
                'redispatch bundle is smaller than an earlier authorized bundle')
    return {**intent, 'completed': sorted(completed),
            'status': 'complete' if len(completed) == len(intent['tokens']) else 'pending'}


def verify_redispatch_audit(intent, cause_raw, audit_raw, registered, history, tokens):
    evidence_sha = sha256(json.dumps(registered, sort_keys=True).encode())
    if intent and any(row['token'] in intent['stop_numbers'] and
                      row['stop'] > intent['stop_numbers'][row['token']]
                      for row in history if 'stop' in row):
        require(sha256(cause_raw) != intent['cause_sha256'] and sha256(audit_raw) != intent['audit_sha256'],
                'replacement stop needs a new committed cause and Astra audit')
    require(json.loads(audit_raw) == {'reviewer': 'Astra', 'genuine_registered_fault': True,
                                     'cause_sha256': sha256(cause_raw), 'stop_evidence_sha256': evidence_sha,
                                     'affected_bundle': sorted(tokens)},
            'Astra audit must confirm this cause, exact stop evidence and affected bundle')
    return evidence_sha


def completed_replacements(intent, history):
    return {tok for tok in intent['completed']
            if not any(row['token'] == tok and row.get('stop', 0) > intent['stop_numbers'][tok]
                       for row in history)} if intent else set()


def transcript_attempt(tok):
    number = 1 + sum(row['token'] == tok for row in jsonl(ROOT / 'stops.jsonl'))
    return ROOT / 'transcripts' / tok / f'attempt-{number}'


def move_claude_project(tok, source=None):
    dest = transcript_attempt(tok)
    if dest.is_dir():
        return dest
    work = ROOT / 'rounds' / tok / 'work'
    project = source.parent if source else Path.home() / '.claude/projects' / ('-' + str(work).strip('/').replace('/', '-'))
    if project.is_dir():
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(project), str(dest))
    return dest


def find_claude_session(tok):
    output = ROOT / 'rounds' / tok / 'work/.devlyn/claude-judge.r0.output.json'
    session = load_envelope(output).get('session_id')
    dest = move_claude_project(tok)
    if isinstance(session, str) and not dest.is_dir():
        try:
            source = transcript(session)
        except SystemExit:
            source = None
        if source:
            dest = move_claude_project(tok, source)
    transcripts = sorted(dest.rglob('*.jsonl')) if dest.is_dir() else []
    return {'files': sorted(path for transcript_path in transcripts
                            for path in attachments(transcript_path, ROOT / 'rounds' / tok / 'work'))
            if transcripts else None,
            'transcript': [str(path) for path in transcripts],
            'sha256': {str(path): sha256(path.read_bytes()) for path in transcripts},
            'session_id': session}


def call(tok, entry):
    work = Path(entry['work'])
    devlyn = work / '.devlyn'
    guard(work.is_dir(), 'home-drift', f'{tok}: round copy missing')
    guard(observed('home-drift', lambda: digest_inventory(work)) == entry['pristine']['work_inventory']
          and observed('home-drift', lambda: digest_inventory(ROOT / 'homes' / tok)) == entry['pristine']['home_inventory'],
          'home-drift', f'{tok}: round copy or home differs from pristine bytes')
    guard(observed('account-drift', account_hashes) == load(ROOT / 'manifest.json')['accounts'],
          'account-drift', f'{tok}: account id drift')
    leftovers = sorted(p.name for p in devlyn.iterdir() if re.match(r'(claude|codex)-judge\.|verify-judge\.|verify-merge', p.name))
    guard(not leftovers, 'home-drift', f'{tok}: copy already used: {leftovers}')
    try:
        checks = preflight(tok, work, entry['repo'])
    except (SystemExit, OSError, ValueError) as exc:
        raise Fault('dispatch-drift', str(exc)) from exc
    checks.pop('prompts')
    guard(checks == {key: entry[key] for key in checks}
          and observed('dispatch-drift', lambda: round_env(tok, work, entry['repo'])) == entry['env']
          and observed('home-drift', lambda: sha256((ROOT / 'homes' / tok / '.codex/models_cache.json').read_bytes())) == entry['models_cache_sha256']
          and discovery(work) == entry['discovery'],
          'dispatch-drift', f'{tok}: input, dispatch or environment drift')
    auth = ROOT / 'homes' / tok / '.codex/auth.json'
    started, clock, code, child = now(), time.monotonic(), None, None
    stdout = stderr = b''
    error = None
    try:
        shutil.copyfile(Path.home() / '.codex/auth.json', auth)
        auth.chmod(0o400)
        with sealed(tok, entry['repo']):
            if not STOP:
                child = subprocess.Popen([sys.executable, str(SHARED / 'verify-judges.py'), '--devlyn-dir', str(devlyn)],
                                         cwd=work, env=entry['env'], stdin=subprocess.DEVNULL,
                                         stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
                CHILD.append(child)
                if STOP:
                    child.send_signal(signal.SIGTERM)
                stdout, stderr = child.communicate()
                code = child.returncode
    except (Exception, SystemExit) as exc:
        error = exc
    finally:
        CHILD.clear()
        try:
            auth.unlink(missing_ok=True)
            (work.parent / f'{tok}.driver.stdout').write_bytes(stdout)
            (work.parent / f'{tok}.driver.stderr').write_bytes(stderr)
            dump(work.parent / f'{tok}.driver.json', {'exit_code': code, 'started_at': started, 'ended_at': now(),
                                                      'wall_ms': round((time.monotonic() - clock) * 1000),
                                                      'stop_signals': list(STOP)})
        except (Exception, SystemExit) as exc:
            error = error or exc
        try:
            move_claude_project(tok)
        except (Exception, SystemExit) as exc:
            error = error or exc
    classes = []
    try:
        seats = []
        for engine in ('claude', 'codex'):
            carrier = devlyn / f'{engine}-judge.r0.prompt.transport.json'
            err = devlyn / f'{engine}-judge.r0.stderr'
            prompt = devlyn / f'{engine}-judge.r0.prompt'
            seats.append({'engine': engine, 'carrier': load(carrier) if carrier.is_file() else {},
                          'stderr': err.read_bytes().decode('utf-8', errors='replace') if err.is_file() else '',
                          'prompt': prompt.read_bytes().decode('utf-8') if prompt.is_file() else None,
                          'envelope': load_envelope(devlyn / 'claude-judge.r0.output.json') if engine == 'claude' else {}})
        classes.extend(classify_infra(seats))
        # No judge output, merged verdict or finding has been read before this point.
        instruction = find_claude_session(tok)
        dump(work.parent / f'{tok}.instructions.json', instruction)
        if instruction['files'] is None or instruction['files']:
            classes.append('instruction-load')
    except (Exception, SystemExit) as exc:
        error = error or exc
    if STOP:
        classes.append('operator-signal')
    if error:
        classes.append('driver-error')
    if not classes:
        classes = ['none']
    if set(classes) <= FIX_CLASSES:
        folder = stop_round(tok, classes)
    else:
        folder = work.parent
        if classes != ['none']:
            final_fault(tok, classes, str(error) if error else 'operator signal')
    classified(tok, folder, classes)
    return classes


def attempt(tok, entry):
    try:
        return call(tok, entry)
    except Fault as exc:
        dump(ROOT / 'fault.json', {'token': tok, 'class': exc.kind,
                                   'message': str(exc), 'time': now()})
        folder = stop_round(tok, [exc.kind])
        classified(tok, folder, [exc.kind])
        return [exc.kind]
    except (Exception, SystemExit) as exc:
        if (ROOT / 'rounds' / tok).is_dir():
            final_fault(tok, ['driver-error'], str(exc))
            classified(tok, ROOT / 'rounds' / tok, ['driver-error'])
        return ['driver-error']


def integrity():
    manifest = frozen(calls=False)
    actual = sealed_inventory()
    unchanged = actual == manifest['sealed_inputs']
    dump(ROOT / 'integrity.json', {'checked_at': now(), 'actual': actual,
                                   'expected': manifest['sealed_inputs'], 'unchanged': unchanged})
    guard(unchanged, 'sealed-input-drift', 'SEALED INPUTS CHANGED after run')


def recurred(fixes, classes):
    """A stop on any token repeats a class already covered by a committed fix."""
    return any(kind in row['classes'] for kind in set(classes) & FIX_CLASSES for row in fixes)


def ledger_recurrence():
    """Recurrence derived from the durable ledgers, never from a marker a crash could lose: a stop recorded after a
    committed fix whose registered classes it repeats."""
    fixes = jsonl(ROOT / 'fixes.jsonl')
    return [row for row in jsonl(ROOT / 'stops.jsonl')
            if any(set(row.get('classes', [row['class']])) & set(fix['classes']) & FIX_CLASSES
                   and row['time'] > fix['time'] for fix in fixes)]


def recurrence(tok, classes, cause=None):
    if recurred(jsonl(ROOT / 'fixes.jsonl'), classes):
        dump(ROOT / 'recurrence.json', {'outcome': 'NOT PASS', 'token': tok, 'classes': classes,
                                        'cause': cause, 'time': now()})
        fail(f'{tok}: fixed cause {classes} recurred; screen NOT PASS')


def charge_drift(tok, exc, cause=None):
    dump(ROOT / 'fault.json', {'token': tok, 'class': exc.kind,
                               'message': str(exc), 'time': now()})
    folder = stop_round(tok, [exc.kind])
    classified(tok, folder, [exc.kind])
    recurrence(tok, [exc.kind], cause)
    fail(f'{tok}: input drift ({exc.kind}): {exc}')


def finish_run(pr, order, tok, cause=None):
    try:
        frozen()
        first = min(load(ROOT / 'rounds' / item / f'{item}.driver.json')['started_at'] for item in order)
        witness(pr, observation='end', first_started=first)
        integrity()
    except Fault as exc:
        charge_drift(tok, exc, cause)


def run(pr):
    intent = finish_intent()
    require(not intent or intent['status'] == 'complete',
            'interrupted redispatch must resume through the audited bundle')
    manifest = None
    try:
        manifest = frozen(calls=False)
        order = observed('mapping-drift', lambda: private_order(manifest))
    except Fault as exc:
        candidates = [row['token'] for row in manifest['rounds']] if manifest else sorted(
            path.name for path in (ROOT / 'rounds').iterdir() if path.is_dir() and '.stop-' not in path.name)
        tok = next((item for item in candidates if not (ROOT / 'rounds' / item /
                   f'{item}.classified.json').is_file()), candidates[-1])
        charge_drift(tok, exc)
    require(not ledger_recurrence(), 'screen is NOT PASS after same-cause recurrence')
    history = jsonl(ROOT / 'stops.jsonl')
    require(not any(row.get('final') for row in history), 'final operator or driver fault; score this round')
    try:
        witness(pr, observation='start')
    except Fault as exc:
        tok = next((item for item in order if not (ROOT / 'rounds' / item /
                   f'{item}.classified.json').is_file()), order[-1])
        charge_drift(tok, exc)
    for signum in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP):
        signal.signal(signum, forward)
    by_token = {row['token']: row for row in manifest['rounds']}
    for number, tok in enumerate(order, 1):
        entry = by_token[tok]
        if STOP:
            fail(f'operator signal {STOP[0]} stopped run')
        folder = ROOT / 'rounds' / tok
        if (folder / f'{tok}.classified.json').exists():
            guard((folder / f'{tok}.driver.json').exists(), 'driver-error',
                  f'{tok}: classified marker without driver record')
            require(load(folder / f'{tok}.classified.json')['classes'] == ['none'],
                    f'{tok}: classified stop is final without audited redispatch')
            continue
        require(not any(row['token'] == tok for row in history),
                f'{tok}: interrupted redispatch must resume through the audited bundle')
        if (folder / f'{tok}.driver.json').exists():
            final_fault(tok, ['interrupted-classification'], 'driver record lacks classification marker')
            classified(tok, folder, ['interrupted-classification'])
            fail(f'{tok}: interrupted classification is final; score this round')
        try:
            frozen()
        except Fault as exc:
            charge_drift(tok, exc)
        classes = attempt(tok, entry)
        recurrence(tok, classes)
        driver_record = folder / f'{tok}.driver.json'
        exit_code = load(driver_record).get('exit_code') if driver_record.is_file() else 'stopped'
        print(f'[0226] round {number}/64 exit={exit_code} classes={classes}',
              file=sys.stderr, flush=True)
        require(classes == ['none'], f'{tok}: stopped for {classes}; audit required before redispatch')
    finish_run(pr, order, order[-1])


def redispatch(cause_file, audit_file, tokens):
    intent = finish_intent(tokens)
    manifest = None
    try:
        manifest = frozen(calls=False)
        order = observed('mapping-drift', lambda: private_order(manifest))
    except Fault as exc:
        charge_drift(tokens[0] if tokens else manifest['rounds'][0]['token'], exc)
    for signum in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP):
        signal.signal(signum, forward)
    require(not ledger_recurrence(), 'screen is NOT PASS; further redispatch refused')
    cause_path = Path(cause_file).resolve()
    cause_raw = committed_file(cause_path)
    cause = json.loads(cause_raw)
    require(all(isinstance(cause.get(k), str) and cause[k] for k in ('cause', 'fix', 'reasoning'))
            and isinstance(cause.get('affected_bundle'), list),
            'cause file needs cause, fix, reasoning and affected_bundle')
    require(tokens and set(tokens) == set(cause['affected_bundle']), 'tokens must equal cause affected_bundle')
    history = jsonl(ROOT / 'stops.jsonl')
    pending = {row['token'] for row in history if not (
        ROOT / 'rounds' / row['token'] / f'{row["token"]}.classified.json').is_file() or
        load(ROOT / 'rounds' / row['token'] / f'{row["token"]}.classified.json')['classes'] != ['none']}
    if intent and intent['status'] == 'pending':
        pending.update(set(intent['tokens']) - set(intent['completed']))
    require(pending, 'redispatch requires an unresolved stop')
    require(pending <= set(tokens), f'cause bundle omits stopped rounds: {sorted(pending - set(tokens))}')
    require(not any(row.get('final') for row in history), 'final stop cannot be redispatched')
    registered = [row for row in history if row['token'] in tokens and
                  set(row.get('classes', [row['class']])) <= FIX_CLASSES]
    require(registered and all(set(row.get('classes', [row['class']])) <= FIX_CLASSES | {'affected-bundle'}
                               for row in history if row['token'] in pending),
            'redispatch requires an audited registered fault; affected-bundle is not a fix class')
    require(set(tokens) <= set(order) and len(tokens) == len(set(tokens)),
            'redispatch bundle has unknown or duplicate tokens')
    for tok in tokens:
        active = ROOT / 'rounds' / tok
        if active.is_dir() and not (active / f'{tok}.classified.json').is_file() and (
                active / f'{tok}.driver.json').exists():
            final_fault(tok, ['interrupted-classification'], 'round lacks classification marker')
            classified(tok, active, ['interrupted-classification'])
            fail(f'{tok}: interrupted classification is final; score this round')
    branch = git(REPO, 'symbolic-ref', '--short', 'HEAD')
    require(git(REPO, 'ls-remote', 'origin', 'refs/heads/' + branch).split()[0] ==
            git(REPO, 'rev-parse', 'HEAD'), 'cause and Astra audit must be pushed')
    audit_raw = committed_file(audit_file)
    evidence_sha = verify_redispatch_audit(intent, cause_raw, audit_raw, registered, history, tokens)
    by_token = {row['token']: row for row in manifest['rounds']}
    with tempfile.TemporaryDirectory(prefix='restore-', dir=ROOT) as raw:
        staging = Path(raw)
        completed = completed_replacements(intent, history)
        for tok in order:
            if tok not in tokens or tok in completed:
                continue
            for suffix, destination in (('.tar', staging / 'rounds' / tok),
                                        ('.home.tar', staging / 'homes')):
                path = PRIVATE / 'pristine' / (tok + suffix)
                require(sha256(path.read_bytes()) == by_token[tok]['pristine'][suffix],
                        f'{tok}: pristine tar changed')
                destination.mkdir(parents=True, exist_ok=True)
                with tarfile.open(path) as archive:
                    archive.extractall(destination, filter='data')
            if by_token[tok]['repo'] == 'joi':
                link = staging / 'rounds' / tok / 'work/node_modules'
                require(not link.exists() and not link.is_symlink(), f'{tok}: unexpected node_modules in tar')
                link.symlink_to(ROOT / 'toolchains/joi/node_modules', target_is_directory=True)
                require(link.readlink() == ROOT / 'toolchains/joi/node_modules', f'{tok}: wrong Joi link target')
            require(digest_inventory(staging / 'rounds' / tok / 'work') ==
                    by_token[tok]['pristine']['work_inventory'] and
                    digest_inventory(staging / 'homes' / tok) == by_token[tok]['pristine']['home_inventory'],
                    f'{tok}: restored copy or home differs from pristine bytes')
        intent_path = ROOT / 'redispatch-intent.json'
        identity = {'tokens': sorted(tokens), 'cause': str(cause_path), 'cause_sha256': sha256(cause_raw),
                    'audit': str(Path(audit_file).resolve()),
                    'audit_sha256': sha256(audit_raw),
                    'stop_evidence_sha256': evidence_sha,
                    'stop_numbers': {tok: max((row['stop'] for row in history
                                               if row['token'] == tok and 'stop' in row), default=0)
                                     for tok in tokens}}
        if not intent or any(
                intent.get(key) != value for key, value in identity.items()):
            atomic_dump(intent_path, identity)
        classes = sorted({kind for row in registered for kind in row.get('classes', [row['class']])})
        if not any(row.get('cause_sha256') == sha256(cause_raw)
                   and row.get('audit_sha256') == sha256(audit_raw)
                   for row in jsonl(ROOT / 'fixes.jsonl')):
            with (ROOT / 'fixes.jsonl').open('a', encoding='utf-8') as handle:
                handle.write(json.dumps({'classes': classes, 'cause': str(cause_path),
                                         'audit': str(Path(audit_file).resolve()),
                                         'cause_sha256': sha256(cause_raw), 'audit_sha256': sha256(audit_raw),
                                         'tokens': sorted(tokens), 'time': now()}, sort_keys=True) + '\n')
        for number, tok in enumerate([item for item in order if item in tokens], 1):
            if tok in completed:
                continue
            for folder in ('rounds', 'homes'):
                active = ROOT / folder / tok
                if active.exists():
                    active.rename(active.with_name(f'{tok}.stop-{identity["stop_numbers"][tok]}'))
            (staging / 'rounds' / tok).rename(ROOT / 'rounds' / tok)
            (staging / 'homes' / tok).rename(ROOT / 'homes' / tok)
            try:
                if number == 1:
                    witness(load(ROOT / 'witness.json')['pr'], observation='start')
                frozen()
            except Fault as exc:
                charge_drift(tok, exc, str(cause_path))
            except (SystemExit, OSError, ValueError) as exc:
                final_fault(tok, ['driver-error'], str(exc))
                classified(tok, ROOT / 'rounds' / tok, ['driver-error'])
                fail(f'{tok}: witness check failed: {exc}')
            outcome = attempt(tok, by_token[tok])
            recurrence(tok, outcome, str(cause_path))
            print(f'[0226] redispatch round {number}/{len(tokens)} classes={outcome}',
                  file=sys.stderr, flush=True)
            require(outcome == ['none'], f'{tok}: redispatch stopped for {outcome}')
    tok = [item for item in order if item in tokens][-1]
    try:
        frozen()
    except Fault as exc:
        charge_drift(tok, exc, str(cause_path))
    if all((ROOT / 'rounds' / tok / f'{tok}.classified.json').exists() for tok in order):
        finish_run(load(ROOT / 'witness.json')['pr'], order, tok, str(cause_path))


def score_ready():
    intent = finish_intent()
    require(not intent or intent['status'] == 'complete', 'redispatch has incomplete replacement rounds')
    manifest = frozen(calls=False)
    require(sealed_inventory() == manifest['sealed_inputs'], 'sealed inputs changed after freeze')
    return manifest


def jsonl(path):
    return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()] if path.is_file() else []


def canon(row):
    return json.dumps({k: v for k, v in row.items() if k != 'source'}, sort_keys=True)


def excluded_path(raw, cwd, work, repo):
    if any(char in raw for char in '{}*?[]$`~'):
        raise ValueError(f'ambiguous shell path: {raw}')
    path = Path(raw)
    path = (path if path.is_absolute() else cwd / path).resolve()
    allowed = (work, ROOT / 'product', ROOT / 'bin', ROOT / 'toolchains' / repo)
    if any(path.is_relative_to(folder) for folder in allowed):
        return None
    targets = (ROOT, REPO, Path.home() / '.claude/projects')
    if any(path.is_relative_to(target) for target in targets):
        return str(path)
    if any(target.is_relative_to(path) for target in targets):
        raise ValueError(f'ancestor of an excluded area: {path}')
    return None


def shell_expands(command):
    """True when the shell could expand part of this command (a `$` or backtick outside single quotes, or a glob,
    brace or tilde outside any quotes). Such commands go to adjudication whole; their literal words are still scanned."""
    quote, escaped = None, False
    for char in command:
        if escaped:
            escaped = False
            continue
        if char == '\\' and quote != "'":
            escaped = True
        elif quote == "'":
            quote = None if char == "'" else quote
        elif char in '$`':
            return True
        elif quote == '"':
            quote = None if char == '"' else quote
        elif char in '\'"':
            quote = char
        elif char in '{}*?[]~':
            return True
    return False


def codex_exec_paths(stderr, prompt=None):
    _, separator, stream = stderr.partition('\nuser\n')
    if separator and prompt is not None and stream.startswith(prompt):
        stream = stream[len(prompt):]
    lines = (stream if separator else stderr).splitlines()
    paths, ambiguous = [], []
    index = 0
    status = re.compile(r'^ (?:succeeded in|exited -?\d+ in|failed in|declined)')
    while index < len(lines):
        if lines[index] != 'exec':
            index += 1
            continue
        start = index + 1
        end = next((pos for pos in range(start + 1, len(lines)) if status.match(lines[pos])
                    and re.search(r' in /\S+$', lines[pos - 1])), None)
        if end is None:
            ambiguous.append('\n'.join(lines[start:]))
            break
        raw = '\n'.join(lines[start:end])
        index = end + 1
        try:
            match = re.fullmatch(r'(?s)(.*) in (/\S+)', raw)
            if not match:
                raise ValueError('missing command or cwd')
            outer = shlex.split(match[1])
            if '-lc' not in outer or outer.index('-lc') + 1 >= len(outer):
                raise ValueError('missing -lc script')
            command = outer[outer.index('-lc') + 1]
            if any(char in match[2] for char in '{}*?[]$`~'):
                raise ValueError('ambiguous cwd')
            cwd = Path(match[2]).resolve()
            block_paths = [(str(cwd), cwd)]
            lexer = shlex.shlex(command, posix=True, punctuation_chars=';&|()<>')
            lexer.whitespace_split = True
            lexer.commenters = ''
            words = list(lexer)
            # Shell semantics cannot be recovered statically; every candidate is only a lead for adjudication, and a
            # block whose meaning depends on expansion, continuation, subshells or directory changes goes whole.
            if (shell_expands(command) or '\\\n' in command or '(' in words or ')' in words
                    or any(word in ('cd', 'pushd', 'popd') for word in words)):
                ambiguous.append(raw)
            for word in words:
                if word.startswith('-') and '=' not in word:
                    body = word.lstrip('-')
                    # An attached option value can start after any option letter (`-fsrc/…`, `-nf/…`).
                    block_paths.extend((body[start:], cwd) for start in range(len(body))
                                       if '/' in body[start:] or body[start:] in ('.', '..'))
                    continue
                value = word.split('=', 1)[-1]
                block_paths.append((value, cwd))
                for embedded in re.findall(r'(?<![A-Za-z0-9])/(?:[^\s"\'`|;&()<>]+)', value):
                    if embedded != value:
                        block_paths.append((embedded, cwd))
            paths.extend(block_paths)
        except ValueError:
            ambiguous.append(raw)
    return paths, ambiguous


def read_scan(tok):
    """Read only tool inputs, never authored finding prose or the Claude result."""
    work = ROOT / 'rounds' / tok / 'work'
    entry = next(row for row in load(ROOT / 'manifest.json')['rounds'] if row['token'] == tok)
    outside, ambiguous = set(), []

    def check_path(raw, cwd, strong=True):
        try:
            found = excluded_path(raw, cwd, work, entry['repo'])
        except ValueError:
            ambiguous.append(raw)
        else:
            if found and strong:
                outside.add(found)
            elif found:
                ambiguous.append(raw)

    marker = ROOT / 'rounds' / tok / f'{tok}.classified.json'
    number = sum(row['token'] == tok for row in jsonl(ROOT / 'stops.jsonl'))
    number += marker.is_file() and load(marker)['classes'] == ['none']
    transcript_path = ROOT / 'transcripts' / tok / f'attempt-{number}'
    for session_path in transcript_path.rglob('*.jsonl'):
        for line in session_path.read_text(encoding='utf-8').splitlines():
            message = json.loads(line).get('message') or {}
            for block in message.get('content', []) if isinstance(message, dict) else []:
                if not isinstance(block, dict) or block.get('type') != 'tool_use' or block.get('name') not in ('Read', 'Grep', 'Glob'):
                    continue
                inputs = block.get('input') or {}
                for raw in (inputs.get(key) for key in ('file_path', 'path')) if isinstance(inputs, dict) else ():
                    if isinstance(raw, str):
                        check_path(raw, work)
    stem = next(seat['stem'] for seat in entry['seats'].values() if seat['engine'] == 'codex')
    stderr = work / '.devlyn' / (stem + '.stderr')
    if not stderr.is_file():
        return sorted(outside), ambiguous + ['<Codex stderr missing>']
    try:
        prompt_path = stderr.with_name(stem + '.prompt')
        prompt = prompt_path.read_bytes().decode('utf-8') if prompt_path.is_file() else None
        paths, unparsed = codex_exec_paths(stderr.read_bytes().decode('utf-8'), prompt)
    except (OSError, UnicodeError):
        return sorted(outside), ambiguous + ['<Codex stderr unreadable>']
    ambiguous.extend(unparsed)
    for raw, cwd in paths:
        check_path(raw, cwd, strong=False)  # a Codex shell word is never a definite read: adjudicate its hits
    return sorted(outside), ambiguous


def facts(entry):
    tok = entry['token']
    work = Path(entry['work'])
    devlyn = work / '.devlyn'
    try:
        state = load(devlyn / 'pipeline.state.json')
    except (OSError, ValueError):
        state = {}
    verify = (state.get('phases') or {}).get('verify') or {}
    record = load(devlyn / 'verify-judge.r0.dispatch.json') if (devlyn / 'verify-judge.r0.dispatch.json').is_file() else {}
    merged = jsonl(devlyn / 'verify-merged.findings.jsonl')
    code = modules()
    salt = (PRIVATE / 'salt').read_bytes()
    findings = []
    seats = {}
    seat_rows = set()
    for role, seat in entry['seats'].items():
        stem = seat['stem']
        carrier_path = devlyn / f'{stem}.prompt.transport.json'
        carrier = load(carrier_path) if carrier_path.is_file() else {}
        try:
            authenticated = code['auth']['authenticate'](devlyn, state, role) == (
                verify.get('role_evidence') or {}).get(role)
        except (IndexError, KeyError, OSError, TypeError, UnicodeError, ValueError, SystemExit):
            authenticated = False
        parsed, summary = [], {}
        if authenticated:
            try:
                parsed, summary = code['parser']['collect_judge'](devlyn / (stem + '.stdout'))
            except (SystemExit, OSError, UnicodeError, ValueError) as exc:
                summary = {'verdict': None, 'error': str(exc)}
                authenticated = False
        source = 'judge' if role == 'primary_judge' else 'pair_judge'
        seat_rows.update(canon(row) for row in parsed)
        accepted = authenticated and all(any(canon(row) == canon(other)
                                             for other in merged) for row in parsed) and (
                                                 devlyn / 'verify-merged.findings.jsonl').is_file() and (
                                                 devlyn / ('verify.findings.jsonl' if source == 'judge'
                                                           else 'verify.pair.findings.jsonl')).is_file() and (
                                                 verify.get('sub_verdicts') or {}).get(source) is not None
        for index, row in enumerate(parsed):
            rank = code['parser']['finding_rank'](row)
            if rank >= 1:
                findings.append({'finding_key': sha256(salt + f'{tok}|{role}|{index}'.encode()), 'seat': role,
                                 'index': index, 'rank': rank, 'accepted_by_merge': accepted,
                                 **{key: row.get(key) for key in ('severity', 'verdict_binding', 'rule_id',
                                                                 'file', 'line', 'message', 'id')}})
        seats[role] = {'carrier': {key: carrier.get(key) for key in
                                   ('outcome', 'exit_code', 'started_at', 'ended_at', 'elapsed_ms')},
                       'completed': carrier.get('outcome') == 'exited' and carrier.get('exit_code') == 0,
                       'authenticated': authenticated, 'accepted_by_merge': accepted,
                       'verdict': summary.get('verdict'),
                       'model_observed': ((verify.get('role_evidence') or {}).get(role) or {}).get('model_observed'),
                       'effort_observed': ((verify.get('role_evidence') or {}).get(role) or {}).get('effort_observed'),
                       'requested_effort': seat['requested_effort'], 'dispatched_effort': seat['effort']}
    harness = [row for row in merged if canon(row) not in seat_rows]
    driver_path = work.parent / f'{tok}.driver.json'
    driver = load(driver_path) if driver_path.is_file() else {}
    stops = [line for name in (f'{tok}.driver.stdout', f'{tok}.driver.stderr')
             if (work.parent / name).is_file()
             for line in (work.parent / name).read_text(errors='replace').splitlines() if 'BLOCKED' in line]
    text = lambda row: ' '.join(str(row.get(k, '')) for k in ('id', 'rule_id', 'message'))
    instr_path = work.parent / f'{tok}.instructions.json'
    instruction = load(instr_path) if instr_path.is_file() else {'files': None, 'transcript': None}
    envelope_path = devlyn / 'claude-judge.r0.output.json'
    envelope = load_envelope(envelope_path)
    counters = ('input_tokens', 'cache_creation_input_tokens', 'cache_read_input_tokens', 'output_tokens')
    usage = {'claude': {'status': 'COMPLETE' if
                       all(isinstance((envelope.get('usage') or {}).get(key), int) for key in counters) else 'UNKNOWN',
                       'usage': envelope.get('usage'),
                       'model_usage': envelope.get('modelUsage')},
             'codex': {'status': 'UNKNOWN', 'total_tokens': None, 'output_tokens': 'UNKNOWN'}}
    codex_stderr = devlyn / 'codex-judge.r0.stderr'
    if codex_stderr.is_file():
        tokens = re.findall(rb'tokens used\n([\d,]+)', codex_stderr.read_bytes())
        if tokens:
            usage['codex'].update(status='PARTIAL', total_tokens=int(tokens[-1].replace(b',', b'')))
    carriers = [seat['carrier'] for seat in seats.values()]
    stamps = [carrier.get(key) for carrier in carriers for key in ('started_at', 'ended_at')]
    outside_paths, ambiguous = read_scan(tok)
    all_tokens = [row['token'] for row in load(ROOT / 'manifest.json')['rounds']]
    ambiguous_reads = [{'id': sha256(f'{tok}|{index}|{raw}'.encode()),
                        'read': mask_rounds(raw, all_tokens)}
                       for index, raw in enumerate(ambiguous)]
    marker = work.parent / f'{tok}.classified.json'
    classifications = load(marker).get('classes', []) if marker.is_file() else ['unclassified']
    return {'token': tok, 'exit_code': driver.get('exit_code'), 'wall_ms': driver.get('wall_ms'),
            'verdict': verify.get('verdict'), 'sub_verdicts': verify.get('sub_verdicts'),
            'snapshot_matches': record.get('snapshot_sha256') == entry['snapshot_sha256'],
            'resolution_matches': record.get('resolution_sha256') == entry['resolution_sha256'],
            'argv_matches': {role: (devlyn / (seat['stem'] + '.argv.json')).is_file() and
                             sha256((devlyn / (seat['stem'] + '.argv.json')).read_bytes()) == seat['argv_sha256']
                             for role, seat in entry['seats'].items()},
            'decisions': {role: item.get('decision') for role, item in record.get('roles', {}).items()},
            'pair_trigger': record.get('pair_trigger'), 'seats': seats,
            'overlap': len(stamps) == 4 and all(isinstance(s, str) for s in stamps)
            and min(carrier['ended_at'] for carrier in carriers) > max(carrier['started_at'] for carrier in carriers),
            'findings': findings, 'harness_rows': harness, 'stops': stops,
            'input_flags': [text(row) for row in merged if any(tag in text(row) for tag in INPUT_BLOCKERS)]
            + [line for line in stops if any(tag in line for tag in INPUT_BLOCKERS)],
            'instructions': instruction, 'outside_paths': outside_paths,
            'ambiguous_reads': ambiguous_reads, 'classes': classifications, 'usage': usage}


def score():
    manifest = score_ready()
    witness(load(ROOT / 'witness.json')['pr'], observation='score')
    rows = [facts(entry) for entry in manifest['rounds']]
    require(not any(tok in read['read'] for row in rows for read in row['ambiguous_reads']
                    for tok in (item['token'] for item in manifest['rounds'])),
            'round token leaked into ambiguous reads')
    dump(PRIVATE / 'score.json', {'scored_at': now(), 'rounds': rows,
                                  'ambiguous_reads': [read for row in rows for read in row['ambiguous_reads']]})
    print(f'[0226] scored {len(rows)} rounds')


def mask_rounds(value, tokens):
    for tok in tokens:
        value = value.replace(str(ROOT / 'rounds' / tok), '<round>')
        value = re.sub(r'rs-[A-Za-z0-9-]+-' + re.escape(tok), '<round>', value)
        value = value.replace(tok, '<round>')
    return value


def pool():
    score_ready()
    rows = load(PRIVATE / 'score.json')['rounds']
    mapping = load(PRIVATE / 'mapping.json')['tokens']
    salt = (PRIVATE / 'salt').read_bytes()
    pooled, keys = [], {}
    for row in rows:
        task = mapping[row['token']].split('|')[0]
        for finding in row['findings']:
            key = finding['finding_key']
            keys[key] = {'token': row['token'], 'seat': finding['seat'], 'index': finding['index']}
            fields = {field: finding.get(field) for field in
                      ('rank', 'severity', 'verdict_binding', 'rule_id', 'file', 'line', 'message')}
            for field in ('file', 'message'):
                if isinstance(fields[field], str):
                    fields[field] = mask_rounds(fields[field], mapping)
            pooled.append({'finding_key': key, 'task': task, **fields})
    pooled.sort(key=lambda row: sha256(salt + row['finding_key'].encode()))
    path = PRIVATE / 'pool.jsonl'
    raw = ''.join(json.dumps(row, sort_keys=True) + '\n' for row in pooled)
    require(not any(tok in raw for tok in mapping), 'round token leaked into masked pool')
    path.write_text(raw, encoding='utf-8')
    dump(PRIVATE / 'pool-map.json', keys)
    print(f'[0226] pooled {len(pooled)} findings')


def check(task, key, script):
    score_ready()
    pool_map = load(PRIVATE / 'pool-map.json')
    require(key in pool_map, f'finding key not in pool: {key}')
    mapped_task = load(PRIVATE / 'mapping.json')['tokens'][pool_map[key]['token']].split('|')[0]
    require(task == mapped_task, f'finding {key} belongs to {mapped_task}, not {task}')
    script = Path(script).resolve()
    require(script.is_relative_to(REPO) and script.is_file() and os.access(script, os.X_OK),
            'check script must be executable in the research repository')
    salt = (PRIVATE / 'salt').read_bytes()
    results = {}
    _corpus, info, _repo = source_data(task)
    scratch = ROOT / 'check-work'
    scratch.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=key + '-', dir=scratch) as raw:
        for variant in ('base', 'reference', 'twin'):
            work = Path(raw) / variant
            materialize(key, task, variant, 'claude', slug(salt, task), work, apparatus=False)
            env = round_env(key, work, info['repo'])
            proc = subprocess.run([str(script), str(work)], cwd=work, env=env, capture_output=True, text=True)
            results[variant] = proc.returncode == 0
    path = PRIVATE / 'checks' / f'{key}.jsonl'
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('a', encoding='utf-8') as handle:
        handle.write(json.dumps({'task': task, 'finding_key': key,
                                 'script': str(script.relative_to(REPO)),
                                 'script_sha256': sha256(script.read_bytes()),
                                 'results': results, 'checked_at': now()}, sort_keys=True) + '\n')
    print(f'[0226] check {key}: {results}')


def evaluate(rows, labels, mapping, *, reads=None, recurrence=False):
    """Frozen registered outcome, independent of filesystem and labels' author."""
    violations = {str(i): [] for i in range(1, 7)}
    events = []
    hits = set()
    false_alarms = set()
    extras = set()
    invalid_refs = set()
    for row in rows:
        tok = row['token']
        task, variant, orientation, rep = mapping[tok].split('|')
        round_events = []
        for finding in row['findings']:
            key = finding['finding_key']
            label = labels[key]
            rank = finding['rank']
            if label['kind'] == 'coverage':
                kind = 'coverage-neutral'
            elif rank < 2:
                kind = 'detection' if label['match'] and variant == 'twin' else 'rank-one-extra'
                if label.get('disputed'):
                    extras.add(key)
            elif (variant == 'twin' and label['match'] and finding['accepted_by_merge']
                  and row['verdict'] == 'NEEDS_WORK'):
                kind = 'hit'
                hits.add((task, orientation, rep))
            else:
                result = label['results']
                require(isinstance(result, dict) and set(result) == {'base', 'reference', 'twin'}
                        and all(type(value) is bool for value in result.values()),
                        f'{key}: rank-two behavioral result must contain base/reference/twin booleans')
                own = result[variant]
                if own:
                    kind = 'false-alarm' if variant == 'reference' else 'unsupported-extra'
                elif label['clause_source'] == 'existing_test' and not result['base']:
                    kind = 'pre-existing'
                elif not result['reference']:
                    kind = 'invalid-reference'
                else:
                    kind = 'twin-only-extra'
                if kind == 'false-alarm':
                    false_alarms.add(tok)
                elif kind == 'unsupported-extra':
                    extras.add(key)
                elif kind == 'invalid-reference':
                    invalid_refs.add(key)
            round_events.append(kind)
            events.append({'token': tok, 'finding_key': key, 'classification': kind})
        if variant == 'reference' and row['verdict'] == 'NEEDS_WORK' and not any(
                event in ('coverage-neutral', 'pre-existing', 'invalid-reference')
                and row['findings'][idx]['rank'] == 2 for idx, event in enumerate(round_events)):
            false_alarms.add(tok)
            events.append({'token': tok, 'finding_key': None, 'classification': 'unsupported-terminal'})
        if row['verdict'] in (None, 'BLOCKED'):
            violations['5'].append(f'{tok}: merged verdict {row["verdict"]}')
        if row.get('exit_code') != 0 or row.get('input_flags'):
            violations['5'].append(f'{tok}: driver exit or input BLOCKED')
        if row.get('classes') and row['classes'] != ['none']:
            violations['5'].append(f'{tok}: stopped or unclassified round {row["classes"]}')
        for role, seat in row['seats'].items():
            if not all(seat.get(field) for field in ('completed', 'authenticated', 'accepted_by_merge')):
                violations['5'].append(f'{tok}: {role} incomplete, unauthenticated or rejected by merge')
        if (not row.get('overlap') or row.get('outside_paths')
                or any((reads or {}).get(read['id'], {}).get('verdict') != 'allowed'
                       or (reads or {}).get(read['id'], {}).get('disputed')
                       for read in row.get('ambiguous_reads', []))
                or (row.get('instructions') or {}).get('files') != []
                or not row.get('snapshot_matches') or not row.get('resolution_matches')
                or not all(row.get('argv_matches', {}).values())):
            violations['6'].append(f'{tok}: overlap, read, instruction or frozen-input violation')
    expected = {(task, orientation, str(rep)) for task in sorted({rid.split('|')[0] for rid in mapping.values()})
                for orientation in ('claude', 'codex') for rep in (1, 2)}
    violations['1'] = [f'missing target hit {item}' for item in sorted(expected - hits)]
    violations['2'] = [f'false alarm {tok}' for tok in sorted(false_alarms)]
    violations['3'] = [f'unsupported extra {key}' for key in sorted(extras)]
    violations['4'] = [f'invalid reference {key}' for key in sorted(invalid_refs)]
    if recurrence:
        violations['5'].append('same infra cause recurred after redispatch')
    failed = {number: details for number, details in violations.items() if details}
    return {'outcome': 'PASS' if not failed else 'NOT PASS', 'violated_conditions': failed,
            'events': events, 'hits': len(hits), 'reference_false_alarms': len(false_alarms),
            'unsupported_extras': len(extras), 'invalid_references': len(invalid_refs)}


def committed_file(path):
    path = Path(path).resolve()
    require(path.is_relative_to(REPO) and path.is_file(), f'file absent from research repository: {path}')
    raw = git_raw(REPO, 'show', f'HEAD:{path.relative_to(REPO)}')
    require(raw == path.read_bytes(), f'file is not committed byte for byte: {path}')
    return raw


def resolve_dispute(label):
    if label['disputed']:
        label['kind'] = 'behavioral'
        label['match'] = False
        label['results'] = {'base': True, 'reference': True, 'twin': True}


def bind_audit(labels, reads, audit, pool_map, mapping):
    require(isinstance(audit, dict) and audit.get('reviewer') == 'Astra'
            and isinstance(audit.get('labels'), dict) and isinstance(audit.get('reads'), dict)
            and set(audit['labels']) == set(labels) and set(audit['reads']) == set(reads),
            'audit.json must give Astra verdicts for every label and ambiguous read id')
    for key, label in labels.items():
        variant = mapping[pool_map[key]['token']].split('|')[1]
        result = label['results']
        expected = {'kind': label['kind'], 'match': label['match'],
                    'clause_source': label['clause_source'],
                    'reproduced_on_own_tree': not result[variant] if result is not None else None}
        label['disputed'] |= audit['labels'][key] != expected
    for key, read in reads.items():
        read['disputed'] = read.get('disputed', False) or audit['reads'][key] != read['verdict']


def join():
    score_ready()
    witness(load(ROOT / 'witness.json')['pr'], observation='join')
    branch = git(REPO, 'symbolic-ref', '--short', 'HEAD')
    require(git(REPO, 'ls-remote', 'origin', 'refs/heads/' + branch).split()[0] ==
            git(REPO, 'rev-parse', 'HEAD'), 'labels and checks have not been pushed')
    labels_raw = committed_file(HERE / 'labels.json')
    committed_file(HERE / 'labels-audit.md')
    audit_raw = committed_file(HERE / 'audit.json')
    reads_raw = committed_file(HERE / 'reads.json')
    read_entries = json.loads(reads_raw)
    require(isinstance(read_entries, list), 'reads.json must be a list')
    require(all(isinstance(read, dict) and set(read) in ({'id', 'verdict', 'reason'},
                                                      {'id', 'verdict', 'reason', 'disputed'})
                and isinstance(read['id'], str) and re.fullmatch(r'[0-9a-f]{64}', read['id'])
                and read['verdict'] in ('allowed', 'excluded')
                and isinstance(read['reason'], str) and read['reason'].strip()
                and (not 'disputed' in read or type(read['disputed']) is bool)
                for read in read_entries), 'reads.json has an invalid read adjudication')
    reads = {read['id']: read for read in read_entries}
    require(len(reads) == len(read_entries), 'reads.json has duplicate ids')
    labels = json.loads(labels_raw)
    audit = json.loads(audit_raw)
    pool_rows = jsonl(PRIVATE / 'pool.jsonl')
    pool_map = load(PRIVATE / 'pool-map.json')
    mapping = load(PRIVATE / 'mapping.json')['tokens']
    keys = {row['finding_key'] for row in pool_rows}
    require(set(labels) == keys, 'labels.json keys do not equal the masked pool keys')
    checks_digest = {}
    for private_log in sorted((PRIVATE / 'checks').glob('*.jsonl')) if (PRIVATE / 'checks').exists() else []:
        committed_log = committed_file(HERE / 'checks' / private_log.name)
        require(committed_log == private_log.read_bytes(), f'{private_log.name}: check log differs')
        checks_digest[str((HERE / 'checks' / private_log.name).relative_to(REPO))] = sha256(committed_log)
    for finding in pool_rows:
        key = finding['finding_key']
        label = labels[key]
        require(isinstance(label, dict) and set(label) ==
                {'kind', 'match', 'check', 'script_sha256', 'clause_source', 'results', 'disputed'}
                and label.get('kind') in ('coverage', 'behavioral') and type(label.get('match')) is bool
                and type(label.get('disputed')) is bool and label.get('clause_source') in
                (None, 'task', 'existing_test'), f'{key}: invalid label shape')
        if label['kind'] == 'behavioral' and finding['rank'] == 2:
            check_path = label.get('check')
            require(isinstance(check_path, str) and check_path, f'{key}: rank-two behavioral label needs check')
            require(os.access(REPO / check_path, os.X_OK), f'{key}: check script is not executable')
            raw = committed_file(REPO / check_path)
            log_path = HERE / 'checks' / f'{key}.jsonl'
            committed_log = committed_file(log_path)
            require(committed_log == (PRIVATE / 'checks' / f'{key}.jsonl').read_bytes(),
                    f'{key}: committed check log differs from private log')
            record = json.loads(committed_log.splitlines()[-1])
            require(record['script'] == check_path and record['script_sha256'] == sha256(raw)
                    and label['script_sha256'] == record['script_sha256']
                    and record['results'] == label.get('results'), f'{key}: check script or result mismatch')
            checks_digest[check_path] = sha256(raw)
            checks_digest[str(log_path.relative_to(REPO))] = sha256(committed_log)
            require(label['clause_source'] in ('task', 'existing_test'), f'{key}: check needs clause source')
        else:
            require(label.get('check') is None and label.get('results') is None
                    and label.get('script_sha256') is None,
                    f'{key}: coverage/rank-one finding must not have a check')
    frozen_labels = {'labels_sha256': sha256(labels_raw), 'audit_sha256': sha256(audit_raw),
                     'reads_sha256': sha256(reads_raw), 'checks_sha256': checks_digest}
    result_path = PRIVATE / 'result.json'
    if result_path.is_file():
        previous = load(result_path)
        require(previous['frozen_labels'] == frozen_labels, 'join already ran with different labels or checks')
        print(f'[0226] join already complete: {previous["outcome"]}')
        return
    score_data = load(PRIVATE / 'score.json')
    require(score_data['ambiguous_reads'] == [read for row in score_data['rounds']
                                               for read in row.get('ambiguous_reads', [])],
            'score ambiguous reads differ from round reads')
    require(set(reads) == {read['id'] for read in score_data['ambiguous_reads']},
            'reads.json must cover every ambiguous read id exactly')
    bind_audit(labels, reads, audit, pool_map, mapping)
    for label in labels.values():
        resolve_dispute(label)
    outcome = evaluate(score_data['rounds'], labels, mapping, reads=reads,
                       recurrence=bool(ledger_recurrence()))
    dump(result_path, {**outcome, 'joined_at': now(), 'frozen_labels': frozen_labels,
                       'input_blockeds': {row['token']: row['input_flags'] for row in score_data['rounds']
                                          if row['input_flags']}})
    print(f'[0226] {outcome["outcome"]}: conditions {sorted(outcome["violated_conditions"])}')


def self_test():
    global ROOT, PRIVATE
    import copy

    salt = bytes(32)
    tasks = [f'{prefix}{n}' for prefix in ('C', 'J') for n in range(1, 5)]
    ordered = ordered_ids(tasks)
    require(len(ordered) == 64 and ordered[:16] == sorted(ordered[:16],
            key=lambda rid: sha256(f'claude-1|{rid.split("|")[0]}|{rid.split("|")[1]}'.encode())),
            'order derivation self-test failed')
    require(token(salt, 'C1|twin|claude|1') == sha256(salt + b'C1|twin|claude|1')[:12]
            and slug(salt, 'C1') == 'change-' + sha256(salt + b'C1')[:8], 'opaque identity self-test failed')
    try:
        label_scan([b'prompt C1 twin'], b'base', 'C1|twin|claude|1', ())
    except SystemExit:
        pass
    else:
        fail('label scan accepted planted labels')
    label_scan([b'MECHANICAL timing changed'], b'base', 'C1|twin|claude|1', ())
    label_scan([b'prompt twin'], b'base mentions twin', 'C1|twin|claude|1', ())
    label_scan([b'prompt C1'], b'base mentions C1', 'C1|twin|claude|1', ())
    label_scan([b'"sha256": "ab0226cd"'], b'base', 'C1|twin|claude|1', ())
    header = (f'OpenAI Codex v0.156.1\n--------\nmodel: gpt-6-astra\nworkdir: {ROOT}/rounds/tok/work\n'
              'sandbox: read-only\nsession id: fixture\nreasoning effort: high\n--------\n')
    fixture = (header + 'user\nprompt\ncodex\nexec\n'
               f'/bin/zsh -lc "cat {REPO}/AGENTS.md" in {ROOT}/rounds/tok/work\n succeeded in 1ms:\n')
    paths, unparsed = codex_exec_paths(fixture)
    require(not unparsed and any(path == str(REPO / 'AGENTS.md') for path, *_ in paths),
            'Codex exec stderr parse missed research repository')
    def scan_hit(path, cwd):
        try:
            return excluded_path(path, cwd, ROOT / 'rounds/tok/work', 'joi')
        except ValueError:
            return None
    require(any(scan_hit(path, cwd) == str(REPO / 'AGENTS.md')
                for path, cwd, *_ in codex_exec_paths(fixture.replace(
                    f'cat {REPO}/AGENTS.md" in {ROOT}/rounds/tok/work',
                    f'cat {REPO.name}/AGENTS.md" in {REPO.parent}'))[0]),
            'Codex exec relative path escaped the read scan')
    require(codex_exec_paths(fixture.replace(' in ' + str(ROOT), ' at ' + str(ROOT)))[1],
            'unparsed Codex command was lost')
    require(any('$UNKNOWN/AGENTS.md' == path for path, *_ in codex_exec_paths(
            fixture.replace(f'cat {REPO}/AGENTS.md', 'cat $UNKNOWN/AGENTS.md'))[0]),
            'dynamic Codex read was lost')
    multiline = (header + 'user\nprompt\ncodex\nexec\n'
                 '/bin/zsh -lc "nl -ba tests/test_types/test_File.py | sed -n \'35,140p\'\n'
                 f'nl -ba {REPO}/AGENTS.md | sed -n \'115,205p\'" in {ROOT}/rounds/tok/work\n'
                 ' succeeded in 0ms:\n    35 text\n')
    paths, unparsed = codex_exec_paths(multiline)
    require(not unparsed and any(path == str(REPO / 'AGENTS.md') for path, *_ in paths),
            '0225-shaped multi-line Codex exec command was not parsed')
    paths, unparsed = codex_exec_paths(fixture.replace(
        f'cat {REPO}/AGENTS.md', f"sed -n '/^def keys/,$p' {REPO}/AGENTS.md"))
    require(not unparsed and any(path == str(REPO / 'AGENTS.md') for path, *_ in paths),
            'single-quoted dollar was treated as expansion')
    attached = fixture.replace(f'cat {REPO}/AGENTS.md', f'rg -f{REPO}/AGENTS.md tests')
    paths, unparsed = codex_exec_paths(attached)
    require(not unparsed and any(excluded_path(path, cwd, ROOT / 'rounds/tok/work', 'joi') ==
                                 str(REPO / 'AGENTS.md') for path, cwd, *_ in paths),
            'attached option path escaped the read scan')
    virtual_root = Path('/virtual/research')
    virtual_work = Path('/virtual/driver/rounds/tok/work')
    relative = fixture.replace(f'cat {REPO}/AGENTS.md',
                               'rg -f../../../../research/AGENTS.md tests').replace(
                                   f'in {ROOT}/rounds/tok/work', f'in {virtual_work}')
    paths, unparsed = codex_exec_paths(relative)
    saved_root = ROOT
    try:
        ROOT = virtual_root
        require(not unparsed and any(excluded_path(path, cwd, virtual_work, 'joi') ==
                                     str(virtual_root / 'AGENTS.md') for path, cwd, *_ in paths),
                'attached relative option path escaped the read scan')
    finally:
        ROOT = saved_root
    paths, unparsed = codex_exec_paths(fixture.replace(f'cat {REPO}/AGENTS.md',
                                                     'rg -f$PWD/../../../../research/AGENTS.md tests'))
    require(unparsed, 'attached option with an expansion before its path escaped ambiguity')
    continued = fixture.replace(f'cat {REPO}/AGENTS.md', 'cat ../../../../resea\\\nrch/AGENTS.md')
    require(codex_exec_paths(continued)[1], 'a backslash-newline continuation escaped adjudication')
    prefixed = fixture.replace(f'cat {REPO}/AGENTS.md', 'rg -fsrc/../../../../../research/AGENTS.md tests').replace(
        f'in {ROOT}/rounds/tok/work', f'in {virtual_work}')
    paths, unparsed = codex_exec_paths(prefixed)
    saved_root = ROOT
    try:
        ROOT = virtual_root
        require(not unparsed and any(excluded_path(path, cwd, virtual_work, 'joi') ==
                                     str(virtual_root / 'AGENTS.md') for path, cwd, *_ in paths),
                'an attached option value with a directory prefix escaped the read scan')
    finally:
        ROOT = saved_root
    concatenated = fixture.replace(f'cat {REPO}/AGENTS.md', 'cat "."/../../../../research/AGENTS.md').replace(
        f'in {ROOT}/rounds/tok/work', f'in {virtual_work}')
    paths, unparsed = codex_exec_paths(concatenated)
    saved_root = ROOT
    try:
        ROOT = virtual_root
        require(not unparsed and any(excluded_path(path, cwd, virtual_work, 'joi') ==
                                     str(virtual_root / 'AGENTS.md') for path, cwd, *_ in paths),
                'quoted concatenation split one shell word and escaped the read scan')
    finally:
        ROOT = saved_root
    paths, unparsed = codex_exec_paths(fixture.replace(f'cat {REPO}/AGENTS.md',
                                                     'rg -f\\"$PATTERNS\\" tests'))
    require(unparsed, 'quoted attached option expansion escaped adjudication')
    try:
        excluded_path('$PATTERNS', ROOT / 'rounds/tok/work', ROOT / 'rounds/tok/work', 'joi')
    except ValueError:
        pass
    else:
        fail('quoted attached option was not ambiguous')
    for ambiguous_path in (str(REPO)[:-3] + '???/AGENTS.md', '{' + str(REPO / 'AGENTS.md') + ',other}',
                           'sub*/../../../../private/salt'):
        try:
            excluded_path(ambiguous_path, ROOT / 'rounds/tok/work', ROOT / 'rounds/tok/work', 'joi')
        except ValueError:
            pass
        else:
            fail(f'ambiguous shell path passed: {ambiguous_path}')
    try:
        excluded_path(str(REPO.parent), ROOT / 'rounds/tok/work', ROOT / 'rounds/tok/work', 'joi')
    except ValueError:
        pass
    else:
        fail('an ancestor of an excluded area must go to adjudication')
    cd_fixture = fixture.replace(f'cat {REPO}/AGENTS.md', "cd tests && sed -n '1,160p' ../src/cachetools/__init__.py")
    require(codex_exec_paths(cd_fixture)[1], 'a directory change must send its block to adjudication')
    try:
        excluded_path('//', ROOT / 'rounds/tok/work', ROOT / 'rounds/tok/work', 'joi')
    except ValueError:
        pass
    else:
        fail('a pattern resolving to an ancestor must go to adjudication, not count as a read')
    recorded = [{'event': 'committed', 'sha': 'abc123'}]
    require(timeline_intact(recorded, 'abc123') and not timeline_intact(
            recorded + [{'event': 'committed', 'sha': 'def456'}], 'abc123') and not timeline_intact(
            recorded + [{'event': 'head_ref_force_pushed'}], 'abc123'), 'witness timeline shape failed')
    tok = 'abc123def456'
    masked = mask_rounds(f'{ROOT}/rounds/{tok}/work rs-20260928T000000Z-{tok} {tok}', [tok])
    require(tok not in masked and masked.count('<round>') == 3, 'pool token redaction failed')
    with tempfile.TemporaryDirectory() as raw:
        source = Path(raw) / 'home'
        (source / '.codex').mkdir(parents=True)
        (source / '.codex/models_cache.json').write_text('{}')
        scratch = source / '.codex/tmp'
        scratch.mkdir()
        (scratch / 'codex-arg0').symlink_to('/usr/bin/true')
        shutil.rmtree(scratch)
        archive_path = Path(raw) / 'home.tar'
        with tarfile.open(archive_path, 'w') as archive:
            archive.add(source, arcname='home')
        destination = Path(raw) / 'restore'
        destination.mkdir()
        with tarfile.open(archive_path) as archive:
            archive.extractall(destination, filter='data')
        require((destination / 'home/.codex/models_cache.json').read_text() == '{}',
                'home tar did not round trip through restore filter')
    saved_root, saved_private = ROOT, PRIVATE
    try:
        with tempfile.TemporaryDirectory() as raw:
            ROOT = Path(raw)
            transcript_dir = ROOT / 'transcripts' / 'T' / 'attempt-1'
            transcript_dir.mkdir(parents=True)
            (transcript_dir / 'unknown.jsonl').write_text(json.dumps({
                'attachment': {'type': 'instructions', 'files': [{'path': '/tmp/CLAUDE.md'}]}}) + '\n')
            require(find_claude_session('T')['files'] == ['/tmp/CLAUDE.md'],
                    'sessionless transcript instruction attachment was missed')
            for tok in ('A', 'B', 'C'):
                (ROOT / 'rounds' / tok).mkdir(parents=True)
                (ROOT / 'homes' / tok).mkdir(parents=True)
            stop_round('A', ['capacity/overloaded'])
            classified('A', ROOT / 'rounds/A', ['capacity/overloaded'])
            require(all((ROOT / folder / 'A').is_dir() and not
                        (ROOT / folder / 'A.stop-1').exists() for folder in ('rounds', 'homes')),
                    'stop moved the copy before an authorized replacement')
            for folder in ('rounds', 'homes'):
                (ROOT / folder / 'A').rename(ROOT / folder / 'A.stop-1')
                (ROOT / folder / 'A').mkdir()
            for tok in ('A', 'B', 'C'):
                classified(tok, ROOT / 'rounds' / tok, ['none'])
            original = jsonl(ROOT / 'stops.jsonl')
            old_cause = b'capacity cause'
            old_audit = json.dumps({'reviewer': 'Astra', 'genuine_registered_fault': True,
                                    'cause_sha256': sha256(old_cause),
                                    'stop_evidence_sha256': sha256(json.dumps(original, sort_keys=True).encode()),
                                    'affected_bundle': ['A', 'B', 'C']}).encode()
            atomic_dump(ROOT / 'redispatch-intent.json', {
                'tokens': ['A', 'B', 'C'], 'stop_numbers': {'A': 1, 'B': 0, 'C': 0},
                'cause_sha256': sha256(old_cause), 'audit_sha256': sha256(old_audit)})
            try:
                finish_intent(['A', 'C'])
            except SystemExit:
                pass
            else:
                fail('reduced redispatch bundle was accepted')
            intent = finish_intent(['A', 'B', 'C'])
            require(intent['completed'] == ['A'] and intent['status'] == 'pending',
                    'crash after marker did not preserve completed replacement A')
            before = len(jsonl(ROOT / 'stops.jsonl'))
            require(finish_intent(['A', 'B', 'C'])['completed'] == ['A']
                    and len(jsonl(ROOT / 'stops.jsonl')) == before,
                    'restart reran or recharged a completed replacement')
            for folder in ('rounds', 'homes'):
                (ROOT / folder / 'B').rename(ROOT / folder / 'B.stop-0')
                (ROOT / folder / 'B').mkdir()
            stop_round('B', ['network'])
            classified('B', ROOT / 'rounds/B', ['network'])
            history = jsonl(ROOT / 'stops.jsonl')
            require(history[-1]['token'] == 'B' and history[-1]['classes'] == ['network']
                    and finish_intent(['A', 'B', 'C'])['completed'] == ['A', 'B'],
                    'replacement network stop lacks its own row, class or completion marker')
            require(completed_replacements(finish_intent(['A', 'B', 'C']), history) == {'A'},
                    'new audit would rerun completed A or skip stopped B')
            try:
                verify_redispatch_audit(intent, old_cause, old_audit, history, history, ['A', 'B', 'C'])
            except SystemExit:
                pass
            else:
                fail('capacity audit authorized an unaudited network replacement stop')
            new_cause = b'network cause'
            new_evidence = sha256(json.dumps(history, sort_keys=True).encode())
            stale_audit = json.dumps({'reviewer': 'Astra', 'genuine_registered_fault': True,
                                      'cause_sha256': sha256(new_cause),
                                      'stop_evidence_sha256': sha256(json.dumps(original, sort_keys=True).encode()),
                                      'affected_bundle': ['A', 'B', 'C']}).encode()
            try:
                verify_redispatch_audit(intent, new_cause, stale_audit, history, history, ['A', 'B', 'C'])
            except SystemExit:
                pass
            else:
                fail('new audit with old evidence digest authorized a network replacement stop')
            new_audit = json.dumps({'reviewer': 'Astra', 'genuine_registered_fault': True,
                                    'cause_sha256': sha256(new_cause),
                                    'stop_evidence_sha256': new_evidence,
                                    'affected_bundle': ['A', 'B', 'C']}).encode()
            require(verify_redispatch_audit(intent, new_cause, new_audit, history, history,
                                            ['A', 'B', 'C']) == new_evidence,
                    'new cause and audit did not bind replacement stop evidence')
            (ROOT / 'fixes.jsonl').write_text(json.dumps({'classes': ['network']}) + '\n')
            try:
                recurrence('B', ['network'])
            except SystemExit:
                pass
            else:
                fail('replacement stop escaped recurrence')
            (ROOT / 'fixes.jsonl').write_text(json.dumps({'classes': ['mapping-drift']}) + '\n')
            try:
                charge_drift('B', Fault('mapping-drift', 'invalid mapping'))
            except SystemExit:
                pass
            else:
                fail('mapping drift escaped its stop')
            require(load(ROOT / 'recurrence.json')['classes'] == ['mapping-drift'] and
                    load(ROOT / 'rounds/B/B.classified.json')['classes'] == ['mapping-drift'],
                    'mapping drift did not charge stop and recurrence')
    finally:
        ROOT, PRIVATE = saved_root, saved_private
    prompt = 'prompt\nERROR: 429 inside echoed prompt\n'
    terminal = header + 'user\n' + prompt + '\ncodex\nworking\n\nERROR: exceeded retry limit, last status: 429\n'
    trailer = 'tokens used\n123\n[codex-monitored] codex exited: code=1 elapsed=1s\n'
    cases = [
        (['capacity/overloaded'], {'engine': 'claude', 'stderr': '[claude-code:overloaded] at capacity'}),
        (['network'], {'stderr': 'ERROR: stream disconnected'}),
        (['authentication'], {'engine': 'claude', 'stderr': '[claude-code:auth] login required'}),
        (['cli-binary-crash'], {'carrier': {'outcome': 'exited', 'exit_code': -9}}),
        (['cli-binary-crash'], {'carrier': {'outcome': 'exited', 'exit_code': 137}}),
        (['usage/rate-limit'], {'engine': 'claude', 'envelope': {'is_error': True, 'api_error_status': 429,
                                             'terminal_reason': 'api_error'}}),
        ([], {'carrier': {'outcome': 'timed_out', 'exit_code': 124}}),
        ([], {'engine': 'claude', 'envelope': {'result': 'rate limit', 'is_error': False}}),
        ([], {'carrier': {'outcome': 'cancelled', 'exit_code': 143}}),
        (['usage/rate-limit'], {'stderr': terminal + trailer, 'prompt': prompt}),
        (['authentication'], {'stderr': 'ERROR: 401 Unauthorized\n[codex-monitored] codex exited: code=1'}),
        (['capacity/overloaded'], {'stderr': header + 'user\n' + prompt +
              '\nexec\nrecorded capacity failure: at capacity\n', 'prompt': prompt}),
        ([], {'stderr': header + 'user\n' + 'at capacity\n' +
              '\nassistant\nordinary result\n', 'prompt': 'at capacity\n'}),
        ([], {'carrier': {'outcome': 'exited', 'exit_code': 0},
              'stderr': header + 'user\n' + prompt + '\nat capacity\n', 'prompt': prompt}),
    ]
    for expected, seat in cases:
        require(classify_infra([seat]) == expected, f'infra classifier: {seat}')
    mapping, rows, labels = {}, [], {}
    for rid in ordered:
        tok = token(salt, rid)
        mapping[tok] = rid
        variant = rid.split('|')[1]
        finding_key = sha256((tok + '|primary_judge|0').encode())
        finding = {'finding_key': finding_key, 'rank': 2, 'accepted_by_merge': True}
        row = {'token': tok, 'verdict': 'NEEDS_WORK' if variant == 'twin' else 'PASS',
               'exit_code': 0, 'input_flags': [], 'findings': [finding] if variant == 'twin' else [],
               'seats': {role: {'completed': True, 'authenticated': True, 'accepted_by_merge': True}
                         for role in ('primary_judge', 'pair_judge')},
               'overlap': True, 'outside_paths': [], 'ambiguous_reads': [], 'instructions': {'files': []},
               'snapshot_matches': True, 'resolution_matches': True,
               'argv_matches': {'primary_judge': True, 'pair_judge': True}}
        rows.append(row)
        if variant == 'twin':
            labels[finding_key] = {'kind': 'behavioral', 'match': True, 'results':
                                   {'base': True, 'reference': True, 'twin': False},
                                   'clause_source': 'task'}
    clean = evaluate(rows, labels, mapping)
    require(clean['outcome'] == 'PASS' and clean['hits'] == 32, 'clean join should PASS with 32 hits')
    with tempfile.TemporaryDirectory() as raw:
        try:
            PRIVATE = Path(raw)
            for value in (None, {}, {'tokens': dict(list(mapping.items())[:-1])}):
                if value is not None:
                    dump(PRIVATE / 'mapping.json', value)
                try:
                    observed('mapping-drift', lambda: private_order({'rounds': [
                        {'token': tok} for tok in mapping]}))
                except Fault as exc:
                    require(exc.kind == 'mapping-drift', 'mapping failure escaped drift classification')
                else:
                    fail('missing, malformed or incomplete mapping passed validation')
        finally:
            PRIVATE = saved_private

    def variant_rows():
        return copy.deepcopy(rows), copy.deepcopy(labels)

    def assert_condition(number, mutate):
        test_rows, test_labels = variant_rows()
        mutate(test_rows, test_labels)
        result = evaluate(test_rows, test_labels, mapping)
        require(result['outcome'] == 'NOT PASS' and set(result['violated_conditions']) == {str(number)},
                f'condition {number} isolation failed: {result["violated_conditions"]}')

    twin = next(i for i, row in enumerate(rows) if mapping[row['token']].split('|')[1] == 'twin')
    assert_condition(1, lambda rs, ls: rs[twin]['findings'].clear())
    reference = next(i for i, row in enumerate(rows) if mapping[row['token']].split('|')[1] == 'reference')

    def add_finding(rs, ls, index, suffix, *, kind='behavioral', match=False, results=None,
                    clause_source='task'):
        key = sha256((rs[index]['token'] + suffix).encode())
        rs[index]['findings'].append({'finding_key': key, 'rank': 2, 'accepted_by_merge': True})
        ls[key] = {'kind': kind, 'match': match, 'results': results, 'clause_source': clause_source}
        return key

    def false_alarm(rs, ls):
        rs[reference]['verdict'] = 'NEEDS_WORK'
        add_finding(rs, ls, reference, 'false', results={'base': True, 'reference': True, 'twin': True})

    assert_condition(2, false_alarm)

    def unsupported(rs, ls):
        add_finding(rs, ls, twin, 'extra', results={'base': True, 'reference': True, 'twin': True})

    assert_condition(3, unsupported)

    def invalid_reference(rs, ls):
        rs[reference]['verdict'] = 'NEEDS_WORK'
        add_finding(rs, ls, reference, 'invalid', results={'base': True, 'reference': False, 'twin': False})

    assert_condition(4, invalid_reference)
    assert_condition(5, lambda rs, ls: rs[0]['seats']['pair_judge'].update(completed=False))
    assert_condition(6, lambda rs, ls: rs[0].update(overlap=False))
    ambiguous_rows, ambiguous_labels = variant_rows()
    read_id = sha256(b'ambiguous-read')
    ambiguous_rows[0]['ambiguous_reads'] = [{'id': read_id, 'read': 'sub*/../../private/salt'}]
    require('6' in evaluate(ambiguous_rows, ambiguous_labels, mapping)['violated_conditions']
            and '6' in evaluate(ambiguous_rows, ambiguous_labels, mapping,
                                reads={read_id: {'verdict': 'excluded'}})['violated_conditions']
            and '6' not in evaluate(ambiguous_rows, ambiguous_labels, mapping,
                                    reads={read_id: {'verdict': 'allowed'}})['violated_conditions'],
            'ambiguous read needs an allowed adjudication for condition 6')
    read = {read_id: {'verdict': 'allowed'}}
    bind_audit({}, read, {'reviewer': 'Astra', 'labels': {}, 'reads': {read_id: 'excluded'}}, {}, mapping)
    require('6' in evaluate(ambiguous_rows, ambiguous_labels, mapping, reads=read)['violated_conditions'],
            'dissenting read audit authorized PASS')
    disputed_labels = copy.deepcopy(labels)
    key = rows[twin]['findings'][0]['finding_key']
    label = disputed_labels[key]
    label['disputed'] = False
    agreeing = {'kind': label['kind'], 'match': label['match'],
                'clause_source': label['clause_source'], 'reproduced_on_own_tree': True}
    bind_audit({key: label}, {}, {'reviewer': 'Astra', 'labels': {key: agreeing}, 'reads': {}},
               {key: {'token': rows[twin]['token']}}, mapping)
    require(not label['disputed'], 'failing own-tree check and reproduced=true disagreed')
    passing_labels = copy.deepcopy(labels)
    passing_labels[key]['results']['twin'] = True
    passing_labels[key]['disputed'] = False
    bind_audit({key: passing_labels[key]}, {}, {'reviewer': 'Astra', 'labels': {key: agreeing},
                                                'reads': {}},
               {key: {'token': rows[twin]['token']}}, mapping)
    require(passing_labels[key]['disputed'], 'passing own-tree check and reproduced=true agreed')
    label['disputed'] = False
    bind_audit({key: label}, {}, {'reviewer': 'Astra', 'labels': {key: {
        'kind': label['kind'], 'match': False, 'clause_source': label['clause_source'],
        'reproduced_on_own_tree': True}}, 'reads': {}},
        {key: {'token': rows[twin]['token']}}, mapping)
    resolve_dispute(label)
    require(evaluate(rows, disputed_labels, mapping)['outcome'] == 'NOT PASS',
            'dissenting label audit authorized PASS')
    rank_one_rows = copy.deepcopy(rows)
    rank_one_labels = copy.deepcopy(labels)
    rank_one_rows[twin]['findings'][0]['rank'] = 1
    rank_one_labels[key]['disputed'] = True
    resolve_dispute(rank_one_labels[key])
    require('3' in evaluate(rank_one_rows, rank_one_labels, mapping)['violated_conditions'],
            'dissenting rank-one audit authorized PASS')
    require(evaluate(rows, labels, mapping, recurrence=True)['violated_conditions'].keys() == {'5'},
            'same-cause redispatch recurrence must be NOT PASS under condition 5')
    fixes = [{'classes': ['usage/rate-limit'], 'tokens': [rows[0]['token']]}]
    saved_root = ROOT
    with tempfile.TemporaryDirectory() as raw:
        ROOT = Path(raw)
        try:
            (ROOT / 'fixes.jsonl').write_text(json.dumps({'classes': ['capacity/overloaded'], 'time': '2026-01-01T00:00:01.000Z'}) + '\n')
            (ROOT / 'stops.jsonl').write_text(
                json.dumps({'token': 'A', 'class': 'capacity/overloaded', 'classes': ['capacity/overloaded'], 'time': '2026-01-01T00:00:00.000Z'}) + '\n')
            require(not ledger_recurrence(), 'the stop a fix addresses must not count as its recurrence')
            with (ROOT / 'stops.jsonl').open('a') as handle:
                handle.write(json.dumps({'token': 'B', 'class': 'capacity/overloaded', 'classes': ['capacity/overloaded'],
                                         'time': '2026-01-01T00:00:02.000Z'}) + '\n')
            require(ledger_recurrence() and not (ROOT / 'recurrence.json').exists(),
                    'recurrence must be derived from the ledgers even when its marker was never written')
        finally:
            ROOT = saved_root
    require(recurred(fixes, ['usage/rate-limit'])
            and not recurred(fixes, ['network'])
            and recurred(fixes, ['network', 'usage/rate-limit'])
            and not recurred(fixes, ['operator-signal', 'affected-bundle']),
            'recurrence must match a fixed class on any later token')

    coverage_rows, coverage_labels = variant_rows()
    coverage_rows[reference]['verdict'] = 'NEEDS_WORK'
    add_finding(coverage_rows, coverage_labels, reference, 'coverage', kind='coverage', results=None)
    require(evaluate(coverage_rows, coverage_labels, mapping)['outcome'] == 'PASS',
            'coverage-only finding must be neutral, including reference terminal')
    for index, condition in ((reference, '2'), (twin, '3')):
        disputed_rows, disputed_labels = variant_rows()
        if index == reference:
            disputed_rows[index]['verdict'] = 'NEEDS_WORK'
        key = add_finding(disputed_rows, disputed_labels, index, 'disputed', kind='coverage', results=None)
        disputed_labels[key]['disputed'] = True
        resolve_dispute(disputed_labels[key])
        result = evaluate(disputed_rows, disputed_labels, mapping)
        require(result['outcome'] == 'NOT PASS' and condition in result['violated_conditions'],
                'disputed coverage was not counted as a false alarm or unsupported extra')

    pre_rows, pre_labels = variant_rows()
    pre_rows[reference]['verdict'] = 'NEEDS_WORK'
    pre_key = add_finding(pre_rows, pre_labels, reference, 'pre', results={
        'base': False, 'reference': False, 'twin': False}, clause_source='existing_test')
    pre_result = evaluate(pre_rows, pre_labels, mapping)
    require(pre_result['outcome'] == 'PASS' and any(event['finding_key'] == pre_key
            and event['classification'] == 'pre-existing' for event in pre_result['events']),
            'pre-existing check order failed')
    invalid_rows, invalid_labels = variant_rows()
    invalid_reference(invalid_rows, invalid_labels)
    require(any(event['classification'] == 'invalid-reference' for event in
                evaluate(invalid_rows, invalid_labels, mapping)['events']), 'invalid reference order failed')
    extra_rows, extra_labels = variant_rows()
    key = add_finding(extra_rows, extra_labels, twin, 'twin-only', results={
        'base': True, 'reference': True, 'twin': False})
    require(any(event['finding_key'] == key and event['classification'] == 'twin-only-extra' for event in
                evaluate(extra_rows, extra_labels, mapping)['events']), 'twin-only extra order failed')
    own_rows, own_labels = variant_rows()
    false_alarm(own_rows, own_labels)
    require(any(event['classification'] == 'false-alarm' for event in
                evaluate(own_rows, own_labels, mapping)['events']), 'own-tree pass order failed')
    print('SELFTEST PASS: conditions 1-6, reads, audits, intent, drift, stops, post-join order')


def main(argv):
    if argv == ['self-test']:
        self_test()
    elif argv == ['prepare']:
        prepare()
    elif len(argv) == 3 and argv[:2] == ['run', '--pr']:
        run(int(argv[2]))
    elif (len(argv) >= 7 and argv[:2] == ['redispatch', '--cause'] and argv[3] == '--audit'
          and argv[5] == '--tokens'):
        redispatch(argv[2], argv[4], argv[6:])
    elif argv == ['score']:
        score()
    elif argv == ['pool']:
        pool()
    elif len(argv) == 7 and argv[0] == 'check' and argv[1] == '--task' and argv[3] == '--key' and argv[5] == '--script':
        check(argv[2], argv[4], argv[6])
    elif argv == ['join']:
        join()
    else:
        fail(__doc__)


if __name__ == '__main__':
    main(sys.argv[1:])
