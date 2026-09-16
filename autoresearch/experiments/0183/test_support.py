"""CLI acceptance utilities; no import-shape dependence on the implementation."""
from pathlib import Path
import json, shutil, subprocess, sys, tempfile, unittest

SOURCE = Path(__file__).resolve().parents[1] / 'scripts/skill-token-gauge.py'
KEYS = ('lines', 'chars', 'words', 'tokens_c4', 'tokens_w13')
FILES = {
    'config/skills/alpha/SKILL.md': '# Alpha\nSome words.\n',
    'config/skills/alpha/references/detail.md': '한국어 reference\n',
    'config/skills/beta/SKILL.md': '# Beta\nB b b\n',
    'optional-skills/alpha/SKILL.md': '# Optional Alpha\n',
    'optional-skills/GAMMA/SKILL.md': '# Upper\n',
    'config/skills/_shared/helper.md': '# Shared\n',
    'AGENTS.md': '# Root\n',
    'CLAUDE.md': '# Other root\n',
}

class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='gauge-acceptance-')
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.home = self.base/'default tree'
        self.home.mkdir()
        (self.home/'scripts').mkdir()
        self.script = self.home/'scripts/skill-token-gauge.py'
        shutil.copyfile(SOURCE, self.script)
        self.populate(self.home)

    def populate(self, root, files=FILES):
        for name, body in files.items():
            path = root/name
            path.parent.mkdir(parents=True,exist_ok=True)
            path.write_text(body,encoding='utf-8')

    def cli(self, *args, cwd=None):
        return subprocess.run([sys.executable,'-B',str(self.script),*args],
            cwd=cwd or self.base,text=True,capture_output=True,timeout=15)

    def report(self, *args, cwd=None):
        result = self.cli('--json',*args,cwd=cwd)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(result.stderr,'')
        return json.loads(result.stdout)

    def check_totals(self, data):
        groups = data['skills']+[data['shared'],data['root']]
        for group in groups:
            self.assertEqual(group['totals'],{k:sum(f[k] for f in group['files']) for k in KEYS})
        self.assertEqual(data['grand_total'],{k:sum(g['totals'][k] for g in groups) for k in KEYS})

    def bad(self, *args):
        result = self.cli(*args)
        self.assertEqual(result.returncode,2,result.stderr)
        self.assertEqual(result.stdout,'')
        self.assertTrue(result.stderr.strip())
