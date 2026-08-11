import assert from "node:assert/strict";
import test from "node:test";

import { AccountBook } from "../account-book.js";
import { executeTransferBatch } from "../batch-service.js";
import { LedgerJournal } from "../ledger-journal.js";
import { LedgerWriter } from "../ledger-writer.js";
import { MandateCheck } from "../mandate-check.js";
import { createTransfer } from "../transfer.js";

function transfer(id, mandateId, amountCents = 100) {
  return createTransfer({
    id,
    mandateId,
    fromAccount: "operating",
    toAccount: "supplier",
    amountCents,
  });
}

function setup(mandates) {
  const writer = new LedgerWriter(
    new AccountBook({ operating: 1_000, supplier: 200 }),
    new LedgerJournal(),
  );
  return { writer, mandateCheck: new MandateCheck(mandates) };
}

test("an authorized batch returns committed transfer ids", () => {
  const { writer, mandateCheck } = setup({
    "mandate-open": {
      status: "active",
      debitAccount: "operating",
      limitCents: 500,
    },
  });

  const result = executeTransferBatch(writer, mandateCheck, [
    transfer("supplier-payment", "mandate-open", 175),
  ]);

  assert.deepEqual(result, {
    status: "committed",
    transferIds: ["supplier-payment"],
    denial: null,
  });
});

test("a denied first instruction leaves the ledger unchanged", () => {
  const { writer, mandateCheck } = setup({
    "mandate-closed": {
      status: "revoked",
      debitAccount: "operating",
      limitCents: 500,
    },
  });
  const before = writer.snapshot();

  const result = executeTransferBatch(writer, mandateCheck, [
    transfer("blocked-payment", "mandate-closed"),
  ]);

  assert.equal(result.status, "denied");
  assert.deepEqual(writer.snapshot(), before);
});
