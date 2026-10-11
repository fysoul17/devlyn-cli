from uuid import uuid4
from .codec import decode
from .model import Receipt

def claim(store, owner, now, lease_seconds):
    if lease_seconds <= 0:
        raise ValueError('lease_seconds must be positive')
    with store.transaction() as db:
        row = db.execute("""SELECT * FROM jobs
            WHERE (state='ready' AND available_at <= ?)
               OR (state='leased' AND lease_until < ?)
            ORDER BY available_at, seq LIMIT 1""", (now, now)).fetchone()
        if row is None:
            return None
        token = str(uuid4())
        until = now + lease_seconds
        attempt = row['attempts'] + 1
        db.execute("""UPDATE jobs SET state='leased', owner=?, token=?,
            lease_until=?, attempts=? WHERE job_id=?""",
            (owner, token, until, attempt, row['job_id']))
        return Receipt(row['job_id'], decode(row['payload']), owner, token, until, attempt)

def complete(store, receipt, now):
    with store.transaction() as db:
        cursor = db.execute("""UPDATE jobs SET state='done', owner=NULL,
            token=NULL, lease_until=NULL WHERE job_id=?""", (receipt.job_id,))
        return cursor.rowcount == 1

def retry(store, receipt, now, delay, error):
    if delay < 0:
        raise ValueError('delay must be nonnegative')
    with store.transaction() as db:
        cursor = db.execute("""UPDATE jobs SET state='ready', available_at=?,
            owner=NULL, token=NULL, lease_until=NULL, last_error=?
            WHERE job_id=?""", (now + delay, str(error), receipt.job_id))
        return cursor.rowcount == 1
