from .codec import encode
from .errors import PayloadConflict

def enqueue(store, job_id, payload, available_at):
    encoded = encode(payload)
    with store.transaction() as db:
        existing = db.execute('SELECT payload FROM jobs WHERE job_id = ?', (job_id,)).fetchone()
        if existing is not None and existing['payload'] != encoded:
            raise PayloadConflict(job_id)
        db.execute("""INSERT INTO jobs(job_id, payload, state, available_at)
                      VALUES (?, ?, 'ready', ?)
                      ON CONFLICT(job_id) DO UPDATE SET
                      state='ready', available_at=excluded.available_at,
                      owner=NULL, token=NULL, lease_until=NULL""",
                   (job_id, encoded, available_at))
        return existing is None
