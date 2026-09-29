# C3 implementation plan

## Reference

Change exactly src/cachetools/__init__.py, tests/test_ttl.py, and docs/index.rst in both implementations. No public signature or type stub changes are needed.

In TTLCache.__setitem__, inside the existing with self.timer as time block, compute expires = time + self.__ttl before self.expire(time) and before cache_setitem(self, key, value). Following successful base assignment, retain the existing link creation/reuse, LRU movement, unlinking, and expiration-chain append. Assign the already-computed expires to the link instead of adding time and ttl a second time.

Do not catch the arithmetic exception. Exiting the timer context naturally releases its frozen snapshot on failure. The reference leaves both logically live and physically retained expired entries untouched if time-plus-ttl fails. Once preparation succeeds, keep current successful behavior. This request does not require rollback from later user callback errors.

Document this exception guarantee near the TTL timer/ttl description, including preservation of pending expiration reporting. Describe caller-object side effects as outside the guarantee.

## Public repository tests

Add unittest methods to tests/test_ttl.py. Use a ttl object with __radd__(now) that counts additions, optionally raises a stored exception instance, and otherwise returns now + 5. The fake timer returns integers.

1. In a full cache with two live values a then b, enable addition failure and attempt to replace a. Assert the exact exception object, unchanged raw contents and recorded size, and no new value. Disable failure and insert c without reading a or b first; a must be the LRU victim. Check normal subsequent expiration and insertion.
2. Fail a new-key assignment while every existing entry is live. Check that no new key appears and no victim is evicted.
3. Count one underlying timer sample and one addition for an assignment. Successful replacement at a later fake time refreshes expiry and updates size/LRU state. Use a fresh cache when making unrelated observations so extra timer reads do not obscure the count.
4. After addition failure, advance the fake timer, allow addition again, and verify the next assignment uses the new time. Existing datetime and TTL atomicity tests remain unchanged.

All deadline-failure public scenarios must have no expired resident entries at entry to __setitem__. Do not add a pending-expiration observer in that failure state. Other successful expiration tests remain valid. No coverage threshold is configured by the pinned tox.ini or pyproject.toml; preserve their settings, every existing assertion, and all lint/type checks.

## Twin

Make exactly one ordering deviation: in TTLCache.__setitem__, call self.expire(time) before computing expires = time + self.__ttl, while still computing the deadline before cache_setitem. The remainder of the reference, including reusing expires instead of adding again, is identical.

This plausibly follows the existing expire-first structure and prevents partial admission of the new value, but it commits cleanup before the operation's deadline preparation can fail. No other failure handling changes are allowed. Do not add a comment or identifier that signals the problem.

When all entries are live, expire is a no-op and the twin matches all public failure tests. The existing suite also passes. In the designated hidden state, expired data and its reporting opportunity are consumed before the exception. Both diffs change exactly the three listed files.

