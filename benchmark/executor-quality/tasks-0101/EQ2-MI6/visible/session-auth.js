function denied(reason) {
  return { authorized: false, reason };
}

export class SessionAuth {
  #sessions;

  constructor(sessions) {
    this.#sessions = new Map(sessions.map((session) => [session.id, { ...session }]));
  }

  authorize({ sessionId, accountId }) {
    const session = this.#sessions.get(sessionId);
    if (!session) {
      return denied("session_missing");
    }
    if (session.status !== "active") {
      return denied(`session_${session.status}`);
    }
    if (session.accountId !== accountId) {
      return denied("account_mismatch");
    }
    return { authorized: true, accountId: session.accountId };
  }
}
