import assert from "node:assert/strict";
import test from "node:test";

import { createRenewalFixture, validRenewal } from "../fixtures.js";
import { renewCertificate } from "../renewal-service.js";

test("an authorized valid renewal completes the issuance chain", () => {
  const state = createRenewalFixture();
  const result = renewCertificate(state, validRenewal());
  assert.equal(result.status, "renewed");
  assert.equal(result.certificate.serial, 7000);
  assert.equal(state.serialPool.holds.length, 0);
  assert.deepEqual(state.serialPool.committed, [7000]);
  assert.equal(state.certificateStore.certificates.length, 1);
  assert.equal(state.rejectionLedger.entries.length, 0);
});

test("a valid CSR cannot cross certificate ownership", () => {
  const state = createRenewalFixture();
  const result = renewCertificate(
    state,
    validRenewal({ accountId: "account-south" }),
  );
  assert.deepEqual(result, { ok: false, error: "renewal_denied" });
  assert.equal(state.rejectionLedger.entries.length, 0);
  assert.equal(state.serialPool.committed.length, 0);
  assert.equal(state.certificateStore.certificates.length, 0);
});
