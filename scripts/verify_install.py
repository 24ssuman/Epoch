"""Exercise installed runtime with all socket connections blocked (no server/worker needed)."""
import json
from pathlib import Path
import socket
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    def blocked(*args, **kwargs):
        raise AssertionError('Offline verification attempted a network connection')
    socket.socket.connect = blocked
    socket.socket.connect_ex = blocked
    socket.create_connection = blocked
    socket.getaddrinfo = blocked
    from fastapi.testclient import TestClient
    from backend.app import app
    from backend.astrotime import calendar_jd
    from backend.jobs import build_sim, load_checkpoint, SEED_JD
    from backend import frame_cache
    client = TestClient(app)
    assert client.get('/').status_code == 200
    assert client.get('/api/health').json()['offline']
    bootstrap = client.get('/api/bootstrap').json()
    assert bootstrap['star_count'] > 100000
    checks = []
    for year in (-14999, -14000, -13200, -10000, 0, 2000, 2026, 5000):
        # Noon avoids a light-time evaluation just before the first supported instant.
        jd = calendar_jd(year, 1, 1, 12)
        response = client.get('/api/snapshot', params=dict(jd=jd, lat=22.5726, lon=88.3639, limit=9000))
        assert response.status_code == 200, response.text[:200]
        snapshot = response.json()
        assert snapshot['solar_system_available'], (year, snapshot['coverage_message'])
        assert len(snapshot['bodies']) >= 10 and len(snapshot['stars']) > 3000
        checks.append(dict(year=year, stars=len(snapshot['stars']), bodies=len(snapshot['bodies'])))
    assert client.get('/api/object/hip:32349', params={'jd': 2451545.}).json()['sanskrit_devanagari']
    assert len(client.get('/api/comets').json()['comets']) == 29
    seed = json.loads((ROOT / 'data/jobs/calibration/seed-asteroids.json').read_text())['seed']
    simulation, extras = build_sim(jd=SEED_JD, asteroid_states=seed['states'])
    assert simulation.N == 27
    checkpoint = load_checkpoint('past', -1)
    assert checkpoint is not None and checkpoint[0].N == 27
    # Repeating a view must hit a cache generated here, without any distributed saved frames.
    response = client.get('/api/snapshot', params=dict(jd=2451545., limit=100)).json()
    repeated = client.get('/api/snapshot', params=dict(jd=2451545., limit=100)).json()
    assert repeated['playback_cache']['hit'] and response['stars'] == repeated['stars']
    report = dict(network='socket connections and DNS resolution blocked', checks=checks, comets=29,
                  reconstruction_particles=simulation.N, checkpoint_readable=True,
                  local_cache=frame_cache.statistics())
    output = ROOT / 'tmp/installation-verification.json'
    output.parent.mkdir(exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
