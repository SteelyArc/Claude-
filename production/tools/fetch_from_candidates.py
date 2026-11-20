"""Download Commons originals listed in research/commons_candidates.json (metadata already recorded there),
append licence records to assets/SOURCES.jsonl. usage: fetch_from_candidates.py OUTDIR "File:..." ..."""
import json, sys, os, re, time, urllib.request, urllib.error
UA = "ClaudeCode-DocumentaryResearch/1.0 (https://claude.ai/code; low-volume, one request at a time)"
cand = {it['title']: it for items in json.load(open('research/commons_candidates.json')).values() for it in items}
out = sys.argv[1]; os.makedirs(out, exist_ok=True)
for t in sys.argv[2:]:
    it = cand[t]; url = it['url'].split('?')[0]; ext = os.path.splitext(url)[1].lower()
    w = int(sys.argv[0] and os.environ.get('THUMB_W', '1920'))
    if it.get('w') and it['w'] > w:  # standard thumbnail step (originals are rate-limited)
        base, name = url.rsplit('/', 1); url = base.replace('/commons/', '/commons/thumb/') + f'/{name}/{w}px-{name}'
        if ext in ('.tif', '.tiff'): url += '.jpg'; ext = '.jpg'
    fn = re.sub(r'[^A-Za-z0-9._-]+', '_', t[5:])[:80].rsplit('.', 1)[0] + ext; path = os.path.join(out, fn)
    if not os.path.exists(path):
        for i in range(40):
            try:
                data = urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': UA}), timeout=180).read()
                assert len(data) > 1000, 'short read'
                open(path, 'wb').write(data); break
            except urllib.error.HTTPError as e:
                wt = max(2 * int(e.headers.get('retry-after', 60)), 1500); print('retry', e.code, 'wait', wt, flush=True); time.sleep(wt)
            except Exception as e: print('retry', e); time.sleep(20)
        if not os.path.exists(path): print('FAILED', t, flush=True); continue
        time.sleep(1500)
        rec = dict(file=path, fetched_url=url, **{k: it[k] for k in ('title', 'page', 'url', 'license', 'artist', 'date', 'desc', 'credit')})
        open('assets/SOURCES.jsonl', 'a').write(json.dumps(rec, ensure_ascii=False) + '\n')
    print(os.path.getsize(path) // 1024, 'KB', it['license'], fn, flush=True)
