from pathlib import Path
import json,os,subprocess,sys,tempfile,unittest

SCRIPT=Path(__file__).resolve().parents[1]/'benchmark/auto-resolve/scripts/collect-swebench-predictions.py'
class Smoke(unittest.TestCase):
    def test_success(self):
        with tempfile.TemporaryDirectory(dir=os.environ.get('TMPDIR')) as temp:
            root=Path(temp);patch=root/'patches'/'case-a'/'patch.diff'
            patch.parent.mkdir(parents=True);patch.write_text('diff content\n')
            out=root/'result.jsonl'
            p=subprocess.run([sys.executable,'-B',str(SCRIPT),'--patch-root',str(root/'patches'),'--model-name','test','--out',str(out)],capture_output=True,text=True)
            self.assertEqual(p.returncode,0,p.stderr)
            self.assertEqual(json.loads(out.read_text()),dict(instance_id='case-a',model_name_or_path='test',model_patch='diff content\n'))
            self.assertEqual(json.loads(p.stdout)['predictions_written'],1)
if __name__=='__main__':unittest.main()
