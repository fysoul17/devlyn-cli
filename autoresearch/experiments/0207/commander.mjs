// External oracle. Only the supplied repository is imported; no participant edits.
import assert from 'node:assert/strict';
import { pathToFileURL } from 'node:url';
import { mkdtempSync, writeFileSync, rmSync } from 'node:fs';
import { join } from 'node:path';
import { spawnSync } from 'node:child_process';
const [repo, task, scratch] = process.argv.slice(2);
const uri = pathToFileURL(join(repo, 'index.js')).href;
const { Command, Option } = await import(uri);
const results = [];
function check(id, fn) {
  try { fn(); results.push({ id, pass: true }); }
  catch (e) { results.push({ id, pass: false, error: String(e) }); }
}
const command = () => new Command().exitOverride().configureOutput({ writeErr: () => {} });
if (task === 'D1') {
  check('D1.1', () => {
    for (const flag of ['<值...>', '[值...]']) {
      const opt = new Option('--tag ' + flag);
      assert.equal(opt.variadic, true);
      assert.deepEqual(command().addOption(opt).parse(['--tag', 'one', 'two'], { from: 'user' }).opts(), { tag: ['one', 'two'] });
    }
  });
  check('D1.2', () => {
    for (const word of ['value', 'A1_', '9', 'λ', '١٢', '数']) {
      for (const flag of [`<${word}...>`, `[${word}...]`]) {
        assert.equal(new Option('--tag ' + flag).variadic, true, flag);
      }
    }
  });
  check('D1.3', () => {
    for (const flag of ['<value,...>', '[value,...]', '<value|...>', '<...>', '[...]', '<value>', '[值]']) {
      assert.equal(new Option('--tag ' + flag).variadic, false, flag);
    }
    assert.deepEqual(command().option('--tag <值>').argument('[rest...]').parse(['--tag', 'one', 'two'], { from: 'user' }).opts(), { tag: 'one' });
  });
  check('D1.4', () => {
    const p = command().option('--tag <值...>').option('--done');
    p.parse(['--tag', 'one', 'two', '--done'], { from: 'user' });
    assert.deepEqual(p.opts(), { tag: ['one', 'two'], done: true });
    assert.ok(p.helpInformation().includes('--tag <值...>'));
  });
} else if (task === 'D3') {
  const dir = mkdtempSync(join(scratch, 'child-'));
  try {
    writeFileSync(join(dir, 'child.mjs'), `import {Command} from ${JSON.stringify(uri)};
const p=new Command().option('--child').argument('[values...]').action(values=>console.log(JSON.stringify({argv:process.argv.slice(2),values,opts:p.opts()})));p.parse();`);
    writeFileSync(join(dir, 'parent.mjs'), `import {Command} from ${JSON.stringify(uri)};
const p=new Command().name('parent').option('--parent <value>');
p.command('child','child',{executableFile:${JSON.stringify(join(dir, 'child.mjs'))},isDefault:true}).alias('c');p.parse();`);
    const run = (args) => {
      const p = spawnSync(process.execPath, [join(dir, 'parent.mjs'), ...args], { encoding: 'utf8', timeout: 3000 });
      assert.equal(p.error, undefined); assert.equal(p.status, 0, p.stderr);
      return JSON.parse(p.stdout);
    };
    check('D3.1', () => {
      assert.deepEqual(run(['child', '--', '--not-an-option']), { argv: ['--', '--not-an-option'], values: ['--not-an-option'], opts: {} });
    });
    check('D3.2', () => {
      assert.deepEqual(run(['child', 'before', '--', 'after', '--', '--tail']), { argv: ['before', '--', 'after', '--', '--tail'], values: ['before', 'after', '--', '--tail'], opts: {} });
      assert.deepEqual(run(['child', '--child', 'before', '--', '--tail']).opts, { child: true });
    });
    check('D3.3', () => {
      assert.deepEqual(run(['--parent', '--', 'child', '--child', 'plain']), { argv: ['--child', 'plain'], values: ['plain'], opts: { child: true } });
      assert.deepEqual(run(['--parent=x--y', 'child', '--child']).opts, { child: true });
    });
    check('D3.4', () => {
      for (const prefix of [['c'], []]) {
        assert.deepEqual(run([...prefix, '--', '--not-an-option']).values, ['--not-an-option']);
      }
    });
    check('D3.5', () => {
      let actual;
      const p = command(); p.command('child').argument('[values...]').action(v => { actual = v; });
      p.parse(['child', '--', '--literal'], { from: 'user' }); assert.deepEqual(actual, ['--literal']);
      const nested = command(); nested.command('nest').command('leaf').argument('[values...]').action(v => { actual = v; });
      nested.parse(['nest', 'leaf', '--', '--literal'], { from: 'user' }); assert.deepEqual(actual, ['--literal']);
      const pass = command().enablePositionalOptions(); pass.command('child').passThroughOptions().argument('[values...]').action(v => { actual = v; });
      pass.parse(['child', 'one', '--option'], { from: 'user' }); assert.deepEqual(actual, ['one', '--option']);
      const help = spawnSync(process.execPath, [join(dir, 'parent.mjs'), '--help'], { encoding: 'utf8', timeout: 3000 });
      assert.equal(help.status, 0); assert.ok(help.stdout.includes('Usage: parent'));
    });
    // Exit/signal/spawn-failure coverage is executed from the unchanged upstream suite.
  } finally { rmSync(dir, { recursive: true }); }
} else { throw new Error('unknown task'); }
console.log(JSON.stringify(results));
process.exitCode = results.every(r => r.pass) ? 0 : 1;
