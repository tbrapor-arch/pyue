"""Build the reader app: course/ + database -> app/dist/index.html (one self-contained file).

  python3 -I tools/build_app.py

Same template and data shape as Tsheh-tû (app/index.template.html), so fixes carry over between the two apps. The
JSON keeps Tsheh-tû's field names: `hanji` = characters, `tailo` = Jyutping, `en` = English. Lesson files use
`hanzi`, `jyutping`, `en` (see course/perfectionnement/_template.yaml); this script maps them.
"""
import base64
import datetime
import glob
import hashlib
import io
import json
import os
import sqlite3
import sys
import unicodedata

import markdown
import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import jyutping as jp  # noqa: E402
import cards  # noqa: E402
import english  # noqa: E402
import tone_drill  # noqa: E402

ROOT = os.path.dirname(HERE)
con = sqlite3.connect(os.path.join(ROOT, 'data/build/yue.db'))
CEDICT = english.load_cedict()
cards.init(con, None, CEDICT)
dictionary, lookup, tokenize = cards.dictionary, cards.lookup, cards.tokenize
PART2 = 100


def _in_big5(ch):
    try:
        ch.encode('cp950')
        return True
    except UnicodeEncodeError:
        return False


def tailo_font_css():
    """Tsheh-tû's embedded Noto Sans (app/fonts/tailo-noto-sans.woff2), same name ('TailoSans'), same use: the
    romanisation above the characters looks exactly as in Tsheh-tû and sy-zy."""
    b64 = base64.b64encode(open(os.path.join(ROOT, 'app/fonts/tailo-noto-sans.woff2'), 'rb').read()).decode()
    return (f"@font-face{{font-family:'TailoSans';font-weight:400 800;font-display:swap;"
            f"src:url(data:font/woff2;base64,{b64}) format('woff2');}}")


def han_font_css(text, skip=''):
    """'PyueExt': the LXGW WenKai TC glyphs of every Chinese character in the app that Iansui (Tsheh-tû's character
    font) does not have — Cantonese characters such as 哋, 咗, 嘢. Both fonts are made from Klee One, so every character
    keeps Tsheh-tû's handwriting look (sy-zy does the same with LXGW WenKai for simplified characters).
    Characters missing from both come from Plangothic ('TaigiExt', a plain sans) as a last resort.
    `skip`: characters another @font-face of the same families already covers (the side file of 粵字 adds only its own
    glyphs: same family names, other unicode-range, so the browser joins them)."""
    fdir = os.path.join(ROOT, 'data/raw/fonts')
    ian, wk = os.path.join(fdir, 'Iansui-Regular.ttf'), os.path.join(fdir, 'LXGWWenKaiTC-Regular.ttf')
    try:
        from fontTools import subset
        from fontTools.ttLib import TTFont
    except ImportError:
        return ''
    if not (os.path.exists(ian) and os.path.exists(wk)):
        print('WARNING: fonts missing (sh data/fetch_fonts.sh): Cantonese characters fall back to Noto Sans TC')
        return ''
    have = set(TTFont(ian).getBestCmap())
    skip = set(skip)
    need = sorted({ord(c) for c in text if (0x3400 <= ord(c) <= 0x9fff or 0xf900 <= ord(c) <= 0xfaff or ord(c) >= 0x20000)
                   and ord(c) not in have and unicodedata.category(c) != 'Cn' and c not in skip})
    if not need:
        return ''
    font = TTFont(wk)
    cmap = font.getBestCmap()
    got = [c for c in need if c in cmap]
    missing = ''.join(chr(c) for c in need if c not in cmap)
    css = ''
    if got:
        sub = subset.Subsetter(subset.Options(flavor='woff2', layout_features=[], name_IDs=['*']))
        sub.populate(unicodes=got)
        sub.subset(font)
        font.flavor = 'woff2'
        buf = io.BytesIO()
        font.save(buf)
        print(f'embedded {len(got)} characters Iansui lacks ({len(buf.getvalue()) // 1024} KB)')
        rng = ','.join(f'U+{c:X}' for c in got)
        css = (f"@font-face{{font-family:'PyueExt';font-display:swap;src:url(data:font/woff2;base64,"
               f"{base64.b64encode(buf.getvalue()).decode()}) format('woff2');unicode-range:{rng};}}")
    if missing:
        print('not in LXGW WenKai TC either (Plangothic used):', missing)
        css += '\n' + ext_font_css(missing)
    return css


def ext_font_css(text):
    """@font-face rules with only the glyphs of rare characters (not in Big5) used by the app, from Plangothic:
    many Cantonese characters (𠝹, 𨋢, 冚…) are missing from common fonts."""
    try:
        from fontTools import subset
        from fontTools.ttLib import TTFont
    except ImportError:
        return ''
    rare = sorted({ch for ch in text if (0x3400 <= ord(ch) <= 0x9fff or ord(ch) >= 0x20000 or 0xf900 <= ord(ch) <= 0xfaff)
                   and not _in_big5(ch)})
    fdir = os.path.join(ROOT, 'data/raw/plangothic/package/fonts')
    chunks = {}
    for ch in rare:
        base = ord(ch) & ~0xff
        for plane in ('P1', 'P2'):
            p = os.path.join(fdir, f'Plangothic{plane}-400-{base:06x}.woff2')
            if os.path.exists(p):
                chunks.setdefault(p, []).append(ord(ch))
                break
    css = []
    for p, cps in chunks.items():
        font = TTFont(p)
        have = [c for c in cps if c in font.getBestCmap()]
        if not have:
            continue
        sub = subset.Subsetter(subset.Options(flavor='woff2', layout_features=[], name_IDs=['*']))
        sub.populate(unicodes=have)
        sub.subset(font)
        font.flavor = 'woff2'
        buf = io.BytesIO()
        font.save(buf)
        b64 = base64.b64encode(buf.getvalue()).decode()
        rng = ','.join(f'U+{c:X}' for c in have)
        css.append(f"@font-face{{font-family:'TaigiExt';font-display:swap;src:url(data:font/woff2;base64,{b64}) "
                   f"format('woff2');unicode-range:{rng};}}")
    print(f'embedded {sum(len(c) for c in chunks.values())} rare characters in {len(css)} font chunks')
    return '\n'.join(css)


def title(t):
    return {'hanji': t.get('hanzi', ''), 'tailo': t.get('jyutping', ''), 'en': t.get('en', '')}


# ---- lessons: course/perfectionnement/NN.yaml with id N, stored in the app as 100 + N (Tsheh-tû's numbering)
perf_files = sorted(glob.glob(os.path.join(ROOT, 'course/perfectionnement/[0-9]*.yaml')))
if os.environ.get('PYUE_FIXTURES'):      # local check of the app with sample lessons (never published)
    perf_files += sorted(glob.glob(os.path.join(ROOT, 'tools/fixtures/[0-9]*.yaml')))
theme_files = sorted(glob.glob(os.path.join(ROOT, 'course/themes/*.yaml')))
glosses = {}
for f in perf_files:
    for w in yaml.safe_load(open(f, encoding='utf-8')).get('new_words', []) or []:
        if w.get('en'):
            glosses[(w['hanzi'], jp.key(w['jyutping']))] = w['en']
for f in theme_files:
    for sec in yaml.safe_load(open(f, encoding='utf-8'))['sections']:
        for w in sec['words']:
            if w.get('en'):
                glosses.setdefault((w['hanzi'], jp.key(w['jyutping'])), w['en'])
cards.ENGLISH = english.English(con, glosses, CEDICT)

# ---- synthetic audio (tools/tts.py, Azure zh-HK voices): a line gets its file only if the text it was made from is
# still the line's text, so an edited line goes silent until the audio is made again. Files are copied to app/dist/audio.
import shutil  # noqa: E402
import tts  # noqa: E402
AUDIO_DIR = os.path.join(ROOT, 'audio')
AUDIO = json.load(open(os.path.join(AUDIO_DIR, 'index.json'), encoding='utf-8')) \
    if os.path.exists(os.path.join(AUDIO_DIR, 'index.json')) else {}
TTS_FIX = tts.fixes()
audio_used = []


def line_audio(lesson, ln):
    au = AUDIO.get(str(lesson), {}).get(str(ln['n']))
    rel = f"{lesson:02d}/{ln['n']:02d}.mp3"
    if au and au['t'] == tts.spoken(ln.get('hanzi'), TTS_FIX) and os.path.exists(os.path.join(AUDIO_DIR, rel)):
        audio_used.append(rel)
        return f"audio/{rel}?v={au['h']}", f"{au.get('v', 'Azure')} (synthetic)"
    return None, None


lessons = []
for f in perf_files:
    d = yaml.safe_load(open(f, encoding='utf-8'))
    lid = PART2 + d['id']
    lines = []
    for ln in d['dialogue']:
        j = ln['jyutping']
        shown = j.replace('-', ' ')
        lines.append({'n': ln['n'], 'speaker': ln.get('speaker') or '', 'en': ln['en'], 'zh': ln.get('zh'),
                      'tailo': shown, 'hanji': ln['hanzi'], 'spoken': shown, 'tokens': tokenize(ln['hanzi'], j)})
        au, voice = line_audio(d['id'], ln)
        if au:
            lines[-1]['audio'], lines[-1]['voice'] = au, voice
    new_words = [{'tailo': w['jyutping'], 'hanji': w['hanzi'], 'en': w.get('en'),
                  'id': lookup(w['hanzi'], jp.key(w['jyutping']))} for w in d.get('new_words') or []]
    ex = []
    for kind, items in (d.get('exercises') or {}).items():
        for it in items or []:
            e = dict(it, kind=kind)
            if 'hanzi' in e:
                e['hanji'] = e.pop('hanzi')
            if 'jyutping' in e:
                e['tailo'] = e.pop('jyutping')
            if 'answer_hanzi' in e:
                e['answer_hanji'] = e.pop('answer_hanzi')
            ex.append(e)
    lessons.append({'id': lid, 'title': title(d['title']), 'review': d.get('review', False),
                    'genre': d.get('genre', 'dialogue'), 'setting': d.get('setting', ''), 'lines': lines,
                    'notes': d.get('notes') or [], 'pron': d.get('pron') or [], 'intro': d.get('intro', ''),
                    'new_words': new_words, 'exercises': ex})
lessons.sort(key=lambda L: L['id'])

# ---- themes (thematic vocabulary)
themes = []
for f in theme_files:
    t = yaml.safe_load(open(f, encoding='utf-8'))
    secs = []
    for sec in t['sections']:
        ws = [{'hanji': w['hanzi'], 'tailo': w['jyutping'], 'en': w.get('en'), 'zh': w.get('zh'),
               'id': lookup(w['hanzi'], jp.key(w['jyutping']))} for w in sec['words']]
        text = [{'en': x['en'], 'tailo': x['jyutping'], 'hanji': x['hanzi'], 'tokens': tokenize(x['hanzi'], x['jyutping'])}
                for x in sec.get('text', [])]
        secs.append({'n': sec['n'], 'title': title(sec['title']), 'words': ws, 'text': text})
    themes.append({'id': t['id'], 'title': title(t['title']), 'intro': t.get('intro', ''), 'sections': secs,
                   'notes': t.get('notes') or []})

lesson0 = markdown.markdown(open(os.path.join(ROOT, 'course/lessons/000-reading-jyutping.md'), encoding='utf-8').read(),
                            extensions=['tables', 'fenced_code'])
syllabus = (yaml.safe_load(open(os.path.join(ROOT, 'course/syllabus.yaml'), encoding='utf-8')) or {}).get('lessons') or []

# ---- grammar sheets: every course line that uses each structure (course/grammar.yaml)
import re  # noqa: E402
grammar = (yaml.safe_load(open(os.path.join(ROOT, 'course/grammar.yaml'), encoding='utf-8')) or {}).get('groups') or []
for g in grammar:
    for it in g['items']:
        rh = re.compile(it['han']) if it.get('han') else None
        rt = re.compile(it['jp']) if it.get('jp') else None
        it['refs'] = [[L['id'], i] for L in lessons for i, ln in enumerate(L['lines'])
                      if (rh and rh.search(ln['hanji'])) or (rt and rt.search(ln['tailo'].lower()))]
        it['tailo'] = it.pop('jyutping', it.get('tailo', ''))
        it.pop('han', None)
        it.pop('jp', None)

# ---- 粵字 (Lessons › 粵字): Cantonese-only characters, grouped (course/yuezi.yaml). Each gets one example: the
# yaml's own `example`, else the course line that suits best (the character read as listed, 8–24 characters, earliest
# lesson, a line no other character uses yet, without stage directions; failing that the shortest line), plus the 進修 new words that contain it.
SYL = re.compile(r'[a-z]+[1-6]')


def han_chars(s):
    return [c for c in s if 0x3400 <= ord(c) <= 0x9fff or ord(c) >= 0x20000 or 0xf900 <= ord(c) <= 0xfaff]


def yuezi_build():
    src = yaml.safe_load(open(os.path.join(ROOT, 'course/yuezi.yaml'), encoding='utf-8'))
    perf = {d['id']: d for d in (yaml.safe_load(open(f, encoding='utf-8')) for f in perf_files)}
    by_id = {L['id']: L for L in lessons}
    groups, used, built = [], set(), {}
    # characters with the fewest lines choose first, so a rare one keeps its only line
    order = sorted((it for g in src['groups'] for it in g['chars']),
                   key=lambda it: sum(it['c'] in ln['hanji'] for L in lessons for ln in L['lines']))
    for it in order:
        if True:
            c, want = it['c'], [s.rstrip('123456') for s in it['jyutping'].split()]
            ex = it.get('example')
            uses = [(L['id'], i) for L in lessons for i, ln in enumerate(L['lines']) if c in ln['hanji']]
            if ex:
                ex = {'hanji': ex['hanzi'], 'tailo': ex['jyutping'], 'en': ex['en'],
                      'tokens': tokenize(ex['hanzi'], ex['jyutping']), 'src': None}
            else:
                good = []
                for lid, i in uses:
                    ln = by_id[lid]['lines'][i]
                    hs, ss = han_chars(ln['hanji']), SYL.findall(ln['tailo'].lower())
                    ok = len(hs) == len(ss) and any(
                        ''.join(hs[k:k + len(c)]) == c and [s.rstrip('123456') for s in ss[k:k + len(c)]] == want
                        for k in range(len(hs)))
                    good.append((ok, len(hs), lid, i))
                def rank(x):    # an unused line first, then one without stage directions, then the earliest
                    stage = '（' in by_id[x[2]]['lines'][x[3]]['hanji']
                    return ((x[2], x[3]) in used, stage, x[2], x[1])
                fit = [x for x in good if x[0] and 8 <= x[1] <= 24]
                okl = [x for x in good if x[0]]
                if not okl:
                    sys.exit(f'yuezi.yaml: no lesson line reads {c} as {it["jyutping"]}: give it an example')
                pick = min(fit, key=rank) if fit else min(okl, key=lambda x: x[1])
                used.add((pick[2], pick[3]))
                ln = by_id[pick[2]]['lines'][pick[3]]
                ex = {'hanji': ln['hanji'], 'tailo': ln['tailo'], 'en': ln['en'], 'tokens': ln['tokens'],
                      'src': [pick[2], ln['n']]}
            words, seen = [], set()
            for n in sorted(perf):
                for w in perf[n].get('new_words') or []:
                    if c in w['hanzi'] and w['hanzi'] != c and w['hanzi'] not in seen and len(words) < 6:
                        seen.add(w['hanzi'])
                        words.append({'hanji': w['hanzi'], 'tailo': w['jyutping'], 'en': w.get('en', ''),
                                      'id': lookup(w['hanzi'], jp.key(w['jyutping'])), 'lesson': PART2 + n})
            built[c] = {'c': c, 'tailo': it['jyutping'], 'en': it['en'], 'zh': str(it.get('zh', '')),
                        'uses': len(uses), 'ex': ex, 'words': words}
    for g in src['groups']:
        groups.append({'id': g['id'], 'en': g['en'], 'hanji': g['hanzi'], 'kind': g.get('kind', ''), 'items': [built[it['c']] for it in g['chars']]})
    return groups



# ---- 粵字 not in the lessons yet: everything from words.hk, grouped by part of speech
MORE_GROUPS = [('verbs', '動詞', 'Verbs', ('動詞',)), ('nouns', '名詞', 'Nouns', ('名詞',)),
               ('describe', '形容詞', 'Describing words', ('形容詞', '區別詞')),
               ('measure', '量詞', 'Measure words', ('量詞',)),
               ('particles', '助詞嘆詞', 'Particles, sounds and exclamations', ('助詞', '感嘆詞', '擬聲詞')),
               ('function', '虛詞', 'Pronouns, adverbs, linking words', ('代詞', '副詞', '連詞', '介詞', '數詞')),
               ('bound', '詞素', 'Only inside words', ()), ('vulgar', '粗口', 'Vulgar', ())]


def yuezi_more():
    src = yaml.safe_load(open(os.path.join(ROOT, 'course/yuezi.yaml'), encoding='utf-8'))
    chars = [c for c in src.get('more', '') if not c.isspace()]
    # sentences written for the list (course/yuezi_examples.yaml, optional) for characters words.hk has no example of
    wpath = os.path.join(ROOT, 'course/yuezi_examples.yaml')
    written = ((yaml.safe_load(open(wpath, encoding='utf-8')) or {}).get('examples') or {}) if os.path.exists(wpath) else {}
    rank = {}
    for h, r in con.execute("SELECT hanzi, MIN(freq_rank) FROM entry WHERE freq_rank IS NOT NULL GROUP BY hanzi"):
        rank[h] = r

    def senses(i):
        return [e for (e,) in con.execute("SELECT en FROM wordshk_sense WHERE id=? ORDER BY n", (i,)) if e]

    def examples(i, c):
        return [r for r in con.execute("SELECT hanzi, jyutping, en, kind FROM wordshk_ex WHERE id=? ORDER BY n", (i,))
                if c in r[0] and r[1] and r[2] and '(' not in r[0]]

    def tokens(h, j):
        if len(han_chars(h)) != len(SYL.findall(j)):
            return None
        try:
            return tokenize(h, j)
        except Exception:
            return None

    groups = {g[0]: [] for g in MORE_GROUPS}
    for c in chars:
        rows = con.execute("SELECT id, hanzi, jkey, pos FROM wordshk WHERE instr(hanzi, ?) > 0", (c,)).fetchall()
        single = [r for r in rows if r[1] == c]
        nex = {r[0]: con.execute("SELECT COUNT(*) FROM wordshk_ex WHERE id=?", (r[0],)).fetchone()[0] for r in rows}
        # words: dictionary frequency first, then the words.hk entries with most examples (drops fragments like 屙唔)
        multi = sorted({r for r in rows if r[1] != c and 2 <= len(r[1]) <= 4 and 'Х' not in r[1]},
                       key=lambda r: (rank.get(r[1], 10 ** 7), -nex[r[0]], len(r[1]), r[1]))
        if not rows:
            continue
        # the reading most words use comes first (喱 lei1 as in 咖喱, before the rare nei1 'hide')
        use = {}
        for r in multi:
            sy = r[2].split('-')
            if len(sy) == len(r[1]):
                k = sy[r[1].index(c)]
                use[k] = use.get(k, 0) + 1
        single.sort(key=lambda r: (-use.get(r[2], 0), -nex[r[0]]))
        reads = []
        for r in single:
            reads.append(r[2])
        if not reads:
            for r in multi:
                sy = r[2].split('-')
                if len(sy) == len(r[1]):
                    reads.append(sy[r[1].index(c)])
        reads = list(dict.fromkeys(reads))[:3]
        pos = ' '.join(r[3] or '' for r in (single or multi[:3]))
        vulgar = '粗俗' in pos
        gid = 'vulgar' if vulgar else next((g[0] for g in MORE_GROUPS if single and any(
            t in (single[0][3] or '').split() for t in g[3])), 'bound')
        en = []
        for r in single:
            for e in senses(r[0]):
                if e not in en:
                    en.append(e)
        ex = None
        cands = []
        for r in single + multi[:12]:
            for h, j, e, k in examples(r[0], c):
                t = tokens(h, j)
                if t:
                    cands.append((k != 'sentence', not 6 <= len(han_chars(h)) <= 24, len(h), h, j, e, t))
        if cands:
            _, _, _, h, j, e, t = min(cands)
            ex = {'hanji': h, 'tailo': j, 'en': e, 'tokens': t, 'src': None, 'by': 'words.hk'}
        elif (written.get(c) or {}).get('hanzi'):
            w_ = written[c]
            h, j = w_['hanzi'], w_.get('jyutping', '')
            ex = {'hanji': h, 'tailo': j, 'en': w_.get('en', ''), 'tokens': tokens(h, j) or tokenize(h, j), 'src': None,
                  'by': 'written'}
        words, seen = [], set()
        for r in multi:
            if r[1] in seen or len(words) >= 5:
                continue
            s_ = senses(r[0])
            if not s_:
                continue
            seen.add(r[1])
            words.append({'hanji': r[1], 'tailo': r[2].replace('-', ' '), 'en': s_[0][:60],
                          'id': lookup(r[1], r[2])})
        if not en:
            en = ['in ' + ', '.join(w['hanji'] for w in words[:3])] if words else []
        groups[gid].append({'c': c, 'tailo': ' / '.join(x.replace('-', ' ') for x in reads), 'en': '; '.join(en[:2])[:140],
                            'zh': '', 'uses': 0, 'ex': ex, 'words': words, 'n': len(rows)})
    out = []
    for gid, han, en, _ in MORE_GROUPS:
        items = sorted(groups[gid], key=lambda x: -x['n'])
        if items:
            out.append({'id': 'more-' + gid, 'en': en, 'hanji': han, 'kind': 'more' + ('-vulgar' if gid == 'vulgar' else ''),
                        'items': items})
    return out


_yz = yuezi_build()

VIDEO = os.path.join(ROOT, 'course/video.yaml')
video = yaml.safe_load(open(VIDEO, encoding='utf-8')) if os.path.exists(VIDEO) else {'shows': []}
MUSIC = os.path.join(ROOT, 'course/music.yaml')
music = yaml.safe_load(open(MUSIC, encoding='utf-8')) if os.path.exists(MUSIC) else {'albums': []}
data = {'podcast': None, 'video': video, 'music': music, 'tones': tone_drill.build(lessons), 'grammar': grammar,
        'syllabus': syllabus, 'lessons': lessons, 'themes': themes, 'yuezi': [], 'accents': [], 'bridge': [],
        'dict': dictionary, 'lesson0': lesson0, 'built': datetime.date.today().isoformat(), 'recorded': 0}

# ---- 粵字 part (b), the characters not in the lessons yet, goes to a side file (app/dist/yuezi-more.json) that the
# page fetches the first time 粵字 is opened: with it inline, index.html grew by 2 MB and every start parsed it.
# index.html keeps the lesson and borderline groups and, for part (b), only each group's name and count. The side
# file holds its groups, the word cards only it uses (not those index.html has), and the font glyphs only it needs.
import copy  # noqa: E402
inline_dict = copy.deepcopy(dictionary)     # yuezi_more() adds cards and appends to the 'in' list of existing ones
more = yuezi_more()
data['yuezi'] = ([g for g in _yz if g['kind'] != 'borderline'] + [dict(g, items=[], n=len(g['items'])) for g in more]
                 + [g for g in _yz if g['kind'] == 'borderline'])
data['dict'] = inline_dict
# full cards for the words shown as buttons; a light card (no example, Mandarin, other readings, compounds) for words
# that are only tokens of an example sentence; nothing for cards the dictionary made on the way and nobody points to
full, light = [], []
for g in more:
    for it in g['items']:
        full += [w['id'] for w in it['words'] if w['id']]
        for t in (it['ex'] or {}).get('tokens') or []:
            if t.get('w'):
                light += [t['w']['id']] + t['w'].get('x', []) if t['w']['id'] else []
full = list(dict.fromkeys(i for i in full if i not in inline_dict))
for i in list(full):
    light += dictionary[i].get('comp') or dictionary[i].get('parts') or []
LIGHT_KEYS = ('hanji', 'tkey', 'gloss', 'gloss_src', 'check', 'cognate', 'source', 'rank')
side_dict = {}

def _bare(c):       # tailo (= tkey with spaces) is put back by the page; empty fields dropped (check: null has a meaning)
    return {k: v for k, v in c.items() if k != 'tailo' and (k == 'check' or v not in (None, [], ''))}


for i in full:
    c = _bare(dictionary[i])
    if c.get('in'):
        c['in'] = [p for p in c['in'] if p in inline_dict or p in full]
    side_dict[i] = c
for i in dict.fromkeys(light):
    if i not in inline_dict and i not in side_dict:
        c = _bare({k: v for k, v in dictionary[i].items() if k in LIGHT_KEYS})
        if dictionary[i].get('senses'):
            c['senses'], c['senses_src'] = dictionary[i]['senses'][:2], dictionary[i].get('senses_src')
        side_dict[i] = c
# words of part (b) that now also list, under "Used in", a word of index.html's cards
side_in = {i: [p for p in c['in'][len(inline_dict[i].get('in') or []):] if p in side_dict]
           for i, c in dictionary.items() if i in inline_dict and len(c.get('in') or []) > len(inline_dict[i].get('in') or [])}
side_in = {i: v for i, v in side_in.items() if v}

def _wid(h, t):     # a word's card id when it is the word read as shown (the usual case): the page rebuilds it
    return f"{h}|{t.replace(' ', '-')}"


for g in more:          # the page puts back what is the same for every token or item (yzUnpack in the template)
    for it in g['items']:
        for t in (it['ex'] or {}).get('tokens') or []:
            w = t.get('w')
            if w and w.get('s') == w.get('t'):
                del w['s']
            if w and w.get('id') and w['id'] == _wid(w['h'], w['t']):
                del w['id']
        for w in it['words']:
            if w['id'] and w['id'] == _wid(w['hanji'], w['tailo']):
                del w['id']
        for k, v in (('zh', ''), ('uses', 0)):
            if it.get(k) == v:
                del it[k]
        it.pop('n', None)
        if it['ex']:        # only the tokens are shown
            for k in ('src', 'hanji', 'tailo'):
                it['ex'].pop(k, None)
side = {'groups': {g['id']: g['items'] for g in more}, 'dict': side_dict, 'in': side_in}

dist_audio = os.path.join(ROOT, 'app/dist/audio')
shutil.rmtree(dist_audio, ignore_errors=True)
for rel in audio_used:
    os.makedirs(os.path.dirname(os.path.join(dist_audio, rel)), exist_ok=True)
    shutil.copy(os.path.join(AUDIO_DIR, rel), os.path.join(dist_audio, rel))
print(f'audio: {len(audio_used)} lines with a synthetic recording')

tpl = open(os.path.join(ROOT, 'app/index.template.html'), encoding='utf-8').read()
inline_text = json.dumps(data, ensure_ascii=False) + tpl.replace('㐀-鿿', '').replace('豈-﫿', '')
tpl = tpl.replace('/*__FONTS__*/', tailo_font_css() + '\n' + han_font_css(inline_text))
# the side file's own glyphs: injected as a <style> when it arrives (same font families, its characters only)
side['css'] = han_font_css(json.dumps(side, ensure_ascii=False), skip=inline_text)
os.makedirs(os.path.join(ROOT, 'app/dist'), exist_ok=True)
side_json = unicodedata.normalize('NFC', json.dumps(side, ensure_ascii=False, separators=(',', ':')))
open(os.path.join(ROOT, 'app/dist/yuezi-more.json'), 'w', encoding='utf-8').write(side_json)
# its name carries a hash of its content: a new build is fetched anew, and the service worker keeps the one it got
data['yzMore'] = 'yuezi-more.json?v=' + hashlib.sha1(side_json.encode()).hexdigest()[:10]
print(f'yuezi-more.json: {sum(len(g["items"]) for g in more)} characters, {len(side_dict)} word cards '
      f'({len(full)} full), {len(side_json.encode()) // 1024} KB')
payload = json.dumps(data, ensure_ascii=False).replace('</', '<\\/')
out = os.path.join(ROOT, 'app/dist/index.html')
open(out, 'w', encoding='utf-8').write(unicodedata.normalize('NFC', tpl.replace('/*__DATA__*/null', payload)))
from collections import Counter  # noqa: E402
_src = Counter((c.get('gloss_src') or ('written/course' if c.get('gloss') else 'none')).split(':')[0]
               for c in dictionary.values())
print('English on word cards:', ', '.join(f'{k} {v}' for k, v in _src.most_common()))
open(os.path.join(ROOT, 'app/dist/english-auto.txt'), 'w', encoding='utf-8').write(''.join(
    f"{c['hanji']}\t{c['tailo']}\t{c.get('gloss_src') or 'none'}\t{c.get('gloss') or ''}\n"
    for c in dictionary.values() if c.get('gloss_src') or not c.get('gloss')))
print(out, f'{len(lessons)} lessons, {len(inline_dict)} dictionary cards, {os.path.getsize(out) // 1024} KB')
