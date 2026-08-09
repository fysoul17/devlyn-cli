import { normalizeJob } from "./job.js";
import { rankJobs } from "./priority.js";

export function enqueueAll(submissions) {
  const jobs = submissions.map((submission, sequence) => normalizeJob(submission, sequence));
  return rankJobs(jobs);
}
