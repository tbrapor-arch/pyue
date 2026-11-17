"""Readers for the two Cantonese dictionaries added to `make db` (see data/fetch.sh and ATTRIBUTION.md).

  CC-Canto (Pleco, CC BY-SA 3.0)    cccanto-webdist.txt: Cantonese words with English
                                    cccedict-canto-readings.txt: Jyutping for CC-CEDICT's entries
  words.hk 粵典 (Non-Commercial Open Data License 1.0)
                                    the Yomitan build: senses in Cantonese and English, example sentences with Jyutping

Both are read into their own tables by tools/build_db.py; they never add rows to `entry` (rime-cantonese stays the
word list that cuts lines), so adding them changes cards, not cuts.
"""
import json
import re
import zipfile

LINE = re.compile(r'^(\S+) (\S+) \[([^\]]*)\] \{([^}]*)\}(?: /(.*)/)?')


def cccanto(path):
    """(traditional, jyutping, [English senses]) per line. Comments after '#' are dropped; CC-Canto writes one
    line per reading, and a few lines give alternatives as 'a1 / b1'."""
    with open(path, encoding='utf-8') as f:
        for line in f:
            if line.startswith('#'):
                continue
            line = line.split(' # ')[0].rstrip('\n')
            m = LINE.match(line)
            if not m:
                continue
            trad, _, _, jy, defs = m.groups()
            senses = [d.strip() for d in (defs or '').split('/') if d.strip()]
            for j in jy.split('/'):
                if j.strip():
                    yield trad, j.strip().lower(), senses


def cedict_readings(path):
    """(traditional, pinyin, jyutping) for CC-CEDICT entries: lets a CC-CEDICT gloss be matched by reading."""
    with open(path, encoding='utf-8') as f:
        for line in f:
            if line.startswith('#'):
                continue
            m = LINE.match(line.rstrip('\n'))
            if m:
                trad, _, py, jy, _ = m.groups()
                yield trad, py, jy.strip().lower()


# ---- words.hk (Yomitan structured content)
def _tag(node):
    return (node.get('data') or {}).get('wordshk') if isinstance(node, dict) else None


def _find(node, name, out=None):
    """Every sub-node whose data-wordshk is `name` (not searching inside a match)."""
    out = [] if out is None else out
    if isinstance(node, list):
        for x in node:
            _find(x, name, out)
    elif isinstance(node, dict):
        if _tag(node) == name:
            out.append(node)
        else:
            _find(node.get('content'), name, out)
    return out


def _lang(node, lang, out=None):
    out = [] if out is None else out
    if isinstance(node, list):
        for x in node:
            _lang(x, lang, out)
    elif isinstance(node, dict):
        if node.get('lang') == lang and node.get('tag') == 'li':
            out.append(node)
        else:
            _lang(node.get('content'), lang, out)
    return out


def _text(node):
    """Plain text, without the Jyutping of ruby (rt)."""
    if isinstance(node, str):
        return node
    if isinstance(node, list):
        return ''.join(_text(x) for x in node)
    if isinstance(node, dict):
        if node.get('tag') == 'rt':
            return ''
        return _text(node.get('content'))
    return ''


def _ruby(node, out=None):
    """(base, rt) pairs and plain strings, in order."""
    out = [] if out is None else out
    if isinstance(node, str):
        out.append((node, None))
    elif isinstance(node, list):
        for x in node:
            _ruby(x, out)
    elif isinstance(node, dict):
        if node.get('tag') == 'ruby':
            c = node.get('content')
            c = c if isinstance(c, list) else [c]
            base = ''.join(x for x in c if isinstance(x, str))
            rt = ''.join(_text(x.get('content')) for x in c if isinstance(x, dict) and x.get('tag') == 'rt')
            out.append((base, rt.strip() or None))
        elif node.get('tag') != 'rt':
            _ruby(node.get('content'), out)
    return out


def _example(node):
    yue = _lang(node, 'yue')
    en = _lang(node, 'en')
    if not yue:
        return None
    pairs = _ruby(yue[0])
    han = ''.join(b for b, _ in pairs).strip()
    jy = ' '.join(r for _, r in pairs if r)
    return {'hanzi': han, 'jyutping': jy, 'en': _text(en[0]).strip() if en else ''}


def wordshk(path):
    """One dict per words.hk entry: id (a running number), pos, heads [(characters, jyutping)], senses [{en, yue, ex: [...]}]."""
    z = zipfile.ZipFile(path)
    seen, n = set(), 0
    for name in sorted(z.namelist()):
        if not name.startswith('term_bank'):
            continue
        for e in json.loads(z.read(name)):
            term, reading, pos, sc = e[0], e[1], e[2], e[5]
            heads = [(b, r) for hw in _find(sc, 'headword') for b, r in _ruby(hw) if r]
            key = tuple(heads) or ((term, reading),)
            body = json.dumps(sc, sort_keys=True, ensure_ascii=False)
            if body in seen:           # the Yomitan build repeats an entry once per variant spelling
                continue
            seen.add(body)
            n += 1
            senses = []
            for s in _find(sc, 'sense'):
                ex = _find(s, 'explanation')
                en = ' '.join(_text(x).strip() for x in _lang(ex, 'en')) if ex else ''
                yue = ' '.join(_text(x).strip() for x in _lang(ex, 'yue')) if ex else ''
                exs = []
                for kind in ('sentence', 'phrase'):
                    for block in _find(s, kind):
                        for x in _find(block, 'example'):
                            got = _example(x)
                            if got and got['hanzi']:
                                exs.append(dict(got, kind=kind))
                senses.append({'en': en, 'yue': yue, 'ex': exs})
            yield {'id': n, 'pos': pos or '', 'heads': list(key), 'senses': senses}
