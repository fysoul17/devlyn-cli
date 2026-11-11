// Origin: 0260/results/witnesses/f10-one-process-path-alias.js; sha256 21088c64050723c55d2314441d86061e3a4cc15ea91e0a927a732ff6c4819239.
// Applicability: exported createApp function required (exit 3); errors exit 2 (unresolved).
// Root's check of c011's sentences "each save is queued behind the previous one for the same file" and "The save queue
// only works inside one Node process" (result review round 1). Same as f10-one-process-two-apps.js, except that the
// second createApp instance names the same temp file by its path relative to the working directory, while the first
// uses the absolute path. Run on every tree whose module-level queue is keyed by file. Exit 1 when an item answered
// 201 is missing (an acknowledged item lost), 0 when none is, 2 on setup or runtime failure.
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
    const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'f10-alias-'));
    const dataFile = path.join(dir, 'items.json');
    fs.copyFileSync(path.join(process.cwd(), 'data', 'items.json'), dataFile);
    servers.push(await listen(make(dataFile)), await listen(make(path.relative(process.cwd(), dataFile))));
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
