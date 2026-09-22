"""Packet controls for the omissions observed in the first live cell."""
from pathlib import Path
import json
import subprocess
import tempfile
import unittest

from review import packet


class PacketTests(unittest.TestCase):
    def test_nested_raw_checks_and_untracked_allowed_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            work=Path(tmp)
            subprocess.run(['git','init','-q',str(work)],check=True)
            (work/'original.txt').write_text('preserve')
            subprocess.run(['git','add','.'],cwd=work,check=True)
            subprocess.run(['git','-c','user.name=Fixture','-c','user.email=f@local','commit','-qm','base'],cwd=work,check=True)
            checks=work/'.devlyn/checks-final';(checks/'nested').mkdir(parents=True)
            (work/'.devlyn/caller.json').write_text(json.dumps(dict(review_files=['original.txt'],allowed=['regression*.py'],request='preserve')))
            (work/'regression_new.py').write_text('assert True\n')
            (checks/'nested/stdout').write_text('ACTUAL TEST OUTPUT')
            (checks/'nested/status.json').write_text('{"exit_code":0}')
            (checks/'stdout').write_text('OTHER CHECK')
            hashes,text=packet(work)
            self.assertIn('regression_new.py',hashes)
            self.assertIn('FILE regression_new.py\nassert True',text)
            self.assertIn('CHECK nested/stdout\nACTUAL TEST OUTPUT',text)
            self.assertIn('CHECK nested/status.json\n{"exit_code":0}',text)
            self.assertIn('CHECK stdout\nOTHER CHECK',text)
            self.assertNotIn('NO CHECKS SUPPLIED',text)

    def test_empty_subdirectories_do_not_count_as_checks(self):
        with tempfile.TemporaryDirectory() as tmp:
            work=Path(tmp)
            subprocess.run(['git','init','-q',str(work)],check=True)
            (work/'original.txt').write_text('preserve')
            subprocess.run(['git','add','.'],cwd=work,check=True)
            subprocess.run(['git','-c','user.name=Fixture','-c','user.email=f@local','commit','-qm','base'],cwd=work,check=True)
            (work/'.devlyn/checks-final/empty').mkdir(parents=True)
            (work/'.devlyn/caller.json').write_text(json.dumps(dict(review_files=['original.txt'],allowed=[],request='preserve')))
            self.assertIn('NO CHECKS SUPPLIED',packet(work)[1])


if __name__=='__main__':
    unittest.main()
