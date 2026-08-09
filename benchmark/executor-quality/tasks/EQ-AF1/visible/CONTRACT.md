# Job store contract

job_id identifies a submission attempt exactly once: any later submission that reuses a job_id already present in the store — whether it arrives in a separate call or alongside other jobs in the same call — is a no-op that returns the original stored record without a second side effect.

Bulk submission must preserve the same identity rule as individual submission.
