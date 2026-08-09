export function rankJobs(jobs) {
  return [...jobs].sort(
    (left, right) => right.priority - left.priority || left.sequence - right.sequence,
  );
}
