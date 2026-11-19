import pytest

from src.display.waveshare_display import should_clear_before_update


@pytest.mark.parametrize(
    "n,counter,expected",
    [
        (1, 0, (True, 1)),    # default: clear every update
        (1, 5, (True, 1)),
        (0, 0, (False, 1)),   # never clear, counter still advances
        (0, 7, (False, 8)),
        (3, 0, (True, 1)),    # clear on first update, reset counter
        (3, 1, (False, 2)),   # skip next two
        (3, 2, (False, 3)),
        (3, 3, (True, 1)),    # clear again on the 4th update
    ],
)
def test_should_clear_before_update(n, counter, expected):
    assert should_clear_before_update(n, counter) == expected


@pytest.mark.parametrize("bad", [True, False, -1, -5, "3", 1.5, None])
def test_invalid_values_clamp_to_default(bad):
    # Clamped to n=1: always clear, counter resets to 1.
    assert should_clear_before_update(bad, 4) == (True, 1)
