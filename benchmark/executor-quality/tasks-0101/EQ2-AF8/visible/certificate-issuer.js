export class CertificateIssuer {
  constructor(serialPool, certificateStore) {
    this.serialPool = serialPool;
    this.certificateStore = certificateStore;
  }

  issue(authorization, csr, issuedOn) {
    const hold = this.serialPool.reserve(authorization.certificateId);
    const certificate = this.certificateStore.save({
      serial: hold.serial,
      replaces: authorization.certificateId,
      accountId: authorization.accountId,
      dnsNames: csr.dnsNames,
      keyAlgorithm: csr.keyAlgorithm,
      issuedOn,
    });
    this.serialPool.commit(hold);
    return { ok: true, status: "renewed", certificate };
  }
}
