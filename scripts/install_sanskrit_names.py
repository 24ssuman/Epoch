"""Write data/catalogs/sanskrit_star_names.json and check it against the installed star catalog.

Naming source: Nilesh N. Oak, "When Did the Mahabharata War Happen? The Mystery of Arundhati" (2011),
books/mahabharat_histroy.pdf. Table 3 (PDF p.215) lists the 28 nakshatras with their Yoga Tara; the text
names Arundhati, Vasistha, Atreya and Dhruva. The book is a naming source only. Nothing here asserts a
historical date or validates the book's astronomical claims.
"""
import sys,json,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from backend.paths import DATA

BOOK='Oak, N. N. (2011), When Did the Mahabharata War Happen? The Mystery of Arundhati; books/mahabharat_histroy.pdf'
# hip, book spelling, IAST, Devanagari, role, deity (book Table 3), book's modern star, English display name, search aliases, PDF pages, note
R=[
 ('37826','Punarvasu','Punarvasu','पुनर्वसु','nakshatra 1 of 28','Aditi','Pollux',None,[],'215, 110','Book also discusses Castor as the second of the "two Punarvasus" (p.110); only Pollux, the Table 3 Yoga Tara, is named here.'),
 ('40526','Pushya','Puṣya','पुष्य','nakshatra','Brihaspati','Altarf',None,['Altarf','Al Tarf','Tishya'],'215','Book Yoga Tara is Altarf (beta Cancri; catalog name Tarf). Other traditions use delta Cancri.'),
 ('43813','Ashlesha','Āśleṣā','आश्लेषा','nakshatra','Nagas/Sarpa','zeta Hydrae','Zet Hya',['Aslesha'],'215','Book Table 3 gives zeta Hydrae. The catalog star proper-named "Ashlesha" (IAU) is epsilon Hydrae, a different star; it is shown as Eps Hya in English mode to avoid two stars with one name.'),
 ('49669','Magha','Maghā','मघा','nakshatra','Pitarah','Regulus',None,['Magha'],'215',None),
 ('54872','Purva Phalguni','Pūrvaphalgunī','पूर्वफल्गुनी','nakshatra','Aryaman (Bhaga)','Zosma',None,['Purva-Phalguni','Purvaphalguni'],'215',None),
 ('57632','Uttara Phalguni','Uttaraphalgunī','उत्तरफल्गुनी','nakshatra','Bhaga (Aryaman)','Denebola',None,['Uttara-Phalguni','Uttaraphalguni'],'215',None),
 ('60965','Hasta','Hasta','हस्त','nakshatra','Savitar (Sun?)','Algorab',None,[],'215, 83',None),
 ('65474','Chitra','Citrā','चित्रा','nakshatra','Twastra (Indra)','Spica',None,['Citra'],'215, 47',None),
 ('69673','Swati','Svātī','स्वाती','nakshatra','Vayu','Arcturus',None,['Svati'],'47, 57','Discrepancy inside the book: the text (pp.47, 57) says Swati is Arcturus; Table 3 lists "Zeta Bootis" (catalog hip:71795, Zet Boo). Arcturus is used because the text repeats it; Zet Boo is not labelled.'),
 ('74785','Vishakha','Viśākhā','विशाखा','nakshatra','Indragni','Zubeneschamali',None,['Visakha'],'215, 83',None),
 ('78401','Anuradha','Anurādhā','अनुराधा','nakshatra','Mitra','Dschubba',None,['Maitri'],'215',None),
 ('80763','Jyeshtha','Jyeṣṭhā','ज्येष्ठा','nakshatra','Indra (Varuna)','Antares',None,['Jyestha'],'215, 47',None),
 ('85927','Moola','Mūla','मूल','nakshatra','Pitarah (Nirriti)','Shaula',None,['Mula'],'215, 83',None),
 ('90185','Purva Ashadha','Pūrvāṣāḍhā','पूर्वाषाढा','nakshatra','Apah','Kaus Australis',None,['Purva-Ashadha','Purvashadha'],'215',None),
 ('92855','Uttara Ashadha','Uttarāṣāḍhā','उत्तराषाढा','nakshatra','Visve Devah','Nunki',None,['Uttara-Ashadha','Uttarashadha'],'215',None),
 ('97649','Shravana','Śravaṇa','श्रवण','nakshatra','Vishnu','Altair',None,['Sravana'],'215, 47',None),
 ('91262','Abhijit','Abhijit','अभिजित्','nakshatra (28th, listed between Uttara Ashadha and Shravana)','Brahma','Vega',None,['Abhijita','Brahmarashi'],'215, 47, 49',None),
 ('101958','Dhanishtha','Dhaniṣṭhā','धनिष्ठा','nakshatra','Vasavah','Sualocin',None,['Dhanistha','Shravishtha'],'215, 47',None),
 ('109074','Shatabhisaj','Śatabhiṣaj','शतभिषज्','nakshatra','Indra (Varuna)','Sadalmelik',None,['Shatabhisha','Shatataraka','Satabhisha'],'215, 86','Book marks the identification with "?" in Table 3.'),
 ('113963','Purva Bhadrapada','Pūrvabhādrapadā','पूर्वभाद्रपदा','nakshatra','Aja Ekapad','Markab',None,['Purva-Bhadrapada','Purva Proshthapada'],'215',None),
 ('1067','Uttara Bhadrapada','Uttarabhādrapadā','उत्तरभाद्रपदा','nakshatra','Ahir-Budhyna','Algenib',None,['Uttara-Bhadrapada','Uttara Proshthapada'],'215',None),
 ('7097','Revati','Revatī','रेवती','nakshatra','Pusan','Kullat Nunu',None,['Kullat Nunu','Alpherg'],'215','Kullat Nunu is the traditional name of eta Piscium (catalog name Alpherg). The catalog star proper-named "Revati" (IAU) is zeta Piscium, magnitude 5.2, a different star and fainter than the 4.5 limit; it is shown as Zet Psc in English mode.'),
 ('9884','Ashwini','Aśvinī','अश्विनी','nakshatra','Asvinau','Hamal',None,['Ashvini'],'215',None),
 ('13209','Bharani','Bharaṇī','भरणी','nakshatra','Yama','41 Arietis','41 Ari',[],'215','The catalog already proper-names this star "Bharani" (IAU Sanskrit-derived name); English mode shows 41 Ari so the toggle changes the label.'),
 ('17702','Krittika','Kṛttikā','कृत्तिका','nakshatra','Agni','Pleiades',None,['Krittika','Pleiades'],'215, 47, 49','The nakshatra is the whole Pleiades cluster. Only the brightest member, Alcyone, is labelled; the book gives no Sanskrit names for the other members.'),
 ('21421','Rohini','Rohiṇī','रोहिणी','nakshatra','Prajapati','Aldebaran',None,[],'215, 47',None),
 ('25336','Mrigashirsha','Mṛgaśirā','मृगशिरा','nakshatra','Soma','Bellatrix',None,['Mriga-shirshya','Mrigashira','Mrigashirshya'],'215',None),
 ('27989','Ardra','Ārdrā','आर्द्रा','nakshatra','Rudra','Betelgeuse',None,['Aardra'],'215',None),
 ('65477','Arundhati','Arundhatī','अरुन्धती','Saptarshi companion star','','Alcor',None,[],'47, 60',"The book's central star (the 'Arundhati' of the title)."),
 ('65378','Vasistha','Vasiṣṭha','वसिष्ठ','Saptarshi (Ursa Major) star','','Mizar',None,['Vasishtha'],'47, 60',None),
 ('67301','Atreya','Ātreya','आत्रेय','Saptarshi (Ursa Major) star','','Alkaid',None,[],'62','Low confidence: cited on p.62 as another researcher\'s conjecture ("Atreya (Alkaid)"), not a settled identification.'),
 ('11767','Dhruva','Dhruva','ध्रुव','pole star','','Polaris',None,['Pole Star'],'63, 31','Dhruva names whichever star is the pole star. Polaris is the pole star only near the present; the book itself lists other pole stars across 26,000 years (p.32).'),
 ('36850','Punarvasu','Punarvasu','पुनर्वसु','second star of the Punarvasu pair','Aditi','Castor',None,['Punarvasus'],'110, 111','The book says Pollux and Castor together are the "two Punarvasus" (p.110); Pollux is the Table 3 Yoga Tara.'),
]
# Other Pleiades members: the book identifies Krittika with the Pleiades, "seven-headed" (pp.47, 49, 52), without naming members.
# Several are fainter than the 4.5 prominent-star limit; book stars are always shown.
for hip,english in [('17499','Electra'),('17531','Taygeta'),('17573','Maia'),('17608','Merope'),('17847','Atlas'),('17489','Celaeno'),('17579','Asterope'),('17851','Pleione')]:
    R.append((hip,'Krittika','Kṛttikā','कृत्तिका','member of the Krittika (Pleiades) cluster','Agni','Pleiades',None,['Krittika','Pleiades'],'47, 49, 52',f'{english} is a Pleiades member; the book names the cluster, not individual members.'))
# Stars the book names only in English (no Sanskrit name given). Shown regardless of brightness; labelled in English in both modes.
MENTIONED=[
 ('71795','Listed in Table 3 (p.215) as the Yoga Tara of Swati; the book text uses Arcturus instead.','215'),
 ('62956','Saptarshi star; used with Megrez as a reference line for Vasistha (p.62).','62'),
 ('59774','Saptarshi star; used with Alioth as a reference line for Vasistha (p.62).','62'),
 ('37279','Conjectured as one of five stars around the Moon near Punarvasu (p.111).','110, 111'),
 ('36188','Conjectured as one of five stars around the Moon near Punarvasu (p.111).','110, 111'),
 ('31681','Conjectured as one of five stars around the Moon near Punarvasu (p.111).','111'),
 ('116727','Named as the pole star around 4000 CE (p.31).','31'),
 ('72607','On the path of the north celestial pole (p.32).','32'),
 ('61281','On the path of the north celestial pole (p.32).','32'),
 ('68756','On the path of the north celestial pole (p.32).','32'),
 ('75458','On the path of the north celestial pole (p.32).','32'),
 ('79992','On the path of the north celestial pole (p.32).','32'),
 ('102098','On the path of the north celestial pole (p.32).','32'),
]
# Sun, Moon and planets. basis: 'book' = named directly; 'book (implied)' = only through an epithet such as Suryaputra;
# 'book (conjecture)' = an identification the book reports as conjecture; 'modern convention' = not in the book at all.
BODIES=[
 ('Sun','Sūrya','सूर्य','Surya',['Aditya','Ravi','Bhanu'],'book (implied)','46, 233','Implied by Saturn\'s epithet Suryaputra, "son of Surya" (p.46); the quoted verses also call the Sun Aditya and Bhanuman (p.233).'),
 ('Moon','Candra','चन्द्र','Chandra',['Chandra','Soma','Chandramas'],'book (implied)','41, 46, 131','The book uses Chandra (Chandra Kala, p.41; Chandramas, p.131) and Soma through Mercury\'s epithet Somaputra, "son of the Moon" (p.46).'),
 ('Mercury','Budha','बुध','Budha',['Somaputra','Shashijena','Shashijen'],'book','46, 80, 97',None),
 ('Venus','Śukra','शुक्र','Shukra',['Bhrigusoon','Bhrugusoon'],'book','46, 80',None),
 ('Earth','Pṛthivī','पृथिवी','pRthivI',['Prithivi','Prthivi','Prithvi','Pṛthvī','पृथ्वी','Dharā','धरा','Dhara','Bhumi','भूमि'],'book','274, 275, 46','Pṛthivī is the spelling in the Mahābhārata verses the book quotes (Śalya CE 55.10 "cakampe ca mahākampaṃ pṛthivī", PDF p.274; CE 57.46-56 "cacāla pṛthivī", p.275); Pṛthvī is the later contracted form. Dharā is implied by Mars\'s epithet Dharaputra (p.46).'),
 ('Mars','Maṅgala','मङ्गल','Mangal',['Mangala','Angaraka','Angarakha','Lohitanga','Dharaputra','Parusha graha'],'book','46, 80',None),
 ('Jupiter','Bṛhaspati','बृहस्पति','Brhaspati',['Brihaspati','Guru'],'book','46, 94',None),
 ('Saturn','Śani','शनि','Shani',['Shanischar','Sanaishchara','Shanaishchara','Suryaputra'],'book','46, 94',None),
 ('Uranus','Aruṇa','अरुण','Arun',['Aruna','Harshal'],'modern convention','46, 168','Not from the book. The book says the Mahabharata astronomers knew Uranus but rejects Vartak\'s reading of the "Shweta" planet as Uranus (p.168). Aruna is a modern Indian name.'),
 ('Neptune','Varuṇa','वरुण','Varun',['Varuna'],'modern convention','46, 168','Not from the book. The book rejects Vartak\'s reading of the "Shyama" planet as Neptune (p.168). Varuna is a modern Indian name.'),
 ('Pluto','Tīvra','तीव्र','Tivra',['Tikshna','Yama'],'book (conjecture)','87, 168','Vartak\'s conjecture, which the author accepts: the "Tivra/Tikshna" planet near Krittika is Pluto (pp.87, 168). Tivra means "intense", a description, not a proper name. Modern Indian usage calls Pluto Yama.'),
]
# Catalog stars whose proper name is itself Sanskrit-derived but which are NOT the book's star for that name.
OVERRIDES={'hip:43109':'Eps Hya','hip:5737':'Zet Psc'}

def build():
    stars=json.loads((DATA/'catalogs/stars.json').read_text());by={('hip:'+r['hip']):r for r in stars if r.get('hip')}
    entries=[];report=[]
    for hip,book,iast,deva,role,deity,modern,english,aliases,pages,note in R:
        sid='hip:'+hip;r=by.get(sid)
        if r is None:report.append((sid,book,'MISSING from catalog'));continue
        entries.append(dict(id=sid,hip=hip,sanskrit=iast,devanagari=deva,book_spelling=book,role=role,deity=deity,book_modern_star=modern,
            english=english or r['name'],catalog_name=r['name'],aliases=aliases,book_pdf_pages=pages,note=note,magnitude_catalog=r['mag']))
        report.append((sid,book,f"present as {r['name']} V={r['mag']}"+(' (fainter than 4.5; added as a book star)' if r['mag']>4.5 else '')))
    mentioned=[]
    for hip,note,pages in MENTIONED:
        sid='hip:'+hip;r=by.get(sid)
        if r is None:report.append((sid,'(English only)','MISSING from catalog'));continue
        mentioned.append(dict(id=sid,hip=hip,english=OVERRIDES.get(sid,r['name']),catalog_name=r['name'],book_pdf_pages=pages,note=note,magnitude_catalog=r['mag']))
        report.append((sid,'(English only)',f"present as {r['name']} V={r['mag']}"))
    bodies=[dict(id=b,sanskrit=iast,devanagari=deva,book_spelling=book,aliases=al,basis=basis,book_pdf_pages=pages,note=note) for b,iast,deva,book,al,basis,pages,note in BODIES]
    for b in bodies:report.append((b['id'],b['book_spelling'],b['basis']))
    out=dict(source=BOOK,generated=time.strftime('%Y-%m-%dT%H:%M:%S%z'),frame='Names only; positions come from the ICRS star catalog (HYG 4.1 / Hipparcos)',
        units='magnitude: catalog V at J2000-era epoch',time_scale='not applicable (names)',
        limitations=['Identifications are the book\'s own and are not independently validated here.','Where the book is internally inconsistent or differs from the IAU proper name, the note field says so.','Spellings: book_spelling is as printed; sanskrit is IAST transliteration added for display; Devanagari added for reference.','A Sanskrit name labels a modern star; it does not assert the same star was meant in the Mahabharata era.','Sky labels use Devanagari; IAST is kept for search and reference.'],
        english_overrides=OVERRIDES,stars=entries,mentioned=mentioned,bodies=bodies,
        display_policy='Every star in stars and mentioned is shown at every epoch even when fainter than the 4.5 prominent-star limit.')
    p=DATA/'catalogs/sanskrit_star_names.json';p.write_text(json.dumps(out,ensure_ascii=False,indent=1))
    return report,p

if __name__=='__main__':
    report,p=build()
    for row in report:print(*row,sep=' | ')
    print('wrote',p)
