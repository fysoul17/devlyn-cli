export function publishArtifact({ tokenGate, schemaCheck, registry }, request) {
  const issue = schemaCheck.inspect(
    request.namespace,
    request.artifactVersion,
    request.manifest,
  );
  const authorization = tokenGate.authorize(request.tokenId, request.namespace);
  if (!authorization.ok) {
    return authorization;
  }
  if (issue !== null) {
    return {
      ok: false,
      error: "schema_rejected",
      reason: issue.reason,
      field: issue.field,
    };
  }
  return registry.publish(request, authorization.actorId);
}
