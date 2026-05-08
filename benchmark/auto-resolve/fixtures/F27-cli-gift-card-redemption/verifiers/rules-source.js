const assert = require('node:assert');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { spawnSync } = require('node:child_process');

const workdir = process.env.BENCH_WORKDIR || process.cwd();
const rulesPath = path.join(workdir, 'data', 'gift-cards.json');
const original = fs.readFileSync(rulesPath, 'utf8');

try {
  fs.writeFileSync(rulesPath, JSON.stringify({
    products: {
      TEE: { unit_cents: 1000 }
    },
    cards: {
      'GC-SOURCE': { balance_cents: 900, active: true }
    }
  }, null, 2) + '\n');

  const input = path.join(os.tmpdir(), `gift-card-source-${process.pid}.json`);
  fs.writeFileSync(input, JSON.stringify({
    order_id: 'order-source',
    lines: [
      { sku: 'TEE', qty: 1 }
    ],
    redeems: [
      { card_id: 'GC-SOURCE', amount_cents: 700 }
    ]
  }));

  const proc = spawnSync('node', ['bin/cli.js', 'gift-card', '--input', input], {
    cwd: workdir,
    encoding: 'utf8'
  });

  assert.strictEqual(proc.status, 0, proc.stderr || proc.stdout);
  assert.strictEqual(proc.stderr, '');
  assert.deepStrictEqual(JSON.parse(proc.stdout), {
    order_id: 'order-source',
    subtotal_cents: 1000,
    gift_card_applied_cents: 700,
    amount_due_cents: 300,
    items: [
      { sku: 'TEE', qty: 1, line_cents: 1000 }
    ],
    redemptions: [
      { card_id: 'GC-SOURCE', applied_cents: 700, remaining_balance_cents: 200 }
    ]
  });
} finally {
  fs.writeFileSync(rulesPath, original);
}

process.stdout.write(JSON.stringify({ ok: true }) + '\n');
