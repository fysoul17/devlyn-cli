import gc
import json
import weakref
from datetime import timedelta, tzinfo

from dateutil import tz


class Zone(tzinfo):
    def __init__(self, name):
        self.name = name

    def utcoffset(self, dt):
        return timedelta(0)

    def dst(self, dt):
        return timedelta(0)

    def tzname(self, dt):
        return self.name


class IndexSize(object):
    def __init__(self, value):
        self.value = value

    def __index__(self):
        return self.value


def getter(size):
    result = type(tz.gettz)()
    result.nocache = lambda name=None: Zone(name)
    assert result.set_cache_size(size) is None
    return result


def fill(g, names):
    return {name: weakref.ref(g(name)) for name in names}


def raises(exception_type, function, argument):
    try:
        function(argument)
    except exception_type as raised:
        return raised
    raise AssertionError('Expected {}'.format(exception_type.__name__))


def row_input_validation():
    for value in (0, 1, 5, False, True, IndexSize(2)):
        g = getter(3)
        assert g.set_cache_size(value) is None
    for value in (None, '3', 1.5, object()):
        g = getter(3)
        raises(TypeError, g.set_cache_size, value)
    for value in (-1, IndexSize(-1)):
        g = getter(3)
        raises(ValueError, g.set_cache_size, value)

    failure = RuntimeError('conversion failed')

    class BrokenIndex(object):
        def __index__(self):
            raise failure

    g = getter(3)
    assert raises(RuntimeError, g.set_cache_size, BrokenIndex()) is failure


def row_negative_rejection_followed_by_hit():
    g = getter(3)
    refs = fill(g, ('A', 'B', 'C'))
    gc.collect()
    assert all(ref() is not None for ref in refs.values())
    raises(ValueError, g.set_cache_size, -1)
    assert g('C') is refs['C']()
    gc.collect()
    assert all(ref() is not None for ref in refs.values())


def row_conversion_failure_preserves_capacity_and_recency():
    g = getter(3)
    refs = fill(g, ('A', 'B', 'C'))
    assert g('A') is refs['A']()
    raises(TypeError, g.set_cache_size, '2')
    refs['D'] = weakref.ref(g('D'))
    gc.collect()
    assert refs['B']() is None
    assert all(refs[name]() is not None for name in ('A', 'C', 'D'))
    assert g.set_cache_size(2) is None
    gc.collect()
    assert refs['C']() is None
    assert refs['A']() is not None and refs['D']() is not None


def row_successful_resizing_and_recency():
    g = getter(3)
    refs = fill(g, ('A', 'B', 'C'))
    assert g('A') is refs['A']()
    assert g.set_cache_size(IndexSize(2)) is None
    gc.collect()
    assert refs['B']() is None
    assert refs['A']() is not None and refs['C']() is not None
    assert g.set_cache_size(3) is None
    refs['D'] = weakref.ref(g('D'))
    gc.collect()
    assert all(refs[name]() is not None for name in ('C', 'A', 'D'))
    refs['E'] = weakref.ref(g('E'))
    gc.collect()
    assert refs['C']() is None
    assert all(refs[name]() is not None for name in ('A', 'D', 'E'))


def row_zero_capacity_and_caller_held_identities():
    g = getter(2)
    held = g('A')
    a_ref = weakref.ref(held)
    b_ref = weakref.ref(g('B'))
    assert g.set_cache_size(0) is None
    gc.collect()
    assert b_ref() is None
    assert g('A') is held
    del held
    gc.collect()
    assert a_ref() is None


def row_cache_clear_remains_compatible():
    g = getter(1)
    held = g('A')
    g.cache_clear()
    fresh = g('A')
    assert fresh is not held
    fresh_ref = weakref.ref(fresh)
    del fresh
    g('B')
    gc.collect()
    assert fresh_ref() is None


ROWS = (
    ('P3-I', row_input_validation),
    ('P3-W', row_negative_rejection_followed_by_hit),
    ('P3-F', row_conversion_failure_preserves_capacity_and_recency),
    ('P3-S', row_successful_resizing_and_recency),
    ('P3-Z', row_zero_capacity_and_caller_held_identities),
    ('P3-C', row_cache_clear_remains_compatible),
)


def main():
    results = {}
    for row_id, check in ROWS:
        try:
            check()
        except Exception:
            results[row_id] = False
        else:
            results[row_id] = True
    print(json.dumps({'rows': results}, separators=(',', ':')))


if __name__ == '__main__':
    main()
