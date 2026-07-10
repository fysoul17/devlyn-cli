const assert = require('node:assert');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { spawnSync } = require('node:child_process');

const workdir = process.env.BENCH_WORKDIR || process.cwd();
const rulesPath = path.join(workdir, 'data', 'payout-rules.json');
const original = fs.readFileSync(rulesPath, 'utf8');

try {
  fs.writeFileSync(rulesPath, JSON.stringify({
    processing_fee_percent: 1,
    fixed_fee_cents: 10,
    dispute_fee_cents: 77,
    reserve_percent: 0,
    minimum_payout_cents: 1
  }, null, 2) + '\n');

  const input = path.join(os.tmpdir(), `payout-rules-${process.pid}.json`);
  fs.writeFileSync(input, JSON.stringify({
    events: [
      { id: 'evt-1', merchant_id: 'm_1', type: 'charge', amount_cents: 10000 }
    ]
  }));

  const proc = spawnSync('node', ['bin/cli.js', 'payout', '--input', input], {
    cwd: workdir,
    encoding: 'utf8'
  });

  assert.strictEqual(proc.status, 0, proc.stderr || proc.stdout);
  assert.strictEqual(proc.stderr, '');
  assert.deepStrictEqual(JSON.parse(proc.stdout), {
    total_payout_cents: 9890,
    total_processing_fee_cents: 110,
    total_dispute_fee_cents: 0,
    total_reserve_cents: 0,
    merchants: [
      {
        merchant_id: 'm_1',
        gross_charge_cents: 10000,
        refund_cents: 0,
        dispute_cents: 0,
        processing_fee_cents: 110,
        dispute_fee_cents: 0,
        reserve_cents: 0,
        payout_cents: 9890
      }
    ]
  });
} finally {
  fs.writeFileSync(rulesPath, original);
}

process.stdout.write(JSON.stringify({ ok: true }) + '\n');
