const fs=require('node:fs');const path=require('node:path');
const {fixture,snapshot}=require('../../0185/support');
const product=path.resolve(process.argv[2]);const f=fixture(product,true);
const rename=fs.renameSync,rmdir=fs.rmdirSync;
let failed=false,contender=false,innerError=null,innerReturn=null,outerError=null;
try {
 fs.renameSync=function(from,to,...rest){
  if(!failed && String(to)===path.join(f.target,'devlyn:ideate')){failed=true;throw Error('REPLAY_SECOND_PUBLICATION');}
  return rename.call(this,from,to,...rest);
 };
 fs.rmdirSync=function(dir,...rest){
  if(failed && !contender && String(dir)===f.target){
   contender=true;
   try{innerReturn=f.run();}catch(error){innerError=String(error);}
  }
  return rmdir.call(this,dir,...rest);
 };
 try{f.run();}catch(error){outerError=String(error);}
 fs.renameSync=rename;fs.rmdirSync=rmdir;
 console.log(JSON.stringify({product,failed,contender,innerError,innerReturn,outerError,
  targetAbsent:!fs.existsSync(f.target),after:snapshot(path.join(f.root,'agent')),
  passed:failed && contender && !!innerError && /busy|lock|progress/i.test(innerError) && !!outerError && !fs.existsSync(f.target)}));
}finally{fs.renameSync=rename;fs.rmdirSync=rmdir;f.dispose();}
