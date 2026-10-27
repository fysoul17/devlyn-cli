// Root's check of c020's claim "If the body isn't an object, both fields count as missing" (0258 c031 and 0259 c014
// line). c020 exports only `app` and reads ITEMS_FILE, so the store is a temp copy of the seed set through ITEMS_FILE
// before the server loads. Sends syntactically valid non-object JSON bodies to POST /items. Both fields missing gives
// 400 {error:'invalid_body', field:'name'} (name is checked first). Exit 1 when any such body does not get it (claim
// falsified), 0 when all do, 2 when the setup fails.
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const http = require('node:http');

const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'c020-'));
process.env.ITEMS_FILE = path.join(dir, 'items.json');
fs.copyFileSync(path.join(process.cwd(), 'data', 'items.json'), process.env.ITEMS_FILE);
let app;
try {
  ({ app } = require(path.join(process.cwd(), 'server')));
} catch (error) {
  console.error(error);
  process.exit(2);
}

const server = http.createServer(app).listen(0, '127.0.0.1', async () => {
  const results = [];
  for (const body of ['null', '5', '"text"', 'true', '[1]']) {
    results.push(await new Promise((resolve) => {
      const req = http.request({ host: '127.0.0.1', port: server.address().port, path: '/items', method: 'POST',
        headers: { 'content-type': 'application/json' } }, (res) => {
        let text = '';
        res.on('data', (chunk) => (text += chunk));
        res.on('end', () => {
          let parsed = null;
          try { parsed = JSON.parse(text); } catch {}
          resolve({ body, status: res.statusCode, type: res.headers['content-type'],
            ok: res.statusCode === 400 && parsed?.error === 'invalid_body' && parsed?.field === 'name' });
        });
      });
      req.end(body);
    }));
  }
  server.close();
  console.log(JSON.stringify(results));
  process.exit(results.every((item) => item.ok) ? 0 : 1);
});
