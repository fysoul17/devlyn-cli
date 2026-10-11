from .codec import decode
from .model import Job

def get_job(store, job_id):
    row = store.connection.execute('SELECT * FROM jobs WHERE job_id = ?', (job_id,)).fetchone()
    if row is None:
        return None
    return Job(row['job_id'], decode(row['payload']), row['state'],
               row['available_at'], row['attempts'], row['owner'], row['token'],
               row['lease_until'], row['last_error'])
