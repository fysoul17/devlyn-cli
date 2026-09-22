"""External Click checks; each obligation reports independently."""
import contextlib
import io
import json
import os
from pathlib import Path
import selectors
import subprocess
import sys
import tempfile

repo, task, scratch = sys.argv[1:]
sys.path.insert(0, str(Path(repo) / 'src'))
import click
from click.testing import CliRunner

rows = []
def check(name, fn):
    try:
        fn()
        rows.append(dict(id=name, pass_=True))
    except Exception as exc:
        rows.append(dict(id=name, pass_=False, error=repr(exc)))

def equal(actual, expected):
    assert actual == expected, (actual, expected)

def render(exc):
    out = io.StringIO(); exc.show(out); return out.getvalue()

if task == 'D2':
    def base():
        assert sys.version_info >= (3, 11), 'native add_note unavailable'
        for notes in [['first'], ['first', 'second'], ['first\ncontinuation', 'second']]:
            exc = click.ClickException('message')
            for note in notes: exc.add_note(note)
            equal(render(exc), 'Error: message\n' + ''.join(n + '\n' for n in notes))
    check('D2.1', base)
    def subclasses():
        ctx = click.Context(click.Command('demo'), info_name='demo')
        for exc, expected in [
            (click.UsageError('message'), 'Error: message\n'),
            (click.UsageError('message', ctx), "Usage: demo [OPTIONS]\nTry 'demo --help' for help.\n\nError: message\n"),
            (click.BadParameter('bad', param_hint='--value'), "Error: Invalid value for --value: bad\n"),
            (click.FileError('missing', 'no file'), "Error: Could not open file 'missing': no file\n"),
        ]:
            exc.add_note('note'); equal(render(exc), expected + 'note\n')
        exc = click.exceptions.NoArgsIsHelpError(ctx)
        expected = ctx.get_help() + '\n'
        exc.add_note('note'); equal(render(exc), expected + 'note\n')
    check('D2.2', subclasses)
    def unchanged():
        for cls, code in [(click.ClickException, 1), (click.UsageError, 2)]:
            equal(render(cls('message')), 'Error: message\n')
            @click.command()
            def cli(): raise cls('message')
            result = CliRunner().invoke(cli)
            equal(result.exit_code, code)
            assert result.stderr.endswith('Error: message\n')
    check('D2.3', unchanged)
    def streams():
        for cls in [click.ClickException, click.UsageError]:
            for color in [False, True]:
                ctx = click.Context(click.Command('demo'), color=color)
                with ctx:
                    exc = cls('message', ctx) if cls is click.UsageError else cls('message')
                exc.add_note('\x1b[31mnote\x1b[0m')
                out, err, target = io.StringIO(), io.StringIO(), io.StringIO()
                with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err): exc.show(target)
                equal(out.getvalue(), ''); equal(err.getvalue(), '')
                assert target.getvalue().endswith(('\x1b[31mnote\x1b[0m' if color else 'note') + '\n')
                with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err): exc.show()
                equal(out.getvalue(), ''); equal(err.getvalue(), target.getvalue())
    check('D2.4', streams)
    def pure():
        class Custom(click.ClickException):
            def format_message(self): return 'formatted'
        exc = Custom('message'); exc.add_note('note')
        for _ in range(2): equal(render(exc), 'Error: formatted\nnote\n')
        equal(str(exc), 'message'); equal(exc.format_message(), 'formatted')
        equal(exc.__notes__, ['note']); equal(exc.message, 'message')
    check('D2.5', pure)
    # D2.6 is a separate native Python 3.10 invocation, never a skipped note test.
elif task == 'D2-310':
    def compatibility():
        assert sys.version_info[:2] == (3, 10), sys.version
        for cls in [click.ClickException, click.UsageError]: equal(render(cls('message')), 'Error: message\n')
    check('D2.6', compatibility)
elif task == 'D4':
    def line(process, expected):
        with selectors.DefaultSelector() as sel:
            sel.register(process.stdout, selectors.EVENT_READ)
            assert sel.select(2), 'handshake timeout: ' + expected
            equal(process.stdout.readline().decode().strip(), expected)
    def fifo(mode, symlink):
        with tempfile.TemporaryDirectory(dir=scratch) as tmp:
            root = Path(tmp); pipe = root / 'pipe'; os.mkfifo(pipe)
            path = pipe
            if symlink:
                path = root / 'link'; path.symlink_to(pipe)
            reader_code = '''import sys,json,click
f=click.File(sys.argv[2],lazy=True).convert(sys.argv[1],None,None)
print('converted',flush=True)
sys.stdin.readline()
print('reading',flush=True)
with f: data=f.read()
assert f.closed
print(json.dumps(data.decode() if isinstance(data,bytes) else data),flush=True)
'''
            env = dict(os.environ, PYTHONPATH=str(Path(repo) / 'src'), PYTHONDONTWRITEBYTECODE='1')
            reader = subprocess.Popen([sys.executable, '-B', '-c', reader_code, str(path), mode], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env, bufsize=0)
            writer = None
            try:
                # The writer does not exist until conversion acknowledges completion.
                line(reader, 'converted')
                writer = subprocess.Popen([sys.executable, '-B', '-c', "import sys; print('ready',flush=True); f=open(sys.argv[1],'wb'); f.write('payload λ\\nsecond'.encode()); f.close()", str(pipe)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=0)
                line(writer, 'ready')
                # The read is delayed by a real handshake, never sleeps-as-proof.
                reader.stdin.write(b'go\n'); reader.stdin.flush()
                line(reader, 'reading')
                output, err = reader.communicate(timeout=2)
                equal(reader.returncode, 0); equal(err, b'')
                equal(json.loads(output), 'payload λ\nsecond')
                _, err = writer.communicate(timeout=2); equal(writer.returncode, 0); equal(err, b'')
            finally:
                for child in [reader, writer]:
                    if child is not None:
                        if child.poll() is None: child.kill()
                        child.communicate(timeout=2)
    check('D4.1-2', lambda: [fifo(mode, False) for mode in ['rb', 'r']])
    check('D4.3', lambda: [fifo(mode, True) for mode in ['rb', 'r']])
    def ordinary():
        with tempfile.TemporaryDirectory(dir=scratch) as tmp:
            root = Path(tmp)
            for path in [root / 'missing', root]:
                try: click.File('rb', lazy=True).convert(str(path), None, None)
                except click.BadParameter: pass
                else: raise AssertionError('missing early error: ' + str(path))
            (root / 'file').write_bytes(b'ordinary'); (root / 'link').symlink_to(root / 'file')
            for path in [root / 'file', root / 'link']:
                with click.File('rb', lazy=True).convert(str(path), None, None) as f: equal(f.read(), b'ordinary')
    check('D4.4', ordinary)
    def ownership():
        with tempfile.TemporaryDirectory(dir=scratch) as tmp:
            root = Path(tmp); ctx = click.Context(click.Command('test'))
            stdin = io.StringIO('borrowed')
            original = sys.stdin
            try:
                sys.stdin = stdin
                with ctx:
                    f = click.File('r', lazy=True).convert('-', None, ctx); equal(f.read(), 'borrowed')
                assert not stdin.closed
            finally: sys.stdin = original
            target = root / 'write'; ctx = click.Context(click.Command('test'))
            with ctx: click.File('w', lazy=True).convert(str(target), None, ctx)
            assert not target.exists()
            target.write_text('owned'); ctx = click.Context(click.Command('test'))
            with ctx:
                f = click.File('r', lazy=True).convert(str(target), None, ctx); equal(f.read(), 'owned')
            assert f.closed
    check('D4.5', ownership)
else:
    raise ValueError(task)
print(json.dumps([{('pass' if k == 'pass_' else k): v for k, v in row.items()} for row in rows]))
sys.exit(0 if all(row['pass_'] for row in rows) else 1)
