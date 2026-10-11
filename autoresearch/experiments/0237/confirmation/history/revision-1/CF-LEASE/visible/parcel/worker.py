from .leases import claim, complete, retry
from .model import ProcessResult

def process_one(store, owner, handler, clock, lease_seconds=30, retry_delay=5):
    now = clock()
    receipt = claim(store, owner, now, lease_seconds)
    if receipt is None:
        return ProcessResult('idle')
    try:
        handler(receipt.payload)
        complete(store, receipt, now)
    except Exception as exc:
        retry(store, receipt, now, retry_delay, str(exc))
        return ProcessResult('retried', receipt.job_id)
    return ProcessResult('completed', receipt.job_id)
