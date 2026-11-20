"""Search Commons (generator=search + imageinfo/extmetadata in ONE call per query) -> research/commons_candidates.json"""
import json, sys, time, re, urllib.request, urllib.parse, urllib.error, os
UA = "HistoricalDocResearch/1.0 (educational documentary research)"
def get(url):
    for i in range(20):
        try: return urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': UA}), timeout=120).read()
        except urllib.error.HTTPError as e:
            w = int(e.headers.get('retry-after', 30)) + 3; print('  429 wait', w, flush=True); time.sleep(w)
        except Exception as e: print('  err', e, flush=True); time.sleep(15)
def strip(h): return re.sub(r'\s+', ' ', re.sub('<[^>]+>', '', h or '')).strip()
out = 'research/commons_candidates.json'
res = json.load(open(out)) if os.path.exists(out) else {}
for q in [l.strip() for l in open(sys.argv[1]) if l.strip()]:
    if q in res: continue
    p = {'action':'query','generator':'search','gsrsearch':q,'gsrnamespace':6,'gsrlimit':12,'prop':'imageinfo',
         'iiprop':'url|size|extmetadata','iiextmetadatafilter':'LicenseShortName|Artist|DateTimeOriginal|ImageDescription|Credit|ObjectName','format':'json'}
    d = json.loads(get('https://commons.wikimedia.org/w/api.php?' + urllib.parse.urlencode(p)))
    items = []
    for pg in sorted(d.get('query', {}).get('pages', {}).values(), key=lambda x: x.get('index', 0)):
        ii = pg.get('imageinfo', [{}])[0]; m = ii.get('extmetadata', {})
        items.append({'title': pg['title'], 'url': ii.get('url'), 'page': ii.get('descriptionurl'), 'w': ii.get('width'), 'h': ii.get('height'),
                      'license': strip(m.get('LicenseShortName', {}).get('value')), 'artist': strip(m.get('Artist', {}).get('value'))[:150],
                      'date': strip(m.get('DateTimeOriginal', {}).get('value'))[:80], 'desc': strip(m.get('ImageDescription', {}).get('value'))[:300],
                      'credit': strip(m.get('Credit', {}).get('value'))[:150]})
    res[q] = items; json.dump(res, open(out, 'w'), indent=1, ensure_ascii=False)
    print('DONE', q, len(items), flush=True); time.sleep(3)
