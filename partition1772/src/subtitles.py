"""Subtitle cues from the word-timed transcript (with spelling corrections), and an elegant burn-in renderer."""
import json, re, skia
from engine import *

FIX = {'Thorne,': 'Thorn,', 'Thorne': 'Thorn', 'royal': 'Royal', 'neighboring': 'neighbouring', 'neighbors.': 'neighbours.',
       'neighbors': 'neighbours', 'monarchy': 'Monarchy', 'monarchy,': 'Monarchy,', 'monarchy.': 'Monarchy.', 'northeast,': 'north-east,', 'northeast': 'north-east', 'Northeast,': 'north-east,', 'modernize': 'modernise', 'recognized': 'recognised', 'neighboring': 'neighbouring', 'southeastern': 'south-eastern', 'Vito.': 'Veto.', 'Vito': 'Veto',
       'Tadeuszuretan,': 'Tadeusz Rejtan,', 'centre': 'centre'}
CTX_FIX = [(('Habsburg', 'monarchy'), 'Monarchy'), (('Habsburg', 'monarchy,'), 'Monarchy,')]
MAXC = 34

def words():
    T = json.load(open(D + 'transcript_medium.json'))
    out = []
    for s in T:
        for w in s['words']:
            t = w['w'].strip()
            if not t: continue
            if t.startswith('-') and out:          # "Polish -Lithuanian" -> "Polish-Lithuanian"
                out[-1]['w'] += t; out[-1]['e'] = w['e']; continue
            out.append({'w': t, 's': w['s'], 'e': w['e']})
    for i in range(len(out) - 1, 0, -1):          # '18th century Europe' -> '18th-century Europe'
        if out[i - 1]['w'] == '18th' and out[i]['w'] == 'century':
            out[i - 1]['w'] = '18th-century'; out[i - 1]['e'] = out[i]['e']; del out[i]
    # two-word corrections
    i = 0
    while i < len(out) - 1:
        a_, b_ = out[i]['w'], out[i + 1]['w']
        if a_ == 'Librem' and b_.startswith('Vito'):
            out[i]['w'] = 'liberum'; out[i + 1]['w'] = 'veto' + b_[4:]
        if a_ == 'Tadeusz' and b_.startswith('Reitam'):
            out[i + 1]['w'] = 'Rejtan' + b_[6:]
        if a_ == 'Partition' and b_.startswith('Treaty'):
            out[i]['w'] = 'partition'; out[i + 1]['w'] = 'treaty' + b_[6:]
        if a_ == 'the' and b_ == 'Eastern':
            out[i + 1]['w'] = 'eastern'
        i += 1
    for i, w in enumerate(out):
        prev = out[i - 1]['w'] if i else ''
        if w['w'] in ('monarchy', 'monarchy,', 'monarchy.') and prev != 'Habsburg':
            continue                                # only capitalise 'Habsburg Monarchy'
        if w['w'] == 'royal' and not (i + 1 < len(out) and out[i + 1]['w'].startswith('Prussia')):
            continue
        if w['w'] in ('same', 'same,') and prev == 'the' and i + 1 < len(out) and out[i + 1]['w'] in ('formally', 'ratified', 'the', 'national'):
            w['w'] = w['w'].replace('same', 'Sejm'); continue
        if w['w'] == 'same,' and prev == 'the': w['w'] = 'Sejm,'; continue
        w['w'] = FIX.get(w['w'], w['w'])
    return out

NOBREAK_AFTER = {'Catherine', 'Frederick', 'Maria', 'East', 'Grand', 'Greater', 'Lower', 'Royal', 'Habsburg', 'Russian', 'Baltic',
                 'the', 'a', 'an', 'of', 'its', 'to', 'by', 'in', 'on', 'with', 'Empress', 'King', '18th', 'one', 'Stanisław', 'August', 'Poland-Lithuania', 'and', '18th-century', 'Tadeusz', 'Nicholas', 'King', 'Augustus', 'Union', '3rd'}
GOOD_BEFORE = {'and', 'but', 'which', 'with', 'over', 'in', 'of', 'to', 'that', 'between', 'including', 'along', 'for', 'into', 'by', 'not', 'yet',
               'had', 'was', 'were', 'also', 'became', 'about', 'wanted', 'signed', 'received', 'gained'}

def _split(ws):
    """Optimal line breaks for one sentence: lines <= MAXC chars, phrase-aware penalties, balanced lengths."""
    n = len(ws); L = [len(w['w']) for w in ws]
    best = [0.0] + [1e18] * n; prev = [0] * (n + 1)
    for j in range(1, n + 1):
        for i in range(j - 1, -1, -1):
            ln = sum(L[i:j]) + (j - i - 1)
            if ln > MAXC and j - i > 1: break
            cost = (MAXC - ln) ** 2 * 0.08 + 6           # prefer full-ish lines, few cues
            if j < n:
                last, nxt = ws[j - 1]['w'], ws[j]['w']
                if re.search(r'[,;:]$', last): cost -= 18
                elif last.rstrip(',') in NOBREAK_AFTER or nxt in ('II', 'II,', 'II.', 'century', 'Prussia', 'Prussia.', 'Prussia,', 'Duchy', 'third'): cost += 60
                if nxt in GOOD_BEFORE: cost -= 8
            if ln < 9 and n > 1: cost += 25
            if best[i] + cost < best[j]: best[j] = best[i] + cost; prev[j] = i
    out = []; j = n
    while j > 0: i = prev[j]; out.append(ws[i:j]); j = i
    return out[::-1]

def cues():
    W_ = words(); cs = []; sent = []
    def flush():
        for part in _split(sent) if sent else []:
            cs.append({'t': ' '.join(x['w'] for x in part), 's': part[0]['s'], 'e': part[-1]['e'], 'w': list(part)})
    for i, w in enumerate(W_):
        if sent and w['s'] - sent[-1]['e'] > 0.9: flush(); sent = []
        sent.append(w)
        if re.search(r'[.?!]$', w['w']): flush(); sent = []
    flush()
    for i, c in enumerate(cs):
        nxt = cs[i + 1]['s'] if i + 1 < len(cs) else c['e'] + 1
        c['hold'] = min(c['e'] + 0.6, nxt - 0.04)
    return cs

CUES = cues()
SUB_Y = 1468          # TikTok-safe: above the bottom caption/music area, clear of the right-hand icon rail

def draw_sub(c, a, dark=False, lo=None, hi=None):
    """a = absolute narration time. lo/hi restrict to the audio segment being played."""
    for cu in CUES:
        if cu['s'] - 0.08 <= a < cu['hold']:
            if lo is not None and (cu['s'] < lo - 0.3 or cu['s'] > hi): return
            f = font(BODY_SB, 46)
            k = ramp(a, cu['s'] - 0.08, cu['s'] + 0.12) * (1 - ramp(a, cu['hold'] - 0.12, cu['hold']))
            tw = text_width(cu['t'], f, 0.01)
            pad_x, h = 30, 72
            rr = skia.RRect.MakeRectXY(skia.Rect(W / 2 - tw / 2 - pad_x, SUB_Y - 50, W / 2 + tw / 2 + pad_x, SUB_Y - 50 + h), 14, 14)
            bp = skia.Paint(AntiAlias=True, Color=C(20, 14, 9)); bp.setAlphaf(0.60 * k)
            sp = skia.Paint(AntiAlias=True, Color=C(0, 0, 0), MaskFilter=skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 12)); sp.setAlphaf(0.25 * k)
            c.drawRRect(rr, sp); c.drawRRect(rr, bp)
            # words already spoken in warm cream, upcoming ones slightly dimmer (subtle read-along)
            x = W / 2 - tw / 2
            for i, w in enumerate(cu['w']):
                s = w['w'] + (' ' if i < len(cu['w']) - 1 else '')
                spoken = a >= w['s'] - 0.05
                col = C(250, 240, 220) if spoken else C(214, 200, 176)
                draw_text(c, s, x, SUB_Y, f, col, align='left', tracking=0.01, alpha=k * (1.0 if spoken else 0.78))
                x += text_width(s, f, 0.01) + (0.01 * f.getSize() if i < len(cu['w']) - 1 else 0)
            return
