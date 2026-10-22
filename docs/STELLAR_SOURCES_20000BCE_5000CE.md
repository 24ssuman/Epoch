# Sources for stellar positions: 20,000 BCE–5,000 CE

Research date: 2026-10-21. This is a literature/source comparison, not a numerical validation or runtime change.

## Conclusion

Modern astrometry plus stellar-motion propagation and long-term Earth precession can produce modelled star maps across this interval. None of the sources checked supplies an observed or uniformly validated all-star reconstruction of the entire interval. Catalogue epoch, software input range, model fit accuracy and physical predictive uncertainty are different quantities.

Use astronomical years −19999 to +5000 for 20,000 BCE–5,000 CE; astronomical year 0 is 1 BCE. Specify a calendar when converting dates to Julian dates.

## Source comparison

| Source | What it provides | Coverage and main limitations |
|---|---|---|
| [ESA Gaia DR3](https://www.cosmos.esa.int/web/gaia/dr3) | Modern positions, parallaxes and proper motions for about 1.46 billion objects; mean radial velocities for about 33 million. | Reference epoch J2016.0, based on 34 months of observations. ICRS frame; time coordinate TCB. Not a catalogue of ancient positions. Most sources lack radial velocity. A Gaia six-parameter astrometric solution adds pseudo-colour, not radial velocity: distinguish this from six-dimensional position/velocity data. |
| [ESA Hipparcos catalogue documentation](https://hipparcos-tools.cosmos.esa.int/pstex/sect2_01.pdf) and [ESA tools](https://www.cosmos.esa.int/web/hipparcos/java-tools/show-sky) | Bright-star astrometry, identifiers and proper motions; useful complement for bright objects. | Epoch J1991.25, ICRS. Modern measurements must be propagated; binaries, missing radial velocities and measurement errors limit long extrapolations. Catalogue animation is not independent ancient evidence. |
| [Butkevich & Lindegren (2014)](https://arxiv.org/abs/1407.4664) | Rigorous epoch propagation with perspective effects, light travel time and error propagation. | No fixed calendar cutoff in the mathematical transformation. It assumes uniform rectilinear motion relative to the Solar System barycentre. Galactic acceleration and unresolved orbital motion are not solved by that assumption. Propagation over arbitrary times is not guaranteed physical accuracy. |
| [Vondrák, Capitaine & Wallace (2011)](https://www.aanda.org/articles/aa/pdf/2011/10/aa17274-11.pdf) | Long-term precession of the equator and ecliptic, with implementation in the paper appendix. | Designed for ±200,000 years around J2000.0, covering the requested interval. Authors report few-arcsecond performance through the historical period and better than a degree at extreme endpoints. These statements are not a per-date uncertainty for 20,000 BCE or a total stellar-position error. Ordinary IAU 2006 polynomial extrapolation is intended near J2000, not tens of millennia away. Precession rotates the frame; it does not move individual stars through space. |
| [galpy / MWPotential2014 documentation](https://docs.galpy.org/en/v1.8.3/reference/potential.html) and [Bovy (2015)](https://doi.org/10.1088/0067-0049/216/2/29) | Integrates stellar and Solar trajectories in an assumed Galactic gravitational potential. | Can be integrated over this interval, but has no universal validated historical-star date limit. Depends on initial phase-space data, distance/RV errors, Solar parameters and potential choice. Smooth Galactic motion does not automatically model binary orbits or stellar encounters. Integrate the Sun consistently with stars. More detailed dynamics do not automatically give a more accurate answer. |
| [Stellarium official guide](https://stellarium.org/guide/) and [PDF guide](https://stellarium.org/files/guide.pdf), §§18.11 and F.1 | Ready-to-use planetarium for visual comparison. Bright-star propagation includes six-dimensional astrometry where available, assuming constant straight-line velocity; other stars use more limited motion. | F.1 gives an extended input range of −200,000 to +200,000 (before v25.3: ±100,000). Section 18.11 retains older ±100,000 wording in indexed guide text: record the actual version used. Both exceed our interval. Authors explicitly limit extended-range usefulness to proper motion and precession. Agreement with another program sharing catalogues/models is a consistency check, not independent physical validation. |
| [JPL DE440/DE441 paper summary](https://ssd.jpl.nasa.gov/doc/de440_de441.html) and [paper](https://ssd.jpl.nasa.gov/doc/Park.2021.AJ.DE440.pdf) | Solar System ephemerides, including observer/Earth state for apparent-position corrections. | DE441: astronomical years −13200 to +17191; DE440: 1550–2650. ICRS-linked frame; integration uses TDB. Not a stellar catalogue. DE441 does not cover the earliest roughly 6,800 years of the requested interval. This gap is not a hard limit on barycentric stellar directions. |
| [NASA ΔT reference](https://eclipse.gsfc.nasa.gov/SEcat5/deltat.html) | Explains conversion between uniform dynamical time and Earth rotation time, with historical estimates. | Listed polynomial interval is astronomical years −1999 to +3000. Its historical data do not validate Earth rotation at 20,000 BCE or 5,000 CE. Extrapolated ΔT must be marked as an assumption. |

## Practical error budget

[ESA EDR3 precision summary](https://www.cosmos.esa.int/web/gaia/earlydr3) gives typical proper-motion standard errors of 0.02–0.03 mas/year for G<15, 0.5 mas/year at G=20 and 1.4 mas/year at G=21. DR3 uses EDR3 astrometry. As an illustrative calculation, over approximately 22,000 years a single proper-motion component contributes:

- 0.02–0.03 mas/year → 0.44–0.66 arcseconds.
- 0.5 mas/year → 11 arcseconds.
- 1.4 mas/year → 30.8 arcseconds.

These are first-order statistical contributions, not total accuracy forecasts. They omit covariance, systematic errors, radial-velocity/distance uncertainty, perspective acceleration, binary motion and dynamical-model errors. At 5,000 CE the propagation baseline from J2016 is approximately 2,984 years, substantially shorter than the backward baseline. There is no defensible single all-star error bound from these sources.

Ground-observer coordinates add another independent uncertainty: Earth turns about 15 degrees per hour, so one hour of UT1 uncertainty shifts the rotation angle by roughly 15 degrees. The resulting altitude/azimuth error depends on geometry. This is not the same as a 15-degree error in ICRS star direction.

## Recommended use in this simulator

1. Start from Gaia for suitable stars; retain Hipparcos or individually sourced bright-star solutions where needed. Keep uncertainties, correlations, epoch and provenance.
2. Propagate full position/velocity when available; flag missing RV, unreliable distances and binaries. Compare rectilinear propagation to Galactic integration before claiming an improvement.
3. Use a documented long-term precession model across the full date range. Treat nutation and observer ephemeris validity separately.
4. Report barycentric ICRS direction separately from equator/equinox-of-date coordinates and topocentric altitude/azimuth. Use degrees or radians for angles, mas/year for catalogue motions, pc for distances and km/s for velocities, explicitly declaring conversions.
5. Preserve Gaia TCB epochs; explicitly convert between TCB, TDB and TT for relevant calculations. Ground rotation requires UT1; avoid treating ancient UTC as known.
6. Show per-star propagated uncertainty or a missing-data warning; do not describe an integration-convergence test as historical validation.
7. Use a version-pinned Stellarium comparison for broad checks, plus independent modern astrometric reference cases. Do not infer ancient alignment/event accuracy from a matching screenshot.

No datasets were downloaded and no simulation calculations were changed during this research. The references are for online research; a future implementation can bundle required data/models so runtime remains offline.
