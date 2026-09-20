"""Calibration implementation only; never supplied to participants or shipped."""

def history(args):
    import fnmatch
    work = Path(git(Path(args.repo).resolve(), 'rev-parse', '--show-toplevel')).resolve()
    common = Path(git(work, 'rev-parse', '--path-format=absolute', '--git-common-dir'))
    d = work / '.devlyn'

    def directory(path):
        if not path.exists() and not path.is_symlink():
            return False
        require(stat.S_ISDIR(path.lstat().st_mode), f'not a nonsymlink directory: {path}')
        return True

    def size(path):
        mode = path.lstat().st_mode
        if stat.S_ISREG(mode):
            return path.lstat().st_size
        if stat.S_ISDIR(mode):
            return sum(size(p) for p in path.iterdir())
        return 0

    def item(path):
        return {'path': path.relative_to(work).as_posix(), 'logical_bytes': size(path)}

    def obj(path):
        data = read_json(path)
        require(isinstance(data, dict), f'JSON object required: {path}')
        return data

    records = {}
    receipts = common / 'devlyn-completion'
    if directory(receipts):
        for parent in sorted(receipts.iterdir()):
            require(not parent.is_symlink(), f'redirected receipt directory: {parent}')
            if not parent.is_dir():
                continue
            path = parent / 'receipt.json'
            if not path.exists() and not path.is_symlink():
                continue
            data = obj(path)
            require(data.get('status') is None or isinstance(data['status'], str), f'invalid status: {path}')
            for field in ('reconcile', 'files'):
                require(data.get(field) is None or isinstance(data[field], dict), f'invalid {field}: {path}')
            records[parent.name] = (path, data)
    answer = {key: [] for key in ('runs', 'task_evidence', 'programs', 'pending_reconcile', 'unowned_artifacts')}
    known = {'runs', 'probes', 'process-evidence', 'engines.json', 'ideate-draft.md', 'task-evidence', 'programs'}
    for identity, (path, data) in records.items():
        if (data.get('reconcile') or {}).get('status') == 'PENDING':
            answer['pending_reconcile'].append({'receipt_id': identity, 'path': path.relative_to(common).as_posix(), 'reason': data['reconcile'].get('reason'), 'logical_bytes': size(path)})
        if data.get('worktree') == str(work):
            for raw in data.get('files') or {}:
                p = Path(raw)
                if not p.is_absolute() and '..' not in p.parts and len(p.parts) >= 2 and p.parts[0] == '.devlyn':
                    known.add(p.parts[1])
    if not directory(d):
        return answer
    for folder, key in [('task-evidence', 'task_evidence'), ('programs', 'programs')]:
        if directory(d / folder):
            answer[key] = [item(p) for p in sorted((d / folder).iterdir())]
    groups = {}
    if directory(d / 'runs'):
        for path in sorted((d / 'runs').iterdir()):
            if not path.name.startswith('rs-'):
                continue
            require(not path.is_symlink(), f'redirected run: {path}')
            if not path.is_dir():
                continue
            state = obj(path / 'pipeline.state.json')
            task = state.get('task')
            require(task is None or isinstance(task, dict), f'invalid task: {path}')
            identity = (task or {}).get('receipt_id')
            require(identity is None or (isinstance(identity, str) and identity and identity not in ('.', '..') and '/' not in identity and '\\' not in identity and '\x00' not in identity), f'invalid receipt id: {path}')
            groups.setdefault(identity, []).append(item(path))
    for identity in sorted(groups, key=lambda x: (x is not None, x or '')):
        status = 'untasked' if identity is None else records[identity][1].get('status') if identity in records else 'receipt-missing'
        answer['runs'].append({'receipt_id': identity, 'status': status, 'runs': groups[identity], 'logical_bytes': sum(x['logical_bytes'] for x in groups[identity])})
    patterns = shared('archive_run')['PER_RUN_PATTERNS']
    answer['unowned_artifacts'] = [item(p) for p in sorted(d.iterdir()) if p.name not in known and not any(fnmatch.fnmatchcase(p.name, pattern) for pattern in patterns)]
    return answer
