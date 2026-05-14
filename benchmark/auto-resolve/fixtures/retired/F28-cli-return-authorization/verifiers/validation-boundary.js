'use strict';

const assert = require('node:assert');
const { spawnSync } = require('node:child_process');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');

const work = process.env.BENCH_WORKDIR || process.cwd();
const cli = path.join(work, 'bin', 'cli.js');

function runCase(name, payload) {
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), `f28-return-${name}-`));
  const input = path.join(tmp, 'return.json');
  fs.writeFileSync(input, JSON.stringify(payload, null, 2), 'utf8');
  return spawnSync('node', [cli, 'authorize-return', '--input', input], {
    cwd: work,
    encoding: 'utf8'
  });
}

function assertJsonError(result, label) {
  assert.strictEqual(result.status, 2, `${label}: expected exit 2`);
  assert.strictEqual(result.stdout, '', `${label}: expected empty stdout`);
  const parsed = JSON.parse(result.stderr);
  assert.strictEqual(typeof parsed.error, 'string', `${label}: error must be a string`);
  assert.notStrictEqual(parsed.error.length, 0, `${label}: error must not be empty`);
}

function clone(value) {
  return JSON.parse(JSON.stringify(value));
}

const boundary = runCase('boundary', {
  today: '2026-05-20',
  order: {
    id: 'O-BORDER',
    purchased_at: '2026-05-01',
    items: [
      { sku: 'MUG', qty: 1, unit_cents: 1000, return_window_days: 19, restocking_fee_percent: 25 }
    ]
  },
  request: {
    id: 'R-BORDER',
    lines: [
      { sku: 'MUG', qty: 1, reason: 'changed_mind', condition: 'sealed', resolution: 'refund' }
    ]
  }
});

assert.strictEqual(boundary.status, 0);
assert.strictEqual(boundary.stderr, '');
assert.deepStrictEqual(JSON.parse(boundary.stdout), {
  request_id: 'R-BORDER',
  order_id: 'O-BORDER',
  approved: [
    {
      sku: 'MUG',
      qty: 1,
      resolution: 'refund',
      gross_cents: 1000,
      restocking_fee_cents: 0,
      refund_cents: 1000,
      exchange_credit_cents: 0
    }
  ],
  rejected: [],
  refund_cents: 1000,
  exchange_credit_cents: 0,
  restocking_fee_cents: 0
});

const validBase = {
  today: '2026-05-20',
  order: {
    id: 'O-VALIDATE',
    purchased_at: '2026-05-01',
    items: [
      { sku: 'COAT', qty: 1, unit_cents: 9900, return_window_days: 30, restocking_fee_percent: 12 }
    ]
  },
  request: {
    id: 'R-VALIDATE',
    lines: [
      { sku: 'COAT', qty: 1, reason: 'changed_mind', condition: 'opened', resolution: 'refund' }
    ]
  }
};

const duplicateSku = clone(validBase);
duplicateSku.order.items.push({
  sku: 'COAT',
  qty: 1,
  unit_cents: 9900,
  return_window_days: 30,
  restocking_fee_percent: 12
});
assertJsonError(runCase('duplicate-sku', duplicateSku), 'duplicate order SKU');

const unknownSku = clone(validBase);
unknownSku.request.lines[0].sku = 'SCARF';
assertJsonError(runCase('unknown-sku', unknownSku), 'unknown requested SKU');

const invalidDate = clone(validBase);
invalidDate.today = '2026-02-30';
assertJsonError(runCase('invalid-date', invalidDate), 'invalid calendar date');

const invalidCondition = clone(validBase);
invalidCondition.request.lines[0].condition = 'damaged_box';
assertJsonError(runCase('invalid-condition', invalidCondition), 'invalid condition');

const invalidResolution = clone(validBase);
invalidResolution.request.lines[0].resolution = 'store_credit';
assertJsonError(runCase('invalid-resolution', invalidResolution), 'invalid resolution');

console.log(JSON.stringify({ ok: true }));
