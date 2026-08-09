"use strict";

class AttestationPolicy {
  constructor(trustedSigners) {
    this.trustedSigners = new Map(
      Object.entries(trustedSigners).map(([ring, signers]) => [
        ring,
        new Set(signers.map(String)),
      ]),
    );
  }

  allows(request) {
    return this.trustedSigners.get(request.ring)?.has(request.signer) ?? false;
  }
}

module.exports = { AttestationPolicy };
