"""Install the pinned prepared bundle and explicitly download/verify official JPL kernels."""
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import sys
import tarfile
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.setup_data import download, log


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def matches(path, spec):
    return path.is_file() and path.stat().st_size == spec['bytes'] and digest(path) == spec['sha256']


def install_prepared():
    folder = ROOT / 'data/prepared'
    manifest = json.loads((folder / 'manifest.json').read_text())
    archive = folder / manifest['archive']
    if not matches(archive, dict(bytes=manifest['archive_bytes'], sha256=manifest['archive_sha256'])):
        raise RuntimeError('Prepared-data archive checksum mismatch; restore the archive from GitHub before rerunning.')
    expected = {f['path']: f for f in manifest['files']}
    preserved_jobs = set()
    with tarfile.open(archive, 'r:gz') as tar:
        members = tar.getmembers()
        if len(members) != len(expected) or {m.name for m in members} != set(expected):
            raise RuntimeError('Prepared archive contents do not match the manifest.')
        for member in members:
            relative = PurePosixPath(member.name)
            if not member.isfile() or relative.is_absolute() or '..' in relative.parts or relative.parts[0] != 'data':
                raise RuntimeError('Unsafe prepared-data member: ' + member.name)
            path = ROOT.joinpath(*relative.parts)
            if not path.resolve().is_relative_to(ROOT):
                raise RuntimeError('Prepared-data destination escapes checkout: ' + member.name)
            spec = expected[member.name]
            if matches(path, spec):
                continue
            if path.is_file() and relative.parts[:2] == ('data', 'jobs'):
                preserved_jobs.add(member.name)
                log('Preserved locally updated reconstruction input ' + member.name)
                continue
            content = tar.extractfile(member).read()
            if len(content) != spec['bytes'] or hashlib.sha256(content).hexdigest() != spec['sha256']:
                raise RuntimeError('Prepared member checksum mismatch: ' + member.name)
            if path.exists():
                # Preserve modified local files instead of silently discarding them on setup reruns.
                backup = ROOT / 'tmp/setup-backups' / (time.strftime('%Y%m%dT%H%M%S') + '-' + str(time.time_ns())) / relative
                backup.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(path, backup)
                log('Preserved modified input at ' + str(backup.relative_to(ROOT)))
            path.parent.mkdir(parents=True, exist_ok=True)
            temporary = path.with_name(path.name + '.setup-partial')
            temporary.write_bytes(content)
            os.replace(temporary, path)
    destination = ROOT / 'data/manifest.json'
    previous = json.loads(destination.read_text()) if destination.exists() else {}
    provenance = {name: spec for name, spec in previous.items() if (ROOT / name).is_file()}
    for name, spec in expected.items():
        if name in preserved_jobs:
            path = ROOT / name
            provenance[name] = dict(previous.get(name, {}), bytes=path.stat().st_size,
                                    sha256=digest(path), local_reconstruction=True)
        else:
            provenance[name] = dict(spec['provenance'], bytes=spec['bytes'], sha256=spec['sha256'],
                                    prepared_bundle=manifest['archive_sha256'])
    destination.write_text(json.dumps(provenance, indent=2, ensure_ascii=False) + '\n')
    log(f'Installed/verified {len(expected)} prepared runtime files; no playback cache supplied.')
    return manifest


def main():
    manifest = install_prepared()
    for name, spec in manifest['kernels'].items():
        path = ROOT / 'data/kernels' / name
        if path.exists() and not matches(path, spec):
            raise RuntimeError(f'{name} differs from the pinned checksum; existing file preserved. Move it aside inside tmp/ and rerun setup.')
        download(spec['url'], path, spec['license'])
        if not matches(path, spec):
            raise RuntimeError(f'{name} download checksum mismatch; file and resumable shards retained for inspection.')
        log(f'Verified {name}: {spec["bytes"]:,} bytes, SHA-256 {spec["sha256"]}')


if __name__ == '__main__':
    main()
