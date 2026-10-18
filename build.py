#!/usr/bin/env python3
"""Catalogo RaiPlay / RSI Play / LA7 Cinema -> index.html (rieseguibile ogni giorno)."""
import json, re, os, gzip, pickle, time, html, unicodedata, datetime, urllib.request
from concurrent.futures import ThreadPoolExecutor
D = os.path.dirname(os.path.abspath(__file__)); IM = os.path.join(D, 'imdb')
UA = {'User-Agent': 'Mozilla/5.0'}
EXCL = re.compile(r'sentiment|romant|love|bambin|kids|junior|ragazzi|animazion|famiglia|family|azione|action|reality', re.I)
CLOU_VOTES = 50000

def get(url, tries=3):
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r:
                return json.loads(r.read().decode('utf-8'))
        except Exception as e:
            if i == tries - 1: print('ERR', url, e); return None
            time.sleep(2)

def pmap(f, xs, n=16):
    with ThreadPoolExecutor(n) as ex: return list(ex.map(f, xs))

def norm(s):
    s = unicodedata.normalize('NFKD', s or '').encode('ascii', 'ignore').decode().lower()
    return re.sub(r'[^a-z0-9]+', ' ', s).strip()

# ---------------- RaiPlay ----------------
RAI = 'https://www.raiplay.it'
def rai_genre_pages(tipologia):
    d = get(f'{RAI}/tipologia/{tipologia}/index.json'); gens = []; blocks = {}
    # RaiPlay a volte restituisce una risposta vuota/non JSON: non deve bloccare
    # l'intera compilazione del catalogo.
    if not isinstance(d, dict) or not isinstance(d.get('contents'), list):
        raise RuntimeError(f'Indice RaiPlay non disponibile o non valido: {tipologia}')
    for b in d['contents']:
        if 'Generi' in b.get('type', '') or b['name'].startswith('Generi'):
            gens = [(c['name'], c['path_id']) for c in b['contents']]
        elif b.get('contents'):
            blocks[b['name']] = [c.get('path_id') for c in b['contents']]
    return gens, blocks

def rai_section(tipologia, plat_label):
    gens, blocks = rai_genre_pages(tipologia); items = {}
    for gname, path in gens:
        g = get(RAI + path)
        if not g: continue
        for letter, lst in g['contents'].items():
            for it in lst:
                p = it['path_id']
                e = items.setdefault(p, {'title': it['name'], 'url': RAI + it['weblink'], 'desc': it.get('vanity', ''),
                    'genres': set(), 'info': it.get('info_url'), 'img': it.get('images', {}).get('landscape', '')})
                if gname not in ('Tutti',): e['genres'].add(gname)
    popular = set()
    for bn, ps in blocks.items():
        if re.search(r'top 10|più visti|più viste', bn, re.I): popular |= set(ps)
    novita = set(blocks.get('Novità', []))
    def info(kv):
        p, e = kv
        d = get(RAI + e['info']) if e['info'] else None
        if d:
            det = {x['key']: x.get('value') for x in d.get('details', []) if x.get('type') == 'label'}
            e['year'] = det.get('year'); e['label'] = d.get('label', '') or ''
            e['desc'] = d.get('description') or e['desc']
        m = re.search(r'/dl/img/(\d{4})/(\d\d)/(\d\d)/', e['img'])
        e['added'] = '-'.join(m.groups()) if m else ''
        return e
    out = []
    for p, e in zip(items, pmap(info, list(items.items()))):
        out.append({'platform': plat_label, 'title': e['title'], 'year': e.get('year'), 'genres': sorted(e['genres']),
            'url': e['url'], 'desc': e['desc'], 'added': e['added'],
            'prima': bool(re.search(r'prima visione|in esclusiva|novit', e.get('label', ''), re.I)) or p in novita,
            'popular': p in popular, 'label': e.get('label', '')})
    return out

# ---------------- LA7 Cinema ----------------
L7 = 'https://www.la7.it'
def gethtml(url):
    for i in range(5):
        time.sleep(1.5)  # la7.it risponde 429 se le richieste sono troppo ravvicinate
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r: return r.read().decode('utf-8', 'ignore')
        except Exception as e:
            if i == 4: print('ERR', url, e); return ''
            time.sleep(10 * (i + 1))

def la7():
    links = []
    for p in range(0, 30):
        h = gethtml(f'{L7}/la7-cinema-tutti-i-film/rivedila7' + (f'?page={p}' if p else ''))
        new = [l for l in dict.fromkeys(re.findall(r'href="(/la7-cinema-tutti-i-film/rivedila7/[^"?#]+)"', h)) if l not in links]
        if not new: break
        links += new
    def det(path):
        h = gethtml(L7 + path)
        if not h:  # dettaglio non disponibile: titolo dallo slug
            t = re.sub(r'-\d\d-\d\d-\d{4}-\d+$', '', path.rsplit('/', 1)[-1]).replace('-', ' ').capitalize()
            return {'platform': 'LA7 Cinema', 'title': t, 'year': '', 'genres': [], 'url': L7 + path, 'desc': '',
                    'added': '', 'prima': False, 'popular': False, 'label': ''}
        meta = lambda k: html.unescape((re.search(r'<meta (?:property|name)="%s" content="([^"]*)"' % k, h) or [None, ''])[1])
        t = meta('og:title').split('|'); d = meta('og:description')
        title = t[0].strip() or path
        gm = re.match(r'\s*Film\s*\(([^)]*)\)', d); ym = re.search(r'\((?:[^()]*\s)?(\d{4})\)', d)
        genres = gm.group(1).split() if gm else ([t[1].strip()] if len(t) > 2 else [])
        um = re.search(r'"uploadDate":\s*"(\d{4}-\d\d-\d\d)', h)
        return {'platform': 'LA7 Cinema', 'title': title, 'year': ym.group(1) if ym else '', 'genres': genres,
                'url': L7 + path, 'desc': re.sub(r'^Film \([^)]*\)\s*', '', d)[:300], 'added': um.group(1) if um else '',
                'prima': bool(re.search(r'prima visione', h[:200000], re.I) and re.search(r'prima visione', d + t[0], re.I)),
                'popular': False, 'label': ''}
    out = {}
    for e in map(det, links):
        if e: out.setdefault((norm(e['title']), e['year']), e)  # stesso film, repliche diverse
    return list(out.values())

# ---------------- RSI ----------------
IL = 'https://il.srgssr.ch/integrationlayer/2.0/rsi'
def rsi():
    tl = get(f'{IL}/topicList/tv')['topicList']; out = {}
    for t in tl:
        if t['title'] not in ('Film', 'Serie TV'): continue
        for s in t.get('subTopicList', []):
            tid = s['urn'].split(':')[-1]; url = f'{IL}/mediaList/video/latestByTopic/{tid}?pageSize=100'; n = 0
            while url and n < 10:
                d = get(url); n += 1
                if not d: break
                for m in d.get('mediaList', []):
                    desc = m.get('description', '') or ''
                    if t['title'] == 'Film':
                        key = m['urn']; title = m['title']; link = f'https://www.rsi.ch/play/tv/redirect/detail/{m["id"]}'
                    else:
                        sh = m.get('show', {}); key = sh.get('urn', m['urn']); title = sh.get('title', m['title'])
                        link = f'https://www.rsi.ch/play/tv/redirect/show/{key.split(":")[-1]}'
                    ym = re.search(r'Anno:.*?(\d{4})', desc); om = re.search(r'Titolo originale:\s*(.+)', desc)
                    e = out.setdefault(key, {'platform': 'RSI ' + t['title'], 'title': title, 'year': ym.group(1) if ym else '',
                        'orig': om.group(1).strip() if om else '', 'genres': set(), 'url': link,
                        'desc': m.get('lead') or desc[:300], 'added': (m.get('date') or '')[:10],
                        'prima': bool(re.search(r'prima visione', desc + m.get('lead', ''), re.I)), 'popular': False, 'label': ''})
                    e['genres'].add(s['title'].replace('Serie TV ', '').replace('Serie Tv ', ''))
                    e['added'] = max(e['added'], (m.get('date') or '')[:10])
                url = d.get('next')
    for e in out.values(): e['genres'] = sorted(e['genres'])
    return list(out.values())

def rsi_seen(items, days=10):
    """AGGIUNTI: data di prima comparsa per titolo, salvata in rsi_seen.json (branch 'data')."""
    p = os.path.join(D, 'rsi_seen.json'); today = datetime.date.today()
    lim = (today - datetime.timedelta(days=days)).isoformat()
    seeding = not os.path.exists(p); seen = {} if seeding else json.load(open(p))
    for e in items:
        k = e['url']
        if k not in seen:
            # primo avvio: data pubblicazione RSI se recente, altrimenti "vecchio"
            seen[k] = (e['added'] if e['added'] > lim else (today - datetime.timedelta(days=days + 1)).isoformat()) if seeding else today.isoformat()
        e['seen'] = seen[k]; e['prima'] = seen[k] > lim
    json.dump(seen, open(p, 'w'), indent=0, sort_keys=True)

# ---------------- IMDb ----------------
def imdb_index():
    pk = os.path.join(IM, 'index.pkl'); r = os.path.join(IM, 'title.ratings.tsv.gz')
    if os.path.exists(pk) and os.path.getmtime(pk) > os.path.getmtime(r): return pickle.load(open(pk, 'rb'))
    ratings = {}
    with gzip.open(r, 'rt') as f:
        next(f)
        for l in f:
            a = l.rstrip('\n').split('\t'); ratings[a[0]] = (float(a[1]), int(a[2]))
    idx = {}; years = {}
    types = {'movie', 'tvMovie', 'tvSeries', 'tvMiniSeries'}
    def add(t, k, y):
        if t in ratings: idx.setdefault(k, []).append((y, t))
    with gzip.open(os.path.join(IM, 'title.basics.tsv.gz'), 'rt') as f:
        next(f)
        for l in f:
            a = l.split('\t')
            if a[1] in types and a[0] in ratings:
                y = int(a[5]) if a[5].isdigit() else 0; years[a[0]] = y
                add(a[0], norm(a[2]), y)
                if a[3] != a[2]: add(a[0], norm(a[3]), y)
    with gzip.open(os.path.join(IM, 'title.akas.tsv.gz'), 'rt') as f:
        next(f)
        for l in f:
            a = l.split('\t')
            if a[3] in ('IT', 'CH') and a[0] in years: add(a[0], norm(a[2]), years[a[0]])
    res = (idx, ratings); pickle.dump(res, open(pk, 'wb')); return res

def enrich(items, idx, ratings):
    hit = 0
    for e in items:
        if e.get('rating'): hit += 1; continue
        y = int(e['year']) if str(e.get('year') or '').isdigit() else None
        cands = []
        for t in (e['title'], e.get('orig', ''), re.sub(r'\s*[-–(].*$', '', e['title'])):
            if t: cands += idx.get(norm(t), [])
        best = None
        if y: c = [x for x in cands if abs(x[0] - y) <= 1]
        else: c = [] if len(set(cands)) != 1 else cands
        if not c and 'Serie' in e['platform'] and len({x[1] for x in cands}) == 1: c = cands
        if c: best = max(set(c), key=lambda x: ratings[x[1]][1])
        if best:
            e['rating'], e['votes'] = ratings[best[1]]; e['tconst'] = best[1]; e['imdb'] = 'https://www.imdb.com/title/' + best[1] + '/'; hit += 1
    return hit

# ---------------- HTML ----------------
def page(sections, teche, stats):
    data = json.dumps({'sections': sections, 'teche': teche}, ensure_ascii=False).replace('</', '<\\/')
    now = datetime.datetime.now(__import__('zoneinfo').ZoneInfo('Europe/Rome')).strftime('%d/%m/%Y %H:%M')
    return open(os.path.join(D, 'template.html'), encoding='utf-8').read().replace('__DATA__', data).replace('__NOW__', now).replace('__STATS__', html.escape(stats))

def main():
    t0 = time.time(); S = {}

    # Recupera l'ultimo catalogo pubblicato (Pages): se RaiPlay è temporaneamente
    # irraggiungibile, conserva i dati precedenti invece di svuotare le sezioni.
    previous = None
    for old_path in (os.path.join(D, 'catalogo.json'),
                     'https://edbass1.github.io/catalogo-streaming/catalogo.json'):
        try:
            if old_path.startswith('http'):
                previous = get(old_path, tries=1)
            elif os.path.exists(old_path):
                with open(old_path, encoding='utf-8') as old_file:
                    previous = json.load(old_file)
            if isinstance(previous, dict) and isinstance(previous.get('sections'), dict):
                break
            previous = None
        except Exception as e:
            print('WARN impossibile leggere il catalogo precedente:', e)
            previous = None

    def rai_safe(tipologia, plat_label):
        try:
            return rai_section(tipologia, plat_label)
        except Exception as e:
            old_items = []
            if previous:
                for section in previous.get('sections', {}).values():
                    if isinstance(section, list):
                        old_items.extend(x for x in section
                                         if isinstance(x, dict) and x.get('platform') == plat_label)
            if old_items:
                print(f'WARN {plat_label}: RaiPlay non disponibile ({e}); mantengo {len(old_items)} elementi precedenti')
                return old_items
            print(f'WARN {plat_label}: RaiPlay non disponibile ({e}); nessun dato precedente recuperabile')
            return []

    S['RaiPlay'] = rai_safe('film', 'RaiPlay Film') + rai_safe('serieitaliane', 'RaiPlay Serie italiane')
    teche = rai_safe('techerai', 'Teche Rai')
    S['RSI Play'] = rsi(); rsi_seen(S['RSI Play'])
    S['LA7 Cinema'] = la7()
    def eps(e):
        d = get(e['url'] + '.json', tries=2) or {}
        e['episodes'] = sum((st.get('episode_size') or {}).get('number') or 0 for b in d.get('blocks', []) for st in b.get('sets', []))
    pmap(eps, teche)
    S['Teche Rai'] = teche
    print('Teche box set (>1 episodio):', sum(e['episodes'] > 1 for e in teche))
    idx, ratings = imdb_index()
    stats = []
    for k, v in S.items():
        tot = len(v); h = enrich(v, idx, ratings)
        for e in v:
            e['type'] = 'teche' if k == 'Teche Rai' else ('serie' if 'Serie' in e['platform'] else 'film')
            e['excluded'] = any(EXCL.search(g) for g in e['genres'])
            e['clou'] = (e.get('votes') or 0) >= CLOU_VOTES or (e['popular'] and (e.get('rating') or 0) >= 6.5)
        stats.append(f'{k}: {tot} titoli, {h} con voto IMDb, {sum(e["excluded"] for e in v)} esclusi per genere, '
                     f'{sum(e["prima"] for e in v)} prime visioni/novità, {sum(e["clou"] and not e["excluded"] for e in v)} Il Clou')
    teche.sort(key=lambda e: e['added'], reverse=True)
    for k, v in S.items():
        f = sum(e['type'] == 'film' for e in v); print(f'{k}: {f} film, {len(v) - f} serie')
    s = ' | '.join(stats); print(s)
    open(os.path.join(D, 'index.html'), 'w', encoding='utf-8').write(page(S, [], s))
    json.dump({'sections': S}, open(os.path.join(D, 'catalogo.json'), 'w'), ensure_ascii=False)
    print('ok in %.0fs' % (time.time() - t0))
main()
