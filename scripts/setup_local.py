"""One-time online setup; all downloads, environments and caches stay in the checkout."""
import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='also run backend/frontend tests and offline smoke checks')
    args = parser.parse_args()
    os.chdir(ROOT)
    if sys.version_info < (3, 12):
        raise SystemExit('Python 3.12 or newer is required.')
    npm = shutil.which('npm')
    node = shutil.which('node')
    if not npm or not node:
        raise SystemExit('Install Node.js 20 or newer (including npm), then rerun setup.')
    if int(subprocess.check_output([node, '--version'], text=True).strip().lstrip('v').split('.')[0]) < 20:
        raise SystemExit('Node.js 20 or newer is required.')
    temporary = ROOT / 'tmp'
    temporary.mkdir(exist_ok=True)
    for key, folder in {
        'TMPDIR': '', 'TEMP': '', 'TMP': '', 'PIP_CACHE_DIR': 'pip-cache',
        'npm_config_cache': 'npm-cache', 'XDG_CACHE_HOME': 'cache',
        'XDG_CONFIG_HOME': 'config', 'MPLCONFIGDIR': 'matplotlib', 'ASTROPY_CACHE_DIR': 'astropy',
    }.items():
        target = temporary / folder
        target.mkdir(exist_ok=True)
        os.environ[key] = str(target)
    os.environ['OMP_NUM_THREADS'] = '2'

    def run(command):
        message = 'Setup: ' + ' '.join(map(str, command))
        print(message, flush=True)
        with (ROOT / 'LOG.md').open('a') as log:
            log.write(f'\n- {time.strftime("%Y-%m-%d %H:%M:%S %z")}: {message}\n')
        subprocess.run(list(map(str, command)), check=True, cwd=ROOT)

    python = ROOT / '.venv' / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
    if not python.exists():
        run([sys.executable, '-m', 'venv', ROOT / '.venv'])
    run([python, '-m', 'pip', 'install', '-r', 'backend/requirements-lock.txt'])
    modules = ROOT / 'frontend/node_modules'
    if modules.exists():
        backup = temporary / 'setup-backups' / f'node_modules-{time.time_ns()}'
        backup.parent.mkdir(parents=True, exist_ok=True)
        modules.rename(backup)
        print(f'Preserved previous frontend dependencies in {backup.relative_to(ROOT)}', flush=True)
    run([npm, 'ci', '--prefix', 'frontend', '--no-audit', '--no-fund'])
    run([python, 'scripts/install_runtime_data.py'])
    run([npm, 'run', 'build', '--prefix', 'frontend'])
    if args.check:
        run([python, '-m', 'pytest', '-q', f'--basetemp=tmp/pytest-setup-{time.time_ns()}'])
        run([npm, 'test', '--prefix', 'frontend'])
        run([python, 'scripts/verify_install.py'])
    command = (r'.venv\Scripts\python.exe -m uvicorn backend.app:app --host 127.0.0.1 --port 8765'
               if os.name == 'nt' else './run.sh')
    print(f'Setup complete. Run {command}, then open http://127.0.0.1:8765/', flush=True)


if __name__ == '__main__':
    main()
