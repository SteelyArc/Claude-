"""Polite Wikimedia Commons search + download with licence metadata.

python3 commons_fetch.py search "<query>" [limit]
python3 commons_fetch.py get "<File:Title.jpg>" <out_dir> [width]
Writes <out_dir>/<slug>.jpg and appends metadata to <out_dir>/credits.json
"""
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

UA = "HistoryDocBot/0.1 (educational documentary; non-commercial research)"
API = "https://commons.wikimedia.org/w/api.php"


def fetch(url, tries=6):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=40) as r:
                return r.read()
        except Exception as e:  # noqa: BLE001
            wait = 4 * (i + 1)
            print(f"  retry {i + 1} after {e} (wait {wait}s)", file=sys.stderr)
            time.sleep(wait)
    raise RuntimeError("giving up: " + url)


def api(**params):
    params["format"] = "json"
    return json.loads(fetch(API + "?" + urllib.parse.urlencode(params)))


def strip_html(s):
    return re.sub(r"<[^>]+>", "", s or "").strip()


def search(q, limit=10):
    r = api(action="query", list="search", srnamespace=6, srlimit=limit, srsearch=q)
    return [x["title"] for x in r["query"]["search"]]


def get(title, out_dir, width=1600):
    r = api(action="query", titles=title, prop="imageinfo", iiprop="url|extmetadata|size", iiurlwidth=width)
    page = next(iter(r["query"]["pages"].values()))
    ii = page["imageinfo"][0]
    md = ii.get("extmetadata", {})
    meta = {
        "title": title,
        "page": ii.get("descriptionurl"),
        "licence": strip_html(md.get("LicenseShortName", {}).get("value")),
        "artist": strip_html(md.get("Artist", {}).get("value")),
        "credit": strip_html(md.get("Credit", {}).get("value")),
        "date": strip_html(md.get("DateTimeOriginal", {}).get("value")),
        "description": strip_html(md.get("ImageDescription", {}).get("value"))[:600],
        "size": [ii.get("width"), ii.get("height")],
    }
    os.makedirs(out_dir, exist_ok=True)
    slug = re.sub(r"[^A-Za-z0-9]+", "_", title.replace("File:", ""))[:80].strip("_")
    path = os.path.join(out_dir, slug + ".jpg")
    data = None
    base = ii["url"].split("?")[0]
    name = base.rsplit("/", 1)[1]
    pre = base.replace("/wikipedia/commons/", "/wikipedia/commons/thumb/")
    for w in (960, 500, 330):
        if ii.get("width") and ii["width"] <= w:
            continue
        try:
            data = fetch(f"{pre}/{w}px-{name}", tries=2)
            meta["fetched_width"] = w
            break
        except Exception:  # noqa: BLE001
            continue
    if data is None:
        data = fetch(ii["url"], tries=3)
    with open(path, "wb") as f:
        f.write(data)
    meta["file"] = os.path.basename(path)
    cpath = os.path.join(out_dir, "credits.json")
    credits = json.load(open(cpath)) if os.path.exists(cpath) else []
    credits = [c for c in credits if c["title"] != title] + [meta]
    json.dump(credits, open(cpath, "w"), indent=1, ensure_ascii=False)
    return meta


if __name__ == "__main__":
    if sys.argv[1] == "search":
        for t in search(sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 10):
            print(t)
    else:
        m = get(sys.argv[2], sys.argv[3], int(sys.argv[4]) if len(sys.argv) > 4 else 1600)
        print(json.dumps({k: m[k] for k in ("file", "licence", "artist", "date")}, ensure_ascii=False))
