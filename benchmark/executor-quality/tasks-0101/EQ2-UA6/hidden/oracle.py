#!/usr/bin/env python3
"""Deterministic checks for mandate-reviewed ledger batches."""

import json
from pathlib import Path
import subprocess
import sys


sys.dont_write_bytecode = True
WORKDIR = Path(sys.argv[1]).resolve()
RUNNER = r'''import { pathToFileURL } from "node:url";
const root = process.argv[1];
const load = async (name) => import(pathToFileURL(`${root}/${name}`).href);
const { AccountBook } = await load("account-book.js");
const { executeTransferBatch } = await load("batch-service.js");
const { CreditPostingError, JournalAppendError } = await load("errors.js");
const { LedgerJournal } = await load("ledger-journal.js");
const { LedgerWriter } = await load("ledger-writer.js");
const { MandateCheck } = await load("mandate-check.js");
const { createTransfer } = await load("transfer.js");

const priorRow = {
  sequence: 30,
  transferId: "prior-wire",
  debitAccount: "reserve",
  creditAccount: "clearing",
  amountCents: 25,
};

function writer({ failOnCredit = [], failAfterAppend = [] } = {}) {
  return new LedgerWriter(
    new AccountBook(
      { reserve: 2_000, clearing: 400, vendor: 125, payroll: 50 },
      { failOnCredit },
    ),
    new LedgerJournal([priorRow], { failAfterAppend }),
    { nextSequence: 31 },
  );
}

function wire(id, mandateId, toAccount, amountCents) {
  return createTransfer({
    id,
    mandateId,
    fromAccount: "reserve",
    toAccount,
    amountCents,
  });
}

function checker(statuses) {
  const mandates = Object.fromEntries(
    Object.entries(statuses).map(([id, status]) => [
      id,
      { status, debitAccount: "reserve", limitCents: 1_000 },
    ]),
  );
  return new MandateCheck(mandates);
}

function fingerprint(target) {
  return JSON.stringify(target.snapshot());
}

function denial(transferId, reason) {
  return JSON.stringify({
    status: "denied",
    transferIds: [],
    denial: { transferId, reason },
  });
}

function creditFailureRollsBack() {
  const target = writer({ failOnCredit: ["credit-break"] });
  const before = fingerprint(target);
  try {
    executeTransferBatch(target, checker({ "m-one": "active", "m-two": "active" }), [
      wire("credit-first", "m-one", "vendor", 130),
      wire("credit-break", "m-two", "payroll", 160),
    ]);
  } catch (error) {
    return error instanceof CreditPostingError && fingerprint(target) === before;
  }
  return false;
}

function journalFailureRollsBack() {
  const target = writer({ failAfterAppend: ["journal-break"] });
  const before = fingerprint(target);
  try {
    executeTransferBatch(target, checker({ "m-three": "active" }), [
      wire("journal-break", "m-three", "vendor", 90),
    ]);
  } catch (error) {
    return error instanceof JournalAppendError && fingerprint(target) === before;
  }
  return false;
}

function singleDenialPreventsPosting() {
  const target = writer();
  const before = fingerprint(target);
  const result = executeTransferBatch(target, checker({ "m-four": "expired" }), [
    wire("denied-single", "m-four", "vendor", 80),
  ]);
  return fingerprint(target) === before && JSON.stringify(result) === denial("denied-single", "expired");
}

function leadingDenialPreventsFollowingPosting() {
  const target = writer();
  const before = fingerprint(target);
  const result = executeTransferBatch(
    target,
    checker({ "m-five": "revoked", "m-six": "active" }),
    [
      wire("denied-leading", "m-five", "vendor", 70),
      wire("approved-following", "m-six", "payroll", 60),
    ],
  );
  return fingerprint(target) === before && JSON.stringify(result) === denial("denied-leading", "revoked");
}

function laterDenialAbortsApprovedDecision() {
  const target = writer();
  const before = fingerprint(target);
  const result = executeTransferBatch(
    target,
    checker({ "m-seven": "active", "m-eight": "suspended", "m-nine": "active" }),
    [
      wire("approved-leading", "m-seven", "vendor", 140),
      wire("denied-later", "m-eight", "payroll", 110),
      wire("approved-tail", "m-nine", "vendor", 75),
    ],
  );
  return fingerprint(target) === before && JSON.stringify(result) === denial("denied-later", "suspended");
}

process.stdout.write(JSON.stringify({
  creditFailureRollsBack: creditFailureRollsBack(),
  journalFailureRollsBack: journalFailureRollsBack(),
  singleDenialPreventsPosting: singleDenialPreventsPosting(),
  leadingDenialPreventsFollowingPosting: leadingDenialPreventsFollowingPosting(),
  laterDenialAbortsApprovedDecision: laterDenialAbortsApprovedDecision(),
}));
'''
INVARIANT = (
    "When a transfer batch mixes authorized and unauthorized instructions, all mandate decisions "
    "must be collected and the batch authorized before the ledger writer records any debit or "
    "credit, the denied instruction must abort the whole batch with balances, posting journal, "
    "and sequence exactly at their pre-batch values, and any ledger posting or journal failure "
    "must roll back that same complete ledger state."
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
    ("axis1-a", bool(results.get("creditFailureRollsBack"))),
    ("axis1-b", bool(results.get("journalFailureRollsBack"))),
    ("axis2-a", bool(results.get("singleDenialPreventsPosting"))),
    ("axis2-b", bool(results.get("leadingDenialPreventsFollowingPosting"))),
    ("interaction", bool(results.get("laterDenialAbortsApprovedDecision"))),
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
