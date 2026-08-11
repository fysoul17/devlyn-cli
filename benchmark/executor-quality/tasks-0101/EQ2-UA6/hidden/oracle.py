#!/usr/bin/env python3
"""Deterministic checks for aggregate-mandate ledger batches."""

import json
from pathlib import Path
import subprocess
import sys


WORKDIR = Path(sys.argv[1]).resolve()
RUNNER = r'''import { pathToFileURL } from "node:url";
const root = process.argv[1];
const load = async (name) => import(pathToFileURL(`${root}/${name}`).href);
const { AccountBook } = await load("account-book.js");
const { executeTransferBatch } = await load("batch-service.js");
const { InsufficientFundsError, SettlementRejectedError } = await load("errors.js");
const { LedgerJournal } = await load("ledger-journal.js");
const { LedgerWriter } = await load("ledger-writer.js");
const { MandateCheck } = await load("mandate-check.js");
const { createTransfer } = await load("transfer.js");

const priorRow = {
  batchId: "settled-before",
  sequence: 40,
  transferId: "prior-wire",
  debitAccount: "reserve",
  creditAccount: "clearing",
  amountCents: 25,
};

function setup(blockedBatchIds = []) {
  const journal = new LedgerJournal([priorRow], { blockedBatchIds });
  const writer = new LedgerWriter(
    new AccountBook({ reserve: 2_000, clearing: 400, vendor: 125, payroll: 50 }),
    journal,
    { nextSequence: 41 },
  );
  return { journal, writer };
}

function transfer(id, mandateId, toAccount, amountCents, currency = "USD", fromAccount = "reserve") {
  return createTransfer({ id, mandateId, fromAccount, toAccount, currency, amountCents });
}

function mandate(remainingCents, overrides = {}) {
  return {
    status: "active",
    debitAccount: "reserve",
    currency: "USD",
    expiresOn: "2026-08-31",
    remainingCents,
    ...overrides,
  };
}

function fingerprint(writer) {
  return JSON.stringify(writer.snapshot());
}

function overdrawnDraftLeavesNoNettingState() {
  const { writer } = setup();
  const before = fingerprint(writer);
  const checker = new MandateCheck({ first: mandate(2_000), second: mandate(2_000) });
  try {
    executeTransferBatch(writer, checker, "draft-overdrawn", "2026-08-11", [
      transfer("reserve-first", "first", "vendor", 400),
      transfer("reserve-over", "second", "payroll", 1_900),
    ]);
  } catch (error) {
    return error instanceof InsufficientFundsError && fingerprint(writer) === before;
  }
  return false;
}

function rejectedSettlementCanRetryFromOriginalSequence() {
  const { journal, writer } = setup(["settlement-retry", "settlement-retry:retry-two"]);
  const before = fingerprint(writer);
  const checker = new MandateCheck({ one: mandate(500), two: mandate(500) });
  const transfers = [
    transfer("retry-one", "one", "vendor", 150),
    transfer("retry-two", "two", "payroll", 100),
  ];
  let rejected = false;
  try {
    executeTransferBatch(writer, checker, "settlement-retry", "2026-08-11", transfers);
  } catch (error) {
    rejected = error instanceof SettlementRejectedError;
  }
  const clean = fingerprint(writer) === before;
  journal.allowBatch("settlement-retry");
  journal.allowBatch("settlement-retry:retry-two");
  const result = executeTransferBatch(
    writer,
    checker,
    "settlement-retry",
    "2026-08-11",
    transfers,
  );
  const state = writer.snapshot();
  return rejected
    && clean
    && result.status === "committed"
    && JSON.stringify(result.transferIds) === JSON.stringify(["retry-one", "retry-two"])
    && state.nextSequence === 43
    && state.journal.length === 3
    && JSON.stringify(state.batchNets) === JSON.stringify({
      "settlement-retry": { payroll: 100, reserve: -250, vendor: 150 },
    });
}

function expiryBoundaryUsesBatchDate() {
  const checker = new MandateCheck({ dated: mandate(400, { expiresOn: "2026-08-11" }) });
  const wire = transfer("dated-wire", "dated", "vendor", 120);
  const onDate = setup().writer;
  const accepted = executeTransferBatch(onDate, checker, "date-open", "2026-08-11", [wire]);
  const afterDate = setup().writer;
  const before = fingerprint(afterDate);
  const denied = executeTransferBatch(afterDate, checker, "date-closed", "2026-08-12", [wire]);
  return accepted.status === "committed"
    && denied.status === "denied"
    && denied.denial.reason === "expired"
    && fingerprint(afterDate) === before;
}

function currencyScopeStopsWholeReviewSet() {
  const { writer } = setup();
  const before = fingerprint(writer);
  const checker = new MandateCheck({
    usd: mandate(500),
    eur: mandate(500, { debitAccount: "clearing", currency: "EUR" }),
  });
  const result = executeTransferBatch(writer, checker, "scope-mix", "2026-08-11", [
    transfer("usd-wire", "usd", "vendor", 100),
    transfer("wrong-currency", "eur", "payroll", 90, "USD", "clearing"),
    transfer("usd-tail", "usd", "payroll", 75),
  ]);
  return result.status === "denied"
    && result.denial.transferId === "wrong-currency"
    && result.denial.reason === "currency-scope"
    && fingerprint(writer) === before;
}

function sharedAllowanceIsAuthorizedAsOneBatch() {
  const { writer } = setup();
  const before = fingerprint(writer);
  const checker = new MandateCheck({ shared: mandate(300) });
  const result = executeTransferBatch(writer, checker, "shared-cap", "2026-08-11", [
    transfer("cap-first", "shared", "vendor", 180),
    transfer("cap-over", "shared", "payroll", 160),
  ]);
  return result.status === "denied"
    && result.denial.transferId === "cap-over"
    && result.denial.reason === "batch-allowance"
    && fingerprint(writer) === before;
}

process.stdout.write(JSON.stringify({
  overdrawnDraftLeavesNoNettingState: overdrawnDraftLeavesNoNettingState(),
  rejectedSettlementCanRetryFromOriginalSequence: rejectedSettlementCanRetryFromOriginalSequence(),
  expiryBoundaryUsesBatchDate: expiryBoundaryUsesBatchDate(),
  currencyScopeStopsWholeReviewSet: currencyScopeStopsWholeReviewSet(),
  sharedAllowanceIsAuthorizedAsOneBatch: sharedAllowanceIsAuthorizedAsOneBatch(),
}));
'''
INVARIANT = (
    "A transfer batch must either commit one double-entry netting draft or leave balances, "
    "per-batch net positions, settlement journal, and posting sequence byte-for-byte unchanged; "
    "mandate decisions for effective date, currency, debit account, and aggregate batch allowance "
    "must all complete before that draft begins, so any unauthorized instruction aborts the whole "
    "batch without a ledger change."
)


completed = subprocess.run(
    ["node", "--input-type=module", "--eval", RUNNER, str(WORKDIR)],
    text=True,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    check=False,
    timeout=15,
)
try:
    results = json.loads(completed.stdout) if completed.returncode == 0 else {}
except json.JSONDecodeError:
    results = {}

checks = [
    ("axis1-a", bool(results.get("overdrawnDraftLeavesNoNettingState"))),
    ("axis1-b", bool(results.get("rejectedSettlementCanRetryFromOriginalSequence"))),
    ("axis2-a", bool(results.get("expiryBoundaryUsesBatchDate"))),
    ("axis2-b", bool(results.get("currencyScopeStopsWholeReviewSet"))),
    ("interaction", bool(results.get("sharedAllowanceIsAuthorizedAsOneBatch"))),
]

print(
    json.dumps(
        {
            "manifestations": [
                {"id": identifier, "invariant": INVARIANT, "passed": passed}
                for identifier, passed in checks
            ]
        },
        separators=(",", ":"),
    )
)
