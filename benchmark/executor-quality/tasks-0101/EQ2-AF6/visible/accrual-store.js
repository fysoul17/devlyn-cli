import { CycleMismatchError, UnknownMemberError } from "./errors.js";

function copy(value) {
  return structuredClone(value);
}

function cycleKey(memberId, cycleId) {
  return `${memberId}:${cycleId}`;
}

export class AccrualStore {
  #policy;
  #openingBalances;
  #statements = new Map();

  constructor({ members, policy }) {
    this.#policy = policy;
    this.#openingBalances = new Map(members.map(({ memberId, balance }) => [memberId, balance]));
  }

  appendToStatement(request) {
    return this.#fold(request, false);
  }

  postStatementBatch(request) {
    return this.#fold(request, true);
  }

  #fold(request, detectRepeat) {
    if (!this.#openingBalances.has(request.memberId)) {
      throw new UnknownMemberError(request.memberId);
    }

    for (const event of request.events) {
      if (event.cycleId !== request.cycleId) {
        throw new CycleMismatchError(event.eventId, request.cycleId);
      }
    }

    const key = cycleKey(request.memberId, request.cycleId);
    let statement = this.#statements.get(key);
    if (detectRepeat && statement) {
      const existing = statement.batches.find(
        (batch) => batch.idempotencyKey === request.idempotencyKey,
      );
      if (existing) {
        return copy(existing.outcome);
      }
    }

    if (!statement) {
      const openingBalance = this.#openingBalances.get(request.memberId);
      statement = {
        statementId: `statement:${key}`,
        memberId: request.memberId,
        cycleId: request.cycleId,
        openingBalance,
        cyclePoints: 0,
        closingBalance: openingBalance,
        batches: [],
      };
      this.#statements.set(key, statement);
    }

    const previouslyFolded = new Set(
      statement.batches.flatMap((batch) => batch.allocations.map((item) => item.eventId)),
    );
    let remaining = this.#policy.remaining(statement.cyclePoints);
    const allocations = [];
    for (const event of request.events) {
      if (previouslyFolded.has(event.eventId) || remaining === 0) {
        continue;
      }
      const awarded = Math.min(event.points, remaining);
      allocations.push({ eventId: event.eventId, points: awarded });
      remaining -= awarded;
    }

    const pointsAwarded = allocations.reduce((total, item) => total + item.points, 0);
    statement.cyclePoints += pointsAwarded;
    statement.closingBalance += pointsAwarded;
    const outcome = {
      status: "posted",
      statementId: statement.statementId,
      memberId: request.memberId,
      cycleId: request.cycleId,
      pointsAwarded,
      allocations,
      cyclePointsAfter: statement.cyclePoints,
      balanceAfter: statement.closingBalance,
    };
    statement.batches.push({
      idempotencyKey: request.idempotencyKey,
      allocations: copy(allocations),
      outcome: copy(outcome),
    });
    return copy(outcome);
  }

  snapshot() {
    return {
      statements: [...this.#statements.values()]
        .map(copy)
        .sort((left, right) => left.statementId.localeCompare(right.statementId)),
    };
  }
}
