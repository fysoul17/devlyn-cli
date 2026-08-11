import { CycleMismatchError, UnknownMemberError } from "./errors.js";

function copy(value) {
  return structuredClone(value);
}

function cycleKey(memberId, cycleId) {
  return `${memberId}:${cycleId}`;
}

export class AccrualStore {
  #policy;
  #balances;
  #cycleTotals = new Map();
  #eventPostings = new Map();
  #receipts = [];
  #receiptsByKey = new Map();
  #nextReceipt = 1;

  constructor({ members, policy }) {
    this.#policy = policy;
    this.#balances = new Map(members.map(({ memberId, balance }) => [memberId, balance]));
  }

  replay(idempotencyKey) {
    const receipt = this.#receiptsByKey.get(idempotencyKey);
    return receipt ? copy(receipt) : null;
  }

  remember(idempotencyKey, receipt) {
    if (!this.#receiptsByKey.has(idempotencyKey)) {
      this.#receiptsByKey.set(idempotencyKey, copy(receipt));
    }
  }

  aggregate(request) {
    if (!this.#balances.has(request.memberId)) {
      throw new UnknownMemberError(request.memberId);
    }

    const key = cycleKey(request.memberId, request.cycleId);
    const used = this.#cycleTotals.get(key) ?? 0;
    let remaining = this.#policy.remaining(used);
    const allocations = [];

    for (const event of request.events) {
      if (event.cycleId !== request.cycleId) {
        throw new CycleMismatchError(event.eventId, request.cycleId);
      }
      if (this.#eventPostings.has(event.eventId) || remaining === 0) {
        continue;
      }
      const awarded = Math.min(event.points, remaining);
      const posting = {
        eventId: event.eventId,
        memberId: request.memberId,
        cycleId: request.cycleId,
        points: awarded,
      };
      this.#eventPostings.set(event.eventId, posting);
      allocations.push({ eventId: event.eventId, points: awarded });
      remaining -= awarded;
    }

    const pointsAwarded = allocations.reduce((total, item) => total + item.points, 0);
    const balanceAfter = this.#balances.get(request.memberId) + pointsAwarded;
    this.#balances.set(request.memberId, balanceAfter);
    this.#cycleTotals.set(key, used + pointsAwarded);

    const receipt = {
      status: "accrued",
      receiptId: `cycle-receipt-${this.#nextReceipt}`,
      memberId: request.memberId,
      cycleId: request.cycleId,
      pointsAwarded,
      allocations,
      balanceAfter,
    };
    this.#nextReceipt += 1;
    this.#receipts.push(copy(receipt));
    return copy(receipt);
  }

  snapshot() {
    return {
      balances: [...this.#balances.entries()].sort(([left], [right]) => left.localeCompare(right)),
      cycleTotals: [...this.#cycleTotals.entries()].sort(([left], [right]) => left.localeCompare(right)),
      eventPostings: [...this.#eventPostings.values()].map(copy).sort((left, right) => left.eventId.localeCompare(right.eventId)),
      receipts: this.#receipts.map(copy),
      receiptsByKey: [...this.#receiptsByKey.entries()].map(([key, value]) => [key, copy(value)]).sort(([left], [right]) => left.localeCompare(right)),
      nextReceipt: this.#nextReceipt,
    };
  }
}
