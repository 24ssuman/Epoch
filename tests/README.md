# Verification

Run `python -m pytest -q`. Tests use installed local datasets and saved independent Horizons cases. Runtime network is explicitly disabled in an offline test. Real concurrent progress and bright-first filtering/preview behavior are covered. The reference test writes the requested residual report under docs/; no user data is removed.

test_sanskrit.py checks the 15,000 BCE–5,000 CE limit (snapshot, bootstrap and job requests), that every text-attested star is in the catalog and prominent, unique English labels, additional classical names, both names and basis in snapshots/object detail, and Sanskrit/Devanagari/variant search for stars and planets.
test_sanskrit.py also checks that faint text-attested stars (Pleiades members) are shown and flagged, and that ground-view frames are slim and skip below-horizon stars.
test_checkpoint.py checks checkpoint roundtrip, furthest-progress selection, fallback from a torn latest file to the history archive, legacy-archive resume, and atomic chunk files (temporary folder only).
test_comets.py checks perihelia against JPL elements, the sourced Hale–Bopp brightness, ion (anti-solar) and dust (lagging) tail directions, no comets outside cached windows, and comet search.
test_comets.py also checks the forward-scattering function, that Tsuchinshan–ATLAS's peak falls on 9 Oct 2024, and that Halley 2061 reproduces Marcus's (2023) forecast table. test_sanskrit.py checks spelling-variant search.

test_nasa_crosscheck.py (offline, saved NASA data): geocentric directions vs Horizons over 9,000 BCE–5,000 CE, ΔT within NASA's standard errors, modern greatest-eclipse times vs the Five Millennium Canon, comet splines vs Horizons, and a regression test that the deep-time sidereal angle matches ERFA GAST (it had the wrong sign until 2026-10-21).

`test_performance.py` covers active-version cache dependencies, newly accepted coverage, report reuse, calibration/source edits, constant-cost naming checks, observer-coherent object details and disabled playback previews. The frontend transport suite (`npm test --prefix frontend`) covers exact sample arithmetic, reverse replay, queued latest targets, generation invalidation, pause/scrub/resume and failures. UI/Moon phase layout and collapse checks are verified in the browser.

## Running the checks

With the virtual environment active, from the project root:

```bash
python -m pytest -q
npm test --prefix frontend
npm run build --prefix frontend
```
