"""Sanskrit names for stars, the Sun, Moon and planets.

Two sources, both names only (positions, brightness and motion still come from the catalog):
  data/catalogs/sanskrit_star_names.json   names given in books/mahabharat_histroy.pdf (Oak 2011), plus stars the book
                                           mentions in English only; every book star is within the common star limit (catalog.STAR_LIMIT)
  data/catalogs/classical_star_names.json  classical names (Sūrya Siddhānta, Bṛhat Saṃhitā) for stars the book does not name
Each name carries its basis ('book' or 'classical') and source. See those files for limitations.
"""
from .paths import DATA
import json, threading, unicodedata

def fold(text):
    """Case-, accent- and punctuation-insensitive form so 'Rohiṇī', 'rohini' and 'Mriga-shirshya' all match."""
    decomposed=unicodedata.normalize('NFKD',text.lower())
    # Latin accents have a non-zero combining class and are dropped; Devanagari vowel signs (class 0, category M*) are kept.
    return ''.join(c for c in decomposed if not unicodedata.combining(c) and (c.isalnum() or unicodedata.category(c) in ('Mc','Mn')))

# Spelling-tolerant key, used only after an exact folded match fails. Latin: drop aspiration (sh/kh/th...), long vowels
# (aa/ee/oo) and the r/ri ambiguity of ṛ (Krittika = Kṛttikā), w = v. Devanagari: long vowel signs = short ones,
# candrabindu = anusvara, nukta dropped. Both: doubled letters collapse (त्त typed as त, Moola = Mula after oo -> u).
_LATIN=[('sh','s'),('ch','c'),('kh','k'),('gh','g'),('jh','j'),('th','t'),('dh','d'),('ph','p'),('bh','b'),('aa','a'),('ee','i'),('oo','u'),('ri','r'),('w','v'),('y','i')]
_DEVANAGARI=str.maketrans({'ी':'ि','ू':'ु','ॄ':'ृ','ँ':'ं','़':None,'ॅ':'े','ॉ':'ो'})
def loose(text):
    s=fold(text).translate(_DEVANAGARI)
    for a,b in _LATIN:s=s.replace(a,b)
    out=[]
    for c in s:
        if not out or out[-1]!=c:out.append(c)
    return ''.join(out)

class SanskritNames:
    def __init__(self):
        self.stamp=None;self.by_id={};self.classical={};self.alternatives={};self.bodies={};self.mentioned={};self.overrides={}
        self.search_keys={};self.loose_keys={};self.lock=threading.RLock()
    def load(self):
        book=DATA/'catalogs/sanskrit_star_names.json';classical=DATA/'catalogs/classical_star_names.json'
        with self.lock:
            stamp=tuple(p.stat().st_mtime_ns if p.exists() else 0 for p in (book,classical))
            if stamp==self.stamp:return
            data=json.loads(book.read_text()) if book.exists() else {}
            extra=json.loads(classical.read_text()) if classical.exists() else {}
            self.by_id={e['id']:e for e in data.get('stars',[])};self.mentioned={e['id']:e for e in data.get('mentioned',[])}
            self.overrides=data.get('english_overrides',{});self.bodies={e['id']:e for e in data.get('bodies',[])}
            self.classical={e['id']:e for e in extra.get('stars',[]) if e['id'] not in self.by_id}
            self.alternatives={e['id']:e for e in extra.get('alternatives',[])}
            keys={}
            for i,e in self.by_id.items():keys[i]=[e['sanskrit'],e['devanagari'],e['book_spelling'],e['english'],e['catalog_name'],*e['aliases']]
            for i,e in self.classical.items():keys[i]=[e['sanskrit'],e['devanagari'],*[x for a in e['alternatives'] for x in (a['sanskrit'],a['devanagari'])]]
            for i,e in self.alternatives.items():keys.setdefault(i,[]).extend(x for a in e['alternatives'] for x in (a['sanskrit'],a['devanagari']))
            for i,e in self.bodies.items():keys[i]=[e['sanskrit'],e['devanagari'],e['book_spelling'],*e['aliases']]
            self.search_keys={i:[fold(x) for x in v if x] for i,v in keys.items()}
            self.loose_keys={i:[loose(k) for k in v] for i,v in self.search_keys.items()}
            self.stamp=stamp
    def book_ids(self):
        """Catalog IDs of every star the book names (Sanskrit or English only)."""
        self.load();return set(self.by_id)|set(self.mentioned)
    def english(self,star_id,catalog_name,refresh=True):
        if refresh:self.load()
        e=self.by_id.get(star_id)
        return e['english'] if e else self.overrides.get(star_id,catalog_name)
    def fields(self,star_id,catalog_name,detail=True,refresh=True):
        """Display fields for one star. `name` is always the English label; per-frame results carry only what labels need."""
        if refresh:self.load()
        name=self.english(star_id,catalog_name,refresh=False);e=self.by_id.get(star_id);c=self.classical.get(star_id);m=self.mentioned.get(star_id)
        alt=self.alternatives.get(star_id)
        if e:
            out=dict(name=name,sanskrit_name=e['sanskrit'],sanskrit_devanagari=e['devanagari'],book_star=True)
            if detail:
                out.update(sanskrit_basis='book',sanskrit_role=e['role'],sanskrit_deity=e['deity'] or None,sanskrit_book_star=e['book_modern_star'],sanskrit_note=e['note'],sanskrit_source='Oak (2011), PDF pp. '+e['book_pdf_pages'])
                if alt:out.update(sanskrit_alternatives=alt['alternatives'],sanskrit_alternative_source=alt['source'],sanskrit_alternative_note=alt['note'])
            return out
        if c:
            out=dict(name=name,sanskrit_name=c['sanskrit'],sanskrit_devanagari=c['devanagari'])
            if star_id in self.mentioned:out['book_star']=True
            if detail:out.update(sanskrit_basis='classical',sanskrit_note=c['note'],sanskrit_source=c['source'],sanskrit_source_url=c['source_url'],sanskrit_alternatives=c['alternatives'])
            return out
        if m:
            out=dict(name=name,book_star=True)
            if detail:out.update(book_note=m['note'],sanskrit_source='Oak (2011), PDF pp. '+m['book_pdf_pages'])
            return out
        return dict(name=name)
    def body_fields(self,body_id):
        """Sanskrit fields for the Sun, Moon or a planet (only eleven bodies, so details always ride along)."""
        self.load();e=self.bodies.get(body_id)
        if not e:return {}
        return dict(sanskrit_name=e['sanskrit'],sanskrit_devanagari=e['devanagari'],sanskrit_role='Sanskrit name: '+e['basis'],sanskrit_note=e['note'],
            sanskrit_basis=e['basis'],sanskrit_source=('Oak (2011), PDF pp. ' if e['basis']!='modern convention' else 'Not in Oak (2011); context PDF pp. ')+e['book_pdf_pages'])
    def named_ids(self):
        """Stars with any Sanskrit name (book or classical)."""
        self.load();return set(self.by_id)|set(self.classical)
    def matches(self,star_id,query):
        """True if the query is part of any Sanskrit name, spelling, alias or English label of this star or body."""
        self.load();q=fold(query)
        if not q:return False
        if any(q in k for k in self.search_keys.get(star_id,[])):return True
        # Spelling variants need at least 3 characters so short fragments do not match everything.
        lq=loose(query);return len(lq)>=3 and any(lq in k for k in self.loose_keys.get(star_id,[]))
    def count(self):self.load();return len(self.by_id)+len(self.classical)

SANSKRIT=SanskritNames()
