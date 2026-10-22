# Cross-check against NASA data

Generated 2026-10-22T05:36:07+0530 by `scripts/crosscheck_nasa.py analyze` (offline) from NASA responses saved by `... fetch` in `data/references/crosscheck/`. Machine-readable results: `nasa-crosscheck.json`. Runtime still needs no internet.

## Summary

1. **Sun, Moon and planets, geocentric (A):** with the same NASA kernels the simulator matches Horizons to 0.003 arcsec over 9,000 BCE – 5,000 CE (the printed precision of Horizons is ≈0.003 arcsec). Where the app prefers DE440 (1550–2650) it differs from Horizons' DE441 by up to 0.24 arcsec (Moon); that is DE440 vs DE441, not a calculation error.
2. **Apparent sky outside 1500–2500 CE (B): fixed and improved.** The deep-time sidereal angle had the wrong sign (up to 25.7° from IAU 2006/2000A GAST). With the sign fixed it was still off by up to 138″ within ±1000 years, from treating the equinox offset as the equation of origins. It now uses Vondrák precession, IAU 2000A nutation (within ±4,000 years) and the equation of origins with a CIO locator integrated from the Vondrák pole, and matches GAST to 0.45″ within ±1000 years. Against Horizons the altitude/azimuth error at 1 BCE went from 48° to 0.4°; what remains is the ΔT difference between the two ΔT scenarios.
3. **ΔT (C):** the simulator's polynomial lies within NASA's published standard error at every Morrison–Stephenson table year; modern ΔT agrees with the Astronomical Almanac values to 0.1 s.
4. **Solar eclipses (D):** greatest-eclipse times agree with NASA's Five Millennium Canon to a median 0.3 s for 1800–2100 and grow with antiquity (see table).
5. **Reconstruction (E): rebuilt on NASA data.** The old run started at J2000 and integrated back through 15,000 years that DE441 already covers, and its Moon drifted 27.8″/cy² from DE441 (the reduced model had no Earth tide raised by the Moon). The new run starts from DE441 itself at 13,201 BCE and integrates only what DE441 does not cover; a lunar correction calibrated on a 6,800-year DE441 hold-out (implied tidal acceleration -27.37″/cy²) brings the hold-out Moon from 8.8° rms to 360″ rms.
6. **Comets (F):** cached splines match fresh Horizons vectors to a median 0.00 km and at worst 26 km (0.032″) including perihelion; the three sungrazers now carry 5-minute JPL samples around perihelion (they were off by up to 28,000 km).
7. **Planet magnitudes (G):** now Mallama & Hilton (2018), the models Horizons uses: Mercury, Venus, Jupiter, Uranus, Neptune within 0.001 mag of Horizons APmag, Saturn (with rings) within 0.03 except one deliberate unlit-ring date, Mars 0.11; the previous formulas were off by up to 0.98 mag.

## A. Ephemeris and light time vs JPL Horizons (geocentric, astrometric, ICRS)

Horizons sources: DE441, jup365_merged, mar099, nep098_merged, plu060_merged, sat441l, ura184_merged. Direction error (arcsec) and distance for every body at 23 epochs, 9,000 BCE – 5,000 CE (12:00 TT on 1 January, astronomical year numbers). Frame ICRS, time TT. Horizons' date range ends at 9,999 BCE and has no ephemeris before the DE441 start (13,200 BCE) anyway, so older epochs cannot be checked against NASA. The simulator reads the same NASA DE kernels: this tests the kernel reader, TT/TDB handling and light time.

| Year | kernel used by app | max direction error (arcsec) | worst body | same, DE441 forced |
|---:|:--|---:|:--|---:|
| -9000 | DE441 | 0.0031 | Moon | 0.0031 |
| -8000 | DE441 | 0.0031 | Jupiter | 0.0031 |
| -6000 | DE441 | 0.0031 | Venus | 0.0031 |
| -4000 | DE441 | 0.0031 | Sun | 0.0031 |
| -3000 | DE441 | 0.0031 | Uranus | 0.0031 |
| -2000 | DE441 | 0.0000 | Sun | 0.0000 |
| -1000 | DE441 | 0.0000 | Sun | 0.0000 |
| -500 | DE441 | 0.0000 | Sun | 0.0000 |
| 0 | DE441 | 0.0000 | Sun | 0.0000 |
| 500 | DE441 | 0.0031 | Moon | 0.0031 |
| 1000 | DE441 | 0.0000 | Sun | 0.0000 |
| 1500 | DE441 | 0.0031 | Jupiter | 0.0031 |
| 1600 | DE440 | 0.2367 | Moon | 0.0000 |
| 1800 | DE440 | 0.0208 | Moon | 0.0031 |
| 1900 | DE440 | 0.0000 | Sun | 0.0000 |
| 2000 | DE440 | 0.0000 | Sun | 0.0031 |
| 2026 | DE440 | 0.0000 | Sun | 0.0000 |
| 2100 | DE440 | 0.0053 | Moon | 0.0031 |
| 2200 | DE440 | 0.0115 | Moon | 0.0000 |
| 2500 | DE440 | 0.0486 | Moon | 0.0000 |
| 3000 | DE441 | 0.0000 | Sun | 0.0000 |
| 4000 | DE441 | 0.0031 | Moon | 0.0031 |
| 5000 | DE441 | 0.0000 | Sun | 0.0000 |

Distances agree to 0.0 km at worst (median 0.002 km).

**Barycenter vs body centre (documented limitation).** The app targets planetary-system barycenters (DE targets 4–9). Against the true planet centres (Horizons, 1801–2100 only, where satellite ephemerides exist):

| Planet | median (arcsec) | max (arcsec) |
|:--|---:|---:|
| Mars | 0.000 | 0.000 |
| Jupiter | 0.018 | 0.053 |
| Saturn | 0.020 | 0.047 |
| Uranus | 0.289 | 0.777 |
| Neptune | 0.047 | 0.100 |
| Pluto | 0.070 | 0.077 |

## B. Apparent topocentric sky vs Horizons (New Delhi 28.6139°N 77.2090°E, sea level, airless, 9 bodies)

Full pipeline: light time, aberration, solar deflection, WGS84 parallax, frames, Earth rotation (ΔT). Residual = angular distance between the simulator's and Horizons' altitude/azimuth. Within |year − 2000| ≤ 500 the app uses IAU 2006/2000A; outside it uses Vondrák (2011) long-term precession (no nutation) with an extrapolated spin phase.

**Deep-time sidereal angle vs ERFA GAST (IAU 2006/2000A, valid near these dates; no network).** History of `backend/astrotime.py` on 2026-10-21: wrong sign; sign fixed; then equation of origins + nutation:

| Year | original − GAST | sign fixed only − GAST | current app − GAST |
|---:|---:|---:|---:|
| 1000 | +25.587° | -138.4″ | +0.26″ |
| 1300 | +17.910° | -54.6″ | +0.24″ |
| 1499 | +12.827° | -2.9″ | -0.07″ |
| 2501 | -12.860° | +24.7″ | +0.23″ |
| 2700 | -17.992° | +33.1″ | +0.09″ |
| 3000 | -25.743° | +132.4″ | +0.45″ |

The "pre-fix" column below restores the original sign in the original formula; it is historical, not the current app.

| Year | frame | median alt/az error (current app) | pre-fix | rotation offset still needed (s of time) | residual after removing that rotation, max | sky RA/Dec median |
|---:|:--|---:|---:|---:|---:|---:|
| -9000 | Vondrak 2011 | 24.29° | 88.22° | -6173 | 440.1″ | 173.5″ |
| -8000 | Vondrak 2011 | 19.37° | 103.68° | -4996 | 665.8″ | 161.7″ |
| -6000 | Vondrak 2011 | 11.88° | 133.88° | -3043 | 448.0″ | 63.0″ |
| -4000 | Vondrak 2011 | 6.05° | 125.14° | -1581 | 144.3″ | 40.2″ |
| -3000 | Vondrak 2011 | 3.92° | 109.91° | -1025 | 188.3″ | 17.0″ |
| -2000 | Vondrak 2011 | 2.28° | 93.27° | -582 | 102.9″ | 2.5″ |
| -1000 | Vondrak 2011 | 3589.7″ | 71.80° | -251 | 43.0″ | 2.0″ |
| -500 | Vondrak 2011 | 2773.8″ | 57.69° | -201 | 23.9″ | 2.8″ |
| 0 | Vondrak 2011 | 1462.3″ | 48.35° | -102 | 11.2″ | 3.0″ |
| 500 | Vondrak 2011 | 1449.6″ | 36.28° | -101 | 9.6″ | 2.9″ |
| 1000 | Vondrak 2011 | 1191.3″ | 23.84° | +86 | 14.7″ | 2.3″ |
| 1500 | IAU 2006/2000A | 1399.2″ | — | +96 | 17.9″ | 1.3″ |
| 1600 | IAU 2006/2000A | 135.9″ | — | -9 | 1.2″ | 1.1″ |
| 1800 | IAU 2006/2000A | 70.0″ | — | +5 | 1.0″ | 0.5″ |
| 1900 | IAU 2006/2000A | 10.9″ | — | +1 | 0.3″ | 0.2″ |
| 2000 | IAU 2006/2000A | 0.3″ | — | -0 | 0.4″ | 0.1″ |
| 2026 | IAU 2006/2000A | 0.3″ | — | -0 | 0.3″ | 0.0″ |
| 2100 | IAU 2006/2000A | 1968.1″ | — | -133 | 25.9″ | 0.2″ |
| 2200 | IAU 2006/2000A | 1.48° | — | -373 | 30.2″ | 0.5″ |
| 2500 | IAU 2006/2000A | 5.49° | — | -1391 | 122.1″ | 1.5″ |
| 3000 | Vondrak 2011 | 17.31° | 41.65° | -4373 | 718.4″ | 3.4″ |
| 4000 | Vondrak 2011 | 57.94° | 102.28° | -15123 | 1329.8″ | 7.5″ |
| 5000 | Vondrak 2011 | 122.73° | 131.14° | -32252 | 2455.8″ | 11.3″ |

The rotation offset is the single rotation about Earth's axis that best aligns the simulator with Horizons: it is the Earth-rotation disagreement (ΔT choice), expressed as time. Inferred ΔT used by Horizons (= simulator ΔT − fitted offset), against NASA's own table (section C):

| Year | simulator ΔT (s) | inferred Horizons ΔT (s) | NASA Table 1 (s) |
|---:|---:|---:|---:|
| -9000 | 374609 | 368438 | — |
| -8000 | 308561 | 303568 | — |
| -6000 | 195666 | 192624 | — |
| -4000 | 108370 | 106789 | — |
| -3000 | 74322 | 73298 | — |
| -2000 | 46675 | 46093 | — |
| -1000 | 25427 | 25176 | — |
| -500 | 17203 | 17002 | 17190 ± 430 |
| 0 | 10583 | 10481 | 10580 ± 260 |
| 500 | 5710 | 5609 | 5710 ± 140 |
| 1000 | 1574 | 1660 | 1570 ± 55 |
| 1500 | 198 | 294 | 200 ± 20 |
| 1600 | 120 | 110 | 120 ± 20 |
| 1800 | 14 | 19 | 14 ± 1 |
| 1900 | -3 | -2 | — |
| 2000 | 64 | 64 | — |
| 2026 | 69 | 69 | — |
| 2100 | 203 | 70 | — |
| 2200 | 442 | 70 | — |
| 2500 | 1460 | 69 | — |
| 3000 | 4436 | 65 | — |
| 4000 | 15188 | 72 | — |
| 5000 | 32341 | 103 | — |

Reading this: after 2026 Horizons appears to hold ΔT near 70 s (no extrapolation), while the simulator extrapolates a parabola, so future alt/az differ by design; far past, both are extrapolations and differ by thousands of seconds, i.e. tens of degrees of sky rotation. Residuals beyond ±1000 years likely also include the Vondrák-vs-IAU 1976 precession difference and the missing nutation (not separated here).

## C. ΔT vs NASA

NASA Table 1 (Morrison & Stephenson 2004, with NASA standard errors) vs `delta_t()` in `backend/astrotime.py` (Espenak & Meeus polynomials):

| Year | NASA ΔT (s) | ± (s) | simulator (s) | difference (s) | within NASA error? |
|---:|---:|---:|---:|---:|:--|
| -500 | 17190 | 430 | 17203.7 | +13.7 | yes |
| -400 | 15530 | 390 | 15530.9 | +0.9 | yes |
| -300 | 14080 | 360 | 14078.2 | -1.8 | yes |
| -200 | 12790 | 330 | 12792.2 | +2.2 | yes |
| -100 | 11640 | 290 | 11637.6 | -2.4 | yes |
| 0 | 10580 | 260 | 10583.6 | +3.6 | yes |
| 100 | 9600 | 240 | 9596.9 | -3.1 | yes |
| 200 | 8640 | 210 | 8640.7 | +0.7 | yes |
| 300 | 7680 | 180 | 7681.1 | +1.1 | yes |
| 400 | 6700 | 160 | 6699.2 | -0.8 | yes |
| 500 | 5710 | 140 | 5710.0 | +0.0 | yes |
| 600 | 4740 | 120 | 4739.2 | -0.8 | yes |
| 700 | 3810 | 100 | 3813.2 | +3.2 | yes |
| 800 | 2960 | 80 | 2955.7 | -4.3 | yes |
| 900 | 2200 | 70 | 2200.3 | +0.3 | yes |
| 1000 | 1570 | 55 | 1574.2 | +4.2 | yes |
| 1100 | 1090 | 40 | 1088.9 | -1.1 | yes |
| 1200 | 740 | 30 | 736.4 | -3.6 | yes |
| 1300 | 490 | 20 | 491.9 | +1.9 | yes |
| 1400 | 320 | 20 | 321.8 | +1.8 | yes |
| 1500 | 200 | 20 | 198.3 | -1.7 | yes |
| 1600 | 120 | 20 | 120.0 | +0.0 | yes |
| 1700 | 9 | 5 | 8.8 | -0.2 | yes |
| 1750 | 13 | 2 | 13.4 | +0.4 | yes |
| 1800 | 14 | 1 | 13.7 | -0.3 | yes |
| 1850 | 7 |  | 7.1 | +0.1 |  |
| 1900 | -3 |  | -2.8 | +0.2 |  |
| 1950 | 29 |  | 29.1 | +0.1 |  |

Modern values (Astronomical Almanac, NASA Table 2) vs the simulator, which uses its bundled IERS table from 1973:

| Year | NASA (s) | simulator (s) | difference (s) |
|---:|---:|---:|---:|
| 1955 | 31.1 | 31.06 | -0.04 |
| 1960 | 33.2 | 33.12 | -0.08 |
| 1965 | 35.7 | 35.82 | +0.12 |
| 1970 | 40.2 | 40.23 | +0.03 |
| 1975 | 45.5 | 45.48 | -0.02 |
| 1980 | 50.5 | 50.54 | +0.04 |
| 1985 | 54.3 | 54.34 | +0.04 |
| 1990 | 56.9 | 56.86 | -0.04 |
| 1995 | 60.8 | 60.79 | -0.01 |
| 2000 | 63.8 | 63.83 | +0.03 |
| 2005 | 64.7 | 64.69 | -0.01 |

ΔT column of NASA's Five Millennium Canon (3452 eclipses, −1999 to +3000) vs the simulator, by period:

| Period | n | median |diff| (s) | max |diff| (s) |
|:--|---:|---:|---:|
| -2000…-500 | 615 | 148.8 | 202.4 |
| -500…500 | 736 | 51.9 | 78.8 |
| 500…1600 | 714 | 10.6 | 27.9 |
| 1600…2000 | 463 | 0.3 | 2.0 |
| 2000…3001 | 924 | 3.7 | 14.6 |

Differences of a few minutes before −500 are not larger than NASA's own standard error there (430 s or more); the likely reason is a different ΔT revision, which was not verified.

## D. Greatest solar eclipse vs NASA Five Millennium Canon

312 central eclipses (every 7th eclipse of 15 sampled centuries, −1999 to +3000). For each, the simulator's light-time-corrected geocentric Sun and Moon give the instant the Sun–Moon axis passes closest to Earth's centre and that distance γ (Earth radii); NASA lists the same in TD ≈ TT. No ΔT is involved. NASA computed with ELP-2000/82 and VSOP87 and its own lunar tidal acceleration, whereas the simulator uses JPL DE440/DE441, so differences before about 1600 likely reflect the two lunar theories and their tidal terms (not verified separately).

| Year range | n | median |Δt| (s) | max |Δt| (s) | median |Δγ| | max |Δγ| |
|:--|---:|---:|---:|---:|---:|
| -2000…-1000 | 39 | 290.6 | 342.5 | 0.0017 | 0.0020 |
| -1000…0 | 60 | 61.2 | 135.2 | 0.0003 | 0.0008 |
| 0…1000 | 45 | 9.2 | 32.8 | 0.0000 | 0.0002 |
| 1000…1800 | 46 | 0.6 | 1.9 | 0.0001 | 0.0001 |
| 1800…2100 | 56 | 0.3 | 0.7 | 0.0000 | 0.0001 |
| 2100…3000 | 65 | 3.3 | 13.3 | 0.0001 | 0.0001 |

## E. Background reconstruction vs JPL DE441

### E1. Retired v3 run (baseline)

The v3 worker started from DE440 at J2000 and integrated backward through the DE441 era. Its chunks are kept but never served (DE441 is used there). Largest position difference (km) over each chunk, from the chunk reports:

| Epoch (year) | Moon (geocentric) | Sun | Mercury | Venus | Mars | Jupiter | Saturn | Neptune | Pluto |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| -3636 | 87,057 | 3,230 | 7,171 | 5,219 | 7,946 | 5,396 | 3,255 | 28,293 | 55,620 |
| -3116 | 72,042 | 2,910 | 6,091 | 4,501 | 6,863 | 4,715 | 2,990 | 26,249 | 85,881 |
| -2596 | 58,337 | 2,611 | 5,118 | 3,856 | 5,917 | 4,205 | 2,614 | 27,660 | 105,794 |
| -2076 | 46,160 | 2,303 | 4,214 | 3,244 | 5,195 | 3,623 | 2,322 | 27,932 | 106,276 |
| -1556 | 35,366 | 2,007 | 3,412 | 2,687 | 4,562 | 3,106 | 2,014 | 26,197 | 83,918 |
| -1036 | 26,041 | 1,742 | 2,723 | 2,212 | 3,845 | 2,614 | 1,723 | 24,200 | 57,621 |
| -516 | 18,114 | 1,493 | 2,146 | 1,808 | 3,086 | 2,171 | 1,487 | 26,117 | 34,136 |
| 4 | 11,650 | 1,234 | 1,628 | 1,424 | 2,200 | 1,759 | 1,243 | 21,155 | 31,207 |
| 524 | 6,606 | 942 | 1,146 | 1,040 | 1,353 | 1,294 | 930 | 11,932 | 28,474 |
| 1044 | 2,970 | 624 | 704 | 663 | 767 | 862 | 656 | 5,617 | 14,643 |
| 1564 | 765 | 301 | 316 | 308 | 351 | 396 | 308 | 2,623 | 4,066 |
| 2000 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

Independent check: stored chunk coefficients re-evaluated against the DE441 kernel at 80 random times, as seen from Earth (arcsec). The Moon column is signed along the orbit (+ = reconstruction ahead):

| Year | Moon (arcsec, signed) | Sun | Mercury | Venus | Mars | Jupiter | Saturn |
|---:|---:|---:|---:|---:|---:|---:|---:|
| -3600 | +48,875 | 2 | 2 | 4 | 4 | 1 | 0 |
| -3168 | +34,022 | 4 | 6 | 4 | 4 | 0 | 0 |
| -2596 | +30,269 | 2 | 1 | 3 | 3 | 0 | 0 |
| -2289 | +25,744 | 2 | 4 | 3 | 4 | 0 | 0 |
| -1633 | +16,415 | 1 | 2 | 2 | 2 | 1 | 0 |
| -963 | +13,464 | 1 | 1 | 1 | 2 | 0 | 0 |
| -483 | +7,966 | 0 | 0 | 0 | 2 | 0 | 0 |
| -22 | +6,160 | 1 | 1 | 1 | 1 | 0 | 0 |
| 470 | +3,733 | 0 | 0 | 0 | 0 | 0 | 0 |
| 1090 | +1,317 | 0 | 0 | 0 | 0 | 0 | 0 |
| 1676 | +237 | 0 | 0 | 0 | 0 | 0 | 0 |
| 2000 | +0 | 0 | 0 | 0 | 0 | 0 | 0 |

The v3 lunar offset follows a·t² with a = 13.9″/cy², a mean-motion acceleration difference of 27.8″/cy² (reconstruction ahead in 100% of samples). That equals DE441's lunar tidal acceleration: a direct test showed the REBOUNDx constant-time-lag tide moved the Moon by 0.00″ in 100 years (≈12.9″ expected), because it couples bodies only to particle 0, the Sun.

### E2. Current model (v5): DE441 seed, local integrator clock, calibrated lunar correction

The past run now starts from NASA's DE441 states at its first epoch (JD −3,100,014.5, 13,201 BCE) and integrates only 13,201 → 20,000 BCE (6,800 years; the supported range was narrowed to 15,000 BCE on 2026-10-22, so 1,800 years are used) instead of 22,000 years from J2000. The 16 asteroids, which JPL does not publish that early, come from a reduced integration (scripts/deep_seed.py asteroids).
The missing lunar tide is restored by shifting the Moon's osculating geocentric mean anomaly by −(c1·τ + c2·τ² + c3·τ³), τ in centuries from the seed, with c1 = -205.927″/cy (measured forward from the seed against DE441 over 5 centuries; on the hold-out a forward fit gave −83.13 vs −83.42″/cy backward), c2 = 13.6848″/cy², c3 = -0.00347″/cy³ (implied tidal acceleration -27.37″/cy²; DE430/DE441 use about −25.8). A mean-anomaly shift, unlike a rigid rotation, also moves the Moon correctly along its eccentric orbit.

| Test | n | uncorrected rms | corrected rms | corrected max |
|:--|---:|---:|---:|---:|
| Hold-out (hold-out c1 = -83.42″/cy): seeded from DE441 at 6000 BCE, 6,800 years back, vs DE441 (fit data) | 5495 | 31,825″ | 360.3″ | 1,433.6″ |
| Independent: retired v3 run from J2000, 5,600 years, vs DE441, using the hold-out c1 (not measured at its own seed; shows why the run measures c1 at its seed) | 144 | 19,364″ | 2,798.3″ | 5,795.2″ |

Planets in the hold-out, as seen from Earth, worst case over 6,800 years (no correction applied to planets):

| Body | max error (arcsec) |
|:--|---:|
| Sun | 19.8 |
| Mercury | 39.6 |
| Venus | 23.7 |
| Mars | 17.2 |
| Jupiter | 4.2 |
| Saturn | 2.3 |
| Uranus | 1.8 |
| Neptune | 4.3 |

**Limitation:** Empirical: reproduces DE441 lunar mean motion over the 6,800-year hold-out. Before 13,200 BCE it assumes DE441-era tidal dissipation persists; real ancient dissipation is uncalibrated. Before 13,201 BCE nothing can be checked against NASA; these numbers measure how well the reduced model reproduces DE441 over an equally long interval, not ancient truth.

Current-model chunks published so far: 4, back to 13240 BCE; worst off-node interpolation 0.124 km, worst tighter-integration convergence 0.004 km (numerical gates only).

## F. Comets vs Horizons

Cached cubic splines vs fresh Horizons vectors at 145 off-node epochs over 29 apparitions (barycentric ICRS).

Position error: median 0.00 km, 95th percentile 0.3 km. As seen from Earth: median 0.0000″, 95th percentile 0.000″, max 0.0″.

Worst five (all at the perihelion epoch, +0.05 d; the leading three are sungrazers sampled hourly, where a cubic spline under-resolves the pass):

| Comet | days from perihelion | error (km) | error (arcsec) |
|:--|---:|---:|---:|
| Kohoutek 1973 | +0.05 | 26.3 | 0.032 |
| ISON 2013 | +0.05 | 2.3 | 0.003 |
| McNaught 2007 | +0.05 | 1.5 | 0.002 |
| Ikeya–Seki 1965 | +0.03 | 1.7 | 0.002 |
| Great September Comet 1882 | +0.03 | 1.7 | 0.002 |

Total magnitude, app vs Horizons T-mag at 120 epochs. The app deliberately adds Marcus forward scattering and, for some comets, sourced M1 overrides, so those parts are separated:

| Subset | n | median (app − Horizons) | max abs |
|:--|---:|---:|---:|
| JPL M1/k1, no override, as shown in the app | 55 | +0.03 | 2.84 |
| same, forward-scattering term removed | 55 | -0.00 | 0.39 |
| with a sourced override | 65 | -2.00 | 7.55 |

Comets with a sourced override: the app deliberately departs from Horizons' T-mag to match recorded peak brightness (negative = app brighter). At the brightest sampled epoch:

| Comet | brightest sampled epoch | app (mag) | Horizons (mag) | recorded peak used for calibration |
|:--|:--|---:|---:|---:|
| Hale–Bopp 1997 | 1 Apr 1997 CE | -0.5 | +5.3 | — |
| Halley 1066 | 29 Mar 1066 CE | +2.4 | +4.0 | — |
| Halley 12 BCE | 7 Oct 12 BCE | +2.4 | +4.0 | — |
| Halley 1759 | 13 Mar 1759 CE | +2.7 | +4.4 | — |
| Halley 1835 | 16 Nov 1835 CE | +2.6 | +4.2 | — |
| Halley 1910 | 20 Apr 1910 CE | +2.5 | +4.1 | — |
| Halley 1986 | 9 Feb 1986 CE | +2.4 | +4.6 | — |
| Halley 2061 | 28 Jul 2061 CE | -2.1 | +2.0 | — |
| Halley 240 BCE | 21 May 240 BCE | +0.2 | +2.7 | — |
| Halley 837 | 27 Mar 837 CE | +1.7 | +3.7 | — |
| McNaught 2007 | 12 Jan 2007 CE | -4.9 | -11.0 | -5.5 |
| NEOWISE 2020 | 3 Jul 2020 CE | +0.8 | +5.9 | +0.8 |
| Tsuchinshan–ATLAS 2024 | 27 Sep 2024 CE | +2.0 | +6.4 | -4.9 |

Only five epochs per comet are sampled, so the brightest sampled epoch is not the true peak. The recorded peaks are from non-NASA sources cited in `data/comets/photometry_overrides.json`.

## G. Planet magnitudes vs Horizons APmag (2016–2036, every 30 days, geocentric)

Horizons computes planetary APmag with the Mallama & Hilton (2018) models; the app now implements the same models (`backend/ephemeris.py`). Values below use Horizons' own r, Δ and phase angle, so only the photometric law and the ring/pole geometry are compared. The previous app formulas (Saturn rings ignored) are listed from the measurement made before the change.

| Planet | n | median app − Horizons (mag) | max abs (mag) | previous formulas, max abs |
|:--|---:|---:|---:|---:|
| Moon | 244 | -0.009 | 0.050 | unchanged law |
| Mercury | 244 | +0.000 | 0.001 | 0.939 |
| Venus | 244 | +0.000 | 0.001 | 0.246 |
| Mars | 244 | -0.004 | 0.107 | 0.146 |
| Jupiter | 244 | +0.000 | 0.001 | 0.028 |
| Saturn | 244 | +0.000 | 0.104 | 0.984 |
| Uranus | 244 | -0.000 | 0.000 | 0.052 |
| Neptune | 244 | +0.000 | 0.000 | 0.132 |

Mars omits Mallama & Hilton's rotational and orbital-longitude terms (±0.1 mag). Saturn's single larger difference (April 2025) is deliberate: when the Sun and Earth are on opposite sides of the ring plane we see the unlit face, so the app uses the globe-only law while Horizons keeps the ring formula. The Moon keeps its earlier law, which already matches Horizons; Pluto keeps H = −1.0.

## What this does not show

- Stars: NASA/JPL publishes no star ephemeris, so Hipparcos/HYG positions, proper motion and Galactic orbits are not cross-checked here.
- Before 13,200 BCE (DE441 start) there is no NASA ephemeris; Horizons itself stops at 9,999 BCE. Section E is the only measurement of the reconstruction, and it is a measurement of divergence from DE441, not of accuracy against the real past.
- Agreement of Sun/Moon/planets with Horizons (A, D) is agreement with the same JPL fits, not independent historical truth; ancient ΔT is uncertain in NASA's own data (standard errors in C).
- Only 9 bodies at one site were used for B. Comet positions were checked at 5 epochs per apparition.
- Planet bodies vs system barycenters (A) and stellar positions remain as before; JPL satellite ephemerides that would give planet centres cover only about 1600–2200.
