export class CertificateStore {
  certificates = [];

  save(certificate) {
    const stored = Object.freeze({
      ...certificate,
      dnsNames: Object.freeze([...certificate.dnsNames]),
    });
    this.certificates.push(stored);
    return stored;
  }
}
