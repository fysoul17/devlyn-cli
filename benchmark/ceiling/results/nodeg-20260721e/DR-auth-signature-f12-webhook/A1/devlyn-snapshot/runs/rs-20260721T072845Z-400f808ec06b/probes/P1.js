// P1 — auth_signature_contract: HMAC is computed over the exact raw request
// bytes, and a tampered body (or missing signature header) is rejected with
// 401 { error: 'invalid_signature' }, using the exact key set (no extras).
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
    // Original payload the sender actually signed.
    const originalBodyObj = { id: 'evt-p1-sig', type: 'order.created', timestamp: 1700000000, data: { amount: 42 } };
    const originalBodyBuffer = Buffer.from(JSON.stringify(originalBodyObj), 'utf8');
    const validSignature = sign(originalBodyBuffer);

    // Case A: body bytes on the wire differ from what was signed (tampered
    // after signing) — shape stays valid, only the bytes changed, so this
    // isolates a signature-over-exact-bytes failure from a shape failure.
    const tamperedBodyObj = { ...originalBodyObj, data: { amount: 999999 } };
    const tamperedBodyBuffer = Buffer.from(JSON.stringify(tamperedBodyObj), 'utf8');

    const tampered = await post(server, '/webhook', {
      headers: { 'X-Signature': validSignature },
      bodyBuffer: tamperedBodyBuffer,
    });
    assert.strictEqual(tampered.status, 401, `tampered-body status: expected 401, got ${tampered.status}`);
    assert.deepStrictEqual(tampered.body, { error: 'invalid_signature' }, 'tampered-body response body mismatch');

    // Case B: signature header missing entirely.
    const missingSig = await post(server, '/webhook', {
      headers: {},
      bodyBuffer: originalBodyBuffer,
    });
    assert.strictEqual(missingSig.status, 401, `missing-signature status: expected 401, got ${missingSig.status}`);
    assert.deepStrictEqual(missingSig.body, { error: 'invalid_signature' }, 'missing-signature response body mismatch');

    console.log('P1 PASS');
    process.exitCode = 0;
  } finally {
    server.close();
  }
}

main().catch((err) => {
  console.error('P1 FAIL:', err.message);
  process.exitCode = 1;
});
