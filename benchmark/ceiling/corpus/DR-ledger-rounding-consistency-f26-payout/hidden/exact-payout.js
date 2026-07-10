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

const rules = JSON.parse(fs.readFileSync(path.join(workdir, 'data', 'payout-rules.json'), 'utf8'));
const heldAmount = rules.minimum_payout_cents;
const heldProcessingFee = Math.round(heldAmount * rules.processing_fee_percent / 100)
  + rules.fixed_fee_cents;
const heldNetBeforeReserve = heldAmount - heldProcessingFee;
const heldReserveBeforeHold = heldNetBeforeReserve > 0
  ? Math.round(heldNetBeforeReserve * rules.reserve_percent / 100)
  : 0;
const heldPayoutBeforeMinimum = heldNetBeforeReserve - heldReserveBeforeHold;
assert.ok(
  heldPayoutBeforeMinimum > 0 && heldPayoutBeforeMinimum < rules.minimum_payout_cents,
  'catalog rules must produce a positive below-threshold payout for this case'
);

const holdInput = path.join(os.tmpdir(), `payout-minimum-hold-${process.pid}.json`);
fs.writeFileSync(holdInput, JSON.stringify({
  events: [
    { id: 'evt-hold', merchant_id: 'm_hold', type: 'charge', amount_cents: heldAmount }
  ]
}));
const holdProc = spawnSync('node', ['bin/cli.js', 'payout', '--input', holdInput], {
  cwd: workdir,
  encoding: 'utf8'
});

assert.strictEqual(holdProc.status, 0, holdProc.stderr || holdProc.stdout);
assert.strictEqual(holdProc.stderr, '');
// Public contract (task.txt): "If `0 < payout_cents < minimum_payout_cents`, keep the merchant row, add that original positive payout amount to `reserve_cents`, and set `payout_cents` to `0`."
assert.deepStrictEqual(JSON.parse(holdProc.stdout), {
  total_payout_cents: 0,
  total_processing_fee_cents: heldProcessingFee,
  total_dispute_fee_cents: 0,
  total_reserve_cents: heldNetBeforeReserve,
  merchants: [
    {
      merchant_id: 'm_hold',
      gross_charge_cents: heldAmount,
      refund_cents: 0,
      dispute_cents: 0,
      processing_fee_cents: heldProcessingFee,
      dispute_fee_cents: 0,
      reserve_cents: heldReserveBeforeHold + heldPayoutBeforeMinimum,
      payout_cents: 0
    }
  ]
});

process.stdout.write(JSON.stringify({ ok: true }) + '\n');
