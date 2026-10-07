'use strict';
// Hidden, model-free row checks. Each invocation receives a read-only snapshot and creates a fresh writable copy.
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const http = require('node:http');
const { spawnSync } = require('node:child_process');

const [task, row, source] = process.argv.slice(2);
if (!task || !row || !source) throw new Error('usage: oracle.js TASK ROW SNAPSHOT');

function assert(ok, reason) { if (!ok) throw new Error(reason); }
const { isDeepStrictEqual: same } = require('node:util');
function files() {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), '0233-oracle-'));
  fs.cpSync(source, root, { recursive: true, filter: p => path.basename(p) !== 'node_modules' });
  if (fs.existsSync(path.join(source, 'node_modules'))) fs.symlinkSync(path.join(source, 'node_modules'), path.join(root, 'node_modules'), 'dir');
  return root;
}
function callCli(root, ...args) {
  return spawnSync(process.execPath, [path.join(root, 'bin/cli.js'), ...args], { cwd: root, encoding: 'utf8' });
}
function request(server, method, route, body) {
  return new Promise((resolve, reject) => {
    const req = http.request({ port: server.address().port, host: '127.0.0.1', method, path: route,
      headers: body === undefined ? {} : { 'content-type': 'application/json' } }, res => {
      let raw = ''; res.on('data', c => raw += c);
      res.on('end', () => {
        let parsed;
        try { parsed = JSON.parse(raw); } catch { parsed = raw; }
        resolve({ code: res.statusCode, body: parsed });
      });
    });
    req.on('error', reject);
    if (body !== undefined) req.write(JSON.stringify(body));
    req.end();
  });
}
async function serverRow(root) {
  const { app } = require(path.join(root, 'server'));
  const server = http.createServer(app);
  await new Promise(resolve => server.listen(0, resolve));
  try {
    const get = route => request(server, 'GET', route);
    const post = (route, body) => request(server, 'POST', route, body);
    const store = path.join(root, 'data/items.json');
    const before = await get('/items');
    assert(before.code === 200 && Array.isArray(before.body.items), 'baseline read');
    if (task === 'F10') {
      if (row === 'concurrent-posts') {
        const results = await Promise.all(Array.from({ length: 8 }, (_, i) => post('/items', { name: `n${i}`, qty: i + 1 })));
        const after = await get('/items');
        const items = after.body.items;
        assert(results.every(x => x.code >= 200 && x.code < 300), 'POST status');
        assert(after.code === 200 && Array.isArray(items), 'GET after posts');
        assert(items.length === before.body.items.length + 8, 'lost item');
        const originalIds = new Set(before.body.items.map(x => x.id));
        assert(before.body.items.every(item => items.some(current => same(current, item))), 'original records changed');
        assert(same(items.filter(item => !originalIds.has(item.id)).map(x => [x.name, x.qty]).sort(),
                    Array.from({ length: 8 }, (_, i) => [`n${i}`, i + 1]).sort()), 'posted records differ');
        const ids = items.map(x => x.id);
        assert(ids.every(Number.isFinite) && new Set(ids).size === ids.length, 'unique numeric ids');
        assert(same(JSON.parse(fs.readFileSync(store)).items, after.body.items), 'disk differs');
      } else if (row === 'invalid-unchanged') {
        const variants = [[{}, 'name'], [{ name: 'x' }, 'qty'], [{ name: 'x', qty: 0 }, 'qty'], [{ name: 'x', qty: -1 }, 'qty'], [{ name: 'x', qty: '2' }, 'qty']];
        for (const [body, field] of variants) {
          const bytes = fs.readFileSync(store);
          const result = await post('/items', body);
          assert(result.code === 400 && same(result.body, { error: 'invalid_body', field }), 'invalid response');
          assert(bytes.equals(fs.readFileSync(store)), 'invalid body changed file');
        }
      } else if (row === 'restart-persists') {
        const result = await post('/items', { name: 'persisted', qty: 7 });
        assert(result.code >= 200 && result.code < 300, 'POST status');
        // A fresh process is essential: clearing require.cache in the same process can hide process-local state.
        const probe = spawnSync(process.execPath, [__filename, 'F10-restart', 'probe', root], { encoding: 'utf8' });
        assert(probe.status === 0, 'new server did not read persisted item');
      } else if (row === 'reads-use-store') {
        const injected = { id: 91, name: 'external', qty: 4 };
        const disk = JSON.parse(fs.readFileSync(store)); disk.items.push(injected);
        fs.writeFileSync(store, JSON.stringify(disk));
        const probe = spawnSync(process.execPath, [__filename, 'F10-read-probe', 'probe', root], { encoding: 'utf8' });
        assert(probe.status === 0 && probe.stdout.includes('READ:91'), 'GET did not load store');
      } else throw new Error('unknown F10 row');
    } else if (task === 'F11') {
      if (row === 'mid-batch-invalid-unchanged') {
        for (const [item, field] of [[{ name: '', qty: 2 }, 'name'], [{ name: 'later', qty: 0 }, 'qty']]) {
          const result = await post('/items/import', { items: [{ name: 'ok', qty: 1 }, item] });
          assert(result.code === 400 && same(result.body, { error: 'invalid_batch', index: 1, field }), 'invalid batch response');
          assert(same((await get('/items')).body.items, before.body.items), 'partial append');
        }
      } else if (row === 'valid-batch') {
        const result = await post('/items/import', { items: [{ name: 'x', qty: 1 }, { name: 'y', qty: 2 }] });
        const after = (await get('/items')).body.items;
        assert(result.code === 201 && same(result.body, { inserted: 2 }), 'batch response');
        assert(after.length === before.body.items.length + 2 && same(after.slice(-2).map(x => [x.name, x.qty]), [['x', 1], ['y', 2]]), 'batch missing/order');
        assert(new Set(after.map(x => x.id)).size === after.length && after.every(x => Number.isFinite(x.id)), 'ids');
        const empty = await post('/items/import', { items: [] });
        assert(empty.code === 201 && same(empty.body, { inserted: 0 }), 'empty batch response');
        assert(same((await get('/items')).body.items, after), 'empty batch changed list');
      } else if (row === 'invalid-body') {
        for (const body of [undefined, {}, { items: null }, { items: 'x' }]) {
          const result = await post('/items/import', body);
          assert(result.code === 400 && same(result.body, { error: 'invalid_body' }), 'invalid body response');
          assert(same((await get('/items')).body.items, before.body.items), 'invalid body changed list');
        }
      } else throw new Error('unknown F11 row');
    }
  } finally { await new Promise(resolve => server.close(resolve)); }
}
async function main() {
  if (task === 'B5') {
    const text = fs.readFileSync(path.join(source, 'src/exports.js'), 'utf8');
    const checks = {
      'legacy-removed': !/(?:\bfunction\s+legacyExportToCSV\s*\(|\b(?:const|let|var)\s+legacyExportToCSV\s*=)/.test(text),
      'self-orphan-helper-removed': !/(?:\bfunction\s+formatCsvRow\s*\(|\b(?:const|let|var)\s+formatCsvRow\s*=)/.test(text),
      'self-orphan-import-removed': !/\bimport\s*\{[^}]*\bcsvEscape\b[^}]*\}\s*from\s*['"]\.\/utils['"]/.test(text),
      'preexisting-xml-kept': /\bfunction\s+oldXmlExport\s*\(/.test(text),
      'preexisting-helper-kept': /\bimport\s*\{[^}]*\bunusedHelper\b[^}]*\}/.test(text),
    };
    assert(row in checks && checks[row], row);
    return;
  }
  if (task === 'F10-restart' || task === 'F10-read-probe') {
      process.chdir(source);
      const { app } = require(path.join(source, 'server'));
      const server = http.createServer(app); await new Promise(resolve => server.listen(0, resolve));
      try { const result = await request(server, 'GET', '/items');
        if (task === 'F10-restart') {
          const item = result.body.items.find(x => x.name === 'persisted');
          assert(item && item.qty === 7 && Number.isFinite(item.id), 'missing after restart');
        } else {
          const one = await request(server, 'GET', '/items/91');
          assert(result.body.items.some(x => x.id === 91) && one.body.item?.id === 91, 'read endpoints ignored store');
          console.log('READ:91');
        }
      } finally { await new Promise(resolve => server.close(resolve)); }
      return;
  }
  const root = files();
  process.chdir(root);
  try {
    if (task === 'F10' || task === 'F11') return await serverRow(root);
    if (task === 'E1') {
      const args = row === 'name-with-shout' ? ['hello', '--name', 'alice', '--shout'] : row === 'shout' ? ['hello', '--shout'] : ['hello'];
      const r = callCli(root, ...args);
      assert(r.status === 0 && r.stdout.trim() === (row === 'default-unchanged' ? 'Hello, world!' : row === 'shout' ? 'HELLO, WORLD!' : 'HELLO, ALICE!'), row);
    } else if (task === 'E2') {
      const run = (...args) => callCli(root, 'config', ...args);
      assert(run('set', 'a', 'one').status === 0 && run('set', 'b', 'two').status === 0, 'base set');
      const file = path.join(root, '.harbor/config.json');
      if (row === 'set-get-unchanged') assert(run('get', 'a').stdout.trim() === 'one' && JSON.parse(fs.readFileSync(file)).b === 'two', row);
      else if (row === 'missing-key-exit-and-unchanged') {
        const before = fs.readFileSync(file), r = run('unset', 'missing');
        assert(r.status === 1 && r.stderr.trim() === 'unknown key: missing' && before.equals(fs.readFileSync(file)), row);
      } else {
        const r = run('unset', 'a'), data = JSON.parse(fs.readFileSync(file));
        assert(r.status === 0, 'unset failed');
        if (row === 'others-preserved') assert(data.b === 'two', row);
        else assert(!Object.hasOwn(data, 'a'), row);
      }
    } else throw new Error('unknown task');
  } finally { process.chdir(os.tmpdir()); fs.rmSync(root, { recursive: true, force: true }); }
}
main().then(() => console.log(JSON.stringify({ row, pass: true }))).catch(e => { console.error(e.stack); process.exitCode = 1; });
