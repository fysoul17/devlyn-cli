import { normalizeJob } from "./job.js";
import { rankJobs } from "./priority.js";

export function enqueueAll(submissions, capacity = submissions.length) {
  const jobs = submissions.map((submission, sequence) => normalizeJob(submission, sequence));
  return rankJobs(jobs).slice(0, capacity);
}
