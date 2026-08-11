export class RenewalAuthority {
  #certificates;

  constructor(certificates = []) {
    this.#certificates = new Map(
      certificates.map((certificate) => [certificate.id, {
        ...certificate,
        dnsNames: [...certificate.dnsNames],
      }]),
    );
  }

  subjectFor(certificateId) {
    const certificate = this.#certificates.get(certificateId);
    if (certificate === undefined) {
      return { dnsNames: [] };
    }
    return { dnsNames: [...certificate.dnsNames] };
  }

  authorize(certificateId, accountId, requestDay) {
    const certificate = this.#certificates.get(certificateId);
    const allowed = certificate?.status === "active"
      && certificate.accountId === accountId
      && requestDay >= certificate.renewableFrom
      && requestDay <= certificate.renewableUntil;
    if (!allowed) {
      return { ok: false, error: "renewal_denied" };
    }
    return {
      ok: true,
      certificateId,
      accountId,
      subject: { dnsNames: [...certificate.dnsNames] },
    };
  }
}
