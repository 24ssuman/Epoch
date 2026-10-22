# Exact-frame playback and ground-only UI

Measured 22 October 2026 on this Mac, offline, with installed JPL/catalog/comet/accepted reconstruction data. The background worker was already complete after the separately requested date-range change; it was not restarted for this work. The supported interval remains 15,000 BCE–5,000 CE.

## Warm backend measurements

12 uncached and 12 cached samples per case, Kolkata (22.5726° N, 88.3639° E), elevation 0 m, additional ΔT offset 0 s, common star limit magnitude 5.76. Request-path times include isolated SQLite persistence and JSON serialization; they exclude HTTP, browser and GPU. Speedup compares calculation plus revision-key cost to the captured pre-change baseline on the same machine.

| Case | Uncached median (ms) | Cached median (ms) | Calculation + revision speedup |
|---|---:|---:|---:|
| modern-ground | 59.4 | 17.4 | 5.5× |
| ancient-ground | 94.6 | 16.3 | 3.4× |
| deep-ground | 105.3 | 16.5 | 7.7× |
| modern-space | 107.5 | 43.4 | 25.7× |
| comet-ground | 54.3 | 17.0 | 14.4× |

All five complete snapshots matched their captured baselines exactly after excluding calculation timing fields: IDs, directions, magnitudes, colors, sizes, body phases, comet tails, source/frame/units/time-scale metadata and coverage flags. The space case validates the preserved API, not an exposed UI perspective. Raw samples: [playback-performance.json](playback-performance.json). Reproduce with `scripts/benchmark_playback.py`; the original baselines/backups remain in `tmp/performance/`.

## Playback and rendering

The UI now has only the Earth observer view, with no perspective selector, orbital camera shortcuts, orbital trails controls or Photography tag. Exact 100 ms samples preserve the selected time rate; one active request plus one newest pending target prevents request starvation. Generation guards reject obsolete observer/date/model/direction responses. Scientific projection and existing trajectory evaluation remain unchanged; no display interpolation, star-limit reduction or adaptive quality reduction is used.

On the 1280×720 in-app browser, modern ground playback showed about 9–10 accepted exact updates/s and 60 browser callbacks/s, with a measured request around 63 ms, scene update 2.9 ms and redraw 0.4 ms CPU in one observed sample. These are observations, not guaranteed FPS on every device/date. Existing pre-change observations were about 1–1.5 sky updates/s for uncached playback. Heavier dates, first-use imports, the full-scattering shader, background CPU work, hidden-tab throttling and cache storage limits still affect results. The meter now distinguishes callbacks, renders and accepted exact updates; detailed request/calculation/cache/update/draw timings are in its hover text. GPU execution is not measured by the CPU draw timer.

Buffers/materials/grids/body meshes persist across frames, growing only when capacity needs increase. Hidden pooled objects are bounded by installed body/comet IDs. Labels do not rebuild geometry. Daylight-disabled/atmosphere-disabled paths bypass unused scattering quadrature with the same output. Cache keys track active-version accepted chunks and calibration; old frames remain intact and storage limits remain 512 MB payload / 10 GB workspace.

## Moon phase and verification

The Moon tab in the side rail opens/closes the side panel; the close button also collapses it. It shows phase name, topocentric illuminated percentage, waxing/waning, horizon state, source and TT date from the accepted exact frame. Its SVG disk is schematic, right-lit for waxing and left-lit for waning; orientation and screen size are not presented as a sky image. Missing planetary coverage shows an unavailable state. Checked at desktop and 390×844 phone width.

Validation: 129 Python tests and 8 frontend tests passed (5 scheduler + 3 lunar-light tests); TypeScript/production build passed. Existing Vite bundle-size and Starlette/httpx deprecation warnings remain. Saved Horizons scientific tolerances still pass. Local browser checks cover phase panel/collapse, ground playback and reverse stored-frame replay; renderer resource counters and errors are exposed for inspection.

Subsequent Moon-lighting refinement adds one reused local billboard and a small SVG lit-shape blur. It intentionally changes lunar appearance and the broad lunar background tint, without changing backend scientific snapshots. See [MOON_LIGHTING.md](MOON_LIGHTING.md).

After the Moon-lighting refinement, one loaded 6°-FOV lunar playback check showed 60 browser callbacks/s, 5 accepted exact updates/s, request ~137 ms, scene update ~5.7 ms and redraw ~0.9 ms CPU; 21 geometries and 7 programs stayed bounded. This illustrates host/backend variability versus the earlier 9–10 updates/s run; the glow adds no full-screen pass. Raw observation: tmp/performance/moon-live-metrics.json.
