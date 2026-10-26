// Root's check of the codex assessor's severe finding on c007: two createApp({ dataFile }) instances on one store
// can both answer 201 while one append is lost. Starts two server processes (distinct pids, as two deployments
// would be) on a temp copy of the seed, sends one POST to each at once, and repeats for up to 20 rounds.
// Exit 1 when a round has both POSTs 201 and the store lacks one of the created items, 0 when no round does,
// 2 when the setup fails.
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const http = require('node:http');
const { fork } = require('node:child_process');

if (process.argv[2] === 'serve') {
  const { createApp } = require(path.join(process.cwd(), 'server'));
  const server = http.createServer(createApp({ dataFile: process.argv[3] })).listen(0, '127.0.0.1', () => {
    process.send(server.address().port);
  });
  return;
}

function start(dataFile) {
  return new Promise((resolve, reject) => {
    const child = fork(__filename, ['serve', dataFile], { cwd: process.cwd(), stdio: ['ignore', 'ignore', 'inherit', 'ipc'] });
    child.once('message', (port) => resolve({ child, port }));
    child.once('error', reject);
    child.once('exit', (code) => reject(new Error(`server exited ${code}`)));
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
        resolve({ status: res.statusCode, item: parsed && parsed.item });
      });
    });
    req.on('error', reject);
    req.end(body);
  });
}

(async () => {
  const servers = [];
  try {
    const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'c007-'));
    const dataFile = path.join(dir, 'items.json');
    fs.copyFileSync(path.join(process.cwd(), 'data', 'items.json'), dataFile);
    servers.push(await start(dataFile), await start(dataFile));
    const rounds = [];
    for (let round = 0; round < 20; round += 1) {
      const names = [`a-${round}`, `b-${round}`];
      const answers = await Promise.all(servers.map((server, index) => post(server.port, names[index])));
      const stored = JSON.parse(fs.readFileSync(dataFile, 'utf8')).items.map((item) => item.name);
      const lost = answers.every((answer) => answer.status === 201) && names.some((name) => !stored.includes(name));
      rounds.push({ round, statuses: answers.map((answer) => answer.status), ids: answers.map((answer) => answer.item && answer.item.id), lost });
      if (lost) break;
    }
    console.log(JSON.stringify(rounds));
    process.exitCode = rounds.some((round) => round.lost) ? 1 : 0;
  } catch (error) {
    console.error(error);
    process.exitCode = 2;
  } finally {
    for (const { child } of servers) child.kill();
  }
})();
