"""Compare an ElevenLabs take with the script and build a per-line timing JSON.

python3 align_take.py <take.json> <script.txt> [timing_out.json]
Prints coverage stats; writes timing in the narration_lewis_timing.json format.
"""
import difflib
import json
import re
import sys

NUM = {"1918": "nineteen eighteen", "1919": "nineteen nineteen", "1923": "nineteen twenty-three",
       "1929": "nineteen twenty-nine", "1930": "nineteen thirty", "1932": "nineteen thirty-two",
       "1933": "nineteen thirty-three", "1934": "nineteen thirty-four", "1889": "eighteen eighty-nine",
       "1930s": "nineteen thirties", "1920s": "nineteen twenties"}


def norm_words(text):
    t = text.lower().replace("’", "'").replace("—", " ").replace("–", " ").replace("…", " ")
    t = re.sub(r"[^a-z0-9äöüß' -]", " ", t)
    out = []
    for w in t.split():
        w = w.strip("'-")
        if not w:
            continue
        if w in NUM:
            out.extend(NUM[w].replace("-", " ").split())
        elif w in ("führer", "fuehrer"):
            out.append("fuhrer")
        else:
            out.extend(w.replace("-", " ").split())
    return out


def script_lines(path):
    lines, section = [], 0
    for raw in open(path):
        l = raw.strip()
        if not l:
            continue
        if l == "---":
            section += 1
            continue
        if l.startswith("["):
            continue
        lines.append((section, l))
    return lines


def main():
    take = json.load(open(sys.argv[1]))
    lines = script_lines(sys.argv[2])
    tw = []
    for s in take:
        for w, a, b, p in s["words"]:
            ww = w.strip().lower()
            m = re.match(r"^(\d+)%[.,]?$", ww)
            pct = {"18": "eighteen", "37": "thirty seven", "33": "thirty three", "43": "forty three"}
            if m and m.group(1) in pct:
                for n in (pct[m.group(1)] + " percent").split():
                    tw.append((n, a, b, p))
                continue
            if ww.strip(".,") == "ii":
                tw.append(("the", a, b, p)); tw.append(("second", a, b, p))
                continue
            for n in norm_words(w):
                tw.append((n, a, b, p))
    merged = []
    for t in tw:
        if merged and merged[-1][0] == "anti" and t[0] in ("semitism", "semitic"):
            merged[-1] = ("anti" + t[0], merged[-1][1], t[2], min(merged[-1][3], t[3]))
        else:
            merged.append(t)
    tw = [(("fuhrer" if n in ("fuehrer", "führer") else n), a, b, p) for n, a, b, p in merged]
    sw, owner = [], []
    for li, (_, l) in enumerate(lines):
        for n in norm_words(l):
            sw.append(n)
            owner.append(li)
    sm = difflib.SequenceMatcher(a=sw, b=[x[0] for x in tw], autojunk=False)
    match = [None] * len(sw)
    for blk in sm.get_matching_blocks():
        for k in range(blk.size):
            match[blk.a + k] = blk.b + k
    matched = sum(m is not None for m in match)
    extra = len(tw) - matched
    print(f"script words {len(sw)}, matched {matched} ({100 * matched / len(sw):.1f} %), transcript words {len(tw)}, extra {extra}")
    lowp = [(w, round(a, 1), round(p, 2)) for w, a, b, p in tw if p < 0.35]
    print("low-confidence words:", len(lowp), lowp[:25])
    timing, missing_lines = [], []
    for li, (sec, l) in enumerate(lines):
        idx = [match[k] for k in range(len(sw)) if owner[k] == li and match[k] is not None]
        if not idx:
            missing_lines.append(l)
            continue
        timing.append({"section": sec, "tag": "", "text": l, "start": round(tw[min(idx)][1], 3), "end": round(tw[max(idx)][2], 3),
                       "coverage": round(len(idx) / max(1, sum(1 for k in range(len(sw)) if owner[k] == li)), 2)})
    weak = [(t["text"][:60], t["coverage"]) for t in timing if t["coverage"] < 0.8]
    print("lines not spoken:", len(missing_lines), missing_lines[:10])
    print("lines partly spoken (<80 %):", len(weak), weak[:10])
    gaps = [(round(timing[i]["start"] - timing[i - 1]["end"], 1), timing[i]["text"][:40]) for i in range(1, len(timing))
            if timing[i]["start"] - timing[i - 1]["end"] > 2.5]
    print("long gaps (>2.5 s):", gaps[:10])
    if len(sys.argv) > 3:
        json.dump(timing, open(sys.argv[3], "w"), indent=1, ensure_ascii=False)
        print("written", sys.argv[3], len(timing), "lines; last end", timing[-1]["end"])


if __name__ == "__main__":
    main()
