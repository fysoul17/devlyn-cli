export class PublishTokenGate {
  #tokens;

  constructor(tokens = []) {
    this.#tokens = new Map(tokens.map((token) => [token.id, { ...token }]));
  }

  authorize(tokenId, namespace) {
    const token = this.#tokens.get(tokenId);
    if (token?.active !== true || !token.namespaces.includes(namespace)) {
      return { ok: false, error: "publish_denied" };
    }
    return { ok: true, actorId: token.actorId };
  }
}
