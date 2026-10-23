# Clean installation verification — 23 October 2026

The complete setup was tested in an isolated checkout under the project's temporary test folder, exported from the proposed GitHub files. No existing local environment, original kernels, raw catalogs, worker history or saved playback database was supplied. The prepared bundle was the only local scientific input; setup downloaded both JPL kernels from their official URLs and installed Python/JavaScript dependencies online.

## Verified environment and command

macOS 26.6.2 arm64, Python 3.14.2, Node.js 20.17.0 / npm 10.8.2. Run `./setup.sh --check` (or the Python setup entry point). Package metadata also permits the documented Python 3.12 minimum; other operating systems were not exercised in this local verification.

## Results

- Complete online installation, interrupted-download resumption and repeat setup passed. Transient JPL range failures recovered automatically. Existing matching inputs were reused; original local data was never substituted for missing downloads.
- 135 backend tests and all 8 frontend tests passed; the production frontend built successfully.
- Offline verification passed with socket connections and DNS resolution blocked in the verifier process, covering eight ancient/modern/future dates, 29 comet apparitions, Sanskrit object metadata, reconstruction initialization and the readable 27-particle resume checkpoint. New exact frames were calculated and cached locally without a distributed playback database.
- Nine complete scientific snapshots matched the original installation exactly after excluding execution timings. Samples included 15,000 BCE, the DE441 boundary era, J2000-era comet apparitions, the present era and the last day of 5,000 CE. Observer: Kolkata, ground view with horizon filtering. These are model-equivalence checks, not validation of ancient physical accuracy.
- Live HTTP checks passed for the built HTML/JavaScript/CSS, both local imagery assets, bootstrap/catalog metadata, all 29 comets and four modern/deep-time/future ground-view snapshots with 11 solar-system bodies each. The catalog contains 119,625 stars before the normal magnitude filter.
- Browser checks passed for loading the sky, finding the next night and displaying the Moon phase panel. No deployment was performed.
- Setup preservation checks cover an existing playback cache, backups of modified prepared catalogs, and locally advanced worker/checkpoint files. Reconstruction files stay in place during reruns and their actual hashes are recorded.

## Distributed data and downloads

| Item | Exact bytes | SHA-256 |
| --- | ---: | --- |
| Prepared bundle (455 files; 73,977,150 unpacked bytes) | 37,889,120 | `61435c1a59c447af20870f816fe333b21da2a9d90d71a791a2f608d62059761c` |
| de440.bsp (downloaded during setup) | 119,799,808 | `a4ce9bf9b3282becc9f4b2ac3cebe03a2ae7599981aabd7265fd8482fff7c4b5` |
| de441.bsp (downloaded during setup) | 3,307,878,400 | `9a824e6a8ce3d39f8a513b17278ff7b7ad226f964c76d2019b0a51d8808d6ff5` |

The 529 MB saved playback cache is excluded. The runtime bundle is about 37.9 MB compressed; the two official kernels total about 3.43 GB. Original HYG/JMDC tables are unnecessary for normal installation because their prepared products, source attribution and source checksums are supplied. See the [prepared-data guide](../data/prepared/README.md) for frames, units, time scales, licenses and scientific limitations.

Research holdout samples and retired trajectory generations remain outside the runtime bundle. Existing Starlette test-client deprecation and Vite bundle-size advisories were observed; all checks completed successfully.
