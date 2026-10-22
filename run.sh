#!/bin/zsh
set -eu
cd "${0:A:h}"
export XDG_CACHE_HOME="$PWD/tmp/cache"
export XDG_CONFIG_HOME="$PWD/tmp/config"
export MPLCONFIGDIR="$PWD/tmp/matplotlib"
export ASTROPY_CACHE_DIR="$PWD/tmp/astropy"
export TMPDIR="$PWD/tmp"
export OMP_NUM_THREADS=2
mkdir -p "$XDG_CACHE_HOME" "$XDG_CONFIG_HOME" "$MPLCONFIGDIR" "$ASTROPY_CACHE_DIR"
if [[ ! -x .venv/bin/python || ! -f frontend/dist/index.html ]]; then
  echo 'Run ./setup.sh first.'
  exit 1
fi
exec .venv/bin/python -m uvicorn backend.app:app --host 127.0.0.1 --port "${PORT:-8765}"
