// Root's same-process check of c007's sentence "The one-at-a-time guarantee only holds within a single server
// process": two createApp({ dataFile }) instances in ONE process on a temp copy of the seed, one POST to each at
// once, up to 20 rounds. After every round, every item ever answered 201 must still be in the store. Exit 1 when one
// is missing (an acknowledged item lost), 0 when none is, 2 when the setup fails. Non-201 answers, and items stored
// although their POST failed, are recorded.
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const http = require('node:http');
const { createApp } = require(path.join(process.cwd(), 'server'));

function listen(app) {
  return new Promise((resolve) => {
    const server = http.createServer(app).listen(0, '127.0.0.1', () => resolve(server));
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
    const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'c007-same-'));
    const dataFile = path.join(dir, 'items.json');
    fs.copyFileSync(path.join(process.cwd(), 'data', 'items.json'), dataFile);
    servers.push(await listen(createApp({ dataFile })), await listen(createApp({ dataFile })));
    const rounds = [];
    const acknowledged = [];
    for (let round = 0; round < 20; round += 1) {
      const names = [`a-${round}`, `b-${round}`];
      const answers = await Promise.all(servers.map((server, index) => post(server.address().port, names[index])));
      names.forEach((name, index) => { if (answers[index].status === 201) acknowledged.push(name); });
      const stored = JSON.parse(fs.readFileSync(dataFile, 'utf8')).items.map((item) => item.name);
      const missing = acknowledged.filter((name) => !stored.includes(name));
      const storedAfterFailure = names.filter((name, index) => answers[index].status !== 201 && stored.includes(name));
      const lost = missing.length > 0;
      rounds.push({ round, statuses: answers.map((answer) => answer.status), ids: answers.map((answer) => answer.item && answer.item.id),
        missing, storedAfterFailure, lost });
      if (lost) break;
    }
    console.log(JSON.stringify(rounds));
    process.exitCode = rounds.some((round) => round.lost) ? 1 : 0;
  } catch (error) {
    console.error(error);
    process.exitCode = 2;
  } finally {
    for (const server of servers) server.close();
  }
})();
