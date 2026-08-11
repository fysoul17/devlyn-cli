function denied(reason) {
  return { authorized: false, reason };
}

export class MemberTokenRegistry {
  #tokens;

  constructor(tokens) {
    this.#tokens = new Map(tokens.map((token) => [token.value, structuredClone(token)]));
  }

  inspect(value) {
    const token = this.#tokens.get(value);
    if (!token || token.signature !== "trusted") {
      return { verified: false, reason: "token_invalid" };
    }
    return {
      verified: true,
      claims: {
        tokenId: token.tokenId,
        memberId: token.memberId,
        status: token.status,
        cycles: [...token.cycles],
      },
    };
  }

  authorizeClaims(claims, { memberId, cycleId }) {
    if (claims.status !== "active") {
      return denied(`token_${claims.status}`);
    }
    if (claims.memberId !== memberId) {
      return denied("token_member_mismatch");
    }
    if (!claims.cycles.includes(cycleId)) {
      return denied("token_cycle_mismatch");
    }
    return { authorized: true, tokenId: claims.tokenId };
  }

  authorize({ value, memberId, cycleId }) {
    const inspected = this.inspect(value);
    if (!inspected.verified) {
      return denied(inspected.reason);
    }
    return this.authorizeClaims(inspected.claims, { memberId, cycleId });
  }
}
