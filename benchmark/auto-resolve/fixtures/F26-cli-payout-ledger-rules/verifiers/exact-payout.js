const assert = require('node:assert');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { spawnSync } = require('node:child_process');

const workdir = process.env.BENCH_WORKDIR || process.cwd();
const input = path.join(os.tmpdir(), `payout-success-${process.pid}.json`);

const charge1 = { id: 'evt-1', merchant_id: 'm_1', type: 'charge', amount_cents: 10000 };
fs.writeFileSync(input, JSON.stringify({
  events: [
    charge1,
    { id: 'evt-2', merchant_id: 'm_2', type: 'charge', amount_cents: 5000 },
    charge1,
    { id: 'evt-3', merchant_id: 'm_1', type: 'refund', amount_cents: 2500 },
    { id: 'evt-4', merchant_id: 'm_1', type: 'charge', amount_cents: 3333 },
    { id: 'evt-5', merchant_id: 'm_2', type: 'dispute', amount_cents: 2000 }
  ]
}));

const proc = spawnSync('node', ['bin/cli.js', 'payout', '--input', input], {
  cwd: workdir,
  encoding: 'utf8'
});

assert.strictEqual(proc.status, 0, proc.stderr || proc.stdout);
assert.strictEqual(proc.stderr, '');
assert.deepStrictEqual(JSON.parse(proc.stdout), {
  total_payout_cents: 10539,
  total_processing_fee_cents: 622,
  total_dispute_fee_cents: 1500,
  total_reserve_cents: 1172,
  merchants: [
    {
      merchant_id: 'm_1',
      gross_charge_cents: 13333,
      refund_cents: 2500,
      dispute_cents: 0,
      processing_fee_cents: 447,
      dispute_fee_cents: 0,
      reserve_cents: 1039,
      payout_cents: 9347
    },
    {
      merchant_id: 'm_2',
      gross_charge_cents: 5000,
      refund_cents: 0,
      dispute_cents: 2000,
      processing_fee_cents: 175,
      dispute_fee_cents: 1500,
      reserve_cents: 133,
      payout_cents: 1192
    }
  ]
});

process.stdout.write(JSON.stringify({ ok: true }) + '\n');
