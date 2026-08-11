import assert from "node:assert/strict";
import test from "node:test";

import { RenewalAuthority } from "../authorization.js";
import { collectCsrDefects } from "../csr-policy.js";

test("renewal authority combines ownership, status, and window checks", () => {
  const authority = new RenewalAuthority([{
    id: "cert",
    accountId: "owner",
    status: "active",
    dnsNames: ["service.example"],
    renewableFrom: 30,
    renewableUntil: 40,
  }]);
  assert.equal(authority.authorize("cert", "owner", 35).ok, true);
  assert.deepEqual(authority.authorize("cert", "visitor", 35), {
    ok: false,
    error: "renewal_denied",
  });
  assert.deepEqual(authority.authorize("cert", "owner", 20), {
    ok: false,
    error: "renewal_denied",
  });
});

test("CSR collection retains every defect for policy ranking", () => {
  const defects = collectCsrDefects(
    { keyAlgorithm: "legacy-rsa", dnsNames: ["new.example", "bad name"] },
    { dnsNames: ["service.example"] },
  );
  assert.deepEqual(defects.map(({ reason }) => reason), [
    "unsupported_key",
    "identity_change",
    "malformed_dns_name",
  ]);
});
