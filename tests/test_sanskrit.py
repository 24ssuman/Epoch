"""Sanskrit names (book and classical texts), stars named in books/mahabharat_histroy.pdf, the supported date interval,
search, and slim ground frames."""
from fastapi.testclient import TestClient
from backend.app import app
from backend.astrotime import calendar_jd,MIN_YEAR,MAX_YEAR
from backend.catalog import CATALOG
from backend.sanskrit import SANSKRIT,fold,loose
from backend.paths import DATA
import json,pytest

client=TestClient(app)
NAKSHATRAS=['Punarvasu','Pushya','Ashlesha','Magha','Purva Phalguni','Uttara Phalguni','Hasta','Chitra','Swati','Vishakha','Anuradha','Jyeshtha','Moola','Purva Ashadha','Uttara Ashadha','Shravana','Abhijit','Dhanishtha','Shatabhisaj','Purva Bhadrapada','Uttara Bhadrapada','Revati','Ashwini','Bharani','Krittika','Rohini','Mrigashirsha','Ardra']

def entries():return json.loads((DATA/'catalogs/sanskrit_star_names.json').read_text())['stars']

def test_interval_is_15000_bce_to_5000_ce():
    assert (MIN_YEAR,MAX_YEAR)==(-14999,5000)
    assert client.get('/api/snapshot',params={'jd':calendar_jd(-14999)-1,'limit':100}).status_code==422
    assert client.get('/api/snapshot',params={'jd':calendar_jd(5000,12,31)+1.5,'limit':100}).status_code==422
    assert client.get('/api/bootstrap').json()['range']==[calendar_jd(-14999),calendar_jd(5000,12,31)]
    assert client.post('/api/jobs',json={'action':'resume','end_year':-15000}).status_code==422  # 15,001 BCE: rejected, nothing launched

def test_all_book_nakshatras_and_named_stars_are_in_the_catalog():
    CATALOG.load();names={e['book_spelling'] for e in entries()}
    assert set(NAKSHATRAS)<=names and {'Arundhati','Vasistha','Dhruva','Atreya'}<=names
    for e in entries():assert e['id'] in CATALOG.id_index,e
    assert len({e['id'] for e in entries()})==len(entries())  # one star per entry
    assert 'hip:36850' in {e['id'] for e in entries()}  # Castor, the second of the 'two Punarvasus'
    assert {'Alioth','Thuban','Kap Dra','Zet Boo'}<={m['catalog_name'] for m in json.loads((DATA/'catalogs/sanskrit_star_names.json').read_text())['mentioned']}

def test_common_star_limit_includes_faint_book_stars_and_ordinary_stars():
    from backend.catalog import STAR_LIMIT
    assert STAR_LIMIT==5.76
    data=client.get('/api/snapshot',params={'jd':2451545,'limit':9000}).json()
    faint={s['id']:s for s in data['stars'] if s['magnitude']>4.5}
    assert {'hip:17489','hip:17579','hip:17851'}<=set(faint)  # Celaeno, Asterope, Pleione (Krittika members)
    assert sum(not s.get('book_star') for s in faint.values())>2500   # ordinary stars between 4.5 and 5.76 are shown too
    assert max(s['magnitude'] for s in data['stars'])<=5.7605
    detail=client.get('/api/object/hip:17579',params={'jd':2451545}).json()
    assert detail['sanskrit_source'].startswith('Oak (2011)')
    assert faint['hip:17851']['sanskrit_devanagari']=='कृत्तिका'

def test_ground_view_frames_are_slim_and_skip_below_horizon_stars():
    space=client.get('/api/snapshot',params={'jd':2451545,'lat':22.5726,'lon':88.3639,'limit':9000}).json()
    ground=client.get('/api/snapshot',params={'jd':2451545,'lat':22.5726,'lon':88.3639,'limit':9000,'view':'ground','horizon_only':True}).json()
    assert 0<len(ground['stars'])<len(space['stars'])
    assert all(s['ground_direction'][2]>=-0.035 and 'direction' not in s and 'validity_note' not in s for s in ground['stars'])
    assert all('space_direction' in s for s in space['stars'])
    assert ground['star_fields']['time_scale']=='TDB' and ground['stellar_work']['below_horizon_skipped']>0

def test_english_labels_are_unique_and_replace_sanskrit_derived_catalog_names():
    CATALOG.load();english=[SANSKRIT.english(e['id'],e['catalog_name']) for e in entries()]
    assert len(set(english))==len(english)
    assert SANSKRIT.english('hip:13209','Bharani')=='41 Ari'     # IAU Sanskrit-derived name replaced by designation
    assert SANSKRIT.english('hip:43109','Ashlesha')=='Eps Hya'   # IAU "Ashlesha" is not the book's Ashlesha star
    assert SANSKRIT.english('hip:5737','Revati')=='Zet Psc'
    assert SANSKRIT.english('hip:32349','Sirius')=='Sirius'

def classical():return json.loads((DATA/'catalogs/classical_star_names.json').read_text())

def test_classical_names_are_sourced_catalog_stars_without_book_names():
    CATALOG.load();book={e['id'] for e in entries()};data=classical()
    assert len(data['stars'])>=12
    for e in data['stars']:
        assert e['id'] in CATALOG.id_index and e['id'] not in book,e
        assert e['source'] and e['source_url'].startswith('https://') and e['devanagari'] and e['sanskrit'],e
    ids={e['id']:e['sanskrit'] for e in data['stars']}
    assert ids['hip:30438']=='Agastya' and ids['hip:32349']=='Mṛgavyādha' and ids['hip:24608']=='Brahmahṛdaya' and ids['hip:54061']=='Kratu'

def test_snapshot_carries_both_names_and_basis():
    data=client.get('/api/snapshot',params={'jd':2451545,'lat':22.5726,'lon':88.3639,'limit':300}).json()
    stars={s['id']:s for s in data['stars']}
    assert stars['hip:21421']['name']=='Aldebaran' and stars['hip:21421']['sanskrit_name']=='Rohiṇī' and stars['hip:21421']['sanskrit_devanagari']=='रोहिणी'
    assert stars['hip:32349']['name']=='Sirius' and stars['hip:32349']['sanskrit_devanagari']=='मृगव्याध'
    detail=client.get('/api/object/hip:32349',params={'jd':2451545}).json()
    assert detail['sanskrit_basis']=='classical' and 'Burgess' in detail['sanskrit_source'] and detail['sanskrit_alternatives'][0]['sanskrit']=='Lubdhaka'
    alkaid=client.get('/api/object/hip:67301',params={'jd':2451545}).json()
    assert alkaid['sanskrit_name']=='Ātreya' and alkaid['sanskrit_basis']=='book' and alkaid['sanskrit_alternatives'][0]['sanskrit']=='Marīci'
    bodies={b['id']:b for b in data['bodies']}
    assert bodies['Moon']['sanskrit_devanagari']=='चन्द्र' and bodies['Mars']['sanskrit_devanagari']=='मङ्गल'

@pytest.mark.parametrize('query,target',[('Rohini','hip:21421'),('रोहिणी','hip:21421'),('Kritika','hip:17702'),('Moola','hip:85927'),
    ('Agastya','hip:30438'),('अगस्त्य','hip:30438'),('Lubdhaka','hip:32349'),('Mrigavyadha','hip:32349'),('Brahmahridaya','hip:24608'),
    ('Kratu','hip:54061'),('Pulastya','hip:58001'),('Marichi','hip:67301'),('Mangal','Mars'),('मङ्गल','Mars'),('Shani','Saturn')])
def test_search_accepts_sanskrit_names_and_variants(query,target):
    found=client.get('/api/search',params={'q':query,'jd':2451545.}).json()
    assert target in [f['id'] for f in found],(query,[f['name'] for f in found][:5])

def test_fold_and_loose_keys():
    assert fold('Rohiṇī')=='rohini' and loose('Krittika')==loose('Kṛttikā')==loose('Kritika')
    assert loose('Rohini')!=loose('Revati') and not SANSKRIT.matches('hip:21421','zz')

def test_earth_is_prthivi_with_the_books_verse_spelling():
    data=client.get('/api/snapshot',params={'jd':2451545,'limit':100}).json()
    earth=next(b for b in data['bodies'] if b['id']=='Earth')
    assert earth['sanskrit_devanagari']=='पृथिवी' and earth['sanskrit_name']=='Pṛthivī' and earth['sanskrit_basis']=='book'
    assert 'p.274' in earth['sanskrit_note'] or '274' in earth['sanskrit_source']
    for q in ('Prithvi','Prithivi','Pṛthivī','पृथ्वी','पृथिवी','Dhara'):
        assert 'Earth' in [f['id'] for f in client.get('/api/search',params={'q':q}).json()],q
