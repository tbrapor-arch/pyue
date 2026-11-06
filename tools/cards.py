"""Word cards and line segmentation, shared by the app (tools/build_app.py) and the private module's build (base
course, books, transcripts), so a word gets the same card everywhere and lines are cut the same way.
Same interface as Tsheh-tû's tools/cards.py; card fields keep Tsheh-tû's names (`hanji`, `tailo`, `tkey`) so the
app template carries over unchanged: here `tailo` holds the Jyutping ('zung1 ji3') and `tkey` its key ('zung1-ji3').

    import cards
    cards.init(con, english.English(con, ...))
    cards.lookup('鍾意', 'zung1-ji3')          # -> card id '鍾意|zung1-ji3'
    cards.tokenize(hanzi, jyutping)             # a line cut into words (hyphens in the Jyutping, else the dictionary)
    cards.tokenize(hanzi, jyutping, fallback=True)
    cards.dict_tokens(text)                     # a text with no Jyutping: longest dictionary words, usual readings
"""
import math
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from lint import UNIT_RE, CJK, words, hyphenated, is_syl  # noqa: E402
import english  # noqa: E402

dictionary = {}
con = ENGLISH = None
CEDICT = {}
HEAD = set()        # (characters, key): what counts as a word for cuts, splits and compositions
FREQ = {}           # (characters, key) -> frequency, to choose between cuts
BEST = {}           # characters -> key of the usual reading
MAX = 5


def init(connection, eng=None, ced=None):
    global con, ENGLISH, CEDICT
    con = connection
    CEDICT = ced if ced is not None else english.load_cedict()
    ENGLISH = eng
    HEAD.clear()
    HEAD.update(con.execute("SELECT hanzi, jkey FROM entry WHERE length(hanzi) <= 6"))
    FREQ.clear()
    for h, k, f in con.execute('SELECT hanzi, jkey, MAX(freq) FROM entry WHERE freq IS NOT NULL GROUP BY 1, 2'):
        FREQ[(h, k)] = f or 0
    TOTAL[0] = sum(FREQ.values()) or 1
    BEST.clear()
    for h, k in con.execute('SELECT hanzi, jkey FROM entry ORDER BY COALESCE(share, 100) DESC, freq DESC'):
        BEST.setdefault(h, k)


def is_han(s):
    return bool(s) and all(re.match(CJK, c) for c in s)


def disp(k):
    """'zung1-ji3' -> 'zung1 ji3' (Jyutping is shown with spaces between syllables)."""
    return k.replace('-', ' ')


def _py_marks(num):
    marks = {'a': 'āáǎà', 'e': 'ēéěè', 'i': 'īíǐì', 'o': 'ōóǒò', 'u': 'ūúǔù', 'ü': 'ǖǘǚǜ'}
    out = []
    for syl in num.replace('u:', 'ü').split():
        m = re.match(r'^([a-zü]+)([1-5])$', syl.lower())
        if not m:
            out.append(syl)
            continue
        base, t = m.group(1), int(m.group(2))
        if t == 5:
            out.append(base)
            continue
        idx = base.find('a') if 'a' in base else base.find('e') if 'e' in base else base.find('ou') if 'ou' in base \
            else max(base.rfind(v) for v in 'iouü')
        out.append(base[:idx] + marks[base[idx]][t - 1] + base[idx + 1:])
    return ' '.join(out)


def mandarin_gloss(word):
    e = CEDICT.get(word)
    if e:
        en = '; '.join(g for g in e['english'] if not g.startswith(('variant of', 'old variant', 'CL:')))[:90]
        return {'w': word, 'py': _py_marks(e['pinyin']), 'en': en}
    return {'w': word, 'py': '', 'en': ''}


def lookup(seg, k):
    """Dictionary card for one word (characters + key)."""
    did = f'{seg}|{k}'
    if did in dictionary:
        return did
    card = {'hanji': seg, 'tkey': k, 'tailo': disp(k)}
    row = con.execute("""SELECT source, cognate, mandarin_best, hsk_new, freq_rank, share FROM entry
                         WHERE hanzi=? AND jkey=? LIMIT 1""", (seg, k)).fetchone()
    if row:
        src, cog, mb, hsk, rank, share = row
        mand = [mb] if mb else []
        card.update(source=src, dict_hanji=seg, cognate=cog, mandarin=mand, hsk=hsk, rank=rank,
                    mand=[mandarin_gloss(w) for w in mand])
        others = con.execute('SELECT jyutping, share FROM entry WHERE hanzi=? AND jkey!=? '
                             'ORDER BY COALESCE(share, 100) DESC LIMIT 4', (seg, k)).fetchall()
        if others:
            card['readings'] = [{'t': j, 'share': s} for j, s in others]
        if share is not None:
            card['share'] = share
    else:
        syls = k.split('-')
        chars = UNIT_RE.findall(seg)
        card['parts'] = [lookup(c, s) for c, s in zip(chars, syls)] if len(syls) > 1 and len(chars) == len(syls) else []
    comp = compose(seg, k)
    if comp:
        card['comp'] = comp
    parts = [(dictionary[p].get('gloss'), dictionary[p].get('gloss_src')) for p in card.get('parts') or comp or []]
    en, en_src = ENGLISH.gloss(seg, k, parts)
    if not en and len(seg) == 1:
        en, en_src = english.cedict_en(CEDICT, seg), f'mandarin:{seg}'
    if en:
        card['gloss'] = en
        if en_src not in ('course', 'written'):
            card['gloss_src'] = en_src
    dictionary[did] = card
    return did


TOTAL = [1]


def _cost(w, kk):
    """Unigram cost of a word: -log of its share of the corpus (rime's essay counts). rime's word list also holds
    phrases (你今日, 咁早返); scoring by frequency rather than by fewest pieces cuts them into their words."""
    return -math.log((FREQ.get((w, kk), 0) + 0.5) / TOTAL[0])


def _best_cut(chars, syls, allow_whole):
    """The most likely cut into dictionary words (unigram frequencies): [(start, length)]."""
    n = len(chars)
    best = [(0.0, [])] + [None] * n
    for i in range(n):
        if best[i] is None:
            continue
        for m in range(1, min(n - i, MAX) + 1):
            if m == n and not allow_whole and n > 1:
                continue
            w, kk = ''.join(chars[i:i + m]), '-'.join(syls[i:i + m])
            if m > 1 and ((w, kk) not in HEAD or not is_han(w)):
                continue
            c = (best[i][0] + _cost(w, kk), best[i][1] + [(i, m)])
            if best[i + m] is None or c[0] < best[i + m][0]:
                best[i + m] = c
    return best[n][1]


def _cut_run(chars, syls):
    """A run of characters cut into words: PyCantonese's segmenter (trained on the HKCanCor corpus, so 我哋 and 食 | 咗
    come out as linguists cut them), each piece kept only if the dictionary has it with the line's own reading;
    a piece it lacks is cut again by frequency (食菠蘿包飲 -> 食 | 菠蘿包 | 飲)."""
    try:
        import pycantonese
        pieces = pycantonese.segment(''.join(chars))
    except Exception:       # no segmenter: frequency cut only
        return _best_cut(chars, syls, True)
    out, i = [], 0
    for p in pieces:
        m = len(p)
        if p != ''.join(chars[i:i + m]):          # the segmenter changed the text: do not trust it
            return _best_cut(chars, syls, True)
        if m == 1 or (p, '-'.join(syls[i:i + m])) in HEAD:
            out.append((i, m))
        else:
            out += [(i + a, n) for a, n in _best_cut(chars[i:i + m], syls[i:i + m], True)]
        i += m
    return out


def compose(seg, k):
    """A word of two or more characters cut into the dictionary words it contains (never itself)."""
    chars, syls = UNIT_RE.findall(seg), k.split('-')
    if len(chars) < 2 or len(chars) != len(syls) or not is_han(seg):
        return None
    out = []
    for i, m in _best_cut(chars, syls, False):
        w, kk = ''.join(chars[i:i + m]), '-'.join(syls[i:i + m])
        pid = lookup(w, kk)
        pc = dictionary[pid]
        if not pc.get('gloss') and len(pc.setdefault('in', [])) < 4 and f'{seg}|{k}' not in pc['in']:
            pc['in'].append(f'{seg}|{k}')
        out.append(pid)
    return out


def _alts(units, sylk, gaps, p, own):
    """Dictionary words starting at unit p (the line's own syllables give their reading), longest first."""
    out = []
    for m in range(MAX, 0, -1):
        if p + m > len(units) or any(gaps[p:p + m - 1]):
            continue
        w, kk = ''.join(units[p:p + m]), '-'.join(sylk[p:p + m])
        if not is_han(w) or not all(is_syl(s) for s in sylk[p:p + m]):
            continue
        if (w, kk) in HEAD or f'{w}|{kk}' == own:
            out.append(lookup(w, kk))
    return out if len(out) > 1 else None


def tokenize(hanzi, jyut, groups=None, fallback=False):
    """A line as display tokens: {w: word} or {p: punctuation}. With hyphens in the Jyutping the line is cut as
    written; without, it is cut into dictionary words using the line's own readings. If characters and Jyutping do
    not line up, the line stays one untappable token (or, with `fallback`, is cut by the dictionary)."""
    ws = words(jyut)
    items = [i for w in ws for i in w]
    spans = list(UNIT_RE.finditer(hanzi))
    if len(spans) != len(items):
        return dict_tokens(hanzi) if fallback else [{'w': {'h': hanzi, 't': jyut, 's': jyut, 'id': None}}]
    units = [m.group() for m in spans]
    gaps = [bool(hanzi[spans[j].end():spans[j + 1].start()].strip()) for j in range(len(spans) - 1)] + [True]
    if hyphenated(jyut):
        cut, i = [], 0
        for w in ws:
            cut.append((i, len(w)))
            i += len(w)
    else:
        # dictionary cut inside each run of characters with no punctuation between them
        cut, i = [], 0
        while i < len(units):
            j = i
            while j < len(units) - 1 and not gaps[j] and is_han(units[j]) and is_han(units[j + 1]) and is_syl(items[j]) and is_syl(items[j + 1]):
                j += 1
            run = range(i, j + 1)
            if len(run) == 1 or not is_han(units[i]):
                cut.append((i, 1))
            else:
                cut += [(i + a, m) for a, m in _cut_run(units[i:j + 1], items[i:j + 1])]
            i = j + 1
    out, pos = [], 0
    for s, m in cut:
        start, end = spans[s].start(), spans[s + m - 1].end()
        if start > pos:
            out.append({'p': hanzi[pos:start]})
        seg = hanzi[start:end]
        its = items[s:s + m]
        k = '-'.join(its)
        han = is_han(seg) and all(is_syl(x) for x in its)
        t = ' '.join(its)
        w = {'h': seg, 't': t, 's': t, 'id': lookup(seg, k) if han else None}
        x = _alts(units, items, gaps, s, w['id']) if han else None
        if x:
            w['x'] = x
        out.append({'w': w})
        pos = end
    if pos < len(hanzi):
        out.append({'p': hanzi[pos:]})
    return out


def dict_tokens(text, jyut=None):
    """Cut a text with no usable Jyutping by the dictionary: longest words first, each with its usual reading."""
    chars = list(text)
    out, i = [], 0
    while i < len(chars):
        if not re.match(CJK, chars[i]):
            if out and 'p' in out[-1]:
                out[-1]['p'] += chars[i]
            else:
                out.append({'p': chars[i]})
            i += 1
            continue
        for n in range(MAX, 0, -1):
            w = ''.join(chars[i:i + n])
            if len(w) == n and is_han(w) and w in BEST:
                k = BEST[w]
                out.append({'w': {'h': w, 't': disp(k), 's': disp(k), 'id': lookup(w, k)}})
                i += n
                break
        else:
            out.append({'p': chars[i]})
            i += 1
    return out
