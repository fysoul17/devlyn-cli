import json
import sys
import tempfile
import traceback
from pathlib import Path
sys.path.insert(0, str(Path(sys.argv[1]).resolve()))
results = []
def check(name, fn):
    try:
        fn()
    except Exception as exc:
        results.append({'id': name, 'passed': False, 'detail': traceback.format_exc()})
    else:
        results.append({'id': name, 'passed': True})

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
import sqlite3
from parcel import Store, enqueue, claim, complete, retry, get_job, process_one, PayloadConflict

def boundary():
    with Store(':memory:') as db:
        enqueue(db, 'invoice', {'to': 'accounting'}, 4)
        old = claim(db, 'alpha', 4, 7)
        assert claim(db, 'beta', 10.999, 7) is None
        new = claim(db, 'beta', 11, 7)
        assert new is not None and new.attempt == 2 and new.token != old.token
        assert not complete(db, old, 11)
        assert get_job(db, 'invoice').token == new.token
check('expiry-boundary', boundary)

def expired_settlement():
    for settle in ('complete', 'retry'):
        with Store(':memory:') as db:
            enqueue(db, 'invoice', {'to': 'accounting'}, 4)
            receipt = claim(db, 'alpha', 4, 7)
            before = get_job(db, 'invoice')
            outcome = complete(db, receipt, 11) if settle == 'complete' else retry(db, receipt, 11, 90, 'late')
            assert outcome is False
            assert get_job(db, 'invoice') == before
check('expired-unclaimed-settlement', expired_settlement)

def stale_reopened():
    with tempfile.TemporaryDirectory() as temporary:
        path = Path(temporary) / 'spool.sqlite'
        with Store(path) as old_db:
            enqueue(old_db, 'invoice', {'to': 'accounting'}, 0)
            old = claim(old_db, 'same-worker', 0, 5)
        with Store(path) as new_db:
            new = claim(new_db, 'same-worker', 6, 20)
            before = get_job(new_db, 'invoice')
            assert not complete(new_db, old, 7)
            assert get_job(new_db, 'invoice') == before
            assert not retry(new_db, old, 7, 100, 'stale error')
            assert get_job(new_db, 'invoice') == before
            assert complete(new_db, new, 8)
        with Store(path) as reopened:
            assert get_job(reopened, 'invoice').state == 'done'
            assert not retry(reopened, old, 8, 0, 'late')
            assert claim(reopened, 'third', 1000, 5) is None
check('stale-receipt-reopen', stale_reopened)

def producer_states():
    with Store(':memory:') as db:
        original = {'parts': [1, {'size': 2}], 'to': 'ops'}
        enqueue(db, 'invoice', original, 20)
        for state in ('ready', 'leased', 'done'):
            if state == 'leased':
                receipt = claim(db, 'worker', 20, 20)
            if state == 'done':
                assert complete(db, receipt, 21)
            before = get_job(db, 'invoice')
            assert not enqueue(db, 'invoice', {'to': 'ops', 'parts': [1, {'size': 2}]}, 0)
            assert get_job(db, 'invoice') == before
            try:
                enqueue(db, 'invoice', {'parts': []}, 0)
            except PayloadConflict:
                pass
            else:
                raise AssertionError('payload conflict accepted')
            assert get_job(db, 'invoice') == before
check('idempotent-producer-every-state', producer_states)

def retry_lifecycle():
    with Store(':memory:') as db:
        enqueue(db, 'invoice', {'to': 'ops'}, 1)
        first = claim(db, 'alpha', 1, 10)
        assert retry(db, first, 2, 8, 'temporary failure')
        ready = get_job(db, 'invoice')
        assert (ready.state, ready.available_at, ready.attempts, ready.last_error) == ('ready', 10, 1, 'temporary failure')
        assert (ready.owner, ready.token, ready.lease_until) == (None, None, None)
        assert claim(db, 'beta', 9.999, 10) is None
        second = claim(db, 'beta', 10, 10)
        assert second.attempt == 2 and second.token != first.token
        assert complete(db, second, 11)
        done = get_job(db, 'invoice')
        assert done.last_error is None and done.attempts == 2
        assert (done.owner, done.token, done.lease_until) == (None, None, None)
        assert not complete(db, second, 12)
check('retry-lifecycle-clean-settlement', retry_lifecycle)

def ordering():
    with Store(':memory:') as db:
        enqueue(db, 'older', {}, 1)
        enqueue(db, 'same-time-a', {}, 5)
        enqueue(db, 'same-time-b', {}, 5)
        enqueue(db, 'future', {}, 100)
        first = claim(db, 'alpha', 1, 3)
        assert first.job_id == 'older'
        reclaimed = claim(db, 'beta', 6, 20)
        assert reclaimed.job_id == 'older'
        assert claim(db, 'gamma', 6, 20).job_id == 'same-time-a'
        assert claim(db, 'delta', 6, 20).job_id == 'same-time-b'
        assert claim(db, 'epsilon', 6, 20) is None
check('eligibility-and-stable-order', ordering)

def parallel_claim():
    with tempfile.TemporaryDirectory() as temporary:
        path = Path(temporary) / 'spool.sqlite'
        with Store(path) as db:
            for number in range(8):
                enqueue(db, f'parcel-{number}', {'number': number}, 0)
        barrier = Barrier(8)
        def worker(number):
            with Store(path) as db:
                barrier.wait(timeout=10)
                return claim(db, f'w-{number}', 1, 30)
        with ThreadPoolExecutor(max_workers=8) as executor:
            receipts = list(executor.map(worker, range(8)))
        assert all(receipt is not None for receipt in receipts)
        assert len({receipt.job_id for receipt in receipts}) == 8
        assert len({receipt.token for receipt in receipts}) == 8
        assert all(receipt.attempt == 1 for receipt in receipts)
        with Store(path) as db:
            assert claim(db, 'extra', 2, 30) is None
check('independent-concurrent-claims', parallel_claim)

def worker_expiry_success():
    with Store(':memory:') as db:
        enqueue(db, 'invoice', {}, 0)
        clock = [0]
        successor = []
        def handler(payload):
            clock[0] = 12
            successor.append(claim(db, 'next', 11, 30))
        result = process_one(db, 'old', handler, lambda: clock[0], lease_seconds=10)
        assert result.state == 'lost' and result.job_id == 'invoice'
        assert get_job(db, 'invoice').token == successor[0].token
        assert complete(db, successor[0], 13)
check('worker-success-after-takeover', worker_expiry_success)

def worker_expiry_failure():
    with Store(':memory:') as db:
        enqueue(db, 'invoice', {}, 0)
        clock = [0]
        successor = []
        def handler(payload):
            clock[0] = 12
            successor.append(claim(db, 'next', 11, 30))
            raise RuntimeError('destination unavailable')
        result = process_one(db, 'old', handler, lambda: clock[0], lease_seconds=10)
        assert result.state == 'lost'
        current = get_job(db, 'invoice')
        assert current.token == successor[0].token and current.last_error is None
check('worker-failure-after-takeover', worker_expiry_failure)

def worker_elapsed_retry():
    with Store(':memory:') as db:
        enqueue(db, 'invoice', {}, 0)
        clock = [0]
        def handler(payload):
            clock[0] = 4
            raise RuntimeError('delivery timeout')
        result = process_one(db, 'worker', handler, lambda: clock[0], lease_seconds=20, retry_delay=7)
        assert result.state == 'retried'
        current = get_job(db, 'invoice')
        assert current.available_at == 11 and current.last_error == 'delivery timeout'
        assert claim(db, 'next', 10.999, 20) is None
        assert claim(db, 'next', 11, 20).attempt == 2
check('retry-uses-settlement-clock', worker_elapsed_retry)

def settlement_error_visible():
    with Store(':memory:') as db:
        enqueue(db, 'invoice', {}, 0)
        db.connection.execute("""CREATE TRIGGER reject_done BEFORE UPDATE OF state ON jobs
            WHEN NEW.state='done' BEGIN SELECT RAISE(ABORT, 'storage unavailable'); END""")
        delivered = []
        try:
            process_one(db, 'worker', delivered.append, lambda: 1)
        except sqlite3.DatabaseError:
            pass
        else:
            raise AssertionError('settlement database failure did not escape')
        assert delivered == [{}]
        current = get_job(db, 'invoice')
        assert current.state == 'leased' and current.last_error is None
check('settlement-errors-not-handler-errors', settlement_error_visible)

def handler_base_exception():
    with Store(':memory:') as db:
        enqueue(db, 'invoice', {}, 0)
        def handler(payload):
            raise KeyboardInterrupt('stop process')
        try:
            process_one(db, 'worker', handler, lambda: 1)
        except KeyboardInterrupt:
            pass
        else:
            raise AssertionError('BaseException swallowed')
        assert get_job(db, 'invoice').state == 'leased'
check('process-interruption-retains-lease', handler_base_exception)

def invalid_durations():
    with Store(':memory:') as db:
        enqueue(db, 'invoice', {}, 0)
        before = get_job(db, 'invoice')
        for duration in (0, -2):
            try:
                claim(db, 'worker', 1, duration)
            except ValueError:
                pass
            else:
                raise AssertionError('invalid lease duration accepted')
            assert get_job(db, 'invoice') == before
        receipt = claim(db, 'worker', 1, 10)
        before = get_job(db, 'invoice')
        try:
            retry(db, receipt, 2, -1, 'bad input')
        except ValueError:
            pass
        else:
            raise AssertionError('negative retry delay accepted')
        assert get_job(db, 'invoice') == before
check('invalid-input-no-mutation', invalid_durations)

print(json.dumps({'manifestations': results}, sort_keys=True))
