# Prepared offline runtime data

`runtime-v1.tar.gz` contains the prepared inputs needed by the current Epoch model: HYG-derived stars, measured stellar diameters, galpy stellar trajectories, Sanskrit-name mappings, bounded JPL comet samples and original responses, photometry overrides, JPL constants and asteroid states, current v5 planetary chunks/reports, the latest small resume checkpoint, and reconstruction seed/lunar-calibration parameters. `manifest.json` pins the archive, every unpacked file and the separately downloaded kernels by byte size and SHA-256.

No saved sky/playback frames, obsolete trajectory generations, worker status/PIDs, partial downloads, environments or dependency folders are included. The playback database is created empty on first use. Calibration holdout samples and older checkpoint history are research artifacts, not runtime prerequisites, and are also excluded.

The manifest's `source_inputs` retains URLs, checksums and attribution for the original HYG/JMDC tables without requiring those tables at runtime. After setup, the installed-data manifest lists files actually present in that checkout.

## Sources and attribution

- Stars and their prepared stellar trajectories derive from David Nash's [HYG 4.1 database](https://github.com/astronexus/HYG-Database), incorporating Hipparcos/Yale/Gliese catalogs, under [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/). Epoch converts the catalog to JSON and integrates the supported subset using galpy MWPotential2014; preserve the HYG attribution and share-alike license for these derived catalog products. The unmodified HYG CSV is unnecessary at runtime.
- Measured diameters derive from [JMMC JMDC (II/345)](https://cdsarc.cds.unistra.fr/viz-bin/cat/II/345), Duvert (2016) / Chelli et al. (2016), A&A 589 A112. Original measurement references are retained in the prepared entries; no new stellar-size measurements are asserted. The source table is unnecessary at runtime.
- Comet windows, original target responses, asteroid J2000 states and gravitational constants come from [NASA/JPL Horizons](https://ssd.jpl.nasa.gov/horizons/) and [JPL SPICE constants](https://naif.jpl.nasa.gov/pub/naif/generic_kernels/pck/gm_de440.tpc). Preserve per-target metadata and attribution. Comet magnitude overrides retain their published-model or recorded-peak references.
- Planetary v5 chunks are Epoch's reduced-model calculations seeded from JPL DE441, not a NASA historical reconstruction. Seed asteroid states and lunar coefficients are locally calculated. Each report retains numerical checks and physical limitations.
- Sanskrit mappings are prepared naming metadata; evidence and identification limitations are documented in the [interface guide](../../frontend/README.md#sanskrit-name-sources). No private source books are required or included.

## Frames, units and limits

Supported application dates remain 15,000 BCE–5,000 CE. Stellar pack positions are parsecs in fixed ICRS axes at TT-based Julian epochs, using galpy MWPotential2014; other stars retain approximate rectilinear propagation. Planetary coefficients describe solar-system barycentric positions in AU at TDB Julian dates; runtime positions/velocities are km and km/s. Comet samples use barycentric ICRS km and TDB Julian dates within individually stated windows. Angular stellar diameters retain measurement units and source references in each entry. Lunar correction coefficients are arcseconds per powers of Julian centuries from the seed; asteroid seeds use AU and AU/day in barycentric ICRS.

Model extrapolations before DE441 and long-term Galactic motion are not observed or validated historical skies. Ancient Earth rotation, stellar velocities, reduced planetary dynamics and tidal evolution impose physical uncertainty beyond numerical convergence checks. See the [scientific methods](../../docs/SCIENCE.md) and embedded reports.

## Installation and maintenance

Run the repository setup command. It verifies the archive and its members, installs prepared files, downloads the two pinned official JPL kernels (3.43 GB total), and verifies their SHA-256 hashes. Existing matching files are reused; changed prepared files are backed up inside the checkout before replacement. Mismatched existing kernels are preserved and reported for inspection. Setup reruns never clear playback or worker history.

Locally updated reconstruction files, including advanced checkpoints and calibration/trajectory products, stay in place during setup reruns. Their actual checksums are recorded with a local-reconstruction flag; installation never rolls a worker back to the bundled checkpoint. Other modified prepared inputs are backed up before restoration.

Maintainers can export a new version with `package_runtime_data.py` after explicitly choosing a new archive name. The exporter refuses to overwrite an existing archive. Retain source inputs and validation evidence when preparing a new version; do not rebuild the scientific model during normal installation.
