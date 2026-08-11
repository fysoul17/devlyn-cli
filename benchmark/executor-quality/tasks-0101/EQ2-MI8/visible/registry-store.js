export class ArtifactRegistry {
  versions = [];

  publish({ namespace, artifactVersion, manifest }, actorId) {
    const attributes = Object.fromEntries(
      manifest.attributes.map(({ field, value }) => [field, value]),
    );
    const stored = Object.freeze({
      namespace,
      artifactVersion,
      schemaVersion: manifest.schemaVersion,
      name: attributes.name,
      digest: attributes.digest,
      mediaType: attributes.mediaType ?? null,
      publishedBy: actorId,
    });
    this.versions.push(stored);
    return { ok: true, status: "published", version: stored };
  }
}
