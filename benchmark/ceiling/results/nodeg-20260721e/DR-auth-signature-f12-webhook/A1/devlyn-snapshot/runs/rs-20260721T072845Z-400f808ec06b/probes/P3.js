// P3 — shape_contract (happy path): a well-formed request — valid signature
// computed over the exact raw body bytes, valid {id, type, timestamp, data}
// shape — is accepted with 200 and the exact { accepted: true, id } body
// (no extra/missing keys).
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
    const bodyObj = { id: 'evt-p3-happy', type: 'order.created', timestamp: 1700000200, data: { amount: 7 } };
    const bodyBuffer = Buffer.from(JSON.stringify(bodyObj), 'utf8');
    const validSignature = sign(bodyBuffer);

    const result = await post(server, '/webhook', {
      headers: { 'X-Signature': validSignature },
      bodyBuffer,
    });
    assert.strictEqual(result.status, 200, `happy-path status: expected 200, got ${result.status}`);
    assert.deepStrictEqual(result.body, { accepted: true, id: bodyObj.id }, 'happy-path response body mismatch');

    console.log('P3 PASS');
    process.exitCode = 0;
  } finally {
    server.close();
  }
}

main().catch((err) => {
  console.error('P3 FAIL:', err.message);
  process.exitCode = 1;
});
