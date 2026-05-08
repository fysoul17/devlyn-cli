'use strict';

const http = require('node:http');
const fs = require('node:fs');
const crypto = require('node:crypto');
const path = require('node:path');

const workdir = process.env.BENCH_WORKDIR;
const { app } = require(path.join(workdir, 'server'));
const secret = fs.readFileSync(path.join(workdir, 'data', 'webhook-secret.txt'));

function hmacHex(bytes) {
  return crypto.createHmac('sha256', secret).update(bytes).digest('hex');
}

function postRaw(port, bytes) {
  return new Promise((resolve) => {
    const req = http.request(
      {
        host: '127.0.0.1',
        port,
        method: 'POST',
        path: '/webhook',
        headers: {
          'Content-Type': 'application/json',
          'Content-Length': Buffer.byteLength(bytes),
          'X-Signature': hmacHex(bytes)
        }
      },
      (res) => {
        let body = '';
        res.on('data', (chunk) => { body += chunk; });
        res.on('end', () => {
          let parsed = null;
          try {
            parsed = JSON.parse(body);
          } catch {
            parsed = null;
          }
          resolve({ status: res.statusCode, body: parsed });
        });
      }
    );
    req.on('error', () => resolve({ status: 0, body: null }));
    req.write(bytes);
    req.end();
  });
}

const server = http.createServer(app).listen(0, async () => {
  const { port } = server.address();
  const accepted = Buffer.from('{"id":"evt_hidden_replay","type":"x","timestamp":1,"data":{}}');
  const malformedDuplicate = Buffer.from('{"id":"evt_hidden_replay","type":"x","timestamp":"bad","data":{}}');
  const first = await postRaw(port, accepted);
  const second = await postRaw(port, malformedDuplicate);
  const ok = first.status === 200
    && second.status === 409
    && second.body
    && second.body.error === 'duplicate_event'
    && second.body.id === 'evt_hidden_replay';
  console.log(JSON.stringify({ ok, first: first.status, second: second.status, second_body: second.body }));
  server.close();
  process.exit(ok ? 0 : 1);
});
