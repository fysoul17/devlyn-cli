#!/usr/bin/env python3
"""Protocol-1 finite checkout adapter. Rust owns the allocation subreceipt."""
from __future__ import annotations

import json
import os
from pathlib import Path, PurePosixPath, PureWindowsPath
import runpy
import subprocess

storage = runpy.run_path(str(Path(__file__).with_name('storage-client.py')))
require = storage['require']
validate = storage['validate']
StorageRefusal = storage['StorageRefusal']


def validate_request(op, request, *, windows=None):
    destination = {'state': ('absent', 'precreated_empty'), 'path': 'str'}
    if type(request.get('destination')) is dict and request['destination'].get('state') == 'precreated_empty':
        destination['identity'] = 'identity'
    shapes = {
        'capabilities': {},
        'allocate': {'adapter_protocol': 'u32', 'operation_id': 'str', 'control_directory': 'str',
                     'repository': 'str', 'baseline': 'str', 'branch': 'str', 'owner': 'owner',
                     'external_receipt': 'str', 'destination': destination, 'cache_policy': ('cargo_worktree_v1',)},
        'reconcile-for-removal': {'adapter_protocol': 'u32', 'allocation_operation_id': 'str',
                                 'external_receipt': 'str', 'removal_operation_id': 'str', 'worktree_identity?': 'identity?'},
        'unenroll': {'adapter_protocol': 'u32', 'operation_id': 'str'},
    }
    require(op in shapes, 'unknown checkout adapter operation', 'storage_invalid')
    validate(request, shapes[op], exact=True, windows=windows)
    if op == 'capabilities':
        return request
    require(request['adapter_protocol'] == 1, 'unsupported checkout adapter protocol', 'storage_invalid')
    for field in ('operation_id', 'allocation_operation_id', 'removal_operation_id'):
        if field in request:
            storage['canonical_operation'](request[field])
    path_type = PureWindowsPath if (os.name == 'nt' if windows is None else windows) else PurePosixPath
    for name in ('repository', 'control_directory', 'external_receipt'):
        if name in request:
            path = path_type(request[name])
            require(path.is_absolute() and '..' not in path.parts and '.' not in request[name].replace('\\', '/').split('/'),
                    'adapter paths must be absolute without traversal', 'storage_invalid')
    if op == 'allocate':
        import re
        require(re.fullmatch(r'(?:[0-9a-f]{40}|[0-9a-f]{64})', request['baseline']),
                'baseline must be an exact commit', 'storage_invalid')
    return request


def validate_closure(value):
    require(type(value) is dict, 'positive reservation closure missing')
    tag = value.get('established_by')
    shapes = {'released': {'established_by': ('released',), 'reservation': 'reservation'},
              'authority_migrated': {'established_by': ('authority_migrated',), 'operation_id': 'str'},
              'authority_expired': {'established_by': ('authority_expired',), 'operation_id': 'str'},
              'never_admitted': {'established_by': ('never_admitted',), 'operation_id': 'str'},
              'legacy_unreserved': {'established_by': ('legacy_unreserved',), 'receipt_version': 'u32'}}
    require(tag in shapes, 'positive reservation closure missing')
    validate(value, shapes[tag])
    return value


def decode_reply(raw, op, code):
    require(raw.endswith(b'\n') and b'\n' not in raw[:-1] and len(raw) <= storage['MAX_REPLY'],
            'uncertain adapter output; replay the saved request')
    value = storage['loads'](raw)
    validate(value, {'adapter_protocol': 'u32', 'op': (op,)})
    require(value['adapter_protocol'] == 1 and ('result' in value) != ('error' in value), 'invalid adapter envelope')
    if 'error' in value:
        error = value['error']
        validate(error, {'code': 'str', 'phase': 'str', 'retryable': 'bool', 'receipt': 'str?', 'diagnostic': 'str'})
        require(code == 2, 'adapter refusal exit mismatch')
        refusal = StorageRefusal('storage_invalid' if error['code'] == 'invalid_request' else error['code'],
                                 error['diagnostic'], operation=op, phase=error['phase'])
        refusal.retryable = error['retryable']
        raise refusal
    require(code == 0, 'uncertain adapter exit; replay the saved request')
    result = value['result']
    if op == 'capabilities':
        validate(result, {'cli_checkout_v1': 'bool', 'adapter_protocol': 'u32', 'receipt_version': 'u32',
                          'destination_modes': ['str'], 'helper_release': {'version': 'str', 'os': 'str', 'arch': 'str', 'sha256': 'str'}})
        require(result['cli_checkout_v1'] and result['adapter_protocol'] == 1 and result['receipt_version'] == 3,
                'incompatible checkout helper', 'storage_unsupported')
    elif op == 'allocate':
        validate(result, {'allocation_binding': {'baseline': 'str', 'branch': 'str', 'destination': 'str',
                          'destination_mode': {'state': ('absent', 'precreated_empty'), 'identity?': 'identity'},
                          'owner': 'owner', 'publication_owner': 'owner', 'receipt': 'str',
                          'adapter': {'operation_id': 'str', 'repository': 'str', 'control_directory': 'str', 'external_receipt': 'str'}},
                          'receipt': 'str', 'publications': ['published'], 'warnings': ['warning']})
        validate_closure(result.get('closure_result'))
    elif op == 'reconcile-for-removal':
        validate(result, {'operation_id': 'str', 'cache_ids': ['str']})
        require(len(result['cache_ids']) == len(set(result['cache_ids'])), 'duplicate removal cache ID')
        validate_closure(result.get('closure_result'))
    return result


def call(registration, op, request):
    """One attempt; uncertain stdout leaves the caller's durable request unchanged."""
    validate_request(op, request)
    raw = json.dumps(request, ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode()+b'\n'
    require(len(raw)-1 <= storage['MAX_REQUEST'], 'adapter request exceeds limit', 'storage_invalid')
    try:
        require(storage['regular_digest'](registration['helper_path']) == registration['helper_release']['sha256'],
                'enrolled helper changed')
        # No timeout: killing an allocating holder can turn replay into crash recovery.
        # Spool output to disk so an invalid helper cannot exhaust Python memory.
        import tempfile
        with tempfile.TemporaryFile() as output, tempfile.TemporaryFile() as diagnostic:
            process = subprocess.run([registration['helper_path'], 'storage-checkout', op, '--json'],
                                     input=raw, stdout=output, stderr=diagnostic)
            output.seek(0)
            reply = output.read(storage['MAX_REPLY']+1)
        return decode_reply(reply, op, process.returncode)
    except OSError as exc:
        raise StorageRefusal('storage_unavailable', f'helper outcome uncertain: {exc}; replay saved request',
                             operation=op, phase='helper') from exc
