import pytest

from expiry import is_expired


def test_before_and_after():
    assert is_expired(9, 10) is False
    assert is_expired(11, 10) is True


def test_incompatible_values():
    with pytest.raises(TypeError):
        is_expired(None, 10)
