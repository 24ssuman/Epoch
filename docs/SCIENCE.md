# Scientific methods and limits

## Frames, time and ephemerides

Time is stored as split Julian dates. TT is the calendar input; TDB drives ephemeris evaluation; UT1 orients Earth. Proleptic Gregorian and Julian arithmetic supports astronomical year zero internally and BCE/CE externally. Modern apparent directions include iterated light time, WGS84 observer parallax/rotation, solar deflection and aberration. Near modern epochs ERFA implements IAU 2006/2000A transformations; deep time uses Vondrák long-term precession and an explicitly approximate spin phase.

- JPL DE440/441: https://ssd.jpl.nasa.gov/doc/de440_de441.html
- Horizons conventions/limitations: https://ssd.jpl.nasa.gov/horizons/manual.html
- SOFA: https://www.iausofa.org/current-software
- Vondrák et al. 2011: https://doi.org/10.1051/0004-6361/201117274
- ΔT prescription, published −1999..3000 interval: https://eclipse.gsfc.nasa.gov/LEcat5/deltatpoly.html
- Bundled IERS handling: https://docs.astropy.org/en/stable/utils/iers.html

**Deep-time Earth orientation (2026-10-21).** Beyond 500 years from J2000 the celestial-to-terrestrial rotation is: Vondrák (2011) long-term precession with frame bias (`erfa.ltpb`); IAU 2000A nutation (`erfa.nut06a`, Vondrák mean obliquity) within 4,000 years of J2000 and none beyond (the nutation argument polynomials are not trusted there); and the Earth rotation angle from UT1 minus the equation of origins (`erfa.eors`). The CIO locator s is integrated from its definition, s = −∫(X dY − Y dX)/(1 + Z), on the Vondrák pole; it matches the IAU `s06` series to 0.03″ within 1,000 years, while `s06` diverges far from J2000 (by 254° at 13,000 BCE). The result joins the IAU 2006/2000A branch to ≤0.25″ at 1500 and 2500 CE. This replaced an approximation whose sign was wrong (alt/az off by tens of degrees), and which after the sign fix was still off by up to 138″ at 1000 CE. Units: radians internally, frame GCRS → true equator of date → terrestrial, time scales TT (precession/nutation) and UT1 (rotation). Limitation: ΔT, not the frame, dominates ancient alt/az uncertainty (see docs/NASA_CROSSCHECK.md B).

Far outside observed Earth-rotation records, the ΔT curve is only a scenario. The offset is adjustable and labels remain visible. High decimal precision does not establish historical accuracy.

## Prominent stars, light and sizes

The initial atlas uses HYG 4.1, including Hipparcos bright stars and B−V photometry. Proper motion, distance and radial velocity propagate stellar space motion. Zero radial-velocity placeholders in HYG are conservatively treated as missing. galpy MWPotential2014 trajectories are used for supported bright candidates over the precomputed interval; the observer translates with the Sun while the ICRS axes stay fixed. Incomplete motions remain explicitly approximate.

- HYG source/data description and CC BY-SA license: https://github.com/astronexus/HYG-Database
- Hipparcos: https://www.cosmos.esa.int/web/hipparcos/catalogues
- galpy: https://docs.galpy.org/en/stable/ ; Bovy 2015, https://doi.org/10.1088/0067-0049/216/2/29
- Optional Gaia DR3 data: https://www.cosmos.esa.int/web/gaia/dr3

Brightness follows the inverse-square distance law under constant-luminosity/extinction assumptions. Relative flux is 10^(−0.4m); exposure scales flux by 2^EV. Measured B−V is converted to approximate temperature and display RGB. Actual spectra, variability and exact color perception are not reconstructed. Single-scattering standard-air atmospheric radiance, empirical extinction/airmass and standard refraction are visual models; weather and multiple scattering are omitted.

A stellar brightness halo is an optical point-spread function, not a physical diameter. Direct limb-darkened angular diameters are matched by HD/HIP identity from JMDC; ambiguous identifiers and poor/errorless measurements are excluded. Latest qualifying published measurements are retained with band, uncertainty, notes and bibliographic code. Some diameters describe a component/photosphere of a multiple system, not the binary separation. Unknown diameters are not inferred from apparent brightness. Diameter and distance determine physical radius and its evolving apparent angle; constant photospheric radius is an explicit assumption.

- JMDC measured diameters: https://cdsarc.cds.unistra.fr/viz-bin/cat/II/345
- JMMC compilation context: https://cdsarc.cds.unistra.fr/viz-bin/cat/II/345
- Atmospheric-scattering reference: https://ebruneton.github.io/precomputed_atmospheric_scattering/

Planet magnitudes follow Mallama & Hilton (2018, Astronomy and Computing 25, 10), the models JPL Horizons uses for APmag: Saturn includes its rings (effective tilt = geometric mean of the sub-Earth and sub-Sun ring latitudes; globe only when the unlit ring face is seen), Uranus uses planetographic sub-latitudes, Neptune its 1980–2000 brightening. Against Horizons 2016–2036 they agree to ≤0.002 mag (Mercury, Venus, Jupiter, Uranus, Neptune), 0.03 mag (Saturn, apart from the deliberate unlit-ring case) and 0.11 mag (Mars, whose rotational/seasonal terms are omitted); the earlier phase laws were off by up to 0.98 mag (Saturn rings ignored). The Moon keeps its phase law, which matches Horizons to 0.05 mag. https://doi.org/10.1016/j.ascom.2018.08.002

Planets, Sun and Moon use physical radii and actual angular sizes. Subpixel planets/stars can still produce point-spread light, as with an eye or camera. Same-scale size comparison has no artificial minimum disk diameter. The enlarged-marker setting is separately labelled. Surface textures represent present-day illustrative geography; the model does not infer ancient coastlines or planetary weather.

## Deep-time reconstruction and comets

IAS15 integrates a reduced dynamical model with full first-order post-Newtonian corrections, solar/Earth J2, simplified CTL tides and massive asteroid perturbations. Earth spin direction is refreshed from long-term precession; fixed spin magnitudes and lag parameters are scenario choices. Lunar libration, dissipation history, small perturbers and tidal/spin feedback are incomplete. This is not the JPL integrator.

- IAS15: https://rebound.hanno-rein.de/integrators/ias15/
- REBOUNDx force assumptions: https://reboundx.readthedocs.io/en/stable/effects.html
- GM constants: https://naif.jpl.nasa.gov/pub/naif/generic_kernels/pck/gm_de440.tpc

**Since 2026-10-22 (schema v5)** the past reconstruction starts from NASA's DE441 states at its first epoch (13,201 BCE) and integrates only the interval DE441 does not cover, on a local clock counted from that seed (absolute times near −5.5 million days had made exact sample stops round the clock and inflated integration differences tenfold). REBOUNDx's constant-time-lag tide couples bodies only to particle 0 (the Sun), so the Earth tide raised by the Moon, and with it the lunar secular acceleration, was missing (measured: 0.00″ effect in 100 years instead of ≈13″). It is restored empirically: the Moon's osculating geocentric mean anomaly is shifted by −(c1·τ + c2·τ² + c3·τ³), τ in centuries from the seed; c2 and c3 are fitted on a 6,800-year hold-out seeded from DE441 at 6000 BCE (Moon error 8.8° → 360″ rms against DE441), and c1 is measured forward from the seed against DE441. The correction assumes DE441-era tidal dissipation before 13,201 BCE; it is a scenario, not a calibrated ancient value (data/jobs/calibration/, scripts/deep_seed.py).

Multirate Chebyshev segments store the Earth–Moon barycenter plus geocentric lunar motion, alongside the other body trajectories. Mixed precision is checked with a quantization bound, independent off-node probes and tighter integrations before publication. Numerical errors, disagreement with JPL, and local tidal-parameter sensitivity are distinct; none is a calibrated confidence interval on the ancient sky.

Sungrazers (perihelion < 0.03 AU: Great September Comet 1882, Ikeya–Seki 1965, Lovejoy 2011) also carry 5-minute JPL Horizons vectors for ±1 day around perihelion (data/comets/dense/); with hourly samples alone the spline was off by up to 28,000 km there, now ≤ 2 km. Comets use individually bounded JPL vector packs: Halley 1985–1987/2060–2062, Encke 2025–2028, Hale–Bopp 1996–1998. Outside those intervals they are hidden. Spline interpolation and simple brightness/activity laws are approximate; comet covariance is not propagated and tails are illustrative. Unknown ancient comets are never invented.

## Referenced Moon glow (2026-10-22)
The sky and Moon-phase diagram now scale their soft glow from the existing lunar magnitude, following Krisciunas & Schaefer (1991), Eq. 9, with distance and (for the sky) standard-air attenuation/exposure/daylight. The broad lunar night-sky tint uses relative flux rather than illuminated area. The phase disk and its physical angular size are unchanged. Halo width/opacity are illustrative display choices; eclipse attenuation, opposition surge, site-specific aerosols and calibrated PSFs are not included. Sources, units, frame/time and tests: [MOON_LIGHTING.md](MOON_LIGHTING.md).
