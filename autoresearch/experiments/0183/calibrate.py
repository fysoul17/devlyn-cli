"""Check CLI acceptance against original source, references and focused mutants."""
from pathlib import Path
import json, shutil, subprocess, tempfile

REPO=Path(__file__).resolve().parents[3]
EVIDENCE=REPO/'.devlyn/0183'
SCRATCH=REPO/'.git/devlyn-completion/2137acb862ccbc4bb2ae8500/scratch'

def reference(case, source):
    if case=='root':
        source=source.replace('[--json]', '[--json] [--root PATH]')
        source=source.replace('def main() -> None:\n', 'def main() -> None:\n    global REPO_ROOT\n')
        source=source.replace('    args = parser.parse_args()',
            "    parser.add_argument('--root', type=Path, help='repository directory to measure')\n"
            '    args = parser.parse_args()\n'
            '    if args.root is not None:\n'
            '        if not args.root.is_dir():\n'
            "            parser.error('--root must name an existing directory')\n"
            '        REPO_ROOT = args.root.resolve()')
    else:
        source=source.replace('[--json]', '[--json] [--skill NAME]')
        source=source.replace('    args = parser.parse_args()',
            "    parser.add_argument('--skill', help='exact skill name to report')\n    args = parser.parse_args()")
        source=source.replace('    skills = collect_skills()',
            '    skills = collect_skills()\n'
            '    if args.skill is not None:\n'
            "        skills = [skill for skill in skills if skill['name'] == args.skill]\n"
            '        if not skills:\n'
            "            parser.error('no matching skill: ' + args.skill)")
    return source

def main():
    rows=[]
    for case in ('root','filter'):
        src=(EVIDENCE/'inputs'/case/'scripts/skill-token-gauge.py').read_text()
        ref=reference(case,src)
        variants={'original':src,'reference':ref}
        if case=='root':
            variants['ignores_root']=ref.replace('        REPO_ROOT = args.root.resolve()','        pass')
            variants['rejects_empty']=ref.replace('if not args.root.is_dir():','if not args.root.is_dir() or not any(args.root.iterdir()):')
        else:
            variants['substring']=ref.replace("skill['name'] == args.skill","args.skill in skill['name']")
            variants['first_base_only']=ref.replace('        if not skills:', '        skills = skills[:1]\n        if not skills:')
        for name,code in variants.items():
            with tempfile.TemporaryDirectory(prefix='calibration-',dir=SCRATCH) as tmp:
                work=Path(tmp)/'work'
                shutil.copytree(EVIDENCE/'inputs'/case,work)
                (work/'scripts/skill-token-gauge.py').write_text(code)
                p=subprocess.run(['/opt/homebrew/bin/python3','-B','-m','unittest','discover','-s','tests','-v'],cwd=work,capture_output=True,text=True,timeout=60)
                rows.append(dict(case=case,variant=name,expected_pass=name=='reference',exit_code=p.returncode,stdout=p.stdout,stderr=p.stderr))
        (EVIDENCE/f'{case}.reference.py').write_text(ref)
    (EVIDENCE/'CALIBRATION.json').write_text(json.dumps(rows,indent=2)+'\n')
    assert all((r['exit_code']==0)==r['expected_pass'] for r in rows)
    print(json.dumps([dict(case=r['case'],variant=r['variant'],exit_code=r['exit_code']) for r in rows]))

if __name__=='__main__':main()
