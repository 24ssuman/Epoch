"""Reconstruction checkpoints survive interruption: atomic latest snapshot, history fallback, atomic chunk files.
Runs in a temporary folder; never touches data/jobs or a running worker."""
import numpy as np,pytest,rebound
from backend import jobs

@pytest.fixture
def jobdir(tmp_path,monkeypatch):
    messages=[];monkeypatch.setattr(jobs,'JOB_DIR',tmp_path);monkeypatch.setattr(jobs,'log',messages.append)
    return tmp_path,messages

def simulation(t):
    sim=rebound.Simulation();sim.add(m=1.);sim.add(m=1e-3,a=1.);sim.add(m=1e-5,a=2.,e=.1);sim.t=t;return sim

def test_latest_checkpoint_roundtrip_and_history(jobdir):
    path,_=jobdir;sim=simulation(-3652.5);jobs.save_checkpoint(sim,'past')
    loaded,source=jobs.load_checkpoint('past',-1)
    assert source.name==f'past-{jobs.VERSION}-latest.bin' and loaded.t==sim.t and loaded.particles[2].x==sim.particles[2].x
    assert (path/f'past-{jobs.VERSION}.bin').exists() and not list(path.glob('*.tmp'))

def test_furthest_progress_wins_and_corrupt_latest_falls_back(jobdir):
    path,messages=jobdir
    jobs.save_checkpoint(simulation(-3652.5),'past');jobs.save_checkpoint(simulation(-7305.),'past')
    assert jobs.load_checkpoint('past',-1)[0].t==-7305.
    (path/f'past-{jobs.VERSION}-latest.bin').write_bytes(b'torn write')          # interrupted or corrupted latest file
    loaded,source=jobs.load_checkpoint('past',-1)
    assert source.name==f'past-{jobs.VERSION}.bin' and loaded.t==-7305. and any('Skipped unreadable' in m for m in messages)

def test_legacy_archive_only_still_resumes(jobdir):
    path,_=jobdir;simulation(-1000.).save_to_file(str(path/f'past-{jobs.VERSION}.bin'),delete_file=False)
    assert jobs.load_checkpoint('past',-1)[0].t==-1000. and jobs.load_checkpoint('future',1) is None

def test_atomic_chunk_files(jobdir):
    path,_=jobdir;jobs.write_atomic_npz(path/f'past-{jobs.VERSION}-000000000.npz',a=np.arange(5))
    jobs.write_atomic_text(path/f'past-{jobs.VERSION}-000000000.json','{"accepted": true}')
    with np.load(path/f'past-{jobs.VERSION}-000000000.npz') as g:assert g['a'].tolist()==[0,1,2,3,4]
    assert not list(path.glob('*.tmp'))

def test_chunk_start_state_restores_exactly():
    a=simulation(-5.);state=jobs.snapshot_state(a);b=simulation(0.);b.particles[1].x=9.
    jobs.restore_state(b,state);assert b.t==-5. and b.particles[1].x==a.particles[1].x
