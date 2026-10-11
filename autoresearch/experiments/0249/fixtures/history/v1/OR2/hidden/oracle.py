"""Public asyncio behavior; barriers are events, never wall-clock sleeps."""
import asyncio
import json
from pathlib import Path
import sys
import traceback

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(sys.argv[1]).resolve()))
NAMES = [
    'coalescing-and-independent-keys', 'recursive-result-and-backend-isolation',
    'one-waiter-cancellation-isolation', 'sole-waiter-cancel-and-rejoin',
    'stale-success-keeps-new-flight', 'out-of-order-generations',
    'shared-failure-can-retry', 'stale-failure-keeps-new-flight',
    'backend-cancellation-can-retry', 'shutdown-owns-retired-operations',
    'shutdown-awaits-cleanup', 'consumer-instance-isolation',
]
try:
    from relay import ClosedError, KeyedLoader
except Exception:
    print(json.dumps({'manifestations': [dict(id=name, passed=False, detail=traceback.format_exc()) for name in NAMES]}))
    raise SystemExit(0)


class Request:
    def __init__(self, key):
        self.key = key
        self.answer = asyncio.get_running_loop().create_future()
        self.cancelled = asyncio.Event()
        self.cleanup = asyncio.Event()
        self.cleanup.set()
        self.finished = asyncio.Event()

    def succeed(self, value):
        self.answer.set_result(value)

    def fail(self, error):
        self.answer.set_exception(error)


class Backend:
    def __init__(self):
        self.started = asyncio.Queue()
        self.requests = []

    async def __call__(self, key):
        request = Request(key)
        self.requests.append(request)
        self.started.put_nowait(request)
        try:
            return await request.answer
        except asyncio.CancelledError:
            request.cancelled.set()
            await request.cleanup.wait()
            raise
        finally:
            request.finished.set()

    async def next(self, key):
        request = await self.started.get()
        assert request.key == key
        return request


class Harness:
    def __init__(self):
        self.backend = Backend()
        self.loader = KeyedLoader(self.backend)
        self.callers = []

    async def __aenter__(self):
        return self

    async def get(self, key):
        entered = asyncio.Event()
        async def consume():
            entered.set()
            return await self.loader.get(key)
        task = asyncio.create_task(consume())
        self.callers.append(task)
        # The consumer runs synchronously from entered.set through get's first
        # suspension. No elapsed-time assumption or product internals are used.
        await entered.wait()
        return task

    async def __aexit__(self, *error):
        for request in self.backend.requests:
            request.cleanup.set()
            if not request.answer.done():
                request.succeed({'cleanup': True})
        for caller in self.callers:
            if not caller.done():
                caller.cancel()
        await asyncio.gather(*self.callers, return_exceptions=True)
        await self.loader.close()


async def cancelled(task):
    try:
        await task
    except asyncio.CancelledError:
        return
    raise AssertionError('expected CancelledError')


async def failed(task, kind, message):
    try:
        await task
    except kind as error:
        assert str(error) == message
        return
    raise AssertionError(f'expected {kind.__name__}')


async def sharing():
    async with Harness() as h:
        first = await h.get('a')
        request_a = await h.backend.next('a')
        peer = await h.get('a')
        other = await h.get('b')
        request_b = await h.backend.next('b')
        assert h.loader.snapshot() == {}
        request_b.succeed({'n': 2})
        assert await other == {'n': 2}
        assert not first.done() and not peer.done()
        assert h.loader.snapshot() == {'b': {'n': 2}}
        request_a.succeed({'n': 1})
        assert await first == await peer == {'n': 1}
        assert await h.loader.get('a') == {'n': 1}
        assert [request.key for request in h.backend.requests] == ['a', 'b']


async def ownership():
    async with Harness() as h:
        first = await h.get('a')
        request = await h.backend.next('a')
        peer = await h.get('a')
        source = {'parts': [{'tags': ['clean']}]}
        request.succeed(source)
        one, two = await first, await peer
        source['parts'][0]['tags'].append('backend')
        one['parts'][0]['tags'].append('first')
        snap = h.loader.snapshot()
        snap['a']['parts'][0]['tags'].append('snapshot')
        assert two == {'parts': [{'tags': ['clean']}]}
        assert await h.loader.get('a') == two
        assert h.loader.snapshot() == {'a': two}


async def waiter_cancel():
    async with Harness() as h:
        first = await h.get('a')
        request = await h.backend.next('a')
        peer = await h.get('a')
        first.cancel()
        await cancelled(first)
        assert not request.cancelled.is_set()
        request.succeed({'n': 1})
        assert await peer == {'n': 1}
        assert len(h.backend.requests) == 1


async def sole_cancel():
    async with Harness() as h:
        first = await h.get('a')
        request = await h.backend.next('a')
        first.cancel()
        await cancelled(first)
        assert not request.cancelled.is_set()
        successor = await h.get('a')
        request.succeed({'n': 1})
        assert await successor == {'n': 1}
        assert await h.loader.get('a') == {'n': 1}
        assert len(h.backend.requests) == 1


async def stale_success():
    async with Harness() as h:
        old = await h.get('a')
        retired = await h.backend.next('a')
        h.loader.invalidate('a')
        current = await h.get('a')
        latest = await h.backend.next('a')
        retired.succeed({'generation': 'old'})
        assert await old == {'generation': 'old'}
        assert h.loader.snapshot() == {}
        peer = await h.get('a')
        latest.succeed({'generation': 'current'})
        assert await current == await peer == {'generation': 'current'}
        assert len(h.backend.requests) == 2
        assert h.loader.snapshot() == {'a': {'generation': 'current'}}


async def out_of_order():
    async with Harness() as h:
        callers, requests = [], []
        for index in range(3):
            callers.append(await h.get('a'))
            requests.append(await h.backend.next('a'))
            if index != 2:
                h.loader.invalidate('a')
        requests[2].succeed({'generation': 2})
        assert await callers[2] == {'generation': 2}
        requests[0].succeed({'generation': 0})
        assert await callers[0] == {'generation': 0}
        requests[1].succeed({'generation': 1})
        assert await callers[1] == {'generation': 1}
        assert await h.loader.get('a') == {'generation': 2}
        assert h.loader.snapshot() == {'a': {'generation': 2}}


async def retry():
    async with Harness() as h:
        first = await h.get('a')
        request = await h.backend.next('a')
        peer = await h.get('a')
        request.fail(ValueError('catalog unavailable'))
        await failed(first, ValueError, 'catalog unavailable')
        await failed(peer, ValueError, 'catalog unavailable')
        assert h.loader.snapshot() == {}
        recovery = await h.get('a')
        recovered = await h.backend.next('a')
        recovered.succeed({'n': 2})
        assert await recovery == {'n': 2}
        assert len(h.backend.requests) == 2


async def stale_failure():
    async with Harness() as h:
        old = await h.get('a')
        retired = await h.backend.next('a')
        h.loader.invalidate('a')
        current = await h.get('a')
        latest = await h.backend.next('a')
        retired.fail(LookupError('old generation failed'))
        await failed(old, LookupError, 'old generation failed')
        peer = await h.get('a')
        latest.succeed({'n': 2})
        assert await current == await peer == {'n': 2}
        assert h.loader.snapshot() == {'a': {'n': 2}}
        assert len(h.backend.requests) == 2


async def backend_cancel():
    async with Harness() as h:
        first = await h.get('a')
        request = await h.backend.next('a')
        peer = await h.get('a')
        request.answer.cancel()
        await cancelled(first)
        await cancelled(peer)
        assert h.loader.snapshot() == {}
        recovery = await h.get('a')
        recovered = await h.backend.next('a')
        recovered.succeed({'n': 3})
        assert await recovery == {'n': 3}


async def retired_shutdown():
    async with Harness() as h:
        old = await h.get('a')
        retired = await h.backend.next('a')
        h.loader.invalidate('a')
        current = await h.get('a')
        latest = await h.backend.next('a')
        await h.loader.close()
        assert retired.cancelled.is_set() and retired.finished.is_set()
        assert latest.cancelled.is_set() and latest.finished.is_set()
        await cancelled(old)
        await cancelled(current)
        assert h.loader.snapshot() == {}
        await h.loader.close()
        try:
            await h.loader.get('a')
        except ClosedError:
            pass
        else:
            raise AssertionError('get accepted after close')
        try:
            h.loader.invalidate('a')
        except ClosedError:
            pass
        else:
            raise AssertionError('invalidate accepted after close')


async def shutdown_cleanup():
    async with Harness() as h:
        caller = await h.get('a')
        request = await h.backend.next('a')
        request.cleanup.clear()
        closing = asyncio.create_task(h.loader.close())
        try:
            await request.cancelled.wait()
            assert not closing.done() and not request.finished.is_set()
            entered = asyncio.Event()
            async def close_again():
                entered.set()
                await h.loader.close()
            concurrent = asyncio.create_task(close_again())
            try:
                await entered.wait()
                barrier = asyncio.Event()
                asyncio.get_running_loop().call_soon(barrier.set)
                await barrier.wait()
                assert not request.finished.is_set()
                assert not closing.done() and not concurrent.done()
                assert h.loader.snapshot() == {}
            finally:
                request.cleanup.set()
                await concurrent
            await closing
            assert request.finished.is_set()
            await cancelled(caller)
        finally:
            request.cleanup.set()
            await closing


async def instance_isolation():
    async with Harness() as first, Harness() as second:
        first_call = await first.get('same')
        first_request = await first.backend.next('same')
        second_call = await second.get('same')
        second_request = await second.backend.next('same')
        await first.loader.close()
        await cancelled(first_call)
        assert first_request.finished.is_set()
        assert not second_request.cancelled.is_set()
        second_request.succeed({'n': 5})
        assert await second_call == {'n': 5}
        second.loader.invalidate('unknown')
        assert await second.loader.get('same') == {'n': 5}

FUNCTIONS = [sharing, ownership, waiter_cancel, sole_cancel, stale_success,
             out_of_order, retry, stale_failure, backend_cancel, retired_shutdown,
             shutdown_cleanup, instance_isolation]
results = []
for name, function in zip(NAMES, FUNCTIONS):
    try:
        # This is a deadlock watchdog, not a behavioral timing assertion.
        asyncio.run(asyncio.wait_for(function(), timeout=3))
    except BaseException:
        results.append(dict(id=name, passed=False, detail=traceback.format_exc()))
    else:
        results.append(dict(id=name, passed=True))
print(json.dumps({'manifestations': results}))
