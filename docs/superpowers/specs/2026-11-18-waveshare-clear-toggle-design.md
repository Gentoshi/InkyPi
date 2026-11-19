# Waveshare Spectra 6 Fast Refresh — Clean Skip-Clear Toggle

Date: 2026-11-18

## Intent

Reduce this fork to stock `fatihak/InkyPi` plus exactly one clean improvement: the
`clear_every_n_updates` toggle that roughly halves per-update time (~64 s -> ~32 s) by
skipping the redundant pre-update `Clear()`. The red/blue channel swap and the calibrated
colour-palette work are abandoned and must not survive. The Pi is already redeployed to
stock upstream; this is fork-only work.

## Goals

- A single focused change built on a throwaway branch/worktree off `upstream/main`
  (`2099411`), validated with real unit tests.
- Current fork `main` (`1eb031e`) is left untouched until the user decides what to do
  with it.

## Non-goals

- No red/blue swap, no `color_mapping.py`, no palette code.
- No partial/region refresh — the Spectra 6 panel does not support it.

## Anti-goals

- No rewriting of remote fork history (`Gentoshi/InkyPi`) until the user explicitly
  approves it.
- No redeploy to the Pi until the user decides; when it happens, the live weather config
  must be preserved.

## Constraints

- Base is stock upstream `main`; the toggle defaults to current behaviour (clear before
  every update) so stock configurations are unaffected.
- Config semantics: `0` = never clear; `1` = clear every update (default); `n > 1` = clear
  every n-th update. Invalid values (non-integer, negative, bool) clamp to `1`.
- The counter resets on service restart, so the first update after a restart always
  clears (handles stale panel content after downtime).

## Approaches

- **A — reset fork main to upstream and force-push.** Destructive, no validation gate,
  and overwrites the remote history before the user has seen the result. Rejected.
- **B — keep fork history, revert only the swap commit.** Leaves the palette/docs mess in
  the tree and does not deliver "stock upstream plus one change". Rejected.
- **C — clean branch off upstream, validate, then decide.** Reversible, keeps `main` as a
  safety net, and defers the force-push decision until after validation. **Chosen by the
  user.**

## Design

- Port the pure helper `should_clear_before_update(clear_every_n_updates,
  updates_since_clear)` -> `(do_clear, new_counter)` from commit `1d953b3` verbatim, since
  it is already correct: it sanitizes `n`, implements `0`/`1`/`n>1`, and clamps invalid
  values to `1`.
- In `initialize_display()`: set `self._updates_since_clear = 0` and read
  `clear_every_n_updates` from `device_config` with default `1`. Do **not** read or
  reference `color_palette` / `swap_red_blue`.
- In `display_image()`: call the helper, gate the existing `self.epd_display.Clear()` on
  `do_clear`, store the returned counter, and log which path ran. The display path stays
  exactly as upstream (`self.epd_display.display(self.epd_display.getbuffer(image))`).
- No changes to `README.md`, no new docs beyond the spec/plan committed on the throwaway
  branch.

## Files

- Modified: `src/display/waveshare_display.py` (one tracked file, upstream base).
- Added: `tests/test_waveshare_display.py` — helper cases (`n=1`, `n=0`, `n>1`, invalid
  inputs) and `Clear()` call gating via a fake EPD object.
- Added: this spec and the implementation plan on the throwaway branch.

## Verification

1. `python -m py_compile src/display/waveshare_display.py`.
2. Run the test suite (`pytest`) — new helper and gating tests must pass.
3. Confirm the diff against `upstream/main` is limited to the toggle, its tests, and docs
   (no colour/swap code, no README changes).
4. Report results, then ask the user about promoting the branch, force-pushing the remote
   fork, and redeploying the toggle to the Pi.

## Risk & Mitigation

- Ghosting when clears are skipped or deferred: the `n` counter forces a periodic full
  clear and the value is runtime-configurable, so the user can tune it without a code
  change.
- Remote history: never rewritten without explicit approval; `main` at `1eb031e` remains
  the fallback until then.
