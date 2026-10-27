// Origin: 0260/results/witnesses/f10-one-process-two-apps.js; sha256 fb82b9a718743660ed7d5c017f7f18260bb4c9c72ce17cb12f26a1bacb79dfcb.
// Applicability: exported createApp function required (exit 3); errors exit 2 (unresolved).
// Root's check of the F10 sentence "the one-at-a-time handling works within a single (server/Node) process", 0259's
// c007 line applied to every tree that exports createApp: two createApp instances in ONE process on a temp copy of the
// seed, one POST to each at once, up to 20 rounds. createApp's own parameter form is used (an options object with its
// first named key, else a positional path). After every round, every item ever answered 201 must still be stored.
// Exit 1 when one is missing (an acknowledged item lost), 0 when none is, 2 on setup or runtime failure. Non-201 answers, and
// items stored although their POST failed, are recorded.
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const http = require('node:http');
function unresolved(error) {
  console.error(error);
  process.exit(2);
}
process.on('uncaughtException', unresolved);
process.on('unhandledRejection', unresolved);
let make, key;
try {
  const { createApp } = require(path.join(process.cwd(), 'server'));
  if (typeof createApp !== 'function') {
    console.log('not applicable: no exported createApp');
    process.exit(3);
  }
  const source = createApp.toString();
  const params = source.slice(source.indexOf('(') + 1);
  key = params.match(/^\s*\{\s*([A-Za-z_$][\w$]*)/);
  make = key ? (file) => createApp({ [key[1]]: file }) : (file) => createApp(file);
} catch (error) {
  console.error(error);
  process.exit(2);
}

function listen(app) {
  return new Promise((resolve, reject) => {
    const server = http.createServer(app).listen(0, '127.0.0.1', () => resolve(server));
    server.on('error', reject);
  });
}

function post(port, name) {
  return new Promise((resolve, reject) => {
    const body = JSON.stringify({ name, qty: 1 });
    const req = http.request({ host: '127.0.0.1', port, path: '/items', method: 'POST',
      headers: { 'content-type': 'application/json', 'content-length': Buffer.byteLength(body) } }, (res) => {
      let text = '';
      res.on('data', (chunk) => (text += chunk));
      res.on('end', () => {
        let parsed = null;
        try { parsed = JSON.parse(text); } catch {}
        const item = parsed && (parsed.item || parsed);
        resolve({ status: res.statusCode, id: item && item.id });
      });
    });
    req.on('error', reject);
    req.end(body);
  });
}

function stored(dataFile) {
  const data = JSON.parse(fs.readFileSync(dataFile, 'utf8'));
  return (Array.isArray(data) ? data : data.items).map((item) => item.name);
}

(async () => {
  const servers = [];
  try {
    const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'f10-two-apps-'));
    const dataFile = path.join(dir, 'items.json');
    fs.copyFileSync(path.join(process.cwd(), 'data', 'items.json'), dataFile);
    servers.push(await listen(make(dataFile)), await listen(make(dataFile)));
    const rounds = [];
    const acknowledged = [];
    for (let round = 0; round < 20; round += 1) {
      const names = [`a-${round}`, `b-${round}`];
      const answers = await Promise.all(servers.map((server, index) => post(server.address().port, names[index])));
      names.forEach((name, index) => { if (answers[index].status === 201) acknowledged.push(name); });
      const names_stored = stored(dataFile);
      const missing = acknowledged.filter((name) => !names_stored.includes(name));
      const storedAfterFailure = names.filter((name, index) => answers[index].status !== 201 && names_stored.includes(name));
      const lost = missing.length > 0;
      rounds.push({ round, statuses: answers.map((answer) => answer.status), ids: answers.map((answer) => answer.id),
        missing, storedAfterFailure, lost });
      if (lost) break;
    }
    console.log(JSON.stringify({ form: key ? `{ ${key[1]} }` : 'positional', rounds }));
    process.exitCode = rounds.some((round) => round.lost) ? 1 : 0;
  } catch (error) {
    console.error(error);
    process.exitCode = 2;
  } finally {
    for (const server of servers) server.close();
  }
})();
