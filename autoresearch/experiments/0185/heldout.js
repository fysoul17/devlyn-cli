const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {spawnSync} = require('node:child_process');
const {fixture, snapshot, injected} = require('./support');
const product = process.env.PRODUCT || path.resolve('bin/devlyn.js');
function use(body) {const f=fixture(product);try {body(f);} finally {f.dispose();}}

test('another process cannot enter while source copy holds destination lock', () => use(f => {
  const child = `const api=require(${JSON.stringify(path.join(__dirname,'support.js'))}).load(${JSON.stringify(product)},${JSON.stringify(f.root)},${JSON.stringify(f.target)});try{api.installSkillsForCLI('codex');process.exit(9)}catch(e){if(!/busy|lock|progress/i.test(e.message))throw e}`;
  const fired=injected('copyFileSync',src=>String(src).startsWith(f.source),()=>{
    const result=spawnSync(process.execPath,['-e',child],{encoding:'utf8',timeout:5000});
    assert.equal(result.status,0,result.stderr);
  },()=>assert.equal(f.run(),6));
  assert.ok(fired);assert.equal(f.run(),6);
}));
test('ambiguous aliases fail without clearing original marker', () => use(f => {
  f.write('agent/skills/devlyn\uF03Aresolve/existing.txt','alias');
  const before=snapshot(path.join(f.root,'agent'));
  assert.throws(f.run,/ambiguous/i);
  assert.deepEqual(snapshot(path.join(f.root,'agent')),before);
}));
test('single foreign alias is replaced; source missing nested file fails cleanly', () => use(f => {
  fs.renameSync(path.join(f.target,'devlyn:resolve'),path.join(f.target,'devlyn\uF03Aresolve'));
  const before=snapshot(path.join(f.root,'agent'));
  const fired=injected('copyFileSync',src=>String(src).includes('devlyn:queue/references/nested.md'),()=>{throw Error('nested copy fault')},()=>assert.throws(f.run,/nested copy fault/));
  assert.ok(fired);assert.deepEqual(snapshot(path.join(f.root,'agent')),before);
  assert.equal(f.run(),6);assert.equal(fs.existsSync(path.join(f.target,'devlyn\uF03Aresolve')),false);
}));
test('one-shot filesystem fault sweep preserves old or reports post-commit disposal failure', () => {
  const methods=['mkdirSync','copyFileSync','cpSync','writeFileSync','renameSync','rmSync','unlinkSync','rmdirSync'];
  let operations=[];
  function trace(f, failAt) {
    const originals={};let count=0;let fired=null;
    for(const name of methods){
      originals[name]=fs[name];
      fs[name]=function(...args){
        const relevant=args.some(a=>typeof a==='string' && a.startsWith(path.join(f.root,'agent')));
        if(relevant){
          const row={method:name,args:args.filter(a=>typeof a==='string').map(a=>a.replace(f.root,'<fixture>'))};
          if(failAt===undefined)operations.push(row);
          if(count++===failAt){fired=row;throw Error('sweep failure '+name);}
        }
        return originals[name].apply(this,args);
      };
    }
    let error;
    try{f.run();}catch(e){error=e;}finally{for(const name of methods)fs[name]=originals[name];}
    return {error,fired,count};
  }
  use(f=>assert.equal(trace(f).error,undefined));
  assert.ok(operations.length>0);
  // Every observed forward mutation is an independently calibrated injection point.
  for(let index=0;index<operations.length;index++)use(f=>{
    const before=snapshot(path.join(f.root,'agent'));
    const beforeSource=snapshot(f.source);
    const {error,fired}=trace(f,index);
    assert.ok(fired,'unreached '+index);assert.ok(error,'swallowed '+index);
    assert.deepEqual(snapshot(f.source),beforeSource);
    const after=snapshot(path.join(f.root,'agent'));
    if(JSON.stringify(after)!==JSON.stringify(before)){
      assert.ok(['rmSync','unlinkSync','rmdirSync'].includes(fired.method),'incomplete rollback at '+index+' '+JSON.stringify(fired));
      const marker=JSON.parse(fs.readFileSync(path.join(f.target,'.devlyn-install.json'),'utf8'));
      assert.equal(marker.schemaVersion,1);
      for(const name of f.names){assert.ok(fs.existsSync(path.join(f.target,name,'references/nested.md')));assert.equal(fs.existsSync(path.join(f.target,name,'old.txt')),false);}
      assert.equal(fs.existsSync(path.join(f.target,'devlyn:auto-resolve')),false);
      assert.equal(fs.existsSync(path.join(f.root,'agent/commands/devlyn.handoff.md')),false);
      assert.deepEqual(snapshot(path.join(f.target,'custom')),Object.fromEntries(Object.entries(before).filter(([k])=>k==='skills/custom'||k.startsWith('skills/custom/')).map(([k,v])=>[k==='skills/custom'?'.':k.slice('skills/custom/'.length),v])));
    } else {
      assert.equal(f.run(),6,'retry after '+index);
    }
  });
});
