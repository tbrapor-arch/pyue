"""English for the word cards: one gloss for every word, with where it came from.

Order (first one found wins):
  1. course    English written in the lessons' and themes' `new_words` (passed in by build_app.py)
  2. written   course/glosses_en.tsv: short glosses written for the course (hanzi, jyutping, English)
  3. mandarin  CC-CEDICT English of the word's Mandarin equivalent (`mandarin:<word>`), shown as automatic
  4. parts     glosses of the characters joined with " + "

Used by tools/build_app.py and by the private module's build, so a word gets the same gloss everywhere.
The keys are (characters, Jyutping key) pairs: a homophone never takes another word's gloss.
"""
import csv
import json
import os

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


class English:
    def __init__(self, con, course, ced):
        self.con, self.course, self.ced = con, course, ced
        self.written = load_written()

    def gloss(self, hanzi, k, parts=None):
        if (hanzi, k) in self.course:
            return self.course[(hanzi, k)], 'course'
        if (hanzi, k) in self.written:
            return self.written[(hanzi, k)], 'written'
        r = self.con.execute('SELECT mandarin_best FROM entry WHERE hanzi=? AND jkey=? AND mandarin_best IS NOT NULL',
                             (hanzi, k)).fetchone()
        if r:
            en = cedict_en(self.ced, r[0])
            if en:
                return en, f'mandarin:{r[0]}'
        if parts and all(g for g, _ in parts):
            return ' + '.join(g for g, _ in parts), 'parts'
        return None, None
