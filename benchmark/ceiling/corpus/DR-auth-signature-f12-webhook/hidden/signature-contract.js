'use strict';
const crypto = require('node:crypto');
const fs = require('node:fs');
const path = require('node:path');
const { invokeApp } = require('./invoke-app');

const work = process.env.BENCH_WORKDIR || process.cwd();
const { app } = require(path.join(work, 'server'));
const secret = fs.readFileSync(path.join(work, 'data', 'webhook-secret.txt'));

function hmacHex(bytes) {
  return crypto.createHmac('sha256', secret).update(bytes).digest('hex');
}

function postRaw(bytes, signature) {
  const headers = { 'Content-Type': 'application/json' };
  if (signature !== undefined) headers['X-Signature'] = signature;
  return invokeApp(app, { method: 'POST', path: '/webhook', headers, body: bytes });
}

async function main() {
  const happyBytes = Buffer.from('{"id":"evt_h1","type":"order.created","timestamp":1,"data":{}}');
  const happy = await postRaw(happyBytes, hmacHex(happyBytes));

  const original = Buffer.from('{"id":"evt_t1","type":"x","timestamp":1,"data":{"amount":100}}');
  const tampered = Buffer.from('{"id":"evt_t1","type":"x","timestamp":1,"data":{"amount":9999}}');
  const tamperedResult = await postRaw(tampered, hmacHex(original));

  const missingBytes = Buffer.from('{"id":"evt_m1","type":"x","timestamp":1,"data":{}}');
  const missing = await postRaw(missingBytes);

  const canonical = Buffer.from('{"id":"evt_rb1","type":"x","timestamp":1,"data":{}}');
  const wire = Buffer.from('{ "id":"evt_rb1","type":"x","timestamp":1,"data":{} }');
  const rawBody = await postRaw(wire, hmacHex(canonical));

  const invalidBodyBytes = Buffer.from('{"id":"evt_invalid_first","type":"x","timestamp":"bad","data":{}}');
  const invalidBody = await postRaw(invalidBodyBytes, hmacHex(invalidBodyBytes));
  // Public contract (task.txt): "A body that fails this shape returns 400 with `{ error: 'invalid_body' }` (sig check still runs first — a bad body with a valid sig is 400, not 401)."
  const invalidBodyExact = JSON.stringify(invalidBody.body)
    === JSON.stringify({ error: 'invalid_body' });

  const ok = happy.status === 200
    && happy.body
    && happy.body.accepted === true
    && happy.body.id === 'evt_h1'
    && tamperedResult.status === 401
    && tamperedResult.body
    && tamperedResult.body.error === 'invalid_signature'
    && missing.status === 401
    && missing.body
    && missing.body.error === 'invalid_signature'
    && rawBody.status === 401
    && rawBody.body
    && rawBody.body.error === 'invalid_signature'
    && invalidBody.status === 400
    && invalidBodyExact;
  console.log(JSON.stringify({
    ok,
    happy: happy.status,
    tampered: tamperedResult.status,
    missing: missing.status,
    raw_body: rawBody.status,
    invalid_first_delivery: invalidBody.status,
    invalid_body_exact: invalidBodyExact,
  }));
  process.exitCode = ok ? 0 : 1;
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
