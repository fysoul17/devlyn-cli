#!/usr/bin/env python3
"""Offline regressions for oracle method neutrality and canonical path portability."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

BASE = Path(__file__).resolve().parent

def main():
    predictions = json.loads((BASE / 'predictions-revision-2.json').read_text())['audit_controls']
    controls = BASE / 'controls'
    scratch = controls / 'scratch'
    scratch.mkdir(parents=True, exist_ok=True)
    records = []
    with tempfile.TemporaryDirectory(dir=scratch, prefix='audit-') as temporary:
        temporary = Path(temporary)
        real_tmp = temporary / 'canonical'
        real_tmp.mkdir()
        alias_tmp = temporary / 'symlink'
        alias_tmp.symlink_to(real_tmp, target_is_directory=True)
        task = BASE / 'CF-CONFIG'
        for arm in ('visible', 'gold'):
            work = temporary / ('public-' + arm)
            shutil.copytree(task / arm, work)
            command = [sys.executable, '-B', 'checks/run_checks.py']
            env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', TMPDIR=str(alias_tmp))
            result = subprocess.run(command, cwd=work, env=env, capture_output=True, text=True, timeout=30)
            name = 'public-symlink-tmp-' + arm
            record = {'id':name,'command':command,'TMPDIR':str(alias_tmp),'returncode':result.returncode,
                      'stdout':result.stdout,'stderr':result.stderr}
            (controls / (name + '.json')).write_text(json.dumps(record,indent=2)+'\n')
            assert result.returncode == predictions[name]['returncode'], record
            records.append({'id':name,'returncode':result.returncode})
        for method in ('read_text','read_bytes','open','repeated-read-negative-control'):
            work = temporary / method
            shutil.copytree(task / 'gold', work)
            reader = work / 'beacon/document.py'
            source = reader.read_text()
            expression = "path.read_text(encoding='utf-8')"
            assert source.count(expression) == 1
            if method == 'read_bytes':
                reader.write_text(source.replace(expression,"path.read_bytes().decode('utf-8')"))
            elif method == 'open':
                reader.write_text(source.replace('        data = json.loads(' + expression + ')',
                    "        with open(path, encoding='utf-8') as source:\n            data = json.load(source)"))
            elif method == 'repeated-read-negative-control':
                loader = work / 'beacon/loader.py'
                source = loader.read_text()
                block = '            if path in cache:\n                return cache[path]\n'
                assert source.count(block) == 1
                loader.write_text(source.replace(block,''))
            command = [sys.executable, '-B', str(task / 'hidden/oracle.py'), str(work)]
            env = dict(os.environ,PYTHONDONTWRITEBYTECODE='1',TMPDIR=str(real_tmp))
            result = subprocess.run(command,cwd=work,env=env,capture_output=True,text=True,timeout=30)
            record = {'id':method,'command':command,'returncode':result.returncode,
                      'stdout':result.stdout,'stderr':result.stderr}
            (controls / ('oracle-method-' + method + '.json')).write_text(json.dumps(record,indent=2)+'\n')
            assert result.returncode == 0, record
            manifestations = json.loads(result.stdout)['manifestations']
            failures = [item['id'] for item in manifestations if not item['passed']]
            assert failures == predictions[method]['failed_manifestations'], record
            records.append({'id':method,'passed':len(manifestations)-len(failures),'total':len(manifestations),'failed_manifestations':failures})
    (controls / 'audit-summary.json').write_text(json.dumps({'outcomes':records},indent=2)+'\n')
    print(json.dumps({'outcomes':records},indent=2))

if __name__ == '__main__':
    main()
