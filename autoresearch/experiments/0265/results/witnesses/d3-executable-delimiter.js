'use strict';
// D3: the first -- must reach a real executable child, so option-like words are operands.
// Exit 1 = defect, 0 = correct, 2 = witness error. Run from /work without network.
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { spawnSync } = require('node:child_process');
const { pathToFileURL } = require('node:url');

try {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'witness-d3-'));
  try {
    const entry = pathToFileURL(path.resolve('index.js')).href;
    const child = path.join(root, 'child.mjs');
    const parent = path.join(root, 'parent.mjs');
    fs.writeFileSync(child, `import { Command } from ${JSON.stringify(entry)};
const program = new Command().name('child').option('--child-option').argument('[operands...]').parse();
console.log(JSON.stringify({rawArgs:process.argv.slice(2),operands:program.args,options:program.opts()}));\n`);
    fs.writeFileSync(parent, `import { Command } from ${JSON.stringify(entry)};
const program = new Command('parent');
const executableFile = ${JSON.stringify(child)};
program.command('child', 'run child', {executableFile}).alias('c');
program.command('default', 'default child', {executableFile,isDefault:true});
program.command('nested').command('child', 'nested child', {executableFile});
program.parse(process.argv.slice(2), {from:'user'});\n`);
    const cases = [
      {name:'direct',args:['child','--','--not-an-option'],rawArgs:['--','--not-an-option'],operands:['--not-an-option']},
      {name:'alias',args:['c','--','--not-an-option'],rawArgs:['--','--not-an-option'],operands:['--not-an-option']},
      {name:'default',args:['before','--','--not-an-option'],rawArgs:['before','--','--not-an-option'],operands:['before','--not-an-option']},
      {name:'later delimiters',args:['child','before','--','after','--','--not-an-option','--'],rawArgs:['before','--','after','--','--not-an-option','--'],operands:['before','after','--','--not-an-option','--']},
      {name:'nested',args:['nested','child','--','--not-an-option'],rawArgs:['--','--not-an-option'],operands:['--not-an-option']},
    ];
    const results = [];
    for (const c of cases) {
      const done = spawnSync(process.execPath, [parent, ...c.args], {encoding:'utf8',timeout:5000,
        detached:true,env:{...process.env,NODE_OPTIONS:''}});
      // The parent may have spawned a child before a timeout; clear its group.
      if (done.pid) {
        try { process.kill(-done.pid, 'SIGKILL'); } catch (error) { if (error.code !== 'ESRCH') throw error; }
      }
      if (done.error && done.error.code !== 'ETIMEDOUT') throw done.error;
      let actual = null;
      try { actual = JSON.parse(done.stdout.trim().split('\n').at(-1)); } catch (_) { /* child may reject the argument */ }
      const expected = {rawArgs:c.rawArgs,operands:c.operands,options:{}};
      results.push({name:c.name,status:done.status,error:done.error && done.error.code || null,
        actual,ok:done.status===0 && JSON.stringify(actual)===JSON.stringify(expected),stderr:done.stderr.slice(-250)});
    }
    console.log(JSON.stringify({results}));
    process.exitCode = results.every(x=>x.ok) ? 0 : 1;
  } finally { fs.rmSync(root,{recursive:true,force:true}); }
} catch (error) {
  console.log('WITNESS ERROR: '+(error && error.stack || error));
  process.exitCode=2;
}
