import { RenewalAuthority } from "./authorization.js";
import { CertificateIssuer } from "./certificate-issuer.js";
import { CertificateStore } from "./certificate-store.js";
import { CsrRejectionLedger, CsrReviewer } from "./csr-review.js";
import { IssuanceGate } from "./issuance-gate.js";
import { SerialPool } from "./serial-pool.js";

export function createRenewalFixture() {
  const serialPool = new SerialPool();
  const certificateStore = new CertificateStore();
  const rejectionLedger = new CsrRejectionLedger();
  return {
    authority: new RenewalAuthority([
      {
        id: "cert-north",
        accountId: "account-north",
        status: "active",
        dnsNames: ["api.north.example", "www.north.example"],
        renewableFrom: 80,
        renewableUntil: 100,
      },
      {
        id: "cert-revoked",
        accountId: "account-north",
        status: "revoked",
        dnsNames: ["old.north.example"],
        renewableFrom: 80,
        renewableUntil: 100,
      },
    ]),
    csrReviewer: new CsrReviewer(rejectionLedger),
    issuanceGate: new IssuanceGate(),
    issuer: new CertificateIssuer(serialPool, certificateStore),
    rejectionLedger,
    serialPool,
    certificateStore,
  };
}

export function validRenewal(overrides = {}) {
  return {
    certificateId: "cert-north",
    accountId: "account-north",
    requestDay: 90,
    csr: {
      keyAlgorithm: "ecdsa-p256",
      dnsNames: ["api.north.example", "www.north.example"],
    },
    ...overrides,
  };
}
