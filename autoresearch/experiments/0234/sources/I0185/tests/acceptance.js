const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {fixture, snapshot, injected} = require('./support');

function use(body, fresh = false) {
  const f = fixture(process.env.PRODUCT || path.resolve('bin/devlyn.js'), fresh);
  try { body(f); } finally { f.dispose(); }
}
test('complete replacement, final stamp, unrelated content, repeat install', () => use(f => {
  const user = snapshot(path.join(f.target, 'custom'));
  const source = snapshot(f.source);
  assert.equal(f.run(), 6);
  for (const name of f.names) {
    const dir = path.join(f.target, name);
    assert.equal(fs.existsSync(path.join(dir, 'old.txt')), false);
    assert.ok(fs.readFileSync(path.join(dir, 'SKILL.md'), 'utf8').includes('${CLAUDE_SKILL_DIR:-' + dir + '}'));
  }
  assert.equal(fs.existsSync(path.join(f.target, 'devlyn:auto-resolve')), false);
  assert.equal(fs.existsSync(path.join(f.root, 'agent/commands/devlyn.handoff.md')), false);
  assert.deepEqual(snapshot(path.join(f.target, 'custom')), user);
  assert.deepEqual(snapshot(f.source), source);
  const installed = snapshot(path.join(f.root, 'agent'));
  assert.equal(f.run(), 6);
  assert.deepEqual(snapshot(path.join(f.root, 'agent')), installed);
  assert.equal(f.api.installSkillsForCLI('unknown'), 0);
}));
test('copy failure restores previous installation and permits retry', () => use(f => {
  const before = snapshot(path.join(f.root, 'agent'));
  const fired = injected('copyFileSync', src => String(src).includes('devlyn:ideate'), () => {throw new Error('injected copy failure');}, () => {
    assert.throws(f.run, /injected copy failure/);
  });
  assert.ok(fired);
  assert.deepEqual(snapshot(path.join(f.root, 'agent')), before);
  assert.equal(f.run(), 6);
}));
test('invalid source preserves existing marker and all prior paths', () => use(f => {
  fs.rmSync(path.join(f.source, 'devlyn:queue'), {recursive:true});
  const before = snapshot(path.join(f.root, 'agent'));
  assert.throws(f.run);
  assert.deepEqual(snapshot(path.join(f.root, 'agent')), before);
}));
test('same destination contention refuses promptly and does not release owner lock', () => use(f => {
  let refused = 0;
  const fired = injected('copyFileSync', src => String(src).startsWith(f.source), () => {
    for (let n = 0; n < 2; n++) {
      assert.throws(f.run, /busy|lock|progress/i); refused++;
    }
    assert.equal(f.api.installSkillsForCLI('omp'), 6);
  }, () => assert.equal(f.run(), 6));
  assert.ok(fired); assert.equal(refused, 2);
  assert.equal(f.run(), 6);
}));
test('failed first installation restores absent destination', () => use(f => {
  const fired = injected('copyFileSync', src => String(src).startsWith(f.source), () => {throw new Error('first install failed');}, () => assert.throws(f.run, /first install failed/));
  assert.ok(fired);
  assert.equal(fs.existsSync(f.target), false);
  assert.equal(f.run(), 6);
}, true));
