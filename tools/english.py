"""English for the word cards: one gloss for every word, with where it came from.

Order (first one found wins):
  1. course    English written in the lessons' and themes' `new_words` (passed in by build_app.py)
  2. written   course/glosses_en.tsv: short glosses written for the course (hanzi, jyutping, English)
  3. wordshk   words.hk's English for the same characters + reading (its usual sense; non-commercial licence)
  4. cccanto   CC-Canto's English for the same characters + reading
  5. cedict    CC-CEDICT's English for the same characters, matched by CC-Canto's Jyutping for that entry
     (for a single character the order of 3–5 is reversed: cedict, cccanto, wordshk)
  6. mandarin  CC-CEDICT English of the word's Mandarin equivalent (`mandarin:<word>`), shown as automatic
  7. parts     glosses of the characters joined with " + "

Used by tools/build_app.py and by the private module's build, so a word gets the same gloss everywhere.
The keys are (characters, Jyutping key) pairs: a homophone never takes another word's gloss.
"""
import csv
import json
import os
import re

import jyutping as jp

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WRITTEN = os.path.join(ROOT, 'course/glosses_en.tsv')
CEDICT_JSON = os.path.join(ROOT, 'data/raw/cedict/package/cedict.json')
SKIP = ('variant of', 'old variant', 'CL:', 'used in ', 'see ', 'also written', 'abbr. for', 'surname ')


def load_cedict(path=CEDICT_JSON):
    ced = {}
    if os.path.exists(path):
        for e in json.load(open(path, encoding='utf-8')):
            if e['pinyin'][:1].isupper():      # proper names: keep only if nothing else
                ced.setdefault(e['traditional'], e)
            elif e['traditional'] not in ced or ced[e['traditional']]['pinyin'][:1].isupper():
                ced[e['traditional']] = e
    return ced


def cedict_en(ced, word):
    e = ced.get(word)
    if not e:
        return None
    gs = [g for g in e['english'] if not g.startswith(SKIP)]
    return '; '.join(gs[:3]) or None


def load_written(path=WRITTEN):
    out = {}
    if os.path.exists(path):
        with open(path, encoding='utf-8') as f:
            for row in csv.reader(f, delimiter='\t'):
                if len(row) >= 3 and row[0] and not row[0].startswith('#'):
                    out[(row[0], jp.key(row[1]))] = row[2]
    return out


def clip(text, n=90, senses=4):
    """A dictionary definition shortened for a card's English line: at most `senses` senses, about `n` characters."""
    text = re.sub(r'\s*\([^()]{26,}\)', '', text or '')          # long asides stay on the full sense list
    parts = [p.strip() for p in re.split(r';\s*', text) if p.strip()][:senses]
    out = ''
    for p in parts:
        nxt = f'{out}; {p}' if out else p
        if out and len(nxt) > n:
            break
        out = nxt
    return out if len(out) <= n + 10 else out[:n].rsplit(' ', 1)[0].rstrip(',;:') + '…'


STOP = {'to', 'a', 'an', 'the', 'of', 'be', 'or', 'and', 'in', 'on', 'for', 'with', 'one', "one's", 'sb', 'sth',
        'something', 'someone', 'used', 'as', 'is', 'by', 'at', 'get', 'being', 'make', 'have', 'person', 'thing'}


def _bag(text):
    """Content words cut to 5 letters, so economise = economize and blamed = blame."""
    return {w[:5] for w in re.findall(r"[a-z']+", (text or '').lower()) if w not in STOP and len(w) > 2}


def wordshk_entries(con, hanzi, k):
    """words.hk entry ids for characters + reading, best first. words.hk splits a word into one entry per part of
    speech or meaning (嘢 'thing' and 嘢 the money suffix), in no particular order: the entry whose English shares
    most words with CC-Canto / CC-CEDICT for the same reading comes first (the usual sense), then the fullest."""
    try:
        ids = [r[0] for r in con.execute('SELECT DISTINCT id FROM wordshk WHERE hanzi=? AND jkey=?', (hanzi, k))]
        if len(ids) < 2:
            return ids
        weight = {}               # a reference sense counts more the earlier it is listed (dictionaries put the usual first)
        for (e,) in con.execute("SELECT english FROM canto WHERE trad=? AND jkey=? ORDER BY src='cedict' DESC", (hanzi, k)):
            for r, sense in enumerate(e.split('; ')):
                for w in _bag(sense):
                    weight[w] = max(weight.get(w, 0), 1 / (r + 1))
        scored = []
        for i in ids:
            ss = con.execute('SELECT en FROM wordshk_sense WHERE id=? ORDER BY n', (i,)).fetchall()
            first = _bag(ss[0][0]) if ss else set()
            nx = con.execute('SELECT COUNT(*) FROM wordshk_ex WHERE id=?', (i,)).fetchone()[0]
            scored.append((-sum(weight.get(w, 0) for w in first), -(3 * len(ss) + nx), i))
        return [i for *_, i in sorted(scored)]
    except Exception:          # a database built before the words.hk layer
        return []


class English:
    def __init__(self, con, course, ced):
        self.con, self.course, self.ced = con, course, ced
        self.written = load_written()

    def gloss(self, hanzi, k, parts=None):
        if (hanzi, k) in self.course:
            return self.course[(hanzi, k)], 'course'
        if (hanzi, k) in self.written:
            return self.written[(hanzi, k)], 'written'
        # a single character: CC-CEDICT and CC-Canto list the usual sense first (行 'to walk'); words.hk splits a
        # character into entries in no set order, so it comes last. A word: words.hk first, it is Cantonese-native.
        order = ('cedict', 'cccanto', 'wordshk') if len(hanzi) == 1 else ('wordshk', 'cccanto', 'cedict')
        for src in order:
            if src == 'wordshk':
                for eid in wordshk_entries(self.con, hanzi, k):
                    r = self.con.execute("SELECT en FROM wordshk_sense WHERE id=? AND en!='' ORDER BY n LIMIT 1",
                                         (eid,)).fetchone()
                    if r:
                        return clip(r[0]), 'wordshk'
                continue
            try:
                r = self.con.execute('SELECT english FROM canto WHERE trad=? AND jkey=? AND src=?', (hanzi, k, src)).fetchone()
            except Exception:
                r = None
            if r:
                return clip(r[0]), src
        r = self.con.execute('SELECT mandarin_best FROM entry WHERE hanzi=? AND jkey=? AND mandarin_best IS NOT NULL',
                             (hanzi, k)).fetchone()
        if r:
            en = cedict_en(self.ced, r[0])
            if en:
                return en, f'mandarin:{r[0]}'
        if parts and all(g for g, _ in parts):
            return ' + '.join(g for g, _ in parts), 'parts'
        return None, None
