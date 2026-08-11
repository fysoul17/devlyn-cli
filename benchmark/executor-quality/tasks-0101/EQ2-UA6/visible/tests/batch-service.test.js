import assert from "node:assert/strict";
import test from "node:test";

import { AccountBook } from "../account-book.js";
import { executeTransferBatch } from "../batch-service.js";
import { LedgerJournal } from "../ledger-journal.js";
import { LedgerWriter } from "../ledger-writer.js";
import { MandateCheck } from "../mandate-check.js";
import { createTransfer } from "../transfer.js";

test("an authorized instruction returns one committed batch result", () => {
  const writer = new LedgerWriter(
    new AccountBook({ reserve: 1_000, vendor: 100 }),
    new LedgerJournal(),
  );
  const mandates = new MandateCheck({
    payroll: {
      status: "active",
      debitAccount: "reserve",
      currency: "USD",
      expiresOn: "2026-08-31",
      remainingCents: 500,
    },
  });
  const transfer = createTransfer({
    id: "supplier-one",
    mandateId: "payroll",
    fromAccount: "reserve",
    toAccount: "vendor",
    currency: "USD",
    amountCents: 175,
  });

  assert.deepEqual(
    executeTransferBatch(writer, mandates, "batch-one", "2026-08-11", [transfer]),
    {
      status: "committed",
      batchId: "batch-one",
      transferIds: ["supplier-one"],
      denial: null,
    },
  );
});

test("an expired mandate is denied before a posting", () => {
  const writer = new LedgerWriter(
    new AccountBook({ reserve: 1_000, vendor: 100 }),
    new LedgerJournal(),
  );
  const before = writer.snapshot();
  const mandates = new MandateCheck({
    expired: {
      status: "active",
      debitAccount: "reserve",
      currency: "USD",
      expiresOn: "2026-08-10",
      remainingCents: 500,
    },
  });
  const transfer = createTransfer({
    id: "late-wire",
    mandateId: "expired",
    fromAccount: "reserve",
    toAccount: "vendor",
    currency: "USD",
    amountCents: 100,
  });

  const result = executeTransferBatch(writer, mandates, "batch-late", "2026-08-11", [transfer]);
  assert.equal(result.status, "denied");
  assert.deepEqual(writer.snapshot(), before);
});
