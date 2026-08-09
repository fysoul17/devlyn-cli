"use strict";

const { AttestationPolicy } = require("./attestation-policy");
const { sequenceWaves } = require("./wave-sequencer");

function attestRollout(requests, trustedSigners, waveSize = 2) {
  const policy = new AttestationPolicy(trustedSigners);
  const normalized = requests.map((request, arrival) => ({
    id: String(request.id),
    signer: String(request.signer),
    ring: String(request.ring),
    priority: Number(request.priority),
    arrival,
  }));
  const result = sequenceWaves(normalized, policy, waveSize);

  return {
    accepted: result.accepted.map(({ id, wave, slot }) => ({ id, wave, slot })),
    rejected: [...result.rejected],
  };
}

module.exports = { attestRollout };
