from unittest.mock import MagicMock

import pytest

from src.display.waveshare_display import WaveshareDisplay, should_clear_before_update


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


def _make_display(n, counter=0):
    disp = object.__new__(WaveshareDisplay)
    disp.epd_display = MagicMock()
    disp.epd_display.width = 800
    disp.epd_display.height = 480
    disp.epd_display_init = MagicMock()
    disp.bi_color_display = False
    disp.clear_every_n_updates = n
    disp._updates_since_clear = counter
    return disp


def test_clear_runs_by_default():
    disp = _make_display(1)
    disp.display_image(object())
    assert disp.epd_display.Clear.call_count == 1
    assert disp._updates_since_clear == 1


def test_clear_skipped_when_disabled():
    disp = _make_display(0, counter=4)
    disp.display_image(object())
    assert disp.epd_display.Clear.call_count == 0
    assert disp._updates_since_clear == 5


def test_clear_fires_on_nth_update():
    disp = _make_display(3, counter=3)
    disp.display_image(object())
    assert disp.epd_display.Clear.call_count == 1
    assert disp._updates_since_clear == 1


def test_display_still_called_on_skip():
    disp = _make_display(0)
    disp.display_image(object())
    disp.epd_display.display.assert_called_once()
    disp.epd_display.sleep.assert_called_once()
