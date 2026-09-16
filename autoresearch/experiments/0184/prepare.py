from pathlib import Path
import hashlib,importlib.util,json,shutil,subprocess

REPO=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
E=REPO/'.devlyn/0184';source=E/'source';source.mkdir(exist_ok=True)
REL=Path('benchmark/auto-resolve/scripts/collect-swebench-predictions.py')
original=(REPO/REL).read_text()
(source/'collector.py').write_text(original)
shutil.copyfile(REPO/REL.with_name('pair_evidence_contract.py'),source/'pair_evidence_contract.py')
for case in ('atomic','literal'):
    work=E/'inputs'/case;(work/REL.parent).mkdir(parents=True,exist_ok=True);(work/'tests').mkdir(exist_ok=True)
    shutil.copyfile(source/'collector.py',work/REL)
    shutil.copyfile(source/'pair_evidence_contract.py',work/REL.with_name('pair_evidence_contract.py'))
    shutil.copyfile(HERE/(case+'.md'),work/'spec.md');shutil.copyfile(HERE/'test_smoke.py',work/'tests/test_smoke.py')
    shutil.copyfile(REPO/'autoresearch/experiments/0179/AGENTS.candidate.md',work/'AGENTS.md')
    (work/'.gitignore').write_text('.devlyn/\n__pycache__/\n*.pyc\n')
    (work/'spec.expected.json').write_text(json.dumps(dict(verification_commands=['/opt/homebrew/bin/python3 -B -m unittest discover -s tests -v']),indent=2))
atomic=original.replace('import json\n','import json\nimport os\nimport tempfile\n')
a=atomic.index('    with args.out.open(');b=atomic.index('\n    report = {',a)
block=atomic[a:b]
block=block.replace('with args.out.open("w", encoding="utf8") as f:', 'with tempfile.NamedTemporaryFile(mode="w", encoding="utf8", dir=args.out.parent, delete=False) as f:\n        temporary = Path(f.name)')
# Keep the zero-written check inside the transaction, after closing the staging file.
block='    temporary = None\n    try:\n'+'\n'.join('    '+line for line in block.splitlines())+'\n        os.replace(temporary, args.out)\n    finally:\n        if temporary is not None:\n            temporary.unlink(missing_ok=True)\n'
atomic=atomic[:a]+block+atomic[b:]
atomic=atomic.replace('    raise SystemExit(main())','    try:\n        raise SystemExit(main())\n    except (OSError, ValueError) as exc:\n        print(f"collect-swebench-predictions: {exc}", file=__import__("sys").stderr)\n        raise SystemExit(1)')
literal=original.replace('    for patch_path in sorted(root.glob(f"*/{patch_name}")):\n        instance_id = patch_path.parent.name','    for instance_dir in sorted(root.iterdir()):\n        patch_path = instance_dir / patch_name\n        if not instance_dir.is_dir() or not patch_path.is_file():\n            continue\n        instance_id = instance_dir.name')
literal=literal.replace('    args = parser.parse_args()','    args = parser.parse_args()\n    if not args.patch_name or args.patch_name in {".", ".."} or "/" in args.patch_name or "\\\\" in args.patch_name:\n        parser.error("--patch-name must be one non-empty literal filename")')
for name,code in [('atomic',atomic),('literal',literal)]:
    compile(code,name,'exec');(source/(name+'.reference.py')).write_text(code)
(source/'atomic.mutant.py').write_text(atomic.replace('os.replace(temporary, args.out)','args.out.write_text(temporary.read_text())'))
(source/'literal.mutant.py').write_text(literal.replace('args = parser.parse_args()','args = parser.parse_args()\n    args.patch_name = args.patch_name.strip()'))
spec=importlib.util.spec_from_file_location('checks',HERE/'check.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
rows=[]
for case in ('atomic','literal'):
    for kind,expected in [('original',False),('reference',True),('mutant',False)]:
        path=source/('collector.py' if kind=='original' else case+'.'+kind+'.py')
        row=m.check(case,path.read_bytes());row.update(control=kind,expected_pass=expected);rows.append(row)
(E/'CALIBRATION.json').write_text(json.dumps(rows,indent=2))
print(json.dumps([dict(case=r['case'],control=r['control'],passed=r['passed'],expected=r['expected_pass']) for r in rows]))
assert all(r['passed']==r['expected_pass'] for r in rows)
