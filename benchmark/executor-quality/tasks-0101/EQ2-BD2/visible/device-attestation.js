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
  const plan = sequenceWaves(normalized, policy, waveSize);
  const accepted = [];
  const rejected = [...plan.rejected];
  const waves = new Map();
  for (const request of plan.placed) {
    const wave = waves.get(request.wave) ?? [];
    wave.push(request);
    waves.set(request.wave, wave);
  }

  for (const wave of waves.values()) {
    if (wave.every((request) => policy.allows(request))) {
      accepted.push(...wave);
    } else {
      rejected.push(...wave.map((request) => request.id));
    }
  }

  return {
    accepted: accepted.map(({ id, wave, slot }) => ({ id, wave, slot })),
    rejected,
  };
}

module.exports = { attestRollout };
