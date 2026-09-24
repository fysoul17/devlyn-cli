// Post-seal source-adjudication replay; never part of a participant prompt.
const fs=require('node:fs');
const path=require('node:path');
const {fixture,snapshot,injected}=require('../../0185/support');
const [product,kind]=process.argv.slice(2);
const f=fixture(path.resolve(product));
let result;
try {
  if(kind==='alias') {
    const alias=path.join(f.root,'alias-agent');fs.mkdirSync(alias);fs.symlinkSync(f.target,path.join(alias,'skills'));
    f.api.CLI_TARGETS.omp.skillsDir=path.join(alias,'skills');
    let innerError=null,innerReturn=null,innerUnchanged=false,outerError=null,outerReturn=null;
    const fired=injected('copyFileSync',src=>String(src).startsWith(f.source),()=>{
      const before=snapshot(path.join(f.root,'agent'));
      try{innerReturn=f.api.installSkillsForCLI('omp');}catch(error){innerError=String(error);}
      innerUnchanged=JSON.stringify(snapshot(path.join(f.root,'agent')))===JSON.stringify(before);
    },()=>{try{outerReturn=f.run();}catch(error){outerError=String(error);}});
    result={kind,fired,innerError,innerReturn,innerUnchanged,outerError,outerReturn,
      passed:fired && !!innerError && /busy|lock|progress/i.test(innerError) && innerUnchanged && outerError===null && outerReturn===6};
  } else if(kind==='release') {
    const before=snapshot(path.join(f.root,'agent'));
    const methods=['rmdirSync','rmSync','unlinkSync'];const originals={};const removals=[];
    let fired=null,error=null,returned=null;
    for(const method of methods){
      originals[method]=fs[method];
      fs[method]=function(...args){
        const target=String(args[0]);
        if(target.startsWith(path.join(f.root,'agent'))){
          removals.push({method,path:target.replace(f.root,'<fixture>')});
          // Source inspection must confirm the selected path is the owned lock.
          if(!fired && /lock/i.test(path.basename(target))){
            fired=removals.at(-1);throw Error('REPLAY_LOCK_RELEASE');
          }
        }
        return originals[method].apply(this,args);
      };
    }
    try{returned=f.run();}catch(e){error=String(e);}finally{for(const method of methods)fs[method]=originals[method];}
    const after=snapshot(path.join(f.root,'agent'));
    const restored=JSON.stringify(after)===JSON.stringify(before);
    result={kind,fired,error,returned,restored,before,after,removals,passed:!!fired && !!error && restored};
  } else throw Error('expected alias|release');
  result.product=path.resolve(product);
  console.log(JSON.stringify(result));
} finally {f.dispose();}
