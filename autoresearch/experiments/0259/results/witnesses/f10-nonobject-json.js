// Root's check of c031's claim "A body that isn't a JSON object is treated as empty, so it gets field: 'name'".
// Sends syntactically valid non-object JSON bodies to POST /items on a temp copy of the seed.
// Exit 1 when any such body does not get 400 {error:'invalid_body', field:'name'} (claim falsified), 0 when all do.
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const http = require('node:http');
const { createApp } = require(path.join(process.cwd(), 'server'));

const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'c031-'));
const dataFile = path.join(dir, 'items.json');
fs.copyFileSync(path.join(process.cwd(), 'data', 'items.json'), dataFile);
const server = http.createServer(createApp({ dataFile })).listen(0, async () => {
  const results = [];
  for (const body of ['null', '5', '"text"', 'true', '[1]']) {
    results.push(await new Promise((resolve) => {
      const req = http.request({ port: server.address().port, path: '/items', method: 'POST',
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
