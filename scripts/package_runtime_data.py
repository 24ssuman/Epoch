"""Maintainer-only: package prepared runtime data, never playback or obsolete worker history."""
import gzip
import hashlib
import io
import json
from pathlib import Path
import tarfile

ROOT = Path(__file__).resolve().parents[1]


def main():
    source_manifest = json.loads((ROOT / 'data/manifest.json').read_text())
    paths = [ROOT / 'data/catalogs' / name for name in (
        'README.md', 'stars.json', 'diameters.json', 'galactic.npz',
        'sanskrit_star_names.json', 'classical_star_names.json',
    )]
    paths += sorted((ROOT / 'data/comets').rglob('*'))
    paths += [ROOT / 'data/kernels' / name for name in ('README.md', 'gm_de440.tpc', 'asteroids.json')]
    paths += sorted((ROOT / 'data/kernels').glob('asteroid-*-source.txt'))
    paths += [ROOT / 'data/jobs/README.md']
    paths += sorted((ROOT / 'data/jobs').glob('past-v5-*.npz'))
    paths += sorted((ROOT / 'data/jobs').glob('past-v5-*.json'))
    paths += [ROOT / 'data/jobs/past-v5-latest.bin']
    paths += [ROOT / 'data/jobs/calibration' / name for name in ('seed-asteroids.json', 'lunar_correction.json')]
    paths = sorted(set(p for p in paths if p.is_file()))
    output = ROOT / 'data/prepared'
    output.mkdir(exist_ok=True)
    archive = output / 'runtime-v1.tar.gz'
    if archive.exists():
        raise SystemExit('Archive already exists; preserve it and choose a new version before repackaging.')
    files = []
    with archive.open('wb') as raw, gzip.GzipFile(fileobj=raw, mode='wb', mtime=0, filename='') as compressed:
        with tarfile.open(fileobj=compressed, mode='w') as tar:
            for path in paths:
                name = path.relative_to(ROOT).as_posix()
                content = path.read_bytes()
                entry = tarfile.TarInfo(name)
                entry.size = len(content)
                entry.mode = 0o644
                tar.addfile(entry, io.BytesIO(content))
                provenance = source_manifest.get(name, {})
                files.append(dict(path=name, bytes=len(content), sha256=hashlib.sha256(content).hexdigest(),
                                  provenance=provenance))
    kernels = {name: source_manifest['data/kernels/' + name] for name in ('de440.bsp', 'de441.bsp')}
    manifest = dict(schema='epoch-runtime-bundle-v1', archive=archive.name,
                    archive_bytes=archive.stat().st_size,
                    archive_sha256=hashlib.file_digest(archive.open('rb'), 'sha256').hexdigest(),
                    files=files, kernels=kernels,
                    source_inputs={name: source_manifest[name] for name in (
                        'data/catalogs/hyg.csv', 'data/catalogs/jmdc.dat.gz')},
                    provenance='Prepared by Epoch from HYG 4.1/Hipparcos, JMDC, JPL Horizons/DE441 and galpy MWPotential2014. See README.md in this folder and embedded per-file metadata/reports.',
                    limitations='Pre-DE441 planetary trajectories and Galactic stellar positions are model extrapolations; numerical checks do not establish historical accuracy.')
    (output / 'manifest.json').write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + '\n')
    print(f'{len(files)} files, {sum(f["bytes"] for f in files):,} unpacked bytes; {archive.stat().st_size:,} archive bytes')


if __name__ == '__main__':
    main()
