"""Write data/catalogs/classical_star_names.json: Sanskrit names from classical Indian astronomy for stars the
Mahabharata book (books/mahabharat_histroy.pdf) does not name. Offline; edit the table below, not the JSON.

Only names attested in classical texts with a published star identification are included; most bright stars have none,
and none is invented. Where the book already names a star, the book's name stays primary and the classical name is an
alternative (Alkaid: book Ātreya, Bṛhat Saṃhitā Marīci).

Sources (public domain; local OCR copies under tmp/sanskrit-sources/ when fetched):
  SS   Sūrya Siddhānta ch. VIII vv. 10-12, 20-21, tr. E. Burgess, JAOS 6 (1860) 141-498, notes pp. 356-364
       (identifications after Colebrooke, Asiatic Researches 9). https://archive.org/details/jstor-592174
  BS   Varāhamihira, Bṛhat Saṃhitā ch. 13 vv. 5-6, tr. N. Chidambaram Iyer (1884): the Seven Sages from the east,
       Marīci, Vasiṣṭha, Aṅgiras, Atri, Pulastya, Pulaha, Kratu (= eta ... alpha UMa along the figure); Burgess (1860,
       introduction p. 420) independently identifies Pulastya = gamma and Vasiṣṭha = zeta UMa.
       https://www.wisdomlib.org/hinduism/book/brihat-samhita/d/doc226731.html
"""
import sys,json,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from backend.paths import DATA,ROOT

SS='Sūrya Siddhānta VIII.{v}, tr. Burgess (1860), JAOS 6, p. {p}';SS_URL='https://archive.org/details/jstor-592174'
BS='Bṛhat Saṃhitā 13.5-6 (Varāhamihira), tr. Chidambaram Iyer (1884)';BS_URL='https://www.wisdomlib.org/hinduism/book/brihat-samhita/d/doc226731.html'
# (catalog id, IAST, Devanagari, English, [(alt IAST, alt Devanagari)], source, url, note)
TABLE=[
 ('hip:30438','Agastya','अगस्त्य','Canopus',[],SS.format(v='10',p='356-357'),SS_URL,'Named after the Vedic sage Agastya; its heliacal rising timed rituals.'),
 ('hip:32349','Mṛgavyādha','मृगव्याध','Sirius',[('Lubdhaka','लुब्धक')],SS.format(v='10-11',p='357'),SS_URL,'"Deer-hunter"; also called Lubdhaka, "hunter".'),
 ('hip:25428','Agni','अग्नि','Elnath (β Tau)',[('Hutabhuj','हुतभुज्')],SS.format(v='11-12',p='357'),SS_URL,'The text calls it hutabhuj, "devourer of the sacrifice", an epithet of Agni.'),
 ('hip:24608','Brahmahṛdaya','ब्रह्महृदय','Capella',[],SS.format(v='11-12',p='357'),SS_URL,'"Brahmā\'s heart".'),
 ('hip:28358','Prajāpati','प्रजापति','δ Aur',[('Brahmā','ब्रह्मा')],SS.format(v='20',p='363'),SS_URL,'Burgess: "can hardly be any other than" δ Aurigae; also called Brahmā (SS XIII.9).'),
 ('hip:64238','Apāṃvatsa','अपांवत्स','θ Vir',[],SS.format(v='21',p='363-364'),SS_URL,'"Waters\' child"; Burgess identifies θ Virginis (Colebrooke\'s "nebulous stars b 1,2,3" not found).'),
 ('hip:63090','Āpas','आपस्','Minelauva (δ Vir)',[],SS.format(v='21',p='363'),SS_URL,'"Waters"; identified by Colebrooke with δ Virginis.'),
 ('hip:54061','Kratu','क्रतु','Dubhe',[],BS,BS_URL,'Seventh (westernmost) of the Seven Sages.'),
 ('hip:53910','Pulaha','पुलह','Merak',[],BS,BS_URL,'Sixth of the Seven Sages.'),
 ('hip:58001','Pulastya','पुलस्त्य','Phecda',[],BS,BS_URL,'Fifth of the Seven Sages; Burgess (1860, p. 420) also gives γ UMa.'),
 ('hip:59774','Atri','अत्रि','Megrez',[],BS,BS_URL,'Fourth of the Seven Sages.'),
 ('hip:62956','Aṅgiras','अङ्गिरस्','Alioth',[],BS,BS_URL,'Third of the Seven Sages.'),
]
ALTERNATIVES=[  # stars the book already names: classical name shown as an alternative only
 ('hip:67301',[('Marīci','मरीचि')],BS,BS_URL,'Bṛhat Saṃhitā: easternmost of the Seven Sages, Marīci; the book calls this star Ātreya.'),
]

if __name__=='__main__':
    book=json.loads((DATA/'catalogs/sanskrit_star_names.json').read_text());named={e['id'] for e in book['stars']}
    from backend.catalog import CATALOG
    CATALOG.load()
    out=[]
    for sid,iast,dev,english,alts,source,url,note in TABLE:
        if sid in named:raise SystemExit(f'{sid} already has a book name; list it under ALTERNATIVES')
        if sid not in CATALOG.id_index:raise SystemExit(f'{sid} not in the star catalog')
        out.append(dict(id=sid,sanskrit=iast,devanagari=dev,english=english,alternatives=[dict(sanskrit=a,devanagari=b) for a,b in alts],source=source,source_url=url,note=note))
    alternatives=[dict(id=sid,alternatives=[dict(sanskrit=a,devanagari=b) for a,b in alts],source=source,source_url=url,note=note) for sid,alts,source,url,note in ALTERNATIVES]
    data=dict(source='Classical Indian astronomy (Sūrya Siddhānta, tr. Burgess 1860; Bṛhat Saṃhitā, tr. Chidambaram Iyer 1884); identifications as published there',
        generated=time.strftime('%Y-%m-%dT%H:%M:%S%z'),frame='Names only; positions come from the star catalog',units='none',time_scale='none',
        limitations=['Only stars with a classical name and a published identification are listed; most catalog stars have no attested Sanskrit name.',
                     'Identifications are those of the cited translators (Colebrooke/Burgess; the Seven Sages by their order in the figure); ancient usage may have differed.'],
        stars=out,alternatives=alternatives)
    (DATA/'catalogs/classical_star_names.json').write_text(json.dumps(data,ensure_ascii=False,indent=1))
    with (ROOT/'LOG.md').open('a') as f:f.write(f'\n- {time.strftime("%Y-%m-%d %H:%M:%S %z")}: install_classical_names.py wrote {len(out)} classical Sanskrit star names and {len(alternatives)} alternative to data/catalogs/classical_star_names.json.\n')
    print(len(out),'names,',len(alternatives),'alternatives')
