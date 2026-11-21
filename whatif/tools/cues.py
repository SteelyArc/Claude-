"""Word-level cue lookup on the untouched narration's transcript."""
import json, re, os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORDS = []
for seg in json.load(open(f'{ROOT}/research/transcript_words.json')):
    for w in seg['words']:
        WORDS.append((re.sub(r"[^a-z0-9']", '', w['w'].lower()), w['s'], w['e']))
DUR = 298.84


def cue(phrase, after=0.0, end=False):
    """start (or end) time of the first occurrence of phrase at/after `after` seconds."""
    toks = [re.sub(r"[^a-z0-9']", '', t.lower()) for t in phrase.split()]
    for i in range(len(WORDS) - len(toks) + 1):
        if WORDS[i][1] >= after - 1e-6 and all(WORDS[i + j][0] == toks[j] for j in range(len(toks))):
            return WORDS[i + len(toks) - 1][2] if end else WORDS[i][1]
    raise KeyError(f'{phrase!r} after {after}')
