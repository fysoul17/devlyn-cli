"""Freeze the instruction arms: build_arms.py <out-dir>. Never dispatches models.

Each arm is the exact installed managed block, rendered by the product's own bin/instructions.js
updateInstructions() from a variant body; the product itself is not edited. `current` is the base-SHA
CLAUDE.md/AGENTS.md. `slim` is deletion-only: every piece is a line, or a contiguous part of a line, of the
same engine's current file (packet E2 item 2, section table). `none` is the absence of a file.
"""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
# (1-based line, text the kept part ends with or None for the whole line); pieces are joined by blank lines.
SLIM = {
    'CLAUDE.md': [(1, None), (9, None), (11, None), ((13, 'No config bypasses.'), (14, None), (15, None), (16, None),
                  (17, None), (18, None), (19, None)), (21, None), ((23, None), (24, None), (25, None)), (29, None),
                  (36, None), (46, None),
                  (50, 'or delegate to that engine.'), (103, '## Goal-locked execution'),
                  (113, 'and orthogonal code.**', '**Match existing style'), (180, None), (182, None)],
    'AGENTS.md': [(1, None), (9, None), (11, None), ((13, 'hides a broken contract.'), (14, None), (15, None),
                  (16, None), (17, None), (18, None), (19, None)), (21, None), ((23, None), (24, None), (25, None)),
                  (27, None), (37, None), (39, 'by delegating to that engine;', 'The executor pin binds'),
                  (64, None), (71, 'and orthogonal code.', 'Match existing style')],
}


def piece(lines, line, end=None, start=None):
    text = lines[line - 1]
    if start is not None:
        text = text[text.index(start):]
    if end is not None:
        text = text[:text.index(end) + len(end)]
    return text


def body(lines, spec):
    blocks = []
    for item in spec:
        group = item if isinstance(item[0], tuple) else (item,)
        blocks.append('\n'.join(piece(lines, *entry) for entry in group))
    return '\n\n'.join(blocks) + '\n'


def render(name, text):
    """Install `text` as the packaged template and return the managed block the installer writes."""
    with tempfile.TemporaryDirectory() as temp:
        pkg, proj = Path(temp) / 'pkg', Path(temp) / 'proj'
        (pkg / 'bin').mkdir(parents=True)
        proj.mkdir()
        for source in ('instructions.js', 'instruction-templates.json'):
            shutil.copyfile(REPO / 'bin' / source, pkg / 'bin' / source)
        (pkg / name).write_text(text)
        subprocess.run(['node', '-e', f"require({json.dumps(str(pkg / 'bin/instructions.js'))}).updateInstructions({json.dumps(name)})"],
                       cwd=proj, check=True, capture_output=True)
        return (proj / name).read_text()


def main(out):
    out.mkdir(parents=True, exist_ok=True)
    base = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=REPO, text=True).strip()
    sums = {}
    for name, spec in SLIM.items():
        current = subprocess.check_output(['git', 'show', f'{base}:{name}'], cwd=REPO, text=True)
        lines = current.split('\n')
        slim = body(lines, spec)
        for line in slim.split('\n'):
            if line and line not in current and line.rstrip('.;') not in current:
                raise SystemExit(f'{name}: slim line is not deletion-only: {line[:80]}')
        if 'runtime-principles:section' in slim:
            raise SystemExit(f'{name}: slim keeps a runtime-principles marker')
        for variant, text in (('current', current), ('slim', slim)):
            rendered = render(name, text)
            path = out / f'{variant}.{name}'
            path.write_text(rendered)
            sums[path.name] = hashlib.sha256(rendered.encode()).hexdigest()
    (out / 'SHA256SUMS').write_text(''.join(f'{sha}  {name}\n' for name, sha in sorted(sums.items())))
    (out / 'BASE').write_text(base + '\n')
    print(json.dumps(dict(base=base, sums=sums), indent=2))


if __name__ == '__main__':
    main(Path(sys.argv[1]).resolve())
