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

function postRaw(bytes) {
  return invokeApp(app, {
    method: 'POST',
    path: '/webhook',
    headers: {
      'Content-Type': 'application/json',
      'X-Signature': hmacHex(bytes),
    },
    body: bytes,
  });
}

function isDuplicate(result, id) {
  return result.status === 409
    && result.body
    && result.body.error === 'duplicate_event'
    && result.body.id === id;
}

async function main() {
  const repeated = Buffer.from('{"id":"evt_r1","type":"x","timestamp":1,"data":{}}');
  const first = await postRaw(repeated);
  const second = await postRaw(repeated);

  const accepted = Buffer.from('{"id":"evt_hidden_replay","type":"x","timestamp":1,"data":{}}');
  const malformedDuplicate = Buffer.from('{"id":"evt_hidden_replay","type":"x","timestamp":"bad","data":{}}');
  const hiddenFirst = await postRaw(accepted);
  const hiddenSecond = await postRaw(malformedDuplicate);

  const ok = first.status === 200
    && isDuplicate(second, 'evt_r1')
    && hiddenFirst.status === 200
    && isDuplicate(hiddenSecond, 'evt_hidden_replay');
  console.log(JSON.stringify({
    ok,
    first: first.status,
    second: second.status,
    malformed_first: hiddenFirst.status,
    malformed_second: hiddenSecond.status,
  }));
  process.exitCode = ok ? 0 : 1;
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
