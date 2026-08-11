import assert from "node:assert/strict";
import test from "node:test";

import { AccountBook } from "../account-book.js";
import { LedgerJournal } from "../ledger-journal.js";
import { LedgerWriter } from "../ledger-writer.js";
import { createTransfer } from "../transfer.js";

test("one ledger draft publishes balances, net positions, and sequence together", () => {
  const writer = new LedgerWriter(
    new AccountBook({ reserve: 900, vendor: 100 }),
    new LedgerJournal(),
    { nextSequence: 12 },
  );
  const transfer = createTransfer({
    id: "payment-one",
    mandateId: "mandate-one",
    fromAccount: "reserve",
    toAccount: "vendor",
    currency: "USD",
    amountCents: 250,
  });

  writer.postBatch("batch-net", [transfer]);

  assert.deepEqual(writer.snapshot(), {
    balances: { reserve: 650, vendor: 350 },
    batchNets: { "batch-net": { reserve: -250, vendor: 250 } },
    journal: [{
      batchId: "batch-net",
      sequence: 12,
      transferId: "payment-one",
      debitAccount: "reserve",
      creditAccount: "vendor",
      amountCents: 250,
    }],
    nextSequence: 13,
  });
});
