"""Reconstruct original source; no model output or exposed case reuse."""
from pathlib import Path
import json, shutil, subprocess

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
EVIDENCE = REPO/'.devlyn/0183'
SHA = 'f6be1fb69e67b284fdb286a711c9c5bccb18ee00'
PYTHON = '/opt/homebrew/bin/python3'

def main():
    EVIDENCE.mkdir(exist_ok=True)
    shutil.copyfile(REPO/'.devlyn/0182/models_cache.json', EVIDENCE/'models_cache.json')
    for case in ('root','filter'):
        dest = EVIDENCE/'inputs'/case
        dest.mkdir(parents=True,exist_ok=False)
        (dest/'.gitignore').write_text('.devlyn/\n.agents/\n__pycache__/\n*.pyc\n')
        (dest/'tests').mkdir()
        (dest/'scripts').mkdir()
        (dest/'scripts/skill-token-gauge.py').write_bytes(subprocess.check_output(['git','show',SHA+':scripts/skill-token-gauge.py'],cwd=REPO))
        (dest/'tests/test_acceptance.py').write_bytes((HERE/case/'test_acceptance.py').read_bytes())
        (dest/'tests/test_support.py').write_bytes((HERE/'test_support.py').read_bytes())
        body = (HERE/case/'request.md').read_text()
        required = ['scripts/skill-token-gauge.py']
        cmd = PYTHON+' -B -m unittest discover -s tests -v'
        (dest/'spec.md').write_text('---\ncomplexity: trivial\n---\n# '+case+'\n\n'+body+'\n\n## Verification\n\nRun `'+cmd+'`. Preserve supplied tests, spec.md, spec.expected.json and .gitignore. '
            'Optional focused tests may be added only in tests/test_regression.py. '
            'Keep task-created temporary output out of the delivered tree; preserve original files. '
            'The outer owner handles delivery; local-only experiment commits, no publication.\n')
        (dest/'spec.expected.json').write_text(json.dumps(dict(required_files=required,
            forbidden_files=['spec.md','spec.expected.json','.gitignore','tests/test_support.py','tests/test_acceptance.py'],
            verification_commands=[dict(cmd=cmd,exit_code=0,timeout_sec=60)]),indent=2)+'\n')

if __name__ == '__main__':
    main()
