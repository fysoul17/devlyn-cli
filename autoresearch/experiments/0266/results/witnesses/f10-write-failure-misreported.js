'use strict';
// 0266 witness f10-write-failure-misreported (DESIGN "New witness"), run from a disposable snapshot at /work in the
// cell image without network, not as root. The snapshot is copied into the container's own filesystem first: on
// Docker Desktop's macOS bind mount a read-only mode does not stop the container user from writing (seen 2026-11-12),
// on the container's filesystem it does. The tree's app is started from that copy in a child process on the tree's own
// store (data/items.json under the tree): its exported app, else its exported createApp given that file the way 0260's
// f10-nonobject-items-file does. Once GET /items answers 200, data/items.json and data/ are made read-only and one
// valid item is posted to /items. A 5xx: the failure is reported as the server's (exit 0, does not reproduce). Any other
// response, a 4xx (the client is told its input was wrong) or a 2xx (that the item was saved): misreported (exit 1,
// reproduces). No response within 10 s (the server hung, crashed or dropped the connection): unresolved (exit 2), and
// exit 2 too when the store is still writable (run as root). A tree that cannot be driven (no exported app or
// createApp, the app does not load or listen, or GET /items does not answer 200) reads not applicable (exit 3).
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const http = require('node:http');
const { fork } = require('node:child_process');

const STORE = path.join(process.cwd(), 'data');  // in the child: the copy's own store
const FILE = path.join(STORE, 'items.json');

async function serve() {
  const exported = require(path.join(process.cwd(), 'server'));
  let app = exported.app;
  if (typeof app !== 'function') {
    if (typeof exported.createApp !== 'function') throw new Error('no exported app or createApp');
    const source = exported.createApp.toString();
    const parameters = source.match(/^(?:async\s+)?([A-Za-z_$][\w$]*)\s*=>/)?.[1]
      ?? source.match(/^[^(]*\(([^)]*)\)/)?.[1] ?? '';
    const key = parameters.match(/^\s*\{\s*([A-Za-z_$][\w$]*)/);
    const positional = /^\s*[A-Za-z_$][\w$]*\s*(?:=|,|$)/.test(parameters);
    if (!key && !positional) throw new Error('createApp has no supported data-file parameter');
    app = key ? await exported.createApp({ [key[1]]: FILE }) : await exported.createApp(FILE);
  }
  const server = http.createServer(app);
  await new Promise((resolve, reject) => {
    server.once('error', reject);
    server.listen(0, '127.0.0.1', resolve);
  });
  process.send({ port: server.address().port });
}

function request(port, method, route, body) {
  return new Promise((resolve, reject) => {
    const req = http.request({ host: '127.0.0.1', port, method, path: route,
      headers: body === undefined ? {} : { 'content-type': 'application/json', 'content-length': Buffer.byteLength(body) } },
    (res) => {
      let text = '';
      res.setEncoding('utf8');
      res.on('data', (chunk) => { text += chunk; });
      res.on('end', () => resolve({ status: res.statusCode, body: text.slice(0, 400) }));
      res.on('error', reject);
    });
    req.setTimeout(10000, () => req.destroy(new Error('no response within 10 s')));
    req.on('error', reject);
    req.end(body);
  });
}

function started(child) {
  return new Promise((resolve) => {
    const timer = setTimeout(() => resolve({ error: 'the app did not listen within 15 s' }), 15000);
    child.once('message', (message) => { clearTimeout(timer); resolve(message); });
    child.once('exit', (code, signal) => { clearTimeout(timer); resolve({ error: `the app exited (${code ?? signal})` }); });
  });
}

function finish(code, record) {
  console.log(JSON.stringify(record));
  process.exit(code);
}

async function main() {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'write-failure-'));
  fs.cpSync(process.cwd(), root, { recursive: true, verbatimSymlinks: true });
  const store = path.join(root, 'data');
  const file = path.join(store, 'items.json');
  const child = fork(__filename, ['serve'], { cwd: root, stdio: ['ignore', 'ignore', 'pipe', 'ipc'] });
  let stderr = '';
  child.stderr.on('data', (chunk) => { stderr = (stderr + chunk).slice(-2000); });
  const end = (code, record) => { child.kill('SIGKILL'); finish(code, { ...record, server_stderr: stderr }); };
  const ready = await started(child);
  if (!ready.port) return end(3, { result: 'not applicable', reason: ready.error });
  try {
    const baseline = await request(ready.port, 'GET', '/items');
    if (baseline.status !== 200) return end(3, { result: 'not applicable', reason: `GET /items ${baseline.status}` });
  } catch (error) {
    return end(3, { result: 'not applicable', reason: `GET /items: ${error}` });
  }
  try {
    fs.chmodSync(file, 0o444);
    fs.chmodSync(store, 0o555);
  } catch (error) {
    return end(2, { result: 'unresolved', reason: `the store could not be made read-only: ${error}` });
  }
  for (const target of [store, file]) {
    try {
      fs.accessSync(target, fs.constants.W_OK);
      return end(2, { result: 'unresolved', reason: `${target} is still writable` });
    } catch {}
  }
  let response;
  try {
    response = await request(ready.port, 'POST', '/items', '{"name":"write-failure","qty":1}');
  } catch (error) {
    return end(2, { result: 'unresolved', reason: String(error) });
  }
  const failure = response.status >= 500 && response.status <= 599;
  return end(failure ? 0 : 1, { result: failure ? 'reported as a server failure' : 'misreported', ...response });
}

if (process.argv[2] === 'serve') {
  serve().catch((error) => {
    console.error(String(error && error.stack || error));
    process.exit(64);
  });
} else {
  main().catch((error) => finish(2, { result: 'unresolved', reason: String(error) }));
}
