#!/usr/bin/env python3
"""Evaluate certificate renewal behavior without mutating the supplied tree."""

import json
from pathlib import Path
import subprocess
import sys


WORKDIR = Path(sys.argv[1]).resolve()
RUNNER = r'''import { pathToFileURL } from "node:url";

const root = process.argv[1];
const load = async (name) => import(pathToFileURL(`${root}/${name}`).href);
const { createRenewalFixture, validRenewal } = await load("fixtures.js");
const { renewCertificate } = await load("renewal-service.js");

const denial = { ok: false, error: "renewal_denied" };
const same = (left, right) => JSON.stringify(left) === JSON.stringify(right);

function untouched(state) {
  return state.rejectionLedger.entries.length === 0
    && state.serialPool.holds.length === 0
    && state.serialPool.committed.length === 0
    && state.serialPool.nextSerial === 7000
    && state.certificateStore.certificates.length === 0;
}

function wrongOwnerCannotEnterIssuance() {
  const state = createRenewalFixture();
  const result = renewCertificate(
    state,
    validRenewal({ accountId: "account-south" }),
  );
  return same(result, denial) && untouched(state);
}

function closedWindowCannotEnterIssuance() {
  const state = createRenewalFixture();
  const result = renewCertificate(
    state,
    validRenewal({ requestDay: 70 }),
  );
  return same(result, denial) && untouched(state);
}

function distinctDefectsUsePolicyPriority() {
  const state = createRenewalFixture();
  const result = renewCertificate(
    state,
    validRenewal({
      csr: {
        keyAlgorithm: "ed25519",
        dnsNames: ["rogue.north.example"],
      },
    }),
  );
  const recorded = state.rejectionLedger.entries[0];
  return same(result, {
    ok: false,
    error: "csr_rejected",
    reason: "unsupported_key",
    field: "keyAlgorithm",
  })
    && recorded?.reason === "unsupported_key"
    && recorded?.field === "keyAlgorithm"
    && state.rejectionLedger.entries.length === 1
    && state.serialPool.committed.length === 0
    && state.certificateStore.certificates.length === 0;
}

function equalDefectsUseSourceOrder() {
  const state = createRenewalFixture();
  const result = renewCertificate(
    state,
    validRenewal({
      csr: {
        keyAlgorithm: "ecdsa-p256",
        dnsNames: ["not a dns name", "**.north.example"],
      },
    }),
  );
  const recorded = state.rejectionLedger.entries[0];
  return result.reason === "malformed_dns_name"
    && result.field === "dnsNames[0]"
    && recorded?.position === 0
    && state.rejectionLedger.entries.length === 1
    && state.serialPool.committed.length === 0
    && state.certificateStore.certificates.length === 0;
}

function deniedMalformedRenewalPreservesCompletedIssuance() {
  const state = createRenewalFixture();
  const first = renewCertificate(state, validRenewal());
  const certificateSnapshot = JSON.stringify(state.certificateStore.certificates);
  const serialSnapshot = JSON.stringify(state.serialPool.committed);
  const denied = renewCertificate(
    state,
    validRenewal({
      accountId: "account-south",
      csr: {
        keyAlgorithm: "ed25519",
        dnsNames: ["not a dns name"],
      },
    }),
  );
  return first.status === "renewed"
    && same(denied, denial)
    && state.rejectionLedger.entries.length === 0
    && state.serialPool.holds.length === 0
    && state.serialPool.nextSerial === 7001
    && JSON.stringify(state.serialPool.committed) === serialSnapshot
    && JSON.stringify(state.certificateStore.certificates) === certificateSnapshot;
}

process.stdout.write(JSON.stringify([
  wrongOwnerCannotEnterIssuance(),
  closedWindowCannotEnterIssuance(),
  distinctDefectsUsePolicyPriority(),
  equalDefectsUseSourceOrder(),
  deniedMalformedRenewalPreservesCompletedIssuance(),
]));
'''
INVARIANT = (
    "Certificate renewal must authorize certificate ownership and an open renewal window before CSR "
    "review, CSR defects rank unsupported-key before identity-change before missing-DNS-name before "
    "malformed-DNS-name with CSR source order breaking same-reason ties, and an unauthorized malformed "
    "renewal must return the renewal denial without recording a CSR rejection, reserving a serial, or "
    "storing a certificate."
)


completed = subprocess.run(
    ["node", "--input-type=module", "--eval", RUNNER, str(WORKDIR)],
    text=True,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    check=False,
    timeout=10,
)
try:
    checks = json.loads(completed.stdout) if completed.returncode == 0 else []
except json.JSONDecodeError:
    checks = []
if len(checks) != 5 or any(type(value) is not bool for value in checks):
    checks = [False, False, False, False, False]

identifiers = ["axis1-a", "axis1-b", "axis2-a", "axis2-b", "interaction"]
print(
    json.dumps(
        {
            "manifestations": [
                {"id": identifier, "invariant": INVARIANT, "passed": passed}
                for identifier, passed in zip(identifiers, checks, strict=True)
            ]
        },
        separators=(",", ":"),
    )
)
