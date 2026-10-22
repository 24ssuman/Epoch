# Moon lighting references and display choices

The Moon's phase, angular disk, observer distance and apparent magnitude come from the existing local astronomical calculation. This change only renders those results; no extra online runtime requests or motion interpolation are introduced.

## References

- [Krisciunas & Schaefer (1991), PASP 103, 1033–1039](https://articles.adsabs.harvard.edu/pdf/1991PASP..103.1033K), Eq. 9: empirical V-band magnitude versus lunar phase angle. The simulator already uses this law plus observer-distance scaling. Relative flux is `10^(-0.4 × (m + 12.73))`, with a reference full-Moon magnitude −12.73. The law gives quarter/full flux ≈0.091, rather than the illuminated-area ratio 0.5. It omits the near-full opposition surge and eclipse dimming.
- [NASA, Moonlight](https://science.nasa.gov/moon/moonlight/): moonlight is reflected sunlight; apparent illumination varies through the phases.
- [NASA, Moon Phases](https://science.nasa.gov/moon/moon-phases/): earthshine can faintly reveal the unlit portion of a crescent. The sidebar retains a faint schematic dark-side cue; no cloud/albedo-dependent earthshine intensity is inferred.
- [Jones et al. (2013), An advanced scattered moonlight model for Cerro Paranal](https://arxiv.org/abs/1310.7030): detailed moonlight scattering requires geometry, aerosol properties and atmospheric transfer. This renderer does not claim that spectral or site-specific calibration.

## Implementation

`frontend/src/moonlight.ts` converts the existing lunar magnitude to relative light. The sky uses its already extinction-adjusted magnitude and the current exposure; daylight suppresses the local glow. The smooth halo surrounds the calculated disk, whose sharp phase shading, position and physical angular size remain unchanged. No glow is drawn for a Moon at/below the geometric horizon. The broad night-sky moonlight tint now follows phase-dependent flux with standard-air extinction rather than the illuminated fraction alone.

The sidebar applies a soft glow to the illuminated SVG shape only, scaled from the same relative-light model at its standard preview exposure. It remains a schematic phase diagram: waxing right-lit, waning left-lit; neither sky orientation nor physical screen size is implied.

Display mapping is deliberately bounded: opacity `0.28 × (1 − exp(−3 × flux × exposureGain)) × (1 − daylight)`; gain doubles per two EV relative to the default exposure. These tone-mapping constants, a five-disk-radius halo support and an 8-pixel minimum optical support are artistic display choices, not measured atmospheric halo angles or radiance. A small smooth edge mask keeps the halo outside the physical disk. There is no implied 22° ice-crystal halo, cloud/weather reconstruction, calibrated sensor PSF, lunar terrain texture, spectral radiometry, opposition surge or eclipse attenuation.

Source/frame/units/time: installed JPL/accepted reconstruction inputs; topocentric apparent directions; phase angle in degrees, magnitude in approximate V, angular disk radius in degrees, relative light dimensionless; TT input and TDB dynamics. Existing deep-time and Earth-rotation limitations remain.

## Checks

Frontend tests cover quarter/full scaling, inverse-square distance, monotonic phase/exposure response, daylight suppression, atmospheric attenuation and horizon gating. Production TypeScript/Vite build and local browser checks cover both the sky and phase panel. The new glow adds one reused small billboard mesh, not a full-screen post-processing pass.
