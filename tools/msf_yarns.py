"""Collects the yarn colours on sale at msf.ru (Семёновская пряжа and the brands it sells) into data/yarns-msf.json.
Polite: one request at a time with a pause; swatch photos are cached and only their average colour is kept."""
import re, html, json, time, subprocess, sys, os, datetime
sys.path.insert(0, os.path.dirname(__file__))
from swatch import skein_colour

BRANDS = {1000: 'Семёновская пряжа', 1002: 'YarnArt', 1003: 'Katia', 1005: 'Alize', 1012: 'Пехорка', 1013: 'Камтекс'}
CACHE = sys.argv[1] if len(sys.argv) > 1 else '/tmp/msf-cache'
OUT = os.path.join(os.path.dirname(__file__), '..', 'data', 'yarns-msf.json')
PAUSE = 1.1
os.makedirs(CACHE, exist_ok=True)

def get(url, out=None):
    for t in range(5):
        r = subprocess.run(['curl', '-sS', '-m', '40', '-A', 'Petelka yarn palette (petelka-knit.github.io)'] + (['-o', out] if out else []) + [url], capture_output=True)
        time.sleep(PAUSE)
        if r.returncode == 0:
            return True if out else r.stdout.decode('utf-8', 'ignore')
        time.sleep(4 + 4 * t)
    return None

def text(s):
    return re.sub(r'\s+', ' ', html.unescape(re.sub('<[^>]+>', ' ', s))).strip()

lines = []
for tm, brand in BRANDS.items():
    s = get(f'https://msf.ru/search/?action=2&id_tm={tm}&per_page_all=1') or ''
    seen = {}
    for pid, t in re.findall(r'href="/catalog/1/(\d+)"[^>]*>(.*?)</a>', s, re.S):
        t = text(t)
        if t and pid not in seen:
            seen[pid] = t
    print(brand, len(seen), flush=True)
    for pid, name in seen.items():
        p = get(f'https://msf.ru/catalog/1/{pid}') or ''
        comp = re.search(r'Состав\s*</?[^>]*>?\s*(.*?)</', p, re.S)
        info = text(p[p.find('Состав'):p.find('Состав') + 400]) if 'Состав' in p else ''
        m_len = re.search(r'Длина в мотке \(м\)\s*([\d.,]+)', info)
        m_w = re.search(r'Вес мотка \(кг\)\s*([\d.,]+)', info)
        m_c = re.search(r'Состав\s*(.*?)\s*Вес мотка', info)
        cols = []
        for src, cname, code in re.findall(r'<img src="(/in/color/[^"]+)".*?class="name">(.*?)</div>.*?articlename">(.*?)</span>', p, re.S):
            f = os.path.join(CACHE, src.split('/')[-1])
            if not os.path.exists(f) or os.path.getsize(f) < 500:
                if not get('https://msf.ru' + src, f):
                    continue
            try:
                r = skein_colour(f)
            except Exception:
                r = None
            if not r:
                continue
            cols.append([text(code), text(cname), r[0]] + ([1] if r[1] else []))
        if cols:
            lines.append({'b': brand, 'n': name, 'id': pid, 'comp': (m_c.group(1).replace('_', ' ') if m_c else ''),
                          'm': float(m_len.group(1).replace(',', '.')) if m_len else None,
                          'g': round(float(m_w.group(1).replace(',', '.')) * 1000) if m_w else None, 'c': cols})
        print(f'  {name}: {len(cols)}', flush=True)
        json.dump({'updated': datetime.date.today().isoformat(), 'source': 'msf.ru', 'lines': lines}, open(OUT + '.tmp', 'w'), ensure_ascii=False, separators=(',', ':'))
total = sum(len(l['c']) for l in lines)
print('done', len(lines), total, flush=True)
# a half-finished run (site down, blocked) must not replace a good palette file
try:
    old = sum(len(l['c']) for l in json.load(open(OUT))['lines'])
except Exception:
    old = 0
if total < 0.7 * old:
    print(f'too few colours ({total} vs {old}), keeping the old file', flush=True)
    sys.exit(1)
os.replace(OUT + '.tmp', OUT)
