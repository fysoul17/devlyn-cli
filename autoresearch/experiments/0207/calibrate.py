"""Non-model reference/mutant calibration. Never a participant completion verdict."""
import argparse
import difflib
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile
import time

HERE = Path(__file__).resolve().parent
TASKS = json.loads((HERE.parent / '0206/tasks.json').read_text())['tasks']

def replace(root, name, old, new, count=1):
    path = root / name; text = path.read_text()
    assert text.count(old) == count, (name, old, text.count(old))
    path.write_text(text.replace(old, new))

def reference(root, task):
    if task == 'D1':
        replace(root, 'lib/option.js', r'/\w\.\.\.[>\]]$/', r'/[\p{L}\p{N}_]\.\.\.[>\]]$/u')
    elif task == 'D2':
        for color in ['self.show_color', 'color']:
            old = f'            color={color},\n        )'
            replace(root, 'src/click/exceptions.py', old, old + f'\n        for note in getattr(self, "__notes__", ()):\n            echo(note, file=file, color={color})')
        old = '        echo(self.format_message(), file=file, err=True, color=self.ctx.color)'
        replace(root, 'src/click/exceptions.py', old, old + '\n        for note in getattr(self, "__notes__", ()):\n            echo(note, file=file, err=True, color=self.ctx.color)')
    elif task == 'D3':
        replace(root, 'lib/command.js', '        if (dest === unknown) dest.push(arg);', '''        const target = this._findCommand(operands[0]) || this._findCommand(this._defaultCommandName);
        if (dest === unknown || target?._executableHandler) dest.push(arg);''')
    elif task == 'D4':
        replace(root, 'src/click/utils.py', 'import os\n', 'import os\nimport stat\n')
        replace(root, 'src/click/utils.py', '            if "r" in mode:', '            if "r" in mode and not stat.S_ISFIFO(os.stat(filename).st_mode):')

# Mutants edit product source, not the oracle. Each predicts a named failure.
MUTANTS = {
 'D1': [
  ('required-only', 'D1.1', 'lib/option.js', r'[>\]]$/u', r'>$/u'),
  ('ascii-only', 'D1.2', 'lib/option.js', r'[\p{L}\p{N}_]', r'\w'),
  ('unrestricted-suffix', 'D1.3', 'lib/option.js', r'[\p{L}\p{N}_]', '.'),
  ('rewrite-placeholder', 'D1.4', 'lib/option.js', 'this.flags = flags;', "this.flags = flags.replaceAll('值', 'value');"),
 ],
 'D2': [
  ('omit-notes', 'D2.1', 'src/click/exceptions.py', 'getattr(self, "__notes__", ())', '()', 3),
  ('omit-usage-notes', 'D2.2', 'src/click/exceptions.py', 'echo(note, file=file, color=color)', 'pass'),
  ('change-exit-code', 'D2.3', 'src/click/exceptions.py', 'exit_code: t.ClassVar[int] = 2', 'exit_code: t.ClassVar[int] = 1'),
  ('misroute-notes', 'D2.4', 'src/click/exceptions.py', 'echo(note, file=file, color=self.show_color)', 'echo(note, color=self.show_color)'),
  ('mutate-message', 'D2.5', 'src/click/exceptions.py', 'echo(note, file=file, color=self.show_color)', 'echo(note, file=file, color=self.show_color)\n            self.message += note'),
  ('require-native-notes', 'D2.6', 'src/click/exceptions.py', 'getattr(self, "__notes__", ())', 'self.__notes__', 3),
 ],
 'D3': [
  ('drop-delimiter', 'D3.1', 'lib/command.js', 'dest === unknown || target?._executableHandler', 'dest === unknown'),
  ('duplicate-delimiter', 'D3.2', 'lib/command.js', 'if (dest === unknown || target?._executableHandler) dest.push(arg);', 'if (dest === unknown || target?._executableHandler) dest.push(arg, arg);'),
  ('always-prepend', 'D3.3', 'lib/command.js', '    args = args.slice();', "    args = ['--', ...args];"),
  ('omit-default', 'D3.4', 'lib/command.js', ' || this._findCommand(this._defaultCommandName)', ''),
  ('leak-inprocess', 'D3.5', 'lib/command.js', 'dest === unknown || target?._executableHandler', 'true'),
  ('lose-child-exit', 'D3.6', 'lib/command.js', 'code = code ?? 1;', 'code = 0;'),
 ],
 'D4': [
  ('truncate-data', 'D4.1-2', 'src/click/utils.py', '        return getattr(self.open(), name)', '        value = getattr(self.open(), name)\n        return (lambda *args: value(*args)[:1]) if name == "read" else value'),
  ('eager-fifo', 'D4.1-2', 'src/click/utils.py', ' and not stat.S_ISFIFO(os.stat(filename).st_mode)', ''),
  ('lstat-only', 'D4.3', 'src/click/utils.py', 'os.stat(filename)', 'os.lstat(filename)'),
  ('omit-early-check', 'D4.4', 'src/click/utils.py', 'if "r" in mode and not stat.S_ISFIFO(os.stat(filename).st_mode):', 'if False:'),
  ('close-borrowed', 'D4.5', 'src/click/utils.py', '        if self.should_close:\n            self.close()', '        self.close()'),
 ]
}

def run(argv, cwd, env=None, timeout=120):
    start = time.monotonic()
    native_tmp = Path(cwd).parent / 'native-tmp'
    native_tmp.mkdir(exist_ok=True)
    env = dict(os.environ if env is None else env, TMPDIR=str(native_tmp))
    with subprocess.Popen(argv, cwd=cwd, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, start_new_session=True) as p:
        try:
            stdout, stderr = p.communicate(timeout=timeout)
            return dict(argv=argv, exit_code=p.returncode, stdout=stdout, stderr=stderr, seconds=time.monotonic()-start)
        except subprocess.TimeoutExpired:
            os.killpg(p.pid, signal.SIGKILL)
            stdout, stderr = p.communicate(timeout=2)
            return dict(argv=argv, timeout=True, stdout=stdout, stderr=stderr, seconds=time.monotonic()-start)
        finally:
            try: os.killpg(p.pid, signal.SIGKILL)
            except ProcessLookupError: pass  # The owned process group is already gone.


def evaluate(root, task, args, scratch):
    if task in ('D1', 'D3'):
        record = run([args.node, str(HERE / 'commander.mjs'), str(root), task, str(scratch)], root)
    else:
        record = run([sys.executable, '-B', str(HERE / 'click_checks.py'), str(root), task, str(scratch)], root)
    records = [record]
    if task == 'D2':
        records.append(run([args.python310, '-B', str(HERE / 'click_checks.py'), str(root), 'D2-310', str(scratch)], root))
    rows = []
    for result in records:
        assert result.get('exit_code') in (0, 1), result
        parsed = json.loads(result['stdout'].splitlines()[-1])
        assert isinstance(parsed, list) and parsed and all(type(row.get('pass')) is bool for row in parsed), result
        rows.extend(parsed)
    if task == 'D3':
        env = dict(os.environ, PATH=str(Path(args.node).parent) + os.pathsep + os.environ['PATH'])
        lifecycle = run([args.node, '--test', 'tests/command.executableSubcommand.signals.test.js',
                         'tests/command.executableSubcommand.mock.test.cjs',
                         'tests/command.executableSubcommand.lookup.test.js'], root, env, timeout=15)
        records.append(lifecycle)
        rows.append({'id': 'D3.6', 'pass': lifecycle.get('exit_code') == 0})
    return dict(checks=rows, raw=records)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('commander', 'click', 'scratch', 'output', 'node', 'python310'): parser.add_argument('--' + name, required=True)
    args = parser.parse_args()
    os.environ['PATH'] = str(Path(args.node).parent) + os.pathsep + os.environ['PATH']
    os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
    for key in ('NO_COLOR', 'FORCE_COLOR', 'CLICOLOR', 'CLICOLOR_FORCE', 'NODE_OPTIONS'):
        os.environ.pop(key, None)
    out = Path(args.output).resolve(); out.mkdir(exist_ok=False)
    summary = []
    for task in TASKS:
        source = Path(args.commander if task['id'] in ('D1','D3') else args.click).resolve()
        assert subprocess.check_output(['git','rev-parse','HEAD'], cwd=source, text=True).strip() == task['base_sha']
        assert not subprocess.check_output(['git','status','--porcelain'], cwd=source)
        with tempfile.TemporaryDirectory(prefix=task['id']+'-', dir=args.scratch) as tmp:
            root = Path(tmp) / 'repo'; scratch = Path(tmp) / 'fixtures'; scratch.mkdir()
            shutil.copytree(source, root, symlinks=True, ignore=shutil.ignore_patterns('.git', '.venv', '__pycache__', 'node_modules'))
            variants = [('baseline', None), ('reference', None)] + [(m[0], m) for m in MUTANTS[task['id']]]
            paths = ['lib/option.js', 'lib/command.js'] if task['id'] in ('D1','D3') else ['src/click/exceptions.py', 'src/click/utils.py']
            original = {p: (root / p).read_bytes() for p in paths}
            for name, mutant in variants:
                for p, data in original.items(): (root / p).write_bytes(data)
                if name != 'baseline': reference(root, task['id'])
                if mutant:
                    _, _, path, old, new, *count = mutant
                    replace(root, path, old, new, count[0] if count else 1)
                record = evaluate(root, task['id'], args, scratch)
                record['source_sha256'] = {p: hashlib.sha256((root / p).read_bytes()).hexdigest() for p in paths}
                failed = [r['id'] for r in record['checks'] if not r['pass']]
                expected = bool(failed) if name == 'baseline' else not failed if name == 'reference' else mutant[1] in failed
                record.update(task=task['id'], variant=name, expected=expected, failed=failed, fixture_cleanup=not list(scratch.iterdir()))
                if name in ('baseline', 'reference'):
                    if task['id'] in ('D1', 'D3'):
                        argv, env = [args.node, '--test'], None
                    else:
                        argv = [sys.executable, '-B', '-m', 'pytest', '-q', '-p', 'no:cacheprovider']
                        env = dict(os.environ, PYTHONPATH=str(root / 'src'))
                    record['public_suite'] = run(argv, root, env)
                    record['expected'] = record['expected'] and record['public_suite'].get('exit_code') == 0
                if name == 'reference':
                    record['patch'] = ''.join(line for p in paths for line in difflib.unified_diff(original[p].decode().splitlines(True), (root/p).read_text().splitlines(True), fromfile='a/'+p, tofile='b/'+p))
                (out / f"{task['id']}-{name}.json").write_text(json.dumps(record, indent=2))
                summary.append({k: record[k] for k in ('task','variant','expected','failed','fixture_cleanup')})
                print(json.dumps(summary[-1]), flush=True)
    (out / 'summary.json').write_text(json.dumps(summary, indent=2))
    assert all(r['expected'] and r['fixture_cleanup'] for r in summary), summary

if __name__ == '__main__': main()
