from .leases import claim, complete, retry
from .model import ProcessResult

def process_one(store, owner, handler, clock, lease_seconds=30, retry_delay=5):
    receipt = claim(store, owner, clock(), lease_seconds)
    if receipt is None:
        return ProcessResult('idle')
    try:
        handler(receipt.payload)
    except Exception as exc:
        settled = retry(store, receipt, clock(), retry_delay, str(exc))
        return ProcessResult('retried' if settled else 'lost', receipt.job_id)
    settled = complete(store, receipt, clock())
    return ProcessResult('completed' if settled else 'lost', receipt.job_id)
