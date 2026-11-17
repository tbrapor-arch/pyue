"""Check the course's Jyutping against the dictionaries and print only the suspects.

  python3 -I tools/verify_words.py [lesson.yaml ...]     (default: course/perfectionnement/*.yaml, course/themes/*.yaml)
  python3 -I tools/verify_words.py --all                  also list the accepted changed tones

Run by `make lint` after tools/lint.py. It never fails the build: it prints a short list for a person to look at.
The private module's build uses the same functions (`Verifier`) on its own text.

What is checked
  1. every `new_words` entry: are these characters with this reading in CC-Canto, words.hk or CC-CEDICT (through
     CC-Canto's Jyutping)? rime-cantonese alone is the app's word list, so it does not count as a confirmation.
  2. every line, cut into words as the app cuts it: a word of two or more characters whose reading a dictionary
     confirms is fine. Otherwise each character is checked: a reading rime gives under 5 % of that character's uses
     (行 hong4 alone, 長 zoeng2 alone) or not at all is a suspect, unless no dictionary has the character at all.

Accepted, not suspects
  changed tone (變音): the reading is a listed reading of the character with tone 1 or 2 instead (糖 tong4 -> tong2,
  碟 dip6 -> dip2), as Cantonese speakers say it. Listed with --all.

Suspect classes, worst first
  unknown    no dictionary lists this character with this reading (a typo, or a reading to explain in a note)
  rare       rime gives this reading under 5 % of the character's uses, and no dictionary confirms the word
  unconfirmed  a new word in rime-cantonese only (often fine: rime lists many phrases; worth one look)
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
import cards  # noqa: E402
import english  # noqa: E402

ROOT = os.path.dirname(HERE)
RARE = 5
ORDER = {'unknown': 0, 'rare': 1, 'unconfirmed': 2, 'changed tone': 3}


class Verifier:
    def __init__(self, con):
        self.con = con
        self.share = {}            # character -> {reading key: % of uses} (rime)
        for h, k, s in con.execute("SELECT hanzi, jkey, share FROM entry WHERE kind='char'"):
            d = self.share.setdefault(h, {})
            d[k] = max(d.get(k) or 0, s or 0) if s is not None else d.get(k)
        self.items = []

    def _sources(self, h, k):
        return [s for s in cards.attested(h, k) if s != 'rime']

    def _char(self, where, c, s, text):
        """One character's reading: None if fine, else (class, detail)."""
        rd = self.share.get(c)
        other = bool(self._sources(c, s))
        if rd is None and not other:
            return None                                      # a character no dictionary has: nothing to compare
        if rd and s in rd:
            sh = rd[s]
            if sh is None or sh >= RARE or other and sh >= 1:
                return None
            rest = max(0, 100 - sum(v for v in rd.values() if v))     # readings rime gives no share for split the rest
            best = max(rd, key=lambda r: rd[r] if rd[r] is not None else rest / max(1, list(rd.values()).count(None)))
            return 'rare', f'{c} read {s}: {sh} % of its uses in rime (usually {best.replace("-", " ")})'
        if other:
            return None                                      # CC-Canto or words.hk has it
        base = re.sub(r'[1-6]$', '', s)
        if s[-1] in '12' and any(re.sub(r'[1-6]$', '', r) == base for r in (rd or {})):
            return 'changed tone', f'{c} read {s} (listed: {", ".join(sorted(rd))})'
        return 'unknown', f'{c} read {s}: not a reading of {c} in any dictionary (listed: {", ".join(sorted(rd or {}))})'

    def line(self, where, hanzi, jyut):
        """A line as the app cuts it. Words a dictionary confirms are fine; the rest is checked by character."""
        for t in cards.tokenize(hanzi, jyut):
            w = t.get('w')
            if not w or not w.get('id'):
                continue
            h, k = w['h'], w['t'].replace(' ', '-')
            chars, syls = cards.UNIT_RE.findall(h), k.split('-')
            if len(chars) > 1 and self._sources(h, k):
                continue
            for c, s in zip(chars, syls):
                if not cards.is_han(c):
                    continue
                got = self._char(where, c, s, hanzi)
                if got:
                    self.items.append((got[0], where, got[1], hanzi))

    def word(self, where, hanzi, jyut):
        k = jp.key(jyut)
        if self._sources(hanzi, k):
            return
        if len(cards.UNIT_RE.findall(hanzi)) == 1:
            got = self._char(where, hanzi, k, hanzi)
            if got:
                self.items.append((got[0], where, got[1], hanzi))
            return
        self.items.append(('unconfirmed', where, f'{hanzi} {jyut.replace("-", " ")}: in rime-cantonese only', hanzi))
        self.line(where, hanzi, jyut)                       # and its characters, one by one

    def report(self, show_all=False, out=sys.stdout):
        seen, rows = set(), []
        for cls, where, msg, text in sorted(self.items, key=lambda x: (ORDER[x[0]], x[1])):
            if (cls, where, msg) in seen:
                continue
            seen.add((cls, where, msg))
            rows.append((cls, where, msg))
        from collections import Counter
        n = Counter(c for c, _, _ in rows)
        for cls, where, msg in rows:
            if cls != 'changed tone' or show_all:
                print(f'{cls:12} {where}: {msg}', file=out)
        print('verify: ' + ', '.join(f'{n[c]} {c}' for c in ORDER if n[c]) if n else 'verify: no suspects', file=out)
        return rows


def open_db():
    con = sqlite3.connect(os.path.join(ROOT, 'data/build/yue.db'))
    ced = english.load_cedict()
    cards.init(con, english.English(con, {}, ced), ced)
    return con


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    files = args or sorted(glob.glob(os.path.join(ROOT, 'course/perfectionnement/[0-9]*.yaml'))
                           + glob.glob(os.path.join(ROOT, 'course/themes/*.yaml')))
    v = Verifier(open_db())
    for f in files:
        d = yaml.safe_load(open(f, encoding='utf-8'))
        name = os.path.relpath(f, ROOT).replace('course/perfectionnement/', 'P').replace('.yaml', '')
        for ln in d.get('dialogue') or []:
            if ln.get('hanzi') and ln.get('jyutping'):
                v.line(f'{name} line {ln["n"]}', ln['hanzi'], ln['jyutping'])
        for w in d.get('new_words') or []:
            v.word(f'{name} new word', w['hanzi'], w['jyutping'])
        for sec in d.get('sections') or []:
            for w in sec.get('words', []):
                v.word(f'{name} {sec.get("n")}', w['hanzi'], w['jyutping'])
    v.report('--all' in sys.argv)


if __name__ == '__main__':
    main()
