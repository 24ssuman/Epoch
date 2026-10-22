#!/bin/zsh
set -eu
cd "${0:A:h}"
mkdir -p tmp
export TMPDIR="$PWD/tmp"
export PIP_CACHE_DIR="$PWD/tmp/pip-cache"
export npm_config_cache="$PWD/tmp/npm-cache"
if [[ ! -x .venv/bin/python ]]; then python3 -m venv .venv; fi
.venv/bin/python -m pip install -r backend/requirements.txt
npm install --prefix frontend
.venv/bin/python scripts/setup_data.py --extended
.venv/bin/python scripts/install_assets.py
.venv/bin/python scripts/install_perturbers.py
.venv/bin/python scripts/install_comets.py
.venv/bin/python scripts/install_diameters.py
.venv/bin/python scripts/build_stellar_pack.py
.venv/bin/python scripts/fetch_references.py
npm run build --prefix frontend
.venv/bin/python -m pytest -q
