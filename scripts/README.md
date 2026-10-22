# Offline setup and preprocessing tools

Online-only, explicitly invoked acquisition: setup_data.py (kernels/HYG or optional --gaia), install_assets.py, install_perturbers.py, install_comets.py, install_diameters.py and fetch_references.py. Sources/checksums are retained. Kernel downloads use resumable bounded ranges; optional Gaia uses a retained UWS job.

Offline: build_stellar_pack.py prepares bright-star Galactic trajectories; reconstruct.py runs a checkpointed reduced-model planetary worker. The website launches reconstruction as a standalone process so it can survive server restarts. These scripts preserve inputs/checkpoints and append reasoning/results to the root LOG.md.

install_sanskrit_names.py (offline) writes data/catalogs/sanskrit_star_names.json and reports whether each text-attested star is present in the star catalog. Edit its table, not the JSON, to change a mapping. build_stellar_pack.py targets the active 15,000 BCE–5,000 CE interval, including the last day of 5,000 CE.

Terminal run of the whole interval (resumes from the retained checkpoint; launching clears a website pause): `python scripts/reconstruct.py` (see [Background reconstruction](#background-reconstruction)). After the past run completes it starts the 2000 → 5,000 CE run automatically unless `--no-future` is given. Run one worker at a time; pause from the website or by setting `pause_requested` true in data/jobs/control.json.

install_comets.py (online, explicit) now also lists 25 more apparitions (`MORE`); existing packs are skipped. calibrate_comet_photometry.py (offline) writes peak-calibrated M1 values with sources into data/comets/photometry_overrides.json; rerun it after adding packs.

prune_frame_cache.py (offline): dry run by default; `--apply` deletes saved sky frames created before the newest model-file change (unreachable by cache key), `--vacuum` shrinks the SQLite file. calibrate_comet_photometry.py now includes the Marcus (2007) forward-scattering term, an observable-elongation rule for recorded peaks, and Marcus's (2023) Halley model for all Halley apparitions.

crosscheck_nasa.py: `fetch` (online, explicit; saves JPL Horizons and NASA eclipse-site responses to data/references/crosscheck/ and the manifest, never overwrites) and `analyze` (offline; writes docs/NASA_CROSSCHECK.md and docs/nasa-crosscheck.json). Horizons notes: pass TLIST_TYPE=JD, dates before 9,999 BCE are refused, planet-centre ephemerides exist only for about 1800–2100.

install_classical_names.py (offline) writes data/catalogs/classical_star_names.json from its sourced table (edit the table, not the JSON). deep_seed.py (offline): `asteroids`, `holdout`, `fit`, `seedfit` prepare the DE441-seeded reconstruction and its lunar calibration (data/jobs/calibration/). densify_comets.py (online, explicit) adds 5-minute JPL samples around sungrazing perihelia.

`benchmark_playback.py` runs entirely offline, creates an isolated retained cache under `tmp/performance/`, and reports warm uncached/cached request-path milliseconds (including JSON serialization, excluding HTTP/browser/GPU). Optional `--baseline tmp/performance/baseline.json` verifies whole snapshots against captured originals, ignoring only timing fields. Example: `python scripts/benchmark_playback.py --output tmp/performance/benchmark.json`.

## Shortcut scripts (macOS/Linux)

`setup.sh` and `run.sh` at the project root are zsh shortcuts for the cross-platform steps in the main README. `setup.sh` also keeps pip/npm caches and temporary files in `tmp/`, then runs the test suite. `run.sh` points the XDG, Matplotlib and Astropy caches at `tmp/`, sets `OMP_NUM_THREADS=2`, checks that setup has finished, and starts the server on `PORT` (default 8765). On Windows, or without zsh, run the steps from the main README instead.

## Background reconstruction

Use **Offline data → Generate past / Generate future**. Pause requests finish the current validated checkpoint. Resume retains prior numerical state. The calculation tab also exposes active background progress.

With the virtual environment active, from the project root:

```bash
python scripts/reconstruct.py   # --year defaults to MIN_YEAR (-14999)
```

Keep the terminal open, or run it in the background and redirect output to `tmp/reconstruction.log`. On macOS, prefix the command with `caffeinate -i` to stop the computer sleeping during long runs. Note: the website's **Generate past / Generate future** buttons start the worker through the virtual environment's macOS/Linux interpreter path (`backend/jobs.py`); on Windows start the worker from a terminal as above.

Launching clears a saved website pause and resumes from the latest checkpoint. When the past run completes, the 2000 → 5,000 CE run starts automatically unless `--no-future` is given (DE440/DE441 already cover those dates). Progress is in `data/jobs/status.json` or the Offline data panel. Pause by setting `pause_requested` to true in `data/jobs/control.json`.

The standalone worker uses REBOUND IAS15, first-order relativistic corrections, solar/Earth oblateness, simplified Earth–Moon constant-time-lag tides and 16 massive asteroids. Independent tighter integrations, off-node interpolation probes, JPL overlap residuals and local parameter sensitivity are reported separately. Reduced-model physical uncertainty is **not** calibrated by those checks.

Checkpoints: after every validated 10-year v5 chunk the worker writes the chunk data, then its acceptance report, then the resume point, each by an atomic flushed rename (`data/jobs/past-v5-latest.bin`; the appended `data/jobs/past-v5.bin` archive is history). The archive and latest checkpoint now stop within the supported interval; the last in-range resume point is near 14,991 BCE. If the worker is interrupted, rerun the start command to resume from that checkpoint. The completed in-range coverage is 15,000 BCE–5,000 CE; dates earlier than DE441 are reduced-model extrapolations with the physical limitations listed in [SCIENCE.md](../docs/SCIENCE.md). Multirate compressed chunks and a disk-budget guard prevent silent storage overrun; files are never automatically evicted.

## Pruning the frame cache
`scripts/prune_frame_cache.py` (dry run by default; `--apply --vacuum` to act) deletes only frames that can never be reused: those created before the newest change to any model file, since that change is part of every frame's cache key. On 2026-10-21 it removed 4,043 such frames and shrank the cache from 472 MB to 5.3 MB, keeping the 162 current frames.

## Reference data and NASA cross-check

The saved Horizons cases support offline validation. To explicitly refresh reference data online, use `scripts/fetch_references.py`. Optional full Gaia intake: `python scripts/setup_data.py --gaia`. Rebuild the stellar pack after changing catalogs.

Cross-check against NASA data: `python scripts/crosscheck_nasa.py analyze` (offline) regenerates [docs/NASA_CROSSCHECK.md](../docs/NASA_CROSSCHECK.md) from saved JPL Horizons and NASA eclipse-site responses; `fetch` refreshes them online. It found a deep-time sidereal-angle sign defect (fixed 2026-10-21; ancient-date altitude/azimuth were wrong by tens of degrees) and quantifies the reconstruction's lunar drift from DE441.
