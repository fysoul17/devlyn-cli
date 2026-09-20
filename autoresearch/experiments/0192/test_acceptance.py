"""Public test: real archive module, filesystem fixtures, one controlled IO fault."""
from pathlib import Path
import errno
import json
import os
import runpy
import shutil
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


class ArchiveRecoveryTests(unittest.TestCase):
    def test_partial_copy_and_retry(self):
        module = runpy.run_path(str(ROOT / 'package/archive_run.py'))
        with tempfile.TemporaryDirectory(dir=ROOT) as temporary:
            devlyn = Path(temporary) / '.devlyn'; devlyn.mkdir()
            state = devlyn / 'pipeline.state.json'
            original = json.dumps({'run_id': 'public', 'phases': {}, 'process_evidence': None}).encode()
            state.write_bytes(original)
            target = devlyn / 'runs/public'
            def broken_copy(src, dst, *args, **kwargs):
                Path(dst).write_bytes(b'partial')
                raise OSError(errno.ENOSPC, 'public injected partial copy')
            with patch.object(os, 'rename', side_effect=OSError(errno.EXDEV, 'cross-device')):
                with patch.object(shutil, 'copyfile', side_effect=broken_copy):
                    with self.assertRaises(OSError):
                        module['move_artifacts'](devlyn, target)
            self.assertEqual(state.read_bytes(), original)
            self.assertFalse(any(p.is_file() or p.is_symlink() for p in target.rglob('*')))
            self.assertEqual(module['move_artifacts'](devlyn, target), 1)
            self.assertEqual((target / state.name).read_bytes(), original)
            self.assertFalse(state.exists())

    def test_normal_archive_and_collision(self):
        module = runpy.run_path(str(ROOT / 'package/archive_run.py'))
        with tempfile.TemporaryDirectory(dir=ROOT) as temporary:
            devlyn = Path(temporary) / '.devlyn'; devlyn.mkdir()
            state = devlyn / 'pipeline.state.json'
            state.write_text(json.dumps({'run_id': 'normal', 'phases': {}, 'process_evidence': None}))
            (devlyn / 'plan.md').write_bytes(b'plan\r\n')
            target = devlyn / 'runs/normal'; target.mkdir(parents=True)
            (target / 'plan.md').write_bytes(b'occupied')
            with self.assertRaises(module['ArchiveError']):
                module['move_artifacts'](devlyn, target)
            self.assertTrue(state.is_file())
            self.assertEqual((target / 'plan.md').read_bytes(), b'occupied')
            (target / 'plan.md').unlink()
            self.assertEqual(module['move_artifacts'](devlyn, target), 2)
            self.assertEqual((target / 'plan.md').read_bytes(), b'plan\r\n')
