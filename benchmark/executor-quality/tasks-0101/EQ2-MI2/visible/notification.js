export function normalizeNotification(submission, sequence) {
  return {
    id: String(submission.id),
    body: String(submission.body),
    priority: Number(submission.priority),
    recipients: submission.recipients.map(String),
    sequence,
  };
}
