"""Build the reader app: course/ + database -> app/dist/index.html (one self-contained file).

  python3 -I tools/build_app.py

Same template and data shape as Tsheh-tû (app/index.template.html), so fixes carry over between the two apps. The
JSON keeps Tsheh-tû's field names: `hanji` = characters, `tailo` = Jyutping, `en` = English. Lesson files use
`hanzi`, `jyutping`, `en` (see course/perfectionnement/_template.yaml); this script maps them.
"""
import base64
import datetime
import glob
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


def han_font_css(text):
    """'PyueExt': the LXGW WenKai TC glyphs of every Chinese character in the app that Iansui (Tsheh-tû's character
    font) does not have — Cantonese characters such as 哋, 咗, 嘢. Both fonts are made from Klee One, so every character
    keeps Tsheh-tû's handwriting look (sy-zy does the same with LXGW WenKai for simplified characters).
    Characters missing from both come from Plangothic ('TaigiExt', a plain sans) as a last resort."""
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
    need = sorted({ord(c) for c in text if (0x3400 <= ord(c) <= 0x9fff or 0xf900 <= ord(c) <= 0xfaff or ord(c) >= 0x20000)
                   and ord(c) not in have and unicodedata.category(c) != 'Cn'})
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

VIDEO = os.path.join(ROOT, 'course/video.yaml')
video = yaml.safe_load(open(VIDEO, encoding='utf-8')) if os.path.exists(VIDEO) else {'shows': []}
MUSIC = os.path.join(ROOT, 'course/music.yaml')
music = yaml.safe_load(open(MUSIC, encoding='utf-8')) if os.path.exists(MUSIC) else {'albums': []}
data = {'podcast': None, 'video': video, 'music': music, 'tones': tone_drill.build(lessons), 'grammar': grammar,
        'syllabus': syllabus, 'lessons': lessons, 'themes': themes, 'accents': [], 'bridge': [],
        'dict': dictionary, 'lesson0': lesson0, 'built': datetime.date.today().isoformat(), 'recorded': 0}

tpl = open(os.path.join(ROOT, 'app/index.template.html'), encoding='utf-8').read()
tpl = tpl.replace('/*__FONTS__*/', tailo_font_css() + '\n' + han_font_css(json.dumps(data, ensure_ascii=False) + tpl.replace('㐀-鿿', '').replace('豈-﫿', '')))
payload = json.dumps(data, ensure_ascii=False).replace('</', '<\\/')
os.makedirs(os.path.join(ROOT, 'app/dist'), exist_ok=True)
out = os.path.join(ROOT, 'app/dist/index.html')
open(out, 'w', encoding='utf-8').write(unicodedata.normalize('NFC', tpl.replace('/*__DATA__*/null', payload)))
from collections import Counter  # noqa: E402
_src = Counter((c.get('gloss_src') or ('written/course' if c.get('gloss') else 'none')).split(':')[0]
               for c in dictionary.values())
print('English on word cards:', ', '.join(f'{k} {v}' for k, v in _src.most_common()))
open(os.path.join(ROOT, 'app/dist/english-auto.txt'), 'w', encoding='utf-8').write(''.join(
    f"{c['hanji']}\t{c['tailo']}\t{c.get('gloss_src') or 'none'}\t{c.get('gloss') or ''}\n"
    for c in dictionary.values() if c.get('gloss_src') or not c.get('gloss')))
print(out, f'{len(lessons)} lessons, {len(dictionary)} dictionary cards, {os.path.getsize(out) // 1024} KB')
