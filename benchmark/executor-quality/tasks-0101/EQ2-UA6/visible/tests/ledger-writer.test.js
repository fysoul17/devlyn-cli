import assert from "node:assert/strict";
import test from "node:test";

import { AccountBook } from "../account-book.js";
import { LedgerJournal } from "../ledger-journal.js";
import { LedgerWriter } from "../ledger-writer.js";
import { createTransfer } from "../transfer.js";

test("a posting balances the debit and credit legs", () => {
  const accounts = new AccountBook({ payer: 900, payee: 100 });
  const journal = new LedgerJournal();
  const writer = new LedgerWriter(accounts, journal, { nextSequence: 12 });

  const sequence = writer.write(
    createTransfer({
      id: "payment-one",
      mandateId: "mandate-one",
      fromAccount: "payer",
      toAccount: "payee",
      amountCents: 250,
    }),
  );

  assert.equal(sequence, 12);
  assert.deepEqual(writer.snapshot(), {
    balances: { payee: 350, payer: 650 },
    journal: [
      {
        sequence: 12,
        transferId: "payment-one",
        debitAccount: "payer",
        creditAccount: "payee",
        amountCents: 250,
      },
    ],
    nextSequence: 13,
  });
});
