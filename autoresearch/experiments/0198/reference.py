def owned_task(cwd):
    branch = base_branch(cwd)
    if branch is None:
        return None
    identity = hashlib.sha256(branch.encode('utf-8')).hexdigest()[:24]
    common = pathlib.Path(git_text(cwd, 'rev-parse', '--path-format=absolute', '--git-common-dir'))
    container = common / 'devlyn-completion'
    directory = container / identity
    receipt_path = directory / 'receipt.json'
    for path, is_directory in ((container, True), (directory, True), (receipt_path, False)):
        try:
            mode = path.lstat().st_mode
        except FileNotFoundError:
            return None
        if stat.S_ISLNK(mode) or not (stat.S_ISDIR(mode) if is_directory else stat.S_ISREG(mode)):
            block('BLOCKED:task-receipt', f'Invalid receipt path: {path}')
    receipt = strict_json(receipt_path.read_text(encoding='utf-8'))
    if not isinstance(receipt, dict) or any(not isinstance(receipt.get(key), str) for key in ('branch', 'worktree')):
        block('BLOCKED:task-receipt', f'Invalid receipt structure: {receipt_path}')
    if receipt['branch'] != branch or receipt['worktree'] != str(cwd):
        return None
    if receipt.get('allocation') != 'owned' or receipt.get('id') != identity:
        block('BLOCKED:task-receipt', f'Receipt ownership is invalid: {receipt_path}')
    status = receipt.get('status')
    acceptance = receipt.get('acceptance')
    if (status is not None and not isinstance(status, str)) or ('local_only' in receipt and not isinstance(receipt['local_only'], bool)) or (acceptance is not None and not isinstance(acceptance, dict)):
        block('BLOCKED:task-receipt', f'Invalid receipt status fields: {receipt_path}')
    if status in ('COMPLETE', 'ABANDONED') or ((status == 'LOCAL_ONLY' or receipt.get('local_only') is True) and acceptance is not None):
        block('BLOCKED:task-receipt', f'Terminal task cannot admit another run: {receipt_path}')
    return {'receipt_id': identity}
