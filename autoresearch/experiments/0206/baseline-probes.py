"""Read-only task-existence probes; not the completion evaluator or a model draw."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import tempfile


def command(argv, cwd, timeout=10):
    try:
        p = subprocess.run(argv, cwd=cwd, capture_output=True, text=True, timeout=timeout)
        return dict(exit_code=p.returncode, stdout=p.stdout, stderr=p.stderr)
    except subprocess.TimeoutExpired as e:
        return dict(timeout_seconds=timeout,
                    stdout=(e.stdout or b'').decode(), stderr=(e.stderr or b'').decode())


def probe(commander, click, scratch):
    results = {}
    uri = (commander / 'index.js').as_uri()
    with tempfile.TemporaryDirectory(prefix='0206-probes-', dir=scratch) as tmp:
        work = Path(tmp)
        script = f"""
import {{Command, Option}} from {json.dumps(uri)};
const rows = [];
for (const placeholder of ['<value...>', '<值...>', '[值...]', '<value,...>']) {{
  const option = new Option('--tag ' + placeholder);
  const program = new Command().exitOverride().configureOutput({{writeErr:()=>{{}}}}).addOption(option);
  let result;
  try {{ program.parse(['--tag','one','two'], {{from:'user'}}); result = program.opts(); }}
  catch (e) {{ result = {{error:e.code}}; }}
  rows.push({{placeholder, variadic:option.variadic, result}});
}}
console.log(JSON.stringify(rows));
"""
        results['D1'] = command(['node', '--input-type=module', '-e', script], work)
        script = f"""
import sys, io, json
sys.path.insert(0, {str(click / 'src')!r})
import click
rows=[]
for cls in [click.ClickException, click.UsageError, click.BadParameter]:
    exc=cls('message'); exc.add_note('first'); exc.add_note('second')
    out=io.StringIO(); exc.show(out)
    rows.append(dict(type=cls.__name__, output=out.getvalue(), notes=exc.__notes__))
print(json.dumps(rows))
"""
        results['D2'] = command([sys.executable, '-B', '-c', script], work)
        (work / 'child.mjs').write_text('console.log(JSON.stringify(process.argv.slice(2)));\n')
        (work / 'parent.mjs').write_text(f"""
import {{Command}} from {json.dumps(uri)};
new Command().name('parent').command('child', 'child', {{executableFile:{json.dumps(str(work / 'child.mjs'))}}}).parse();
""")
        results['D3'] = [dict(args=args, **command(['node', str(work / 'parent.mjs'), 'child', *args], work))
                         for args in [['plain'], ['--', '--literal'], ['--', '--', '--literal']]]
        # No writer exists. A constructor that opens the FIFO blocks and the
        # subprocess.run timeout kills/reaps this sole owned probe process.
        script = f"""
import sys, os, json
sys.path.insert(0, {str(click / 'src')!r})
import click
os.mkfifo('pipe')
print('before-convert', flush=True)
value=click.File('rb', lazy=True).convert('pipe', None, None)
print('after-convert', flush=True)
value.close()
"""
        results['D4'] = command([sys.executable, '-B', '-c', script], work, timeout=3)
    return results


def validate(results):
    for task in ('D1', 'D2'):
        assert results[task].get('exit_code') == 0, results[task]
    rows = json.loads(results['D1']['stdout'])
    assert rows[0]['variadic'] and rows[0]['result'] == {'tag': ['one', 'two']}
    assert all(not row['variadic'] for row in rows[1:])
    assert all('first' not in row['output'] and 'second' not in row['output']
               for row in json.loads(results['D2']['stdout']))
    assert all(row.get('exit_code') == 0 for row in results['D3']), results['D3']
    assert [json.loads(row['stdout']) for row in results['D3']] == [
        ['plain'], ['--literal'], ['--', '--literal']]
    assert results['D4'].get('timeout_seconds') == 3, results['D4']
    assert results['D4']['stdout'] == 'before-convert\n', results['D4']


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--commander', type=Path, required=True)
    parser.add_argument('--click', type=Path, required=True)
    parser.add_argument('--scratch', type=Path, required=True)
    args = parser.parse_args()
    results = probe(args.commander.resolve(), args.click.resolve(), args.scratch.resolve())
    print(json.dumps(results, indent=2), flush=True)
    validate(results)
