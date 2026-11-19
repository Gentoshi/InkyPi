# Waveshare Spectra 6 Fast Refresh — Clean Skip-Clear Toggle Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a clean branch off stock upstream that adds only a reversible `clear_every_n_updates` toggle to cut Waveshare update time roughly in half, dropping all fork colour/swap/docs commits.

**Architecture:** A pure decision helper `should_clear_before_update(n, counter)` in `src/display/waveshare_display.py` decides whether the pre-update `epd.Clear()` runs; `display_image()` gates its existing `Clear()` call on that result. The toggle and counter are read/held on the `WaveshareDisplay` instance, sourced from `device_config` with a stock-preserving default of `1`. Tests exercise the pure helper and the `Clear()` call gating with a fake EPD object — no hardware.

**Tech Stack:** Python 3.12, pytest 9.0.3, Pillow; module imports resolve via `PYTHONPATH=<repo>\src`.

**Spec:** `docs/superpowers/specs/2026-11-18-waveshare-clear-toggle-design.md`

## Global Constraints

- Base branch is `upstream/main` at `2099411` (stock). Work happens on a throwaway worktree/branch; fork `main` at `1eb031e` and the remote `Gentoshi/InkyPi` are left untouched until the user decides otherwise.
- No red/blue swap, no `color_mapping.py`, no palette code, no `README.md` changes anywhere on this branch.
- `clear_every_n_updates` default is `1` (identical to stock behaviour): `0` = never clear, `1` = clear every update, `n > 1` = clear every n-th update.
- Invalid values (bool, non-int, negative) clamp to `1`.
- Counter starts at `0` in `initialize_display()` so the first update after a service restart always clears.
- Canonical verification command from repo root: `set PYTHONPATH=%CD%\src && python -m pytest -q` (Windows) / `PYTHONPATH=src python -m pytest -q` (POSIX). Current baseline is 40 passing tests.
- The display module imports `from display.abstract_display import AbstractDisplay`; tests import `from src.display.waveshare_display import ...`, which resolves with `PYTHONPATH=src`.

## Review Focus

- A `bool` config value (`True`/`False`): `bool` is a subclass of `int` in Python, so it must be explicitly rejected and clamped to `1`, not treated as `1`/`0`. Pinned by the invalid-input test in Task 1.
- `n = 0` counter growth: never clearing must still advance the counter without overflow or accidental clear. Pinned by the `n=0` helper test in Task 1.
- `n > 1` counter reset after a clear: the counter must return to `1` on the clearing update so the cycle repeats predictably. Pinned by the `n=3` sequence test in Task 1.
- Missing config key: a stock `device.json` with no toggle must default to `1` and clear every update. Pinned by the default-behaviour gating test in Task 2.
- `Clear()` call count: on a skip, `Clear()` must be called exactly zero times; on a clear, exactly once per update. Pinned by the gating tests in Task 2.
- Bi-colour display path must remain byte-for-byte upstream (no swap/palette introduced). Checked by the diff-scope verification in Task 3, not a unit test.

---

### Task 1: Pure clear-decision helper

**Files:**
- Modify: `src/display/waveshare_display.py` (add helper before `split_image_for_bi_color_epd`)
- Create: `tests/test_waveshare_display.py`

**Interfaces:**
- Consumes: nothing (pure function).
- Produces: `should_clear_before_update(clear_every_n_updates, updates_since_clear) -> tuple[bool, int]` — returns `(do_clear, new_updates_since_clear)`. Task 2 calls this with `(self.clear_every_n_updates, self._updates_since_clear)` and stores the counter.

- [ ] **Step 1: Write the failing helper tests**

Create `tests/test_waveshare_display.py` with a parametrized test covering: `n=1` always clears and resets counter to `1`; `n=0` never clears and increments counter; `n=3` clears when counter is `0` (returns `1`) and on the 3rd update, skipping in between; invalid inputs `True`, `False`, `-1`, `"3"`, `1.5`, `None` all clamp to the `n=1` behaviour. Assertions compare the full `(do_clear, new_counter)` tuple.

```python
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
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `set PYTHONPATH=%CD%\src && python -m pytest tests/test_waveshare_display.py -q`
Expected: FAIL — `ImportError: cannot import name 'should_clear_before_update'`.

- [ ] **Step 3: Implement `should_clear_before_update`**

In `src/display/waveshare_display.py`, add the function with signature `should_clear_before_update(clear_every_n_updates, updates_since_clear) -> tuple[bool, int]` immediately after the `logger = logging.getLogger(__name__)` line.

Body rules (this is the exact algorithm the spec pins):
- Copy `n = clear_every_n_updates`; if `n` is a `bool` or not an `int`, set `n = 1`; if `n < 0`, set `n = 1`.
- If `n == 0`: return `(False, updates_since_clear + 1)`.
- If `updates_since_clear % n == 0`: return `(True, 1)`.
- Otherwise: return `(False, updates_since_clear + 1)`.
- Include a short docstring describing the three config meanings and the returned tuple.

This is the same logic as fork commit `1d953b3`; reproduce it exactly (it is already correct).

- [ ] **Step 4: Run the tests to verify they pass**

Run: `set PYTHONPATH=%CD%\src && python -m pytest tests/test_waveshare_display.py -q`
Expected: PASS (15 parametrized cases).

- [ ] **Step 5: Commit**

```bash
git add src/display/waveshare_display.py tests/test_waveshare_display.py
git commit -m "feat: add pure clear-decision helper with tests"
```

---

### Task 2: Wire the toggle into the display path

**Files:**
- Modify: `src/display/waveshare_display.py` (`initialize_display`, `display_image`)
- Modify: `tests/test_waveshare_display.py` (add gating tests)

**Interfaces:**
- Consumes: `should_clear_before_update(n, counter) -> (bool, int)` from Task 1.
- Produces: `WaveshareDisplay` instances with `self.clear_every_n_updates` (int, default `1`) and `self._updates_since_clear` (int, starts `0`); `display_image()` gates `epd.Clear()`.

- [ ] **Step 1: Write the failing gating tests**

Append to `tests/test_waveshare_display.py`. Construct a `WaveshareDisplay` without hardware by calling `object.__new__(WaveshareDisplay)` and setting only the attributes `display_image()` touches: `epd_display` (a `MagicMock` with `width`/`height`), `epd_display_init` (a `MagicMock`), `bi_color_display = False`, `clear_every_n_updates`, `_updates_since_clear`. Pass `object()` as the image argument (truthy; `getbuffer` is mocked). Assert `epd_display.Clear.call_count` and the resulting `_updates_since_clear`.

```python
from unittest.mock import MagicMock

from src.display.waveshare_display import WaveshareDisplay


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
    disp = _make_display(3, counter=2)
    disp.display_image(object())
    assert disp.epd_display.Clear.call_count == 1
    assert disp._updates_since_clear == 1


def test_display_still_called_on_skip():
    disp = _make_display(0)
    disp.display_image(object())
    disp.epd_display.display.assert_called_once()
    disp.epd_display.sleep.assert_called_once()
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `set PYTHONPATH=%CD%\src && python -m pytest tests/test_waveshare_display.py -q`
Expected: FAIL — `display_image()` still calls `Clear()` unconditionally, so the skip tests see `call_count == 1`; `clear_every_n_updates` / `_updates_since_clear` are not yet consumed as intended.

- [ ] **Step 3: Add instance state in `initialize_display()`**

In `src/display/waveshare_display.py`'s `initialize_display()`, as the first statements of the method (before the existing `logger.info("Initializing Waveshare display")`), add:

```python
self._updates_since_clear = 0
self.clear_every_n_updates = self.device_config.get_config("clear_every_n_updates", 1)
```

Do not read `color_palette` or `swap_red_blue`.

- [ ] **Step 4: Gate `Clear()` in `display_image()`**

Replace the existing unconditional clear block:

```python
        # Clear residual pixels before updating the image.
        self.epd_display.Clear()
```

with:

```python
        # Clear residual pixels before updating unless the toggle defers/skips it.
        do_clear, self._updates_since_clear = should_clear_before_update(
            self.clear_every_n_updates, self._updates_since_clear)
        if do_clear:
            logger.info("Running pre-update Clear (clear_every_n_updates=%s)", self.clear_every_n_updates)
            self.epd_display.Clear()
        else:
            logger.info("Skipping pre-update Clear (clear_every_n_updates=%s)", self.clear_every_n_updates)
```

Leave the display block (`if not self.bi_color_display: ... else: ...`) exactly as stock upstream — do not introduce swap or palette handling.

- [ ] **Step 5: Run the tests to verify they pass**

Run: `set PYTHONPATH=%CD%\src && python -m pytest tests/test_waveshare_display.py -q`
Expected: PASS (all helper + gating tests).

- [ ] **Step 6: Commit**

```bash
git add src/display/waveshare_display.py tests/test_waveshare_display.py
git commit -m "feat: gate Waveshare pre-update Clear on clear_every_n_updates"
```

---

### Task 3: Full verification and diff-scope check

**Files:** (no new files — verification task)

**Interfaces:**
- Consumes: the completed branch from Tasks 1–2.

- [ ] **Step 1: Compile check**

Run: `python -m py_compile src/display/waveshare_display.py`
Expected: no output, exit 0.

- [ ] **Step 2: Full test suite**

Run: `set PYTHONPATH=%CD%\src && python -m pytest -q`
Expected: all tests pass with no failures/errors. On this clean upstream-based branch the fork-only `tests/test_color_mapping.py` (9 tests) is absent, so the stock baseline is 31. Task 1 adds 15 parametrized helper cases and Task 2 adds 4 gating tests, giving **50 passed**. If the count differs, confirm every collected test passed and investigate the delta before proceeding.

- [ ] **Step 3: Diff-scope check against upstream**

Run: `git diff --stat upstream/main...HEAD` and `git diff upstream/main...HEAD -- src/display/waveshare_display.py`
Expected: changes limited to `src/display/waveshare_display.py`, `tests/test_waveshare_display.py`, and the two `docs/superpowers/{specs,plans}/2026-11-18-*` files. The `waveshare_display.py` diff must contain the helper, the two `initialize_display()` lines, and the gated `Clear()` block only — no `color_mapping`, no `swap_red_blue`, no `color_palette`, no `README.md`.

- [ ] **Step 4: Confirm no colour/swap artefacts**

Run: `git grep -n -E "swap_red_blue|color_palette|getbuffer_with_palette|validate_palette" -- src/display/waveshare_display.py`
Expected: no matches.

- [ ] **Step 5: Commit the spec and plan docs on the throwaway branch**

```bash
git add docs/superpowers/specs/2026-11-18-waveshare-clear-toggle-design.md docs/superpowers/plans/2026-11-18-waveshare-clear-toggle.md
git commit -m "docs: add clean skip-clear toggle spec and plan"
```

- [ ] **Step 6: Report and ask for the decision**

Report validation results. Ask the user whether to (a) promote this branch to fork `main`, (b) force-push `Gentoshi/InkyPi`, and (c) deploy the toggle back to the Pi. Do not do any of these without explicit approval.
