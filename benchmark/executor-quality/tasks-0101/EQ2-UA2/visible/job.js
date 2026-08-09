export function normalizeJob(submission, sequence) {
  return {
    id: String(submission.id),
    document: String(submission.document),
    priority: Number(submission.priority),
    sequence,
  };
}
