#!/usr/bin/env python3
"""Catalogo RaiPlay / Rakuten TV / RSI Play -> index.html (rieseguibile ogni giorno)."""
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

# ---------------- Rakuten ----------------
RK = 'https://gizmo.rakuten.tv/v3/lists/{}?classification_id=36&device_identifier=web&locale=it&market_code=it&user_status=visitor&per_page=100&page={}'
def rk_list(lid):
    d = get(RK.format(lid, 1))
    if not d: return []
    # NB: l'API pubblica ignora la paginazione (restituisce sempre i primi 18): si aggregano tutte le liste del garden
    return d['data']['contents']['data']

def rakuten():
    """Catalogo completo: URL dalla sitemap pubblica IT + dettaglio gizmo per ogni titolo; tiene solo quelli AVOD (gratis)."""
    import gzip as gz
    urls = []
    for i in range(1, 10):
        try:
            raw = urllib.request.urlopen(urllib.request.Request(f'https://s3-eu-west-1.amazonaws.com/prod-kuato-static.rakuten.tv/sitemaps/it/sitemap{i}.xml.gz', headers=UA), timeout=60).read()
        except Exception: break
        urls += re.findall(r'<loc>https://www.rakuten.tv/it/(movies|tv_shows)/([^<]+)</loc>', gz.decompress(raw).decode())
    Q = 'classification_id=36&device_identifier=web&locale=it&market_code=it&user_status=visitor'
    def det(t):
        d = (get(f'https://gizmo.rakuten.tv/v3/{t[0]}/{t[1]}?{Q}') or {}).get('data')
        if not d: return None
        kinds = {p.get('kind') for p in (d.get('labels') or {}).get('purchase_types', [])}
        free = 'avod' in kinds or bool((d.get('view_options') or {}).get('public', {}).get('adverts'))
        return d if free else None
    alls = [x for x in pmap(det, sorted(set(urls)), 24) if x]
    recent = {x['id'] for x in rk_list('free-recently-added')}
    pop = {x['id'] for l in ('free-top-movies', 'free-top-tv-shows', 'free-best-of-catalogue') for x in rk_list(l)}
    out = []
    for x in alls:
        sc = next((s for s in x.get('scores') or [] if (s.get('site') or {}).get('name') == 'IMDb'), {})
        kind = x['type']
        out.append({'platform': 'Rakuten TV ' + ('Film' if kind == 'movies' else 'Serie'), 'title': x['title'],
            'year': str(x.get('year') or ''), 'genres': [g['name'] for g in x.get('genres', [])],
            'url': f'https://www.rakuten.tv/it/{kind}/{x["id"]}', 'desc': x.get('short_plot') or (x.get('plot') or '')[:300], 'added': '',
            'prima': x['id'] in recent, 'popular': x['id'] in pop, 'rating': sc.get('score'), 'votes': sc.get('amount_of_votes'),
            'imdb': sc.get('href'), 'orig': x.get('original_title') or '', 'label': ''})
    return out

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
            e['rating'], e['votes'] = ratings[best[1]]; e['imdb'] = 'https://www.imdb.com/title/' + best[1]; hit += 1
    return hit

# ---------------- HTML ----------------
def page(sections, teche, stats):
    data = json.dumps({'sections': sections, 'teche': teche}, ensure_ascii=False).replace('</', '<\\/')
    now = datetime.datetime.now().strftime('%d/%m/%Y %H:%M')
    return open(os.path.join(D, 'template.html'), encoding='utf-8').read().replace('__DATA__', data).replace('__NOW__', now).replace('__STATS__', html.escape(stats))

def main():
    t0 = time.time(); S = {}
    S['RaiPlay'] = rai_section('film', 'RaiPlay Film') + rai_section('serieitaliane', 'RaiPlay Serie italiane')
    teche = rai_section('techerai', 'Teche Rai')
    S['Rakuten TV'] = rakuten()
    S['RSI Play'] = rsi()
    idx, ratings = imdb_index()
    stats = []
    for k, v in S.items():
        tot = len(v); h = enrich(v, idx, ratings)
        for e in v:
            e['excluded'] = any(EXCL.search(g) for g in e['genres'])
            e['clou'] = (e.get('votes') or 0) >= CLOU_VOTES or (e['popular'] and (e.get('rating') or 0) >= 6.5)
        stats.append(f'{k}: {tot} titoli, {h} con voto IMDb, {sum(e["excluded"] for e in v)} esclusi per genere, '
                     f'{sum(e["prima"] for e in v)} prime visioni/novità, {sum(e["clou"] and not e["excluded"] for e in v)} Il Clou')
    teche.sort(key=lambda e: e['added'], reverse=True)
    stats.append(f'Teche Rai: {len(teche)} titoli')
    s = ' | '.join(stats); print(s)
    open(os.path.join(D, 'index.html'), 'w', encoding='utf-8').write(page(S, teche[:150], s))
    json.dump({'sections': S, 'teche': teche}, open(os.path.join(D, 'catalogo.json'), 'w'), ensure_ascii=False)
    print('ok in %.0fs' % (time.time() - t0))
main()
