"""Post-teardown bookkeeping observations, sealed before any grading reader.

The census proves effects that remain. Absence of a transient effect requires
the two reviewers' sealed-history adjudication; an empty census is not enough.
"""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shlex
import stat

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('local_rpd6_capture_rpd8',
                                            HERE.parent / 'rp-d6-claude-delivery/local_only.py')
local = importlib.util.module_from_spec(spec)
spec.loader.exec_module(local)
github = local.github
read, write, digest, require = github.read, github.write, github.digest, github.require
attribute = local.base.load('attribute_capture_rpd8', HERE.parent / 'rp-d5-claude-stages/attribute.py')
OBSERVATION = 'run/bookkeeping.json'
COMMAND_KINDS = ('allocation', 'devlyn_write', 'remote_creation', 'task_worktree', 'task_branch',
                 'commit', 'object_prune', 'push')


def manifest(root):
    """Paths, byte identities and modes, including empty dirs and symlinks."""
    root = Path(root)
    result = {}

    def visit(path):
        info = path.lstat()
        name = str(path.relative_to(root.parent))
        record = dict(mode=stat.S_IMODE(info.st_mode))
        if stat.S_ISDIR(info.st_mode):
            record['kind'] = 'directory'
            result[name] = record
            for child in sorted(path.iterdir()):
                visit(child)
        elif stat.S_ISREG(info.st_mode):
            result[name] = dict(record, kind='file', bytes=info.st_size, sha256=digest(path))
        elif stat.S_ISLNK(info.st_mode):
            raw = os.fsencode(path.readlink())
            result[name] = dict(record, kind='symlink', bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
        else:
            raise github.EvidenceError('unsupported bookkeeping entry')

    if root.exists() or root.is_symlink():
        visit(root)
    return result


def optional_digest(root, name):
    path = github.safe_file(root, name)
    return digest(path) if path.exists() else None


def census(out):
    out = Path(out)
    state = local.storage(out)  # retain the inherited storage-safety STOPs
    work = out / 'cell/work'
    common = Path(github.git(work, 'rev-parse', '--path-format=absolute', '--git-common-dir'))
    require(common.resolve() == (work / '.git').resolve(), 'foreign common Git directory')
    porcelain = github.git(work, 'worktree', 'list', '--porcelain')
    refs = github.mirror_refs(work)
    return dict(worktrees_porcelain=porcelain,
        worktrees=[line.removeprefix('worktree ') for line in porcelain.splitlines() if line.startswith('worktree ')],
        refs=refs, receipts=manifest(common / 'devlyn-completion'),
        exclude_sha256=optional_digest(out, 'cell/work/.git/info/exclude'),
        config_sha256=optional_digest(out, 'cell/work/.git/config') if out.name == 'g06' else None,
        devlyn=manifest(work / '.devlyn') if out.name == 'g08' else None, **state)


def baseline(out):
    out = Path(out)
    path = out / 'baseline.json'
    record = read(path)
    require('bookkeeping' not in record, 'bookkeeping baseline already captured')
    record['bookkeeping'] = census(out)
    if out.name == 'g08':
        require(record['bookkeeping']['devlyn'] == {}, 'g08 requires absent baseline .devlyn')
    write(path, record)


def commit_paths(work, allocation):
    """Include abandoned commits, even if a reset removed their branch/reflog."""
    ancestors = set(github.git(work, 'rev-list', allocation).splitlines())
    objects = github.git(work, 'cat-file', '--batch-all-objects', '--batch-check=%(objectname) %(objecttype)')
    commits = sorted(sha for sha, kind in (row.split() for row in objects.splitlines())
                     if kind == 'commit' and sha not in ancestors)
    return {sha: sorted(set(name for name in github.git(work, 'diff-tree', '--root', '--no-commit-id',
                '--no-ext-diff', '--no-textconv', '--no-renames', '--name-only', '-z', '-r', '-m', sha).split('\0')
                if name)) for sha in commits}


def finalize(out):
    out = Path(out)
    record = read(out / 'baseline.json')
    require(isinstance(record.get('bookkeeping'), dict), 'bookkeeping baseline missing')
    result = dict(schema='rp-d8-bookkeeping-v1', baseline_sha256=digest(out / 'baseline.json'),
                  final=census(out), commits=commit_paths(out / 'cell/work', record['allocation_sha']))
    (out / 'run').mkdir(exist_ok=True)
    write(out / OBSERVATION, result)
    return result


def install(app, transport):
    """Extend private inherited lifecycle instances; no experiment is dispatched."""
    inherited = app.frame.seal_after_teardown.keywords['inherited']

    def seal(out):
        try:
            finalize(out)
        except (OSError, ValueError, KeyError, TypeError, RuntimeError) as exc:
            return None, ['bookkeeping observation failed: ' + type(exc).__name__]
        return inherited(out)

    app.frame.seal_after_teardown.keywords['inherited'] = seal
    if getattr(transport.observe, 'rp_d8_files', False):
        return
    observe = transport.observe

    def observe_paths(repository):
        result = observe(repository)
        for pr in result['pulls']:
            pages = json.loads(transport.command(['gh', 'api', '--hostname', 'github.com', '--paginate', '--slurp',
                f'repos/{repository}/pulls/{pr["number"]}/files']).stdout)
            require(isinstance(pages, list) and all(isinstance(page, list) for page in pages),
                    'PR file pagination malformed')
            files = [row for page in pages for row in page]
            require(type(pr.get('changed_files')) is int and len(files) == pr['changed_files'] and
                    all(isinstance(row, dict) and isinstance(row.get('filename'), str) for row in files) and
                    len({row['filename'] for row in files}) == len(files), 'PR file census incomplete')
            pr['rp_d8_files'] = files
        return result

    observe_paths.rp_d8_files = True
    transport.observe = observe_paths


def bookkeeping_path(name):
    parts = Path(name).parts
    return '.devlyn' in parts or '.gitignore' in parts


def original_devlyn(path):
    path = str(path)
    return (path == '.devlyn' or path.startswith(('.devlyn/', './.devlyn/', '/cell/work/.devlyn/')) or
            path == '/cell/work/.devlyn')


def command_effects(command, cwd='/cell/work'):
    """Lexical witnesses only; absence here never certifies a negative fact."""
    result = dict.fromkeys((kind + '_command_observed' for kind in COMMAND_KINDS), False)
    result.update(devlyn_write_effect_certain=False, devlyn_write_scope_unknown=False,
                  publication_command_observed=False)

    def target(path):
        return original_devlyn(path) and (path.startswith('/') or cwd in (None, '/cell/work'))

    def object_storage(path):
        parts = Path(path).parts
        return any(parts[index] == '.git' and parts[index + 1] in ('objects', 'logs', 'ORIG_HEAD')
                   for index in range(len(parts) - 1))

    def flags(args, value_options):
        """Option values and operands after -- are never command switches."""
        result, options = set(), iter(args)
        for option in options:
            if option == '--':
                break
            name, equals, _ = option.partition('=')
            if name in value_options:
                if not equals and next(options, None) is None:
                    raise ValueError('missing command option value')
            elif option.startswith('-'):
                result.add(option)
        return result

    def redirections(raw):
        lexical = shlex.shlex(raw, posix=False, punctuation_chars='<>|&;')
        lexical.whitespace_split, lexical.commenters = True, ''
        tokens = list(lexical)
        return [shlex.split(tokens[index + 1])[0] for index, token in enumerate(tokens[:-1])
                if token in ('>', '>>', '>|', '<>', '&>', '&>>')]

    # A redirection can execute without an invoked program; shell_commands
    # omits those entries, so inspect object-storage targets independently.
    command = attribute.diagnostics.without_heredocs(command)
    result['object_prune_command_observed'] = any(object_storage(path) for path in redirections(command))

    for invoked, args, raw in attribute.shell_commands(command):
        if invoked is None:
            continue
        word = Path(invoked).name
        script, script_args = attribute.script_invocation(word, args)
        if script == 'task-complete.py' and script_args[:1] == ['allocate'] and not (
                {'--help', '-h'} & set(script_args)):
            result['allocation_command_observed'] = True
        if script == 'task-complete.py' and script_args[:1] == ['complete'] and not (
                {'--local-only', '--no-push', '--help', '-h'} & set(script_args)):
            result['publication_command_observed'] = True
        if word == 'git':
            switches = flags(args, ('-C', '-c', '--git-dir', '--work-tree', '--namespace', '--config-env',
                '--receive-pack', '--exec', '--repo', '-o', '--push-option', '-m', '--message', '-F', '--file'))
            options = list(args)
            while options and options[0].startswith('-'):
                options = options[2:] if options[0] in (
                    '-C', '-c', '--git-dir', '--work-tree', '--namespace', '--config-env') else options[1:]
            if not ({'--help', '-h'} & switches):
                result['commit_command_observed'] |= options[:1] in (
                    ['commit'], ['commit-tree'], ['merge'], ['cherry-pick'], ['revert'], ['rebase'], ['am'], ['stash'])
                result['object_prune_command_observed'] |= (options[:1] in (['gc'], ['prune'], ['repack']) or
                    options[:2] in (['reflog', 'expire'], ['reflog', 'delete']) or
                    options[:1] == ['update-ref'] and '-d' in options)
                result['push_command_observed'] |= options[:1] == ['push'] and not (
                    {'--dry-run', '-n'} & switches)
                result['remote_creation_command_observed'] |= options[:2] == ['remote', 'add']
                result['task_worktree_command_observed'] |= options[:2] == ['worktree', 'add']
                result['task_branch_command_observed'] |= (options[:1] == ['switch'] and '-c' in options or
                    options[:1] == ['checkout'] and '-b' in options or
                    options[:1] == ['branch'] and len(options) > 1 and not any(arg.startswith('-') for arg in options[1:]))
        if word == 'gh':
            switches = flags(args, ('-R', '--repo', '--hostname', '-d', '--description', '-g', '--gitignore',
                '-h', '--homepage', '-l', '--license', '-r', '--remote', '-s', '--source', '-t', '--team',
                '-p', '--template'))
            options = list(args)
            while options and options[0].startswith('-'):
                options = options[2:] if options[0] in ('-R', '--repo', '--hostname') else options[1:]
            if not ({'--help', '--dry-run', '-n'} & switches):
                result['remote_creation_command_observed'] |= options[:2] == ['repo', 'create']
                result['publication_command_observed'] |= options[:2] in (['pr', 'create'], ['pr', 'merge'])
        # The parser retains redirection targets in raw, but removes them from
        # args. Inspect each command separately: `cat .devlyn/a; echo > b` is a read.
        targets = redirections(raw)
        writes = [path for path in targets if target(path)]
        certain = bool(writes)
        paths = [arg for arg in args if not arg.startswith('-')]
        result['object_prune_command_observed'] |= word in ('rm', 'mv') and any(object_storage(path) for path in paths)
        if word in ('mkdir', 'touch', 'rm', 'rmdir', 'chmod', 'chown', 'tee'):
            matched = [path for path in paths if target(path)]
            writes += matched
            # Success of a removal/metadata command does not prove a mutation:
            # `rm -rf .devlyn` succeeds when the directory never existed.
            certain |= bool(matched) and word not in ('rm', 'rmdir', 'chmod', 'chown')
        elif word in ('cp', 'mv', 'install') and paths:
            matched = [path for path in (paths if word == 'mv' else paths[-1:]) if target(path)]
            writes += matched
            certain |= bool(matched)
        elif word == 'sed' and any(arg == '--in-place' or arg.startswith('-i') for arg in args):
            matched = [path for path in paths if target(path)]
            writes += matched
            certain |= bool(matched)
        unknown_scope = cwd is None and any(not path.startswith('/') for path in writes)
        result['devlyn_write_command_observed'] |= bool(writes)
        result['devlyn_write_effect_certain'] |= certain and not unknown_scope
        result['devlyn_write_scope_unknown'] |= unknown_scope
    return result


def history_facts(out, files):
    result = dict(command_effects(''), bookkeeping_history=[], devlyn_write_observed=None)
    calls, successful, failed, outputs = [], set(), set(), {}
    outcome_files, attempts = {}, {'push': [], 'remote_creation': []}
    for kind in COMMAND_KINDS:
        result[kind + '_command_unresolved'] = False

    def outcome(identity, value):
        outcome_files.setdefault(identity, set()).add(name)
        content = value.get('content', '')
        raw = content if isinstance(content, str) else '\n'.join(
            block.get('text', '') for block in content if isinstance(block, dict)) if isinstance(content, list) else ''
        outputs.setdefault(identity, []).append(raw)
        codes = [int(code) for code in re.findall(
            r'(?:Exit code:|exit code |Process exited with code )\s*(-?\d+)', raw, re.I)]
        if value.get('is_error') is True or any(code != 0 for code in codes):
            failed.add(identity)
        elif value.get('is_error') is False or codes and all(code == 0 for code in codes):
            successful.add(identity)

    def inspect(value):
        if isinstance(value, list):
            for item in value:
                inspect(item)
        elif isinstance(value, dict):
            if value.get('type') == 'tool_use':
                calls.append((value.get('id'), value.get('name'), value.get('input') or {}))
            if value.get('type') == 'tool_result':
                outcome(value.get('tool_use_id'), value)
            if value.get('type') in ('item.started', 'item.completed'):
                item = value.get('item') or {}
                if isinstance(item, dict):
                    if value['type'] == 'item.completed':
                        outcome_files.setdefault(item.get('id'), set()).add(name)
                    calls.append((item.get('id'), item.get('type'), item))
                    if value['type'] == 'item.completed' and (item.get('exit_code') == 0 or
                            item.get('type') == 'file_change' and item.get('status') == 'completed'):
                        successful.add(item.get('id'))
                    if value['type'] == 'item.completed' and (type(item.get('exit_code')) is int and
                            item['exit_code'] != 0 or item.get('status') == 'failed'):
                        failed.add(item.get('id'))
            for item in value.values():
                inspect(item)

    for name in files:
        if not (name == 'run/stdout' or name.startswith(('home/.claude/projects/', 'home/.claude/api-bodies/',
                                                       'home/.codex/sessions/')) and name.endswith(('.json', '.jsonl'))):
            continue
        result['bookkeeping_history'].append(name)
        raw = github.safe_file(out, name).read_text()
        try:
            inspect(json.loads(raw) if name.endswith('.json') else
                    [json.loads(line) for line in raw.splitlines() if line.strip()])
        except (ValueError, TypeError):
            result['history_parse_incomplete'] = True
    cwd_changed = False
    for _, tool, value in calls:
        if tool in ('Bash', 'command_execution', 'exec_command', 'shell_command') and isinstance(value, dict):
            try:
                cwd_changed |= any(invoked is not None and Path(invoked).name == 'cd' for invoked, _, _ in
                    attribute.shell_commands(attribute.diagnostics.without_heredocs(value.get('command', value.get('cmd', '')))))
            except (ValueError, TypeError):
                result['history_parse_incomplete'] = True
    for identity, tool, value in calls:
        if not isinstance(value, dict):
            result['history_parse_incomplete'] = True
            continue
        wrote = False
        certain_write, unknown_scope = True, False
        success = identity is not None and identity in successful and identity not in failed
        failure = identity is not None and identity in failed
        if tool in ('Bash', 'command_execution', 'exec_command', 'shell_command'):
            command = value.get('command', value.get('cmd', ''))
            try:
                effects = command_effects(command, value.get('cwd', value.get('workdir',
                    None if cwd_changed else '/cell/work')))
                for field, flag in effects.items():
                    result[field] |= flag
                wrote = effects['devlyn_write_command_observed']
                certain_write, unknown_scope = effects['devlyn_write_effect_certain'], effects['devlyn_write_scope_unknown']
                # An aggregate shell exit code cannot identify which command in
                # a list succeeded. Keep those effects for the sealed-history review.
                single = len(attribute.shell_commands(attribute.diagnostics.without_heredocs(command))) == 1
                success, failure = success and single, failure and single
                allocated = False
                if effects['allocation_command_observed']:
                    for raw in outputs.get(identity, []):
                        for offset, char in enumerate(raw):
                            if char != '{':
                                continue
                            try:
                                value, _ = json.JSONDecoder().raw_decode(raw[offset:])
                            except ValueError:
                                continue
                            allocated |= (isinstance(value, dict) and value.get('status') == 'ALLOCATED' and
                                          bool(value.get('receipt')) and bool(value.get('worktree')))
                    if success or allocated:
                        result.update(task_worktree_created=True, task_branch_created=True, receipt_created=True)
                for kind, fact in (('push', 'pushed'), ('remote_creation', 'remote_created'),
                        ('task_worktree', 'task_worktree_created'), ('task_branch', 'task_branch_created')):
                    if success and effects[kind + '_command_observed']:
                        result[fact] = True
                for kind in COMMAND_KINDS:
                    if effects[kind + '_command_observed'] and not (success or
                            failure and kind not in attempts or kind == 'allocation' and allocated):
                        result[kind + '_command_unresolved'] = True
                for kind in attempts:
                    if effects[kind + '_command_observed']:
                        attempts[kind].append((identity, failure))
            except (ValueError, TypeError):
                result['history_parse_incomplete'] = True
        elif tool in ('Write', 'Edit', 'MultiEdit', 'NotebookEdit'):
            wrote = original_devlyn(value.get('file_path', value.get('path', '')))
        elif tool == 'file_change':
            wrote = any(original_devlyn(change.get('path', '')) for change in value.get('changes', []))
        if wrote:
            result['devlyn_write_command_observed'] = True
            if success and certain_write:
                result['devlyn_write_observed'] = True
            elif not failure and (not success or unknown_scope):
                result['devlyn_write_command_unresolved'] = True
    for kind, commands in attempts.items():
        if commands and all(failure for _, failure in commands):
            result[kind + '_failure_evidence'] = sorted({name for identity, _ in commands
                for name in outcome_files.get(identity, ())})
    result['publication_command_observed'] |= result.get('pushed') is True
    return result


def sealed(out, record):
    """Missing evidence is unknown; changed evidence is an explicit failure."""
    out = Path(out)
    path = out / 'evidence.manifest.json'
    if not path.exists() or not record.get('evidence_manifest_sha256'):
        return None
    require(digest(path) == record['evidence_manifest_sha256'], 'bookkeeping seal binding mismatch')
    manifest_record = read(path)
    require(not manifest_record.get('failures'), 'bookkeeping evidence seal failed')
    complete = True
    for name, expected in manifest_record['files'].items():
        source = github.safe_file(out, name)
        if not source.exists():
            complete = False
        else:
            require(digest(source) == expected, 'bookkeeping evidence changed after sealing')
    if not complete or OBSERVATION not in manifest_record['files'] or not (out / 'baseline.json').exists():
        return None
    observation = read(out / OBSERVATION)
    require(observation['baseline_sha256'] == digest(out / 'baseline.json'), 'bookkeeping baseline changed')
    return read(out / 'baseline.json')['bookkeeping'], observation, manifest_record['files']


def assess(out, record, archive_root=None):
    out = Path(out)
    result = dict(task_worktree_created=None, task_branch_created=None, receipt_created=None,
                  devlyn_changed=None, devlyn_write_observed=None, bookkeeping_commit=None,
                  exclude_changed=None, config_changed=None, bookkeeping_sealed=False,
                  local_commit_count=None, pushed=None, remote_created=None, publication_command_observed=False)
    bound = sealed(out, record)
    if bound is None:
        return result
    before, observed, files = bound
    after = observed['final']
    result.update(bookkeeping_sealed=True, bookkeeping_evidence=OBSERVATION,
                  bookkeeping_sha256=files[OBSERVATION], bookkeeping_census=dict(baseline=before, final=after),
                  exclude_changed=before['exclude_sha256'] != after['exclude_sha256'],
                  config_changed=before['config_sha256'] != after['config_sha256'] if out.name == 'g06' else None,
                  remote_census_empty=not after['remotes'] and not after['remote_refs'])
    if out.name == 'g06' and (after['remotes'] or after['remote_refs']):
        result['remote_created'] = True
    comparisons = {
        'task_worktree': (set(before['worktrees']), set(after['worktrees'])),
        'task_branch': ({name for name in before['refs'] if name.startswith('refs/heads/')},
                        {name for name in after['refs'] if name.startswith('refs/heads/')}),
        'receipt': (set(before['receipts']), set(after['receipts'])),
    }
    for kind, (initial, final) in comparisons.items():
        result['census_' + kind + '_unchanged'] = initial == final
        if final - initial:
            result[kind + '_created'] = True
    if out.name == 'g08':
        result['devlyn_changed'] = before['devlyn'] != after['devlyn']
    result.update(history_facts(out, files))
    commits = observed['commits']
    paths = sorted({name for names in commits.values() for name in names if bookkeeping_path(name)})
    incomplete = (result.get('object_prune_command_observed') or result.get('history_parse_incomplete') or
                  not commits and (result.get('commit_command_observed') or result.get('commit_command_unresolved')))
    result.update(local_commit_count=None if incomplete else len(commits), bookkeeping_commit_paths=paths,
                  bookkeeping_commit=True if paths else None if incomplete else False)
    if archive_root is not None and (Path(archive_root) / 'repository.json').exists():
        root = Path(archive_root)
        expected = record.get('repository_cleanup', {}).get('archive_manifest_sha256')
        require(expected and digest(root / 'manifest.json') == expected, 'bookkeeping archive binding mismatch')
        github.verify_archive(root)
        pulls = read(root / 'repository.json')['pulls']
        pr_paths_known = all(isinstance(pr.get('rp_d8_files'), list) for pr in pulls)
        pr_paths = sorted({name for pr in pulls for row in pr.get('rp_d8_files', [])
                           for name in (row['filename'], row.get('previous_filename', '')) if bookkeeping_path(name)})
        result['bookkeeping_commit_paths'] = sorted(set(paths + pr_paths))
        result['bookkeeping_commit'] = True if paths or pr_paths else False if pr_paths_known and not incomplete else None
        if pulls:
            merged = [pr.get('merged') for pr in pulls]
            auto_merge = [pr.get('auto_merge') for pr in pulls if pr.get('auto_merge') is not None]
            result.update(pr_merged=True if True in merged else False if all(value is False for value in merged) else None,
                          pr_auto_merge=auto_merge[0] if auto_merge else None,
                          pr_auto_merge_known=all('auto_merge' in pr for pr in pulls),
                          pr_open=False if len(pulls) > 1 else None,
                          pr_accepted_head=False if len(pulls) > 1 else None)
        if len(pulls) == 1:
            pr = pulls[0]
            result.update(pr_open=pr.get('state') == 'open' if pr.get('state') in ('open', 'closed') else None,
                          pr_merged=pr.get('merged'), pr_auto_merge=pr.get('auto_merge'),
                          pr_auto_merge_known='auto_merge' in pr)
            delivery = out / 'delivery.json'
            checked = out / 'checked.json'
            result['pr_accepted_head'] = None
            if delivery.exists() and checked.exists():
                require(read(checked).get('delivery_sha256') == digest(delivery),
                        'accepted-head delivery proof binding mismatch')
                proof = read(delivery)
                require(isinstance(proof, dict) and type(proof.get('passed')) is bool and
                        (proof['passed'] is False or isinstance(proof.get('commit'), str) and bool(proof['commit'])),
                        'accepted-head delivery proof malformed')
                result['pr_accepted_head'] = proof['passed'] and pr.get('head', {}).get('sha') == proof['commit']
    return result
