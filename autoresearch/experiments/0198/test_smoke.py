from pathlib import Path
import json
import os
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'config/skills/_shared/resolve-bootstrap.py'

class Smoke(unittest.TestCase):
    def test_legacy_branch_has_explicit_null_task(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = dict(os.environ, GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM='1')
            subprocess.run(['git', 'init', '-q', tmp], check=True, env=env)
            subprocess.run(['git', '-C', tmp, '-c', 'user.name=Fixture', '-c', 'user.email=f@local', 'commit', '--allow-empty', '-qm', 'base'], check=True, env=env)
            run = subprocess.run([sys.executable, '-B', str(SCRIPT), 'small', 'task'], cwd=tmp, env=env, capture_output=True, text=True)
            self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
            state = json.loads((Path(tmp) / '.devlyn/pipeline.state.json').read_text())
            self.assertIn('task', state)
            self.assertIsNone(state['task'])
