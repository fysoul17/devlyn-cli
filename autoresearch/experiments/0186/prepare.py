from pathlib import Path
import datetime,hashlib,json,os,shutil,subprocess
R=Path(__file__).resolve().parents[3];H=Path(__file__).resolve().parent;E=R/'.devlyn/0186';SCRATCH=R/'.git/devlyn-completion/de61a898ff4784dd683ba8ef/scratch'
reference=(E/'source/reference.js').read_text()
mutants={
 'no-rollback':reference.replace('if (published) {','if (false) {'),
 'early-unlock':reference.replace('if (published) {','fs.rmdirSync(lock); released = true;\n      if (published) {'),
 'lock':reference.replace('try { fs.mkdirSync(lock); }','try { fs.mkdirSync(lock, {recursive:true}); }'),
 'non-atomic':reference.replace("fs.renameSync(path.join(stage, 'new'), dest);", "fs.writeFileSync(dest, fs.readFileSync(path.join(stage, 'new')));")}
rows=[]
for name in ['original','reference',*mutants]:
 p=E/'source'/(name+'.js')
 if name in mutants:p.write_text(mutants[name])
 run=subprocess.run(['node','--test',str(H/'acceptance.js'),str(H/'heldout.js')],env={**os.environ,'PRODUCT':str(p),'TMPDIR':str(SCRATCH)},capture_output=True,timeout=60)
 for suffix,data in [('stdout',run.stdout),('stderr',run.stderr)]: (E/('calibration-final-'+name+'.'+suffix)).write_bytes(data)
 rows.append({'control':name,'expected_pass':name=='reference','exit_code':run.returncode})
(E/'CALIBRATION.json').write_text(json.dumps(rows,indent=2)+'\n');print(json.dumps(rows),flush=True)
assert all((r['exit_code']==0)==r['expected_pass'] for r in rows)
work=E/'inputs/install';(work/'bin').mkdir(parents=True);(work/'tests').mkdir()
shutil.copyfile(E/'source/original.js',work/'bin/devlyn.js');shutil.copyfile(R/'package.json',work/'package.json');shutil.copyfile(H/'request.md',work/'spec.md')
for n in ('support.js','acceptance.js'):shutil.copyfile(H/n,work/'tests'/n)
(work/'.gitignore').write_text('.devlyn/\n.agents/\n__pycache__/\n*.pyc\n')
(work/'spec.expected.json').write_text(json.dumps({'required_files':['bin/devlyn.js'],'forbidden_files':['spec.md','spec.expected.json','package.json','.gitignore','tests/support.js','tests/acceptance.js'],'verification_commands':[{'cmd':'node --test tests/acceptance.js','exit_code':0,'timeout_sec':90}]},indent=2)+'\n')
shutil.copyfile(R/'.devlyn/0185/models_cache.json',E/'models_cache.json');shutil.copyfile(R/'.devlyn/0179/catalog-setting.txt',E/'catalog-setting.txt')
paths=[p for folder in (H,work,E/'source',R/'config/skills/_shared',R/'config/skills/devlyn:resolve') for p in folder.rglob('*') if p.is_file() and '__pycache__' not in p.parts]
paths += [R/'AGENTS.md',R/'autoresearch/experiments/0179/AGENTS.candidate.md',R/'autoresearch/experiments/0185/launch.py',R/'autoresearch/experiments/0184/native.py',R/'autoresearch/scripts/comparison-controller.py',R/'.devlyn/0179/catalog-setting.txt',E/'models_cache.json',E/'catalog-setting.txt',E/'package.json']
registry={'registered_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'base':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),'order':[{'draw':f'instructions-{1 if i<2 else 2}-{arm}','arm':arm,'case':'install'} for i,arm in enumerate('BCCB')],'sha256':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}}
with (E/'REGISTRATION.json').open('x') as f:json.dump(registry,f,indent=2)
print('REGISTERED',len(registry['sha256']),hashlib.sha256((E/'REGISTRATION.json').read_bytes()).hexdigest())
