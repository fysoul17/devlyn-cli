// P2 — idempotency_replay: first valid delivery of an id is accepted (200),
// and any later delivery of the same id — even with different body content,
// as long as it independently passes signature + shape checks on its own —
// is rejected as a duplicate (409), regardless of that later body's content.
'use strict';

const assert = require('node:assert');
const http = require('node:http');
const crypto = require('node:crypto');
const fs = require('node:fs');
const path = require('node:path');

const { app } = require('../../server');

const REPO_ROOT = path.join(__dirname, '..', '..');
const secret = fs.readFileSync(path.join(REPO_ROOT, 'data', 'webhook-secret.txt'), 'utf8').trim();

function startServer() {
  return new Promise((resolve) => {
    const server = http.createServer(app);
    server.listen(0, () => resolve(server));
  });
}

function sign(rawBodyBuffer) {
  return crypto.createHmac('sha256', secret).update(rawBodyBuffer).digest('hex');
}

function post(server, path_, { headers = {}, bodyBuffer }) {
  return new Promise((resolve, reject) => {
    const { port } = server.address();
    const req = http.request(
      {
        host: '127.0.0.1',
        port,
        path: path_,
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Content-Length': Buffer.byteLength(bodyBuffer),
          ...headers,
        },
      },
      (res) => {
        let body = '';
        res.on('data', (chunk) => (body += chunk));
        res.on('end', () => resolve({ status: res.statusCode, body: JSON.parse(body) }));
      }
    );
    req.on('error', reject);
    req.write(bodyBuffer);
    req.end();
  });
}

async function main() {
  const server = await startServer();
  try {
    const sharedId = 'evt-p2-replay';

    const firstBodyObj = { id: sharedId, type: 'order.created', timestamp: 1700000100, data: { amount: 10 } };
    const firstBodyBuffer = Buffer.from(JSON.stringify(firstBodyObj), 'utf8');
    const first = await post(server, '/webhook', {
      headers: { 'X-Signature': sign(firstBodyBuffer) },
      bodyBuffer: firstBodyBuffer,
    });
    assert.strictEqual(first.status, 200, `first-delivery status: expected 200, got ${first.status}`);
    assert.deepStrictEqual(first.body, { accepted: true, id: sharedId }, 'first-delivery response body mismatch');

    // Same id, different (but still independently valid: correctly signed,
    // correctly shaped) body — must still be rejected as a duplicate purely
    // on id, ignoring the differing content.
    const dupBodyObj = { id: sharedId, type: 'order.updated', timestamp: 1700000999, data: { amount: 99999, note: 'different payload' } };
    const dupBodyBuffer = Buffer.from(JSON.stringify(dupBodyObj), 'utf8');
    const dup = await post(server, '/webhook', {
      headers: { 'X-Signature': sign(dupBodyBuffer) },
      bodyBuffer: dupBodyBuffer,
    });
    assert.strictEqual(dup.status, 409, `duplicate-delivery status: expected 409, got ${dup.status}`);
    assert.deepStrictEqual(dup.body, { error: 'duplicate_event', id: sharedId }, 'duplicate-delivery response body mismatch');

    console.log('P2 PASS');
    process.exitCode = 0;
  } finally {
    server.close();
  }
}

main().catch((err) => {
  console.error('P2 FAIL:', err.message);
  process.exitCode = 1;
});
