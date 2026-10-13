import pytest

from limitcli import parse_limit


def test_default_and_positive():
    assert parse_limit([]) == 10
    assert parse_limit(["--limit", "3"]) == 3


@pytest.mark.parametrize("value", ["-1", "bad", "1.5"])
def test_errors(value):
    with pytest.raises(SystemExit) as caught:
        parse_limit(["--limit", value])
    assert caught.value.code == 2
