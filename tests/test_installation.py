"""Installation must preserve local files, reject bad data and never ship playback frames."""
import hashlib
import io
import json
from pathlib import Path
import tarfile

import pytest
from scripts import install_runtime_data as installer


def bundle(root, name='data/catalogs/example.json', content=b'{"prepared":true}', member_type=None):
    folder = root / 'data/prepared'
    folder.mkdir(parents=True)
    archive = folder / 'test.tar.gz'
    with tarfile.open(archive, 'w:gz') as tar:
        entry = tarfile.TarInfo(name)
        entry.size = len(content)
        if member_type is not None:
            entry.type = member_type
        tar.addfile(entry, io.BytesIO(content))
    manifest = dict(archive=archive.name, archive_bytes=archive.stat().st_size,
                    archive_sha256=installer.digest(archive),
                    files=[dict(path=name, bytes=len(content), sha256=hashlib.sha256(content).hexdigest(), provenance={})])
    (folder / 'manifest.json').write_text(json.dumps(manifest))
    return archive


def test_prepared_install_rerun_preserves_cache_and_backs_up_changed_input(tmp_path, monkeypatch):
    bundle(tmp_path)
    monkeypatch.setattr(installer, 'ROOT', tmp_path)
    monkeypatch.setattr(installer, 'log', lambda message: None)
    cache = tmp_path / 'data/playback/frames.sqlite3'
    cache.parent.mkdir(parents=True)
    cache.write_bytes(b'existing playback')
    installer.install_prepared()
    installed = tmp_path / 'data/catalogs/example.json'
    before = installed.stat().st_mtime_ns
    installer.install_prepared()
    assert installed.stat().st_mtime_ns == before
    installed.write_bytes(b'local modified input')
    installer.install_prepared()
    assert installed.read_bytes() == b'{"prepared":true}'
    assert [p.read_bytes() for p in (tmp_path / 'tmp/setup-backups').rglob('example.json')] == [b'local modified input']
    assert cache.read_bytes() == b'existing playback'


@pytest.mark.parametrize('name,kind', [('data/../../escape', None), ('data/link', tarfile.SYMTYPE)])
def test_prepared_install_rejects_unsafe_members(tmp_path, monkeypatch, name, kind):
    bundle(tmp_path, name=name, member_type=kind)
    monkeypatch.setattr(installer, 'ROOT', tmp_path)
    with pytest.raises(RuntimeError, match='Unsafe'):
        installer.install_prepared()


def test_prepared_install_rejects_corrupt_archive(tmp_path, monkeypatch):
    archive = bundle(tmp_path)
    archive.write_bytes(b'corrupt')
    monkeypatch.setattr(installer, 'ROOT', tmp_path)
    with pytest.raises(RuntimeError, match='checksum'):
        installer.install_prepared()


def test_setup_preserves_advanced_reconstruction_data(tmp_path, monkeypatch):
    bundle(tmp_path, name='data/jobs/past-v5-latest.bin', content=b'bundled checkpoint')
    monkeypatch.setattr(installer, 'ROOT', tmp_path)
    monkeypatch.setattr(installer, 'log', lambda message: None)
    installer.install_prepared()
    checkpoint = tmp_path / 'data/jobs/past-v5-latest.bin'
    checkpoint.write_bytes(b'locally advanced checkpoint')
    installer.install_prepared()
    assert checkpoint.read_bytes() == b'locally advanced checkpoint'
    record = json.loads((tmp_path / 'data/manifest.json').read_text())['data/jobs/past-v5-latest.bin']
    assert record['local_reconstruction'] and record['sha256'] == installer.digest(checkpoint)


def test_distributed_manifest_excludes_playback_and_pins_generated_products():
    folder = Path(__file__).resolve().parents[1] / 'data/prepared'
    manifest = json.loads((folder / 'manifest.json').read_text())
    names = {f['path'] for f in manifest['files']}
    assert not any('/playback/' in name or 'past-v3' in name or 'past-v4' in name for name in names)
    assert {'data/catalogs/galactic.npz', 'data/catalogs/stars.json',
            'data/jobs/calibration/lunar_correction.json', 'data/kernels/gm_de440.tpc',
            'data/comets/photometry_overrides.json'} <= names
    assert set(manifest['kernels']) == {'de440.bsp', 'de441.bsp'}
    assert all(len(k['sha256']) == 64 for k in manifest['kernels'].values())
