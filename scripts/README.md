# Offline setup and preprocessing tools

Online-only, explicitly invoked acquisition: setup_data.py (kernels/HYG or optional --gaia), install_assets.py, install_perturbers.py, install_comets.py, install_diameters.py and fetch_references.py. Sources/checksums are retained. Kernel downloads use resumable bounded ranges; optional Gaia uses a retained UWS job.

Offline: build_stellar_pack.py prepares bright-star Galactic trajectories; reconstruct.py runs a checkpointed reduced-model planetary worker. The website launches reconstruction as a standalone process so it can survive server restarts. These scripts preserve inputs/checkpoints and append reasoning/results to the root LOG.md.

install_sanskrit_names.py (offline) writes data/catalogs/sanskrit_star_names.json and reports whether each book-named star is present in the star catalog. Edit its table, not the JSON, to change a mapping. build_stellar_pack.py targets the active 15,000 BCE–5,000 CE interval, including the last day of 5,000 CE.

Terminal run of the whole interval (resumes from the retained checkpoint; launching clears a website pause): `nohup caffeinate -i .venv/bin/python scripts/reconstruct.py >> tmp/reconstruction.log 2>&1 &`. After the past run completes it starts the 2000 → 5,000 CE run automatically unless `--no-future` is given. Run one worker at a time; pause from the website or by setting `pause_requested` true in data/jobs/control.json.

install_comets.py (online, explicit) now also lists 25 more apparitions (`MORE`); existing packs are skipped. calibrate_comet_photometry.py (offline) writes peak-calibrated M1 values with sources into data/comets/photometry_overrides.json; rerun it after adding packs.

prune_frame_cache.py (offline): dry run by default; `--apply` deletes saved sky frames created before the newest model-file change (unreachable by cache key), `--vacuum` shrinks the SQLite file. calibrate_comet_photometry.py now includes the Marcus (2007) forward-scattering term, an observable-elongation rule for recorded peaks, and Marcus's (2023) Halley model for all Halley apparitions.

crosscheck_nasa.py: `fetch` (online, explicit; saves JPL Horizons and NASA eclipse-site responses to data/references/crosscheck/ and the manifest, never overwrites) and `analyze` (offline; writes docs/NASA_CROSSCHECK.md and docs/nasa-crosscheck.json). Horizons notes: pass TLIST_TYPE=JD, dates before 9,999 BCE are refused, planet-centre ephemerides exist only for about 1800–2100.

install_classical_names.py (offline) writes data/catalogs/classical_star_names.json from its sourced table (edit the table, not the JSON). deep_seed.py (offline): `asteroids`, `holdout`, `fit`, `seedfit` prepare the DE441-seeded reconstruction and its lunar calibration (data/jobs/calibration/). densify_comets.py (online, explicit) adds 5-minute JPL samples around sungrazing perihelia.

`benchmark_playback.py` runs entirely offline, creates an isolated retained cache under `tmp/performance/`, and reports warm uncached/cached request-path milliseconds (including JSON serialization, excluding HTTP/browser/GPU). Optional `--baseline tmp/performance/baseline.json` verifies whole snapshots against captured originals, ignoring only timing fields. Example: `.venv/bin/python scripts/benchmark_playback.py --output tmp/performance/benchmark.json`.
