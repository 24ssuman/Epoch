# Epoch — Offline Sky Simulator

A local astronomical observatory showing the sky from Earth. Built with React, TypeScript, Three.js and a Python/FastAPI scientific service.

## Project website

[Open the browser-based Epoch sky viewer](https://24ssuman.github.io/Epoch/). The separate `gh-pages` branch serves a no-install static viewer with 1,002 precomputed sky frames from 15,000 BCE through 5,000 CE. It steps between saved frames at a target interval of 20 years; it does not calculate dates between frames, interpolate, or extrapolate outside its bundled endpoints. The hosted view uses the saved Kolkata observer. The full local simulator below supports its interactive calculation workflow and additional observing controls.

## Run locally

```sh
./run.sh
```

Open **http://127.0.0.1:8765/**. The installed version needs no internet. Stop the web server with Ctrl-C; a separately launched reconstruction worker can continue independently.

For a fresh installation, run `./setup.sh` while online. All environments, package caches, datasets and temporary work stay in this workspace. The setup downloads several GB. It preserves files and checks the 10 GB workspace budget.

## Observe

- Drag to look around the sky from Earth; use the field-of-view control or mouse wheel to zoom. The perspective selector and orbital/solar-system cameras have been removed.
- Select an offline location or enter coordinates and elevation. Daylight, twilight and night follow the calculated Sun. **Find the next night** moves to a local astronomical night if one exists within 72 hours.
- The **Bright Star Atlas** ("Above your horizon") lists prominent named stars above the local horizon; click its header to collapse or expand it (remembered in this browser). Click one to inspect and center it. Search also accepts names or HIP catalog IDs.
- **Common star limit: magnitude 5.76** (the faintest book-named star, Asterope). Every star at least that bright is calculated and shown (about 3,880 over the whole sky, about 2,000 above the horizon). Larger magnitudes mean fainter apparent brightness, not smaller physical size.
- Calculations screen catalog brightness cheaply, process selected stars in brightness order, and publish the first 128-star preview before the remaining selected stars finish. Faint stars excluded by the filter do not receive detailed apparent-coordinate/color/size calculations.
- **Calculation details** is a small collapsible tab. While calculating it shows real pipeline stages, processed-item counters and elapsed time. Afterward it exposes time conversions, observer inputs, corrections, photometry/size formulas and measured stage timings. Its percentage measures pipeline completion, not time remaining.
- **Center in view** marks the chosen object with a gold reticle and follows it as time advances; dragging releases tracking.
- **From Earth view:** the mouse wheel zooms the field of view toward the pointer (0.01°–110°; the FOV slider and readout stay in sync). **Center in view** also locks the view onto the object: it stays centered as time advances, shown by a *Tracking* chip. Dragging the sky, the chip or *Stop tracking* releases the lock; the wheel does not. Searching or selecting an object always draws its name (bold, gold) regardless of the name limit.
- **Star name limit** slider (Celestial labels) sets the faintest magnitude that gets a name (default 2.6); overlapping names are still thinned. Book stars keep their names in Sanskrit mode. Constellation lines and the coordinate grid are on by default.
- **Track together** (crosshair button in the left rail): add 1–4 stars or planets by search or from the open object card. Each gets its own colored ring and always-visible name. Modes: **Highlight** (rings and names only), **Center** (keeps the selected tracked object in the middle as time moves; select it by clicking its row, its focus button or the star itself) and **Frame** (leaves the stars where they are and pans the view only as far as needed to keep all of them on screen, inside the top bar and timeline; From Earth view only; *Zoom out to fit all* widens the field of view when they are too spread out). Frame keeps every tracked ring and its full name inside the free screen area (clear of the top bar, timeline, azimuth readout, open side panel and object card), and tracked names step apart instead of overlapping. A tracked object that is below the horizon is not followed: Center and the single Center-in-view lock hold the last view, Frame follows only the objects still above the horizon, and the panel marks the set ones. Dragging the sky releases the lock; *lock again* restores it. Rings show only for objects in view and brighter than the star limit.
- **FPS indicator** distinguishes browser callbacks, actual redraws, and accepted exact sky updates per second. Hover for request/calculation/cache/scene CPU timings. Playback samples every 100 ms, preserves the chosen time rate, keeps one request in flight, and skips intermediate samples when busy. All displayed frames are calculated; there is no display interpolation.
- **Sunlight** (Settings → Light & perception) can be switched off: the Sun stays in place but the sky stops scattering its light, so stars and planets show by day. This is a visual aid; the real daytime sky hides them. The status pill reads "sunlight hidden".
- **Comets** appear only inside individually cached NASA JPL Horizons apparitions; nothing is extrapolated outside those windows. 29 are installed: Halley 240 BCE, 12 BCE, 837, 1066, 1759, 1835, 1910, 1986, 2061; Great Comet 1811; Donati 1858; Great September Comet 1882 (fragment B orbit); Great January Comet 1910; Ikeya–Seki 1965 (fragment A); Bennett 1970; Kohoutek 1973; West 1976 (fragment A); Swift–Tuttle 1992 and 2126; Hyakutake 1996; Hale–Bopp 1997; Tempel–Tuttle 1998; McNaught 2007; Lovejoy 2011; ISON 2013 (disintegrated at perihelion; window ends there); NEOWISE 2020; Pons–Brooks 2024; Tsuchinshan–ATLAS 2024; Encke 2026. Where JPL's M1/k1 miss a recorded peak (or are absent), M1 is shifted so the model peak matches the recorded peak, keeping the light-curve slope (`scripts/calibrate_comet_photometry.py`; every entry cites its source). **Forward scattering** follows Marcus (2007): a compound Henyey–Greenstein dust phase function normalised at 90° phase (g_f 0.9, g_b −0.6, k 0.95, dust-to-gas ratio δ90 = 1 unless a comet has a published value); it is known to underestimate the surge beyond ~173°. Calibration includes it, and only counts moments at least 15° from the Sun except comets recorded in daylight. The timing then comes from geometry: Tsuchinshan–ATLAS peaks on 9 Oct 2024, McNaught on 13 Jan 2007 and the Great January Comet on 18 Jan 1910, as observed, and uncalibrated West 1976 reaches −3.9 (recorded ≈ −3). All Halley apparitions use Marcus's published Halley model (H0, n = 4, 4 before / 3.4, 3.0 after perihelion; δ90 = 2 → 5); it reproduces his 2061 forecast table to 0.01 mag (−2.2 on 29 Jul 2061) and gives 2.65 for 1986, −3.5 for 837 and a daylight forward-scattering surge in May 1910. Search finds a comet by name when its window covers the date (the `/api/comets` endpoint lists every cached apparition and its perihelion). Brightness uses JPL's total-magnitude law m = M1 + 5 log Δ + k1 log r, except Hale–Bopp, whose JPL fit (from distant 2022 data) predicts magnitude ~5 at perihelion; a sourced override (NSSDC H ≈ −1; Kidger et al. 1997 n ≈ 3.5) gives the observed ≈ −0.7 (`data/comets/photometry_overrides.json`). Each comet shows a blue **ion tail** pointing straight away from the Sun and a cream, curved **dust tail** lagging behind its motion, in the sky. Tail directions follow that physics; tail length, width and brightness are an illustrative scaling with solar distance and absolute magnitude, labelled as such on the comet's card. Tails switch on inside about 4 AU and fade in daylight (or show with Sunlight off).
- **Sanskrit names** (Settings → Celestial labels, off by default) relabel stars, the Sun, Moon, planets and comets in Devanagari in the sky, atlas, search and object card; the card shows Devanagari, IAST, any alternative name and the English name. Two sources, each name cited in the data: (1) Oak (2011), *When Did the Mahabharata War Happen? The Mystery of Arundhati* (the source PDF is retained only in the local, Git-ignored `books/` folder): the 28 nakshatra stars, Arundhatī, Vasiṣṭha, Ātreya, Dhruva, Castor, the Pleiades as Kṛttikā, the planets, पृथिवी (Pṛthivī) for the Earth, the spelling of the Mahābhārata verses the book quotes (Śalya CE 55.10, PDF p.274; Pṛthvī/Dharā are accepted in search), and धूमकेतु for comets; (2) classical texts for 12 more stars the book does not name: Sūrya Siddhānta VIII (tr. Burgess 1860) Agastya (Canopus), Mṛgavyādha/Lubdhaka (Sirius), Agni (Elnath), Brahmahṛdaya (Capella), Prajāpati (δ Aur), Apāṃvatsa (θ Vir), Āpas (δ Vir), and Bṛhat Saṃhitā 13.5–6 the Seven Sages Kratu (Dubhe), Pulaha (Merak), Pulastya (Phecda), Atri (Megrez), Aṅgiras (Alioth); Alkaid keeps the book's Ātreya with Marīci as alternative. Most bright stars have no attested Sanskrit name and keep English; none is invented. Search accepts Latin, IAST and Devanagari with common spelling variants.
- **Book stars** (Pleione 5.05, Celaeno 5.45, Asterope 5.76) fall within the common limit; Asterope's brightness varies 5.756–5.761 over the interval, so book stars keep a small exemption that only affects it. A name labels a modern star; it does not show the same star was meant in antiquity.
- Atmosphere, extinction, standard-air refraction, names, constellation guides, grids and body markers can be toggled. Rendering retains the same photographic light model; the Photography label is removed.
- Physical body sizes and distances are the default. **Enlarged body markers** is an explicitly nonphysical visual aid. Stellar brightness halos are normalized optical point spread, separate from measured photospheric disks. **Compare true sizes** shows physical or apparent diameters on one common linear scale, without adding a minimum disk size.
- Use the date dialog for BCE/CE and Gregorian/Julian entry, or scrub the timeline. Date input is **TT**, not ancient UTC. Space pauses/plays; keys 1/2/3 switch views. Fast playback can skip events.

## Coverage and accuracy

The interface is limited to **15,000 BCE–5,000 CE** (astronomical years −14999 to +5000, JD −3,757,212.5 to 3,547,636.5; narrowed on request from 100,000 BCE–20,000 CE and then from 20,000 BCE on 2026-10-22). Dates outside it are rejected by the API, the date dialog and the job controls. Out-of-range v5 trajectory chunks and stellar epochs have been removed; the accepted boundary chunk is clipped to the first supported Julian date. DE441 remains a wider shared input because its in-range ephemeris data is required. To change the range, see [Extending the date range](#extending-the-date-range). This is not a claim that all celestial objects can be reconstructed accurately over that interval.

Installed data includes complete JPL DE440 and DE441 kernels, 119,625 HYG/Hipparcos stars, 709 directly measured JMMC stellar diameter matches, a Galactic-motion pack for bright-star candidates, 16 massive-asteroid initial states/GM constants, and bounded JPL comet apparition packs. The full optional Gaia G≤12 expansion was deferred to prioritize prominent stars; its partial download is retained and can be resumed explicitly.

DE440 is preferred within its coverage; DE441 extends approximately from astronomical year −13200 to +17191, so within the supported interval the planets before about 13,200 BCE (roughly 15,000–13,200 BCE) need the background generator. Giant-planet states use system barycenters. Modern apparent directions include light time, parallax, aberration, solar deflection and IAU precession/nutation. Earth rotation uses bundled IERS observations/predictions where available, historical ΔT modelling in its published interval, and explicitly assumed rotation elsewhere. Ancient local clock times are not known precisely.

Outside ephemeris coverage, planets appear only after the background generator publishes a numerically validated chunk. Until then, the interface shows the missing coverage explicitly. Deep-time stars use a bounded galpy MWPotential2014 pack where adequate motion data exists; other stars retain labelled rectilinear/unknown-radial-velocity assumptions. Constant stellar luminosity, extinction and photospheric size are assumptions, especially for variable and evolved stars.

Colors use measured color indices and a blackbody approximation; calibrated per-star spectra are not bundled. Atmosphere is a numerical single-scattering standard-air Rayleigh/Mie model, not a weather reconstruction. Multiple scattering and ozone absorption are omitted. Planetary photometry, Saturn rings, star variability, ancient geography and comet brightness/tails have explicit approximation limits. These are not event-grade eclipse or ancient-alignment predictions.

Read [scientific methods](docs/SCIENCE.md), [validation](docs/VALIDATION.md) and [data provenance](data/README.md).

## Background reconstruction

Use **Offline data → Generate past / Generate future**. Pause requests finish the current validated checkpoint. Resume retains prior numerical state. The calculation tab also exposes active background progress.

```sh
nohup caffeinate -i .venv/bin/python scripts/reconstruct.py >> tmp/reconstruction.log 2>&1 &   # --year defaults to MIN_YEAR (-14999)
```

Launching clears a saved website pause and resumes from the latest checkpoint. When the past run completes, the 2000 → 5,000 CE run starts automatically unless `--no-future` is given (DE440/DE441 already cover those dates). Progress is in `data/jobs/status.json` or the Offline data panel. Pause by setting `pause_requested` to true in `data/jobs/control.json`.

The standalone worker uses REBOUND IAS15, first-order relativistic corrections, solar/Earth oblateness, simplified Earth–Moon constant-time-lag tides and 16 massive asteroids. Independent tighter integrations, off-node interpolation probes, JPL overlap residuals and local parameter sensitivity are reported separately. Reduced-model physical uncertainty is **not** calibrated by those checks.

Checkpoints: after every validated 10-year v5 chunk the worker writes the chunk data, then its acceptance report, then the resume point, each by an atomic flushed rename (`data/jobs/past-v5-latest.bin`; the appended `data/jobs/past-v5.bin` archive is history). The archive and latest checkpoint now stop within the supported interval; the last in-range resume point is near 14,991 BCE. If the worker is interrupted, rerun the start command to resume from that checkpoint. The completed in-range coverage is 15,000 BCE–5,000 CE; dates earlier than DE441 are reduced-model extrapolations with the physical limitations listed in [SCIENCE.md](docs/SCIENCE.md). Multirate compressed chunks and a disk-budget guard prevent silent storage overrun; files are never automatically evicted.

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

## Development and verification

```sh
.venv/bin/python -m pytest -q
npm run build --prefix frontend
```

The saved Horizons cases support offline validation. To explicitly refresh reference data online, use `scripts/fetch_references.py`. Optional full Gaia intake: `.venv/bin/python scripts/setup_data.py --gaia`. Rebuild the stellar pack after changing catalogs.

Cross-check against NASA data: `.venv/bin/python scripts/crosscheck_nasa.py analyze` (offline) regenerates [docs/NASA_CROSSCHECK.md](docs/NASA_CROSSCHECK.md) from saved JPL Horizons and NASA eclipse-site responses; `fetch` refreshes them online. It found a deep-time sidereal-angle sign defect (fixed 2026-10-21; ancient-date altitude/azimuth were wrong by tens of degrees) and quantifies the reconstruction's lunar drift from DE441.

Folder guides: [backend](backend/README.md), [frontend](frontend/README.md), [scripts](scripts/README.md), [tests](tests/README.md), [data](data/README.md), [documentation](docs/README.md). The root `books/` folder is local-only and Git-ignored; its source PDFs are not included in this repository or the Pages site. They were used only as a naming source for Sanskrit star names, not to infer astronomical or historical claims.

### Loading and rendering
The UI now has only the From Earth view. The Moon icon in the left rail opens a collapsible **Moon phase** panel with a schematic disk, phase name, illumination percentage, waxing/waning state, horizon status and TT date for the accepted sky frame. Click the icon again or the close button to collapse it. Missing planetary coverage is shown explicitly.

Ground-view requests include horizon directions and, when the ground is enabled, only stars within 2° below or above the visible hemisphere boundary. Per-star source/epoch/diameter provenance is fetched on the object card; frame-level metadata remains in `star_fields`. Fixed stellar names, colors and radii are cached by source revision; positions, brightness and apparent sizes are calculated for each exact time. Active reconstruction dependencies are indexed by stamped reports, including the short retarded-time interval used for apparent positions. Existing frames and the 512 MB/10 GB guards are preserved.

The scene reuses star buffers, materials, grids and body meshes. Label-only changes do not rebuild geometry; disabled atmosphere/sunlight bypasses unnecessary scattering quadrature without changing its result. See [performance measurements](docs/PERFORMANCE.md). The backend space-data API is retained for compatibility and scientific checks; the UI exposes no space camera.

### Pruning the frame cache
`scripts/prune_frame_cache.py` (dry run by default; `--apply --vacuum` to act) deletes only frames that can never be reused: those created before the newest change to any model file, since that change is part of every frame's cache key. On 2026-10-21 it removed 4,043 such frames and shrank the cache from 472 MB to 5.3 MB, keeping the 162 current frames.

### Stored playback
Completed sky frames are saved locally in `data/playback/frames.sqlite3` and reused when returning to the same date and observer/calculation settings, even after restarting. The calculation tab says **Stored frame** on a hit. Playback uses reversible fixed steps so reversing at the same speed revisits the same frames. New times or locations still need apparent-sky projections, using installed trajectory packs rather than rerunning integration. Scientific model/data changes invalidate affected cached frames. Cache storage stops safely at its 512 MB payload allowance or the 10 GB workspace guard; existing data is preserved.

The calculation drawer includes **How much is stored**: frame count, distinct saved dates, earliest/latest times, compressed storage and validated background trajectory duration. Saved frames are discrete samples; their earliest/latest bounds do not imply gap-free playback coverage.

Default observing location: **Kolkata, India** (22.5726° N, 88.3639° E), per user preference.

### Prominent stars only
The simulator enforces one common apparent-magnitude limit (4.5 until 2026-10-22, now 5.76; `STAR_LIMIT` in backend/catalog.py) for stellar calculations and display, including saved-frame reuse, Galactic trajectory evaluation, search and object selection. Faint-star controls are removed. Old catalog/trajectory/cache files remain preserved, but faint entries are excluded from the active simulation. This supersedes the earlier optional faint-star mode. Planet and comet handling is unchanged.

Installed ephemeris coverage means stored orbital trajectories can be evaluated; each new time/location still needs Earth orientation, light-time/apparent directions, stellar brightness and a sky projection. The calculation drawer labels this “Preparing sky from stored trajectories.” Identical saved sky frames are loaded directly. DE441 body segments are selected by requested date, including its ancient segment. Obsolete queued playback requests are skipped when a newer frame for that browser arrives.

The Moon has a soft, phase/distance-dependent glow in the sky and Moon phase tab, based on the existing lunar magnitude model. It dims in daylight and near the horizon, while the sky glow disappears below the horizon. Its angular disk and phase remain calculated; glow width/tone mapping are illustrative. See [Moon lighting references](docs/MOON_LIGHTING.md).
