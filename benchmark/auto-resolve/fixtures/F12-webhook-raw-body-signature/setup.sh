#!/usr/bin/env bash
# F12 setup — seed the shared secret and stage verifier scripts.
set -e

mkdir -p data

# Single-line secret, no trailing newline (printf, not echo).
printf 'wh_test_secret_a3f9e1c2_d4b6e7' > data/webhook-secret.txt

# Sample event payload for human inspection (not used by verifiers).
cat > data/_sample-event.json <<'JSON'
{"id":"evt_001","type":"order.created","timestamp":1735689600,"data":{"order_id":"o_42","amount_cents":1500}}
JSON

# Verifier 1: happy path — exact bytes the provider signed → 200 accepted.
cat > data/_verify-happy.js <<'JS'
'use strict';
const http = require('http');
const fs = require('fs');
const crypto = require('crypto');
const { app } = require('../server');

const SECRET = fs.readFileSync('data/webhook-secret.txt');

function hmacHex(bytes) {
  return crypto.createHmac('sha256', SECRET).update(bytes).digest('hex');
}

function postRaw(port, bytes, sig) {
  return new Promise((resolve) => {
    const req = http.request(
      { host: '127.0.0.1', port, method: 'POST', path: '/webhook',
        headers: {
          'Content-Type': 'application/json',
          'Content-Length': Buffer.byteLength(bytes),
          'X-Signature': sig,
        } },
      (r) => {
        let b = ''; r.on('data', (c) => (b += c));
        r.on('end', () => {
          let d = null; try { d = JSON.parse(b); } catch {}
          resolve({ status: r.statusCode, body: d });
        });
      }
    );
    req.on('error', () => resolve({ status: 0, body: null }));
    req.write(bytes);
    req.end();
  });
}

const s = http.createServer(app).listen(0, async () => {
  const { port } = s.address();
  const body = Buffer.from('{"id":"evt_h1","type":"order.created","timestamp":1,"data":{}}');
  const sig = hmacHex(body);
  const r = await postRaw(port, body, sig);
  const ok = r.status === 200 && r.body && r.body.accepted === true && r.body.id === 'evt_h1';
  console.log(JSON.stringify({ status: r.status, body: r.body, ok }));
  s.close();
  process.exit(ok ? 0 : 1);
});
JS

# Verifier 2: replay (same id) — first 200, second 409 even with valid sig.
cat > data/_verify-replay.js <<'JS'
'use strict';
const http = require('http');
const fs = require('fs');
const crypto = require('crypto');
const { app } = require('../server');

const SECRET = fs.readFileSync('data/webhook-secret.txt');
function hmacHex(bytes) {
  return crypto.createHmac('sha256', SECRET).update(bytes).digest('hex');
}
function postRaw(port, bytes, sig) {
  return new Promise((resolve) => {
    const req = http.request(
      { host: '127.0.0.1', port, method: 'POST', path: '/webhook',
        headers: {
          'Content-Type': 'application/json',
          'Content-Length': Buffer.byteLength(bytes),
          'X-Signature': sig,
        } },
      (r) => {
        let b = ''; r.on('data', (c) => (b += c));
        r.on('end', () => {
          let d = null; try { d = JSON.parse(b); } catch {}
          resolve({ status: r.statusCode, body: d });
        });
      }
    );
    req.on('error', () => resolve({ status: 0, body: null }));
    req.write(bytes);
    req.end();
  });
}

const s = http.createServer(app).listen(0, async () => {
  const { port } = s.address();
  const body = Buffer.from('{"id":"evt_r1","type":"x","timestamp":1,"data":{}}');
  const sig = hmacHex(body);
  const first  = await postRaw(port, body, sig);
  const second = await postRaw(port, body, sig);
  const ok = first.status === 200 &&
             second.status === 409 &&
             second.body && second.body.error === 'duplicate_event' && second.body.id === 'evt_r1';
  console.log(JSON.stringify({ first: first.status, second: second.status, second_body: second.body, ok }));
  s.close();
  process.exit(ok ? 0 : 1);
});
JS

# Verifier 3: tampered body → 401. Body changed AFTER signing; the original
# sig now corresponds to bytes that are no longer in the request.
cat > data/_verify-tampered.js <<'JS'
'use strict';
const http = require('http');
const fs = require('fs');
const crypto = require('crypto');
const { app } = require('../server');

const SECRET = fs.readFileSync('data/webhook-secret.txt');
function hmacHex(bytes) {
  return crypto.createHmac('sha256', SECRET).update(bytes).digest('hex');
}
function postRaw(port, bytes, sig) {
  return new Promise((resolve) => {
    const req = http.request(
      { host: '127.0.0.1', port, method: 'POST', path: '/webhook',
        headers: {
          'Content-Type': 'application/json',
          'Content-Length': Buffer.byteLength(bytes),
          'X-Signature': sig,
        } },
      (r) => {
        let b = ''; r.on('data', (c) => (b += c));
        r.on('end', () => {
          let d = null; try { d = JSON.parse(b); } catch {}
          resolve({ status: r.statusCode, body: d });
        });
      }
    );
    req.on('error', () => resolve({ status: 0, body: null }));
    req.write(bytes);
    req.end();
  });
}

const s = http.createServer(app).listen(0, async () => {
  const { port } = s.address();
  const original = Buffer.from('{"id":"evt_t1","type":"x","timestamp":1,"data":{"amount":100}}');
  const sig = hmacHex(original); // sig over the original
  const tampered = Buffer.from('{"id":"evt_t1","type":"x","timestamp":1,"data":{"amount":9999}}');
  const r = await postRaw(port, tampered, sig);
  const ok = r.status === 401 && r.body && r.body.error === 'invalid_signature';
  console.log(JSON.stringify({ status: r.status, body: r.body, ok }));
  s.close();
  process.exit(ok ? 0 : 1);
});
JS

# Verifier 4: missing/malformed X-Signature → 401.
cat > data/_verify-missing-sig.js <<'JS'
'use strict';
const http = require('http');
const { app } = require('../server');

const s = http.createServer(app).listen(0, async () => {
  const { port } = s.address();
  const body = Buffer.from('{"id":"evt_m1","type":"x","timestamp":1,"data":{}}');
  const r = await new Promise((resolve) => {
    const req = http.request(
      { host: '127.0.0.1', port, method: 'POST', path: '/webhook',
        headers: { 'Content-Type': 'application/json', 'Content-Length': Buffer.byteLength(body) } },
      (rs) => {
        let b = ''; rs.on('data', (c) => (b += c));
        rs.on('end', () => {
          let d = null; try { d = JSON.parse(b); } catch {}
          resolve({ status: rs.statusCode, body: d });
        });
      }
    );
    req.on('error', () => resolve({ status: 0, body: null }));
    req.write(body);
    req.end();
  });
  const ok = r.status === 401 && r.body && r.body.error === 'invalid_signature';
  console.log(JSON.stringify({ status: r.status, body: r.body, ok }));
  s.close();
  process.exit(ok ? 0 : 1);
});
JS

# Verifier 5: raw-body discrimination — same parsed object, different on-wire
# bytes, signature of an alternate-bytes form. A naive impl that re-serializes
# req.body and HMACs the result will accept this; a correct impl that HMACs
# the actual received bytes will reject. The "alternate" bytes here are the
# canonical (compact) form of the same JSON, so naive's re-stringify produces
# bytes whose HMAC matches the provided signature.
cat > data/_verify-raw-body.js <<'JS'
'use strict';
const http = require('http');
const fs = require('fs');
const crypto = require('crypto');
const { app } = require('../server');

const SECRET = fs.readFileSync('data/webhook-secret.txt');
function hmacHex(bytes) {
  return crypto.createHmac('sha256', SECRET).update(bytes).digest('hex');
}

const s = http.createServer(app).listen(0, async () => {
  const { port } = s.address();
  // Canonical bytes (compact form) — what JSON.stringify(parsed_obj) emits.
  const canonical = Buffer.from('{"id":"evt_rb1","type":"x","timestamp":1,"data":{}}');
  // Sig over canonical bytes — what a naive impl will produce when it
  // re-stringifies req.body and HMACs the result.
  const sig = hmacHex(canonical);
  // Wire bytes: same parsed JSON, but with extra whitespace. Different bytes
  // than canonical; an HMAC over THESE bytes is NOT `sig`.
  const wire = Buffer.from('{ "id":"evt_rb1","type":"x","timestamp":1,"data":{} }');
  const r = await new Promise((resolve) => {
    const req = http.request(
      { host: '127.0.0.1', port, method: 'POST', path: '/webhook',
        headers: {
          'Content-Type': 'application/json',
          'Content-Length': Buffer.byteLength(wire),
          'X-Signature': sig,
        } },
      (rs) => {
        let b = ''; rs.on('data', (c) => (b += c));
        rs.on('end', () => {
          let d = null; try { d = JSON.parse(b); } catch {}
          resolve({ status: rs.statusCode, body: d });
        });
      }
    );
    req.on('error', () => resolve({ status: 0, body: null }));
    req.write(wire);
    req.end();
  });
  // Correct: 401 (HMAC over wire bytes ≠ sig). Naive (JSON.stringify path): 200.
  const ok = r.status === 401 && r.body && r.body.error === 'invalid_signature';
  console.log(JSON.stringify({ status: r.status, body: r.body, ok }));
  s.close();
  process.exit(ok ? 0 : 1);
});
JS

exit 0
