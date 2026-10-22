# Epoch — Offline Sky Simulator

A local astronomical observatory that shows the sky from any place on Earth between **15,000 BCE and 5,000 CE**. It has a React/Three.js interface and a Python/FastAPI scientific service. Once set up, it runs fully offline.

## Requirements

| Tool | Version | Used for |
| --- | --- | --- |
| [Python](https://www.python.org/downloads/) | 3.12 or newer | scientific backend and data setup |
| [Node.js](https://nodejs.org/) (includes npm) | 20 or newer | building the web interface |
| [Git](https://git-scm.com/downloads) | any recent | getting the code |

- **Python packages** (from `backend/requirements.txt`): fastapi, uvicorn, numpy, scipy, astropy, pyerfa, jplephem, rebound, reboundx, galpy, httpx, pytest.
- **JavaScript packages** (from `frontend/package.json`): react, react-dom, three, lucide-react; for the build, typescript and vite.
- **Disk and network:** about 10 GB of free space. Setup downloads several GB once; after that no internet is needed.

## Setup (once, online)

Run these commands in a terminal from the project folder. If `python` is not found, use `python3` or `py`.

```bash
git clone https://github.com/24ssuman/Epoch.git
cd Epoch
python -m venv .venv
```

Activate the virtual environment. Do this in every new terminal before running the commands below:

- macOS / Linux: `source .venv/bin/activate`
- Windows: `.venv\Scripts\activate`

Install the packages and the offline data, then build the interface:

```bash
python -m pip install -r backend/requirements.txt
npm install --prefix frontend
python scripts/setup_data.py --extended
python scripts/install_assets.py
python scripts/install_perturbers.py
python scripts/install_comets.py
python scripts/install_diameters.py
python scripts/build_stellar_pack.py
python scripts/fetch_references.py
npm run build --prefix frontend
```

## Run

With the virtual environment active:

```bash
python -m uvicorn backend.app:app --host 127.0.0.1 --port 8765
```

Open **http://127.0.0.1:8765/** in a browser. Stop the server with Ctrl+C.

## Use

- Drag to look around and use the mouse wheel to zoom. Pick a location or enter coordinates, and set the date in the date dialog or on the timeline. Dates are in **TT** (Terrestrial Time); BCE/CE and Julian/Gregorian calendars are supported.
- Search stars, planets and comets by name or HIP number, and click one to inspect it. Settings let you switch atmosphere, names (including Sanskrit names), grids and constellation lines.
- Planets before about 13,200 BCE come from a background calculation: start it from **Offline data → Generate past / Generate future** in the app.

## Check that it works

```bash
python -m pytest -q
```

## Limitations

Results are calculated from JPL ephemerides (DE440/DE441), the Hipparcos/HYG star catalog and cached JPL comet data. Coverage of the full date range does not mean every object can be reconstructed accurately over it: dates before DE441 are reduced-model extrapolations, and ancient Earth rotation and local clock times are uncertain. See [coverage and accuracy](docs/README.md#coverage-and-accuracy) and [scientific methods](docs/SCIENCE.md).

## More details

- [frontend/README.md](frontend/README.md): full guide to the interface and its controls
- [backend/README.md](backend/README.md): API, caching, star limit, and changing the date range
- [scripts/README.md](scripts/README.md): data setup, background reconstruction, cache pruning, NASA cross-check
- [docs/README.md](docs/README.md): coverage, accuracy, scientific methods and validation
- [data/README.md](data/README.md): data sources and licenses
- [tests/README.md](tests/README.md): what the tests check

Sanskrit-name sources and their limits are documented in the [frontend guide](frontend/README.md#sanskrit-name-sources), with online links to the texts containing the names.
