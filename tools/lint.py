"""Check lesson files against the vocabulary database.

  python3 -I tools/lint.py [lesson.yaml ...]   (default: course/perfectionnement/[0-9]*.yaml, course/themes/*.yaml)

Checks
  E  missing required fields
  E  invalid Jyutping syllable
  E  characters and Jyutping do not line up (one syllable per character; a Latin word such as a name counts as one)
  W  a character read with a reading the database does not list for it (changed tone 變音, or a typo)
  W  a hyphenated word not in the database (every character is still known)
  E  new_words entry not in the database with those characters + reading
Exit code 1 if any E.

Line format: `hanzi` (written Cantonese, traditional) and `jyutping` (syllables with tone numbers, separated by
spaces). Hyphens join the syllables of one word ('zung1-ji3') when the dictionary cut should be overridden; without
hyphens the build cuts the line into dictionary words by itself.
"""
import glob
import os
import re
import sqlite3
import sys

import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import jyutping as jp  # noqa: E402

ROOT = os.path.dirname(HERE)
DB = os.path.join(ROOT, 'data/build/yue.db')
CJK = r'[㐀-鿿\U00020000-\U0003ffff豈-﫿]'
UNIT_RE = re.compile(CJK + r"|[A-Za-zÀ-ɏ]+[0-9]?")
PUNCT = ".,!?;:'\"「」『』、。，！？；：()（）…—–“”‘’《》〈〉"


def units(hanzi):
    """Characters (and Latin words) of a line, in order."""
    return UNIT_RE.findall(hanzi)


def words(jyut):
    """A Jyutping line -> list of words, each a list of items. An item is a syllable ('zung1') or a bare Latin word
    ('Sam'). Words are separated by spaces unless the line uses hyphens, in which case every space-separated chunk
    is one word ('zung1-ji3')."""
    out = []
    for chunk in re.split(r'\s+', jyut.strip()):
        chunk = chunk.strip(PUNCT)
        if not chunk:
            continue
        parts = [p.strip(PUNCT) for p in chunk.split('-') if p.strip(PUNCT)]
        items = []
        for p in parts:
            syl = jp.syllables(p)
            if syl and ''.join(syl) == p.lower():
                items.extend(syl)
            else:
                items.append(p)
        out.append(items)
    return out


def hyphenated(jyut):
    return '-' in jyut


def is_syl(item):
    return bool(re.fullmatch(r'[a-z]+[1-6]', item))


def load_db():
    con = sqlite3.connect(DB)
    pairs = set(con.execute('SELECT hanzi, jkey FROM entry'))
    return con, pairs


def check_line(where, hanzi, jyut, pairs, out):
    us = units(hanzi)
    ws = words(jyut)
    items = [i for w in ws for i in w]
    for i in items:
        if is_syl(i) and not jp.is_syllable(i):
            out.append(('E', where, f'invalid Jyutping syllable {i}'))
    if len(us) != len(items):
        out.append(('E', where, f'{len(us)} characters/words but {len(items)} Jyutping items: {hanzi} | {jyut}'))
        return
    k = 0
    for w in ws:
        chars = us[k:k + len(w)]
        k += len(w)
        for c, s in zip(chars, w):
            if re.match(CJK, c) and is_syl(s) and (c, s) not in pairs:
                out.append(('W', where, f'{c} read {s}: not a reading listed for it'))
        if hyphenated(jyut) and len(w) > 1 and all(re.match(CJK, c) for c in chars):
            if (''.join(chars), '-'.join(w)) not in pairs:
                out.append(('W', where, f'word {"".join(chars)} {"-".join(w)} not in the database'))


def lint_file(f, pairs):
    out = []
    d = yaml.safe_load(open(f, encoding='utf-8'))
    name = os.path.relpath(f, ROOT)
    if 'sections' in d:          # theme file
        for sec in d['sections']:
            for w in sec.get('words', []):
                check_line(f'{name} {w.get("hanzi")}', w['hanzi'], w['jyutping'], pairs, out)
        return out
    for key in ('id', 'title', 'dialogue'):
        if key not in d:
            out.append(('E', name, f'missing {key}'))
    for ln in d.get('dialogue') or []:
        for key in ('n', 'hanzi', 'jyutping', 'en'):
            if key not in ln:
                out.append(('E', f'{name} line {ln.get("n")}', f'missing {key}'))
        if 'hanzi' in ln and 'jyutping' in ln:
            check_line(f'{name} line {ln["n"]}', ln['hanzi'], ln['jyutping'], pairs, out)
    for w in d.get('new_words') or []:
        if (w['hanzi'], jp.key(w['jyutping'])) not in pairs:
            out.append(('E', f'{name} new word', f'{w["hanzi"]} {w["jyutping"]} not in the database'))
    return out


def main():
    files = sys.argv[1:] or sorted(glob.glob(os.path.join(ROOT, 'course/perfectionnement/[0-9]*.yaml'))
                                   + glob.glob(os.path.join(ROOT, 'course/themes/*.yaml')))
    _, pairs = load_db()
    errors = 0
    for f in files:
        for level, where, msg in lint_file(f, pairs):
            print(f'{level} {where}: {msg}')
            errors += level == 'E'
    print(f'{len(files)} files, {errors} errors')
    sys.exit(1 if errors else 0)


if __name__ == '__main__':
    main()
