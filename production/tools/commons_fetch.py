"""Fetch files from Wikimedia Commons with licence/author metadata recorded to assets/SOURCES.jsonl.
usage: commons_fetch.py OUTDIR [--width N] "File:..." ["File:..."]"""
import json, sys, os, time, re, urllib.request, urllib.parse
UA = "HistoricalDocResearch/1.0 (educational documentary; non-commercial research)"
import hashlib, urllib.error
def get(url, tries=12):
    for i in range(tries):
        try:
            return urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': UA}), timeout=180).read()
        except urllib.error.HTTPError as e:
            wait = int(e.headers.get('retry-after', 10 * (i + 1))) + 2
            print('  retry', i, e.code, 'wait', wait, file=sys.stderr); time.sleep(wait)
        except Exception as e:
            print('  retry', i, e, file=sys.stderr); time.sleep(10)
    raise SystemExit('failed ' + url)
def upload_url(title):
    n = title[5:].replace(' ', '_'); h = hashlib.md5(n.encode()).hexdigest()
    return f'https://upload.wikimedia.org/wikipedia/commons/{h[0]}/{h[:2]}/{urllib.parse.quote(n)}'
def strip(h): return re.sub('<[^>]+>', '', h or '').strip()
args = sys.argv[1:]; out = args.pop(0); width = None
if args and args[0] == '--width': width = int(args[1]); args = args[2:]
os.makedirs(out, exist_ok=True)
for title in args:
    q = {'action': 'query', 'titles': title, 'prop': 'imageinfo', 'iiprop': 'url|extmetadata|size|mime', 'format': 'json'}
    if width: q['iiurlwidth'] = width
    page = next(iter(json.loads(get('https://commons.wikimedia.org/w/api.php?' + urllib.parse.urlencode(q)))['query']['pages'].values()))
    if 'imageinfo' not in page: print('MISSING', title); continue
    ii = page['imageinfo'][0]; m = ii.get('extmetadata', {})
    url = upload_url(title)  # original file; thumbnails host is blocked
    ext = os.path.splitext(urllib.parse.urlparse(url).path)[1] or '.bin'
    fn = re.sub(r'[^A-Za-z0-9._-]+', '_', title[5:])[:90]
    fn = os.path.splitext(fn)[0] + ext
    open(os.path.join(out, fn), 'wb').write(get(url))
    rec = {'file': os.path.join(out, fn), 'title': title, 'page': ii.get('descriptionurl'), 'url': url,
           'license': strip(m.get('LicenseShortName', {}).get('value')), 'artist': strip(m.get('Artist', {}).get('value'))[:200],
           'date': strip(m.get('DateTimeOriginal', {}).get('value'))[:100], 'credit': strip(m.get('Credit', {}).get('value'))[:200],
           'description': strip(m.get('ImageDescription', {}).get('value'))[:400], 'size': [ii.get('width'), ii.get('height')]}
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'assets', 'SOURCES.jsonl'), 'a') as f: f.write(json.dumps(rec, ensure_ascii=False) + '\n')
    print('OK', fn, rec['license'], '|', rec['artist'][:60], '|', rec['date'][:30]); time.sleep(2)
