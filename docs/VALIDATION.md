# Validation and remaining coverage

The automated suite checks independent astronomy results, API behavior, offline use and genuine in-flight progress. Run `.venv/bin/python -m pytest -q` from the workspace.

## Independent numerical checks

27 saved JPL Horizons cases cover Sun, Moon, Mercury, Venus, Mars, Jupiter, Saturn, Uranus and Neptune at Greenwich in 1900, 2000 and 2026. Matching TT, airless apparent topocentric conventions are used. The acceptance limit is 1 arcsecond for planets/Sun and 2 arcseconds for the Moon. IAU76/80 vs IAU06/00A frame differences remain in the measured residuals. `modern-validation.json` contains the actual results; this is not a blanket error guarantee outside these cases.

Other tests cover BCE/CE and calendar conversion, orthonormal coordinate bases, polar day/night, inverse-square brightness, prominent-star colors/distances, measured stellar sizes, true angular size versus distance, missing extreme-date coverage, bounded comets, actual-night search, no runtime network, and independent IAS15 convergence/JPL agreement over a short interval.

A progress concurrency test pauses real preparation at 250 of 500 stars, verifies 70% pipeline completion and the processed counts while the request is still active, then verifies completion. Bright-only tests verify sorted apparent-magnitude order, skipped detailed faint-star work and the 128-star first preview.

## Reconstruction verification

A one-year initial reconstruction benchmark published 11 validated chunks and retained a resumable checkpoint. Long-range chunks independently check off-node interpolation and tighter integration, record JPL overlap residuals, and report local tidal-lag sensitivity. Chunks failing gates are not served. Full 100,000 BCE–20,000 CE planetary coverage remains dependent on completing the long background integration. Its progress and ETA are measured from local throughput, not promised in advance.

## Visual checks

The local in-app browser has been used to inspect the responsive ground interface, actual star field, daylight rendering, name labels, bright-star discovery and calculation drawer. Browser interaction checks are recorded in LOG.md. Build success does not substitute for visual checks or astronomy reference tests.

## Known limits

This is a reduced scientific visualization, not a fully calibrated historical reconstruction. Photometric colors, atmosphere, standard refraction, giant-planet barycenters, rings, approximate rise/set, stellar variability, incomplete motion data and unknown comet apparitions retain explicit limitations. Faint Gaia expansion is optional/deferred; Hipparcos/HYG is the default prominent-star atlas. No claim is made that the entire requested planetary interval has already been computed.


## NASA cross-check (2026-10-21)

[NASA_CROSSCHECK.md](NASA_CROSSCHECK.md) extends the modern Horizons cases to 9,000 BCE–5,000 CE and adds NASA's ΔT table, the Five Millennium Canon of Solar Eclipses, the reconstruction-vs-DE441 divergence and comet checks. Summary: geocentric Sun/Moon/planet directions match Horizons to 0.003 arcsec with DE441 (DE440 differs from DE441 by up to 0.24 arcsec); ΔT is within NASA's standard errors; modern eclipse times match to under 1 s. It also found a sign defect in the deep-time sidereal angle (alt/az were wrong by tens of degrees outside about 1500–2500 CE; fixed, with a regression test in tests/test_nasa_crosscheck.py) and shows the reconstructed Moon drifting from DE441 by about 13° at 3400 BCE. Stars cannot be checked against NASA data.

## Model improvements checked against NASA data (2026-10-22)

Deep-time Earth orientation now matches IAU 2006/2000A GAST to 0.45″ within ±1000 years (was 25.7° before the sign fix, 138″ after it); Horizons alt/az residuals at 1 BCE dropped from 48° to 0.4°, the remainder being the ΔT scenario. Planet magnitudes follow Mallama & Hilton (2018) and match Horizons APmag to ≤0.001 mag for five planets. Sungrazer comet splines match Horizons to 2 km at perihelion (was 28,000 km). The past reconstruction is seeded from DE441 and its lunar correction is validated on a 6,800-year DE441 hold-out (360″ rms). Details: [NASA_CROSSCHECK.md](NASA_CROSSCHECK.md). Tests: tests/test_nasa_crosscheck.py, tests/test_science.py.

