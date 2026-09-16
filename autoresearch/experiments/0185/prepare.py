from pathlib import Path
import datetime,hashlib,json,os,shutil,subprocess
HERE=Path(__file__).resolve().parent
REPO=HERE.parents[2];E=REPO/'.devlyn/0185'
SCRATCH=REPO/'.git/devlyn-completion/1dfef6c599ae0b1b68b57f13/scratch'

def main():
 source=E/'source';original=(source/'original.js').read_text();reference=(source/'reference.js').read_text()
 mutants={
 'rollback':reference.replace('for(const restore of undo.reverse())','for(const restore of [])'),
 'lock':reference.replace('try { fs.mkdirSync(lock); }','try { fs.mkdirSync(lock,{recursive:true}); }'),
 'stamp':reference.replace('stampInstalledSkillDir(dest,path.join(target,physicalSkillName(name)))','stampInstalledSkillDir(dest,dest)')}
 rows=[]
 for name,code in [('original',original),('reference',reference),*mutants.items()]:
  p=source/(name+'.js')
  if name not in ('original','reference'):p.write_text(code)
  env={**os.environ,'PRODUCT':str(p),'TMPDIR':str(SCRATCH)}
  result=subprocess.run(['node','--test',str(HERE/'acceptance.js'),str(HERE/'heldout.js')],cwd=REPO,env=env,capture_output=True,timeout=90)
  out=E/('calibration-final-'+name);out.with_suffix('.stdout').write_bytes(result.stdout);out.with_suffix('.stderr').write_bytes(result.stderr)
  rows.append(dict(control=name,exit_code=result.returncode,expected_pass=name=='reference',stdout=str(out.with_suffix('.stdout'))))
 (E/'CALIBRATION.json').write_text(json.dumps(rows,indent=2))
 print(json.dumps(rows),flush=True)
 assert all((r['exit_code']==0)==r['expected_pass'] for r in rows)
 work=E/'inputs/install';(work/'bin').mkdir(parents=True);(work/'tests').mkdir()
 shutil.copyfile(source/'original.js',work/'bin/devlyn.js')
 shutil.copyfile(REPO/'package.json',work/'package.json')
 shutil.copyfile(HERE/'request.md',work/'spec.md')
 for name in ('support.js','acceptance.js'):shutil.copyfile(HERE/name,work/'tests'/name)
 (work/'.gitignore').write_text('.devlyn/\n.agents/\n__pycache__/\n*.pyc\n')
 (work/'spec.expected.json').write_text(json.dumps(dict(required_files=['bin/devlyn.js'],forbidden_files=['spec.md','spec.expected.json','package.json','.gitignore','tests/support.js','tests/acceptance.js'],verification_commands=[dict(cmd='node --test tests/acceptance.js',exit_code=0,timeout_sec=90)]),indent=2)+'\n')
 shutil.copyfile(REPO/'.devlyn/0184/models_cache.json',E/'models_cache.json')
 paths=[p for folder in (HERE,work,REPO/'config/skills/_shared',REPO/'config/skills/devlyn:resolve') for p in folder.rglob('*') if p.is_file() and '__pycache__' not in p.parts]
 paths += [REPO/'AGENTS.md',REPO/'autoresearch/experiments/0179/AGENTS.candidate.md',REPO/'autoresearch/scripts/comparison-controller.py',REPO/'.devlyn/0179/catalog-setting.txt',E/'models_cache.json']
 registry=dict(registered_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),base=subprocess.check_output(['git','rev-parse','HEAD'],cwd=REPO,text=True).strip(),order=[dict(draw=f'install-{1 if i<3 else 2}-{arm}',arm=arm,case='install') for i,arm in enumerate('ABCCBA')],sha256={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths})
 with (E/'REGISTRATION.json').open('x') as f:json.dump(registry,f,indent=2)
 print('REGISTERED',len(registry['sha256']),hashlib.sha256((E/'REGISTRATION.json').read_bytes()).hexdigest(),flush=True)
if __name__=='__main__':main()
