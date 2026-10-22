# UI source

App.tsx: observer/date/view controls, bright-star discovery, true-size comparison, live calculation drawer and background data status.
Sky.tsx: WebGL rendering, actual angular disks, normalized point-spread light, atmosphere, labels and picking.
types.ts: shared frontend result/settings shapes. style.css: responsive visual design. main.tsx: React entry point.

`settings.sanskritNames` (off by default) switches labels to Devanagari via `starLabel()` in types.ts (sky, atlas, search, object card, size comparison); objects without a Sanskrit name keep English, and named stars are labelled down to magnitude 6.5 instead of 2.6. The object card shows Devanagari · IAST, alternatives and English. Rendering is photographic only (the human-eye mode was removed on request 2026-10-21).

Sky.tsx renders on demand (dirty flag set by camera changes, rebuilds, resize, texture/trail/constellation loads); book stars carry a `forced` attribute so the magnitude threshold does not hide them. App requests `view`/`horizon_only` matching the current view.

`settings.sunlight=false` sets daylight to zero and removes solar scattering from the sky shader (the Sun disk stays). It is a labelled, nonphysical visual aid. Body labels use `starLabel` too, so planets show Devanagari in Sanskrit mode.

Comet tails are additive ribbons (`ribbon()` in Sky.tsx) fading along the tail and to zero at the edges, scaled by the head magnitude, exposure and daylight; drawn independently of head visibility so a tail can rise before its head. App's Settings panel has the comet list with jump-to-perihelion.

Phone layout: `--timeline-h` (set from the timeline's measured height) positions the calculation chip, orientation readout, date popover, toast and settings panel; the settings panel starts closed under 760 px.

Stars: default `starLimit` 5.76 (common limit, requested as `max_magnitude=5.76`); every shown star is selectable. The Moon in the ground view uses a phase shader (Sun-from-Moon direction from topocentric vectors, Lommel-Seeliger shading, transparent unlit side that still hides stars); its card shows the phase name.

Playback (`playback.ts`, used by App.tsx): deterministic 100 ms grid anchored by epoch and integer sample index, reversible at the same speed; one active request plus one latest pending target. Observer/model/date/direction/pause changes invalidate generations and reject late responses even when abort is ignored. Cards and the calendar use the displayed frame's time and observer. Progress polling is serial and omitted for closed playback calculations; previews are disabled server-side while playing.

Sky.tsx now renders only ground coordinates. It reuses capacity-growing typed attributes, unit-sphere body meshes, materials and static grids; constellation results have scene-generation guards. Labels and selection changes do not rebuild geometry. The meter separates callback cadence, redraws and accepted exact updates; detailed timing and GPU resource counts are available in its title/data attributes for local verification. Atmosphere/sunlight shader shortcuts preserve the existing result.

MoonPhase.tsx displays the calculated topocentric illuminated fraction and phase name from the accepted snapshot. The disk is a schematic orthographic terminator: waxing bright limb at the right, waning at the left; no sky orientation or physical screen size is claimed. The side-rail Moon button toggles the shared panel and exposes aria-expanded; unavailable trajectory coverage does not produce a fabricated phase.

`moonlight.ts` scales lunar light from the existing phase/distance-dependent magnitude (Krisciunas & Schaefer 1991, Eq. 9). Sky.tsx reuses a small soft billboard outside the Moon disk and applies horizon/daylight/exposure gating. The broad lunar sky tint uses flux and standard-air transmission. MoonPhase.tsx glows only the lit SVG path; widths/opacities remain illustrative. See docs/MOON_LIGHTING.md for sources and limits.
