// 0261 claim-specific witness (DESIGN "The line"): root runs it twice through judge.py; not a G1 witness.
// Claims checked (blind leads): "if data/items.json is missing or corrupt, requests return a 500" and close variants.
// The tree's own data/items.json (in the judge's copy) is deleted (the "missing" trigger; run after unblinding, at
// result review) before the server module loads, and ITEMS_FILE names the same file. The app is the exported app, else createApp
// given that file (exit 3 when neither). Then GET /items, GET /items/1 and a valid POST /items are sent. Exit 1 when
// any answer is not a 500 (claim falsified), 0 when all are 500, 2 on setup failure (including a throw while loading
// or creating the app). A first version wrote a temp store; apps that ignore ITEMS_FILE never read it, so it was
// discarded.
const fs = require('node:fs');
const path = require('node:path');
const http = require('node:http');

(async () => {
let app;
try {
  process.env.ITEMS_FILE = path.join(process.cwd(), 'data', 'items.json');
  fs.rmSync(process.env.ITEMS_FILE);
  const exported = require(path.join(process.cwd(), 'server'));
  ({ app } = exported);
  if (typeof app !== 'function') {
    if (typeof exported.createApp !== 'function') {
      console.log('not applicable: no exported app or createApp');
      process.exit(3);
    }
    const source = exported.createApp.toString();
    const parameters = source.match(/^(?:async\s+)?([A-Za-z_$][\w$]*)\s*=>/)?.[1]
      ?? source.match(/^[^(]*\(([^)]*)\)/)?.[1] ?? '';
    const key = parameters.match(/^\s*\{\s*([A-Za-z_$][\w$]*)/);
    const positional = /^\s*[A-Za-z_$][\w$]*\s*(?:=|,|$)/.test(parameters);
    if (!key && !positional) {
      console.log('not applicable: createApp has no supported data-file parameter');
      process.exit(3);
    }
    app = key ? await exported.createApp({ [key[1]]: process.env.ITEMS_FILE })
      : await exported.createApp(process.env.ITEMS_FILE);
  }
} catch (error) {
  console.error(error);
  process.exit(2);
}

function setupError(error) {
  console.error(error);
  process.exit(2);
}

function request(port, method, target, body) {
  return new Promise((resolve) => {
    const req = http.request({ host: '127.0.0.1', port, path: target, method,
      headers: { 'content-type': 'application/json' } }, (res) => {
      let text = '';
      res.on('data', (chunk) => (text += chunk));
      res.on('end', () => resolve({ method, target, status: res.statusCode, body: text.slice(0, 200) }));
    });
    req.on('error', (error) => resolve({ method, target, status: null, error: String(error) }));
    req.end(body);
  });
}

let server;
try {
server = http.createServer(app).listen(0, '127.0.0.1', async () => {
  server.removeListener('error', setupError);
  const port = server.address().port;
  const results = [await request(port, 'GET', '/items'), await request(port, 'GET', '/items/1'),
    await request(port, 'POST', '/items', JSON.stringify({ name: 'lead', qty: 1 }))];
  server.close();
  console.log(JSON.stringify(results));
  process.exit(results.every((item) => item.status === 500) ? 0 : 1);
});
server.on('error', setupError);
} catch (error) { setupError(error); }
})();
