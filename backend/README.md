# Scientific backend

`app.py` serves the local API and built frontend. `astrotime.py` owns calendars/time/orientation, `ephemeris.py` body trajectories/apparent geometry, `catalog.py` bright-first stellar screening/motion/photometry/diameters, `progress.py` per-request progress/previews, and `jobs.py` standalone multirate reconstruction/validation.

Snapshot API: `/api/snapshot?jd=<TT JD>&lat=...&lon=...&max_magnitude=5.76&limit=9000&progress_id=<unique id>`. A progress ID exposes live stages and an early bright-star preview at `/api/calculation-progress/<id>`. Results include time, frame, units, model/quality, coverage and calculation statistics. Snapshot previews are labelled and superseded by the complete response.

Other interfaces: bootstrap, calendar/date conversion, search/object details, next-night search, actual ephemeris trails, coverage/manifest, and background job start/pause/resume/status. Run through the workspace `run.sh` so package caches stay local. Runtime does not access external services.

`sanskrit.py` merges data/catalogs/sanskrit_star_names.json (book names, `book_star`, English labels; two IAU Sanskrit-derived catalog names that refer to a different star than the book's are replaced by Bayer/Flamsteed labels) with data/catalogs/classical_star_names.json (classical names for stars the book does not name). Star and body results carry `sanskrit_name` (IAST), `sanskrit_devanagari`, and in detail `sanskrit_basis` (book/classical), `sanskrit_source`, `sanskrit_alternatives`. Search matches Sanskrit spellings, IAST, Devanagari, aliases and spelling variants. Supported dates are 15,000 BCE–5,000 CE (`MIN_YEAR`/`MAX_YEAR` in astrotime.py).

Snapshot frames are view-aware: `view=ground&horizon_only=true` returns stars within 2° above the horizon with `ground_direction` only; `view=space` adds ICRS `direction`/`space_direction`. Per-star provenance appears only in `/api/object/<id>`; the frame's `star_fields` gives frame, units and time scale. All stars obey the common limit `catalog.STAR_LIMIT` = 5.76 (frames, search, object detail); book-named stars (`book_star`) keep a tiny exemption only so Asterope (5.756–5.761) never drops out. `paths.guard` refreshes its workspace scan in a background thread; `frame_cache` tracks used bytes in memory.

Bodies carry `sanskrit_*` fields from the book's `bodies` section; comets carry the book's Dhūmaketu label. `ephemeris.brightness()` implements Mallama & Hilton (2018) planetary photometry, as JPL Horizons does.

Reconstruction checkpoints (`jobs.py`): `save_checkpoint` writes `<tag>-v3-latest.bin` by temp file + fsync + rename and appends to the `<tag>-v3.bin` history archive; `load_checkpoint` resumes from the furthest-progressed readable one and skips (never deletes) unreadable files. Chunk `.npz` data and `.json` reports are written atomically, data before report. The independent tighter and tidal-variant checks start from an in-memory copy of the chunk's start state.

`comets.py`: cached JPL comet packs (spline inside each window only), JPL M1/k1 photometry with sourced overrides from data/comets/photometry_overrides.json, perihelion from the samples, and ion/dust tail ribbons (`tails`, heliocentric AU plus observer ground directions). `/api/comets` lists apparitions; search returns comets whose window covers the date.

`comets.py` brightness: `magnitude()` = M1 + 5 log Δ + k1 log r + `phase_correction()` (Marcus 2007 compound Henyey–Greenstein, normalised at 90°, δ90 per comet); `photometry_at()` supports separate pre/post-perihelion laws with a δ90 ramp (used for Halley). `sanskrit.loose()` gives a spelling-tolerant key used after exact matching fails.

Exact-frame performance: frame_cache indexes stamped accepted reports for `jobs.VERSION`, includes calibration and retarded-time dependencies, and detects source edits/new coverage while excluding worker status/control. `playback_cache.timings_ms` reports key/lookup/store/request milliseconds; the scientific calculation timings retain their original meaning. Bootstrap includes `data_revision` for the UI. `/api/snapshot?preview=false` skips preview assembly while playing; it does not change the exact result or cache key. `/api/object/<id>` additionally accepts elevation (m) and dt offset (s) to match the displayed observer. Fixed star naming/color/radius fields are cached by catalog/diameter/naming revision; candidate scratch arrays remain compact. The frontend now requests ground frames only; space/trails APIs and preserved data remain available for compatibility.

## Extending the date range

The supported interval is defined once, as astronomical years, in `backend/astrotime.py`:

```python
MIN_YEAR, MAX_YEAR = -14999, 5000  # astronomical year -N+1 is N BCE; year 0 is 1 BCE
```

To widen (or narrow) it:

1. **Backend:** change `MIN_YEAR` / `MAX_YEAR`. This updates calendar validation, `/api/snapshot` and `/api/calendar` rejection, the `/api/bootstrap` `range` (which the timeline slider reads), the `/api/jobs` limits and default target, the default `--year` of `scripts/reconstruct.py`, and the span of the CIO-locator spline.
2. **Frontend** (`frontend/src/App.tsx`, then `npm run build --prefix frontend`): the initial `range` state (JD of the new bounds; `python -c "from backend.astrotime import calendar_jd; print(calendar_jd(MIN_YEAR), calendar_jd(MAX_YEAR,12,31))"` after step 1), the timeline tick list (`[['15,000 BCE',-14999],…]`), the two "15,000 BCE – 5,000 CE" texts (date dialog and Offline data panel), and the `jobAction` default and **Generate past** / **Generate future** targets.
3. **Tests:** `tests/test_sanskrit.py::test_interval_is_15000_bce_to_5000_ce` and the year lists in `tests/test_science.py` and `tests/test_api.py`.
4. **Planet data for the new dates:**
   - Earlier than 13,200 BCE (DE441 start), planets come from the background reconstruction. Validated v5 chunks cover 13,201–15,000 BCE. The latest retained resume point is inside the supported interval near 14,991 BCE; an accepted chunk clipped at the 15,000 BCE boundary covers the earliest supported dates. After widening the lower limit, run **Generate past** or `scripts/reconstruct.py --year <MIN_YEAR>` to calculate any newly requested earlier interval.
   - Later than 5,000 CE, DE441 covers dates up to about 17,191 CE. Beyond that there is no forward reconstruction (`backend/jobs.py` only integrates the past), so code changes would be needed.
5. **Stars:** the Galactic-motion pack (`data/catalogs/galactic.npz`) covers the supported interval only, from its first Julian-date instant through 31 December 5,000 CE. It uses galpy MWPotential2014 positions in parsecs, with ICRS axes fixed as the Sun and stars move; incomplete stellar motions remain approximate. Rebuild with `scripts/build_stellar_pack.py` after changing `MIN_YEAR`/`MAX_YEAR`.
6. **Science limits do not move with the range:** Earth rotation is `assumed-rotation` outside −1999…3000, nutation is omitted beyond 4,000 years from J2000, and the lunar tidal correction is calibrated only on a 6,800-year DE441 hold-out. Dates added beyond these are extrapolation and must be labelled as such, never as validated.
7. Record the change in `LOG.md` and `PLAN.md`. Note that backend code edits change the playback frame-cache keys, so stored frames are recomputed on demand (`scripts/prune_frame_cache.py` removes the unreachable ones).

## Loading and rendering

Ground-view requests include horizon directions and, when the ground is enabled, only stars within 2° below or above the visible hemisphere boundary. Per-star source/epoch/diameter provenance is fetched on the object card; frame-level metadata remains in `star_fields`. Fixed stellar names, colors and radii are cached by source revision; positions, brightness and apparent sizes are calculated for each exact time. Active reconstruction dependencies are indexed by stamped reports, including the short retarded-time interval used for apparent positions. Existing frames and the 512 MB/10 GB guards are preserved.

The scene reuses star buffers, materials, grids and body meshes. Label-only changes do not rebuild geometry; disabled atmosphere/sunlight bypasses unnecessary scattering quadrature without changing its result. See [performance measurements](../docs/PERFORMANCE.md). The backend space-data API is retained for compatibility and scientific checks; the UI exposes no space camera.

## Stored playback

Completed sky frames are saved locally in `data/playback/frames.sqlite3` and reused when returning to the same date and observer/calculation settings, even after restarting. The calculation tab says **Stored frame** on a hit. Playback uses reversible fixed steps so reversing at the same speed revisits the same frames. New times or locations still need apparent-sky projections, using installed trajectory packs rather than rerunning integration. Scientific model/data changes invalidate affected cached frames. Cache storage stops safely at its 512 MB payload allowance or the 10 GB workspace guard; existing data is preserved.

The calculation drawer includes **How much is stored**: frame count, distinct saved dates, earliest/latest times, compressed storage and validated background trajectory duration. Saved frames are discrete samples; their earliest/latest bounds do not imply gap-free playback coverage.

## Prominent stars only

The simulator enforces one common apparent-magnitude limit (4.5 until 2026-10-22, now 5.76; `STAR_LIMIT` in backend/catalog.py) for stellar calculations and display, including saved-frame reuse, Galactic trajectory evaluation, search and object selection. Faint-star controls are removed. Old catalog/trajectory/cache files remain preserved, but faint entries are excluded from the active simulation. This supersedes the earlier optional faint-star mode. Planet and comet handling is unchanged.

Installed ephemeris coverage means stored orbital trajectories can be evaluated; each new time/location still needs Earth orientation, light-time/apparent directions, stellar brightness and a sky projection. The calculation drawer labels this “Preparing sky from stored trajectories.” Identical saved sky frames are loaded directly. DE441 body segments are selected by requested date, including its ancient segment. Obsolete queued playback requests are skipped when a newer frame for that browser arrives.
