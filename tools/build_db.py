"""Build data/build/yue.db from data/raw (see data/fetch.sh).

  python3 -I tools/build_db.py data/raw data/build/yue.db
"""
import json
import os
import re
import sqlite3
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import jyutping as jp  # noqa: E402

CORE_N = 5000


def rime_rows(path):
    """Body lines of a rime .dict.yaml: (characters, jyutping, weight or None)."""
    with open(path, encoding='utf-8') as f:
        body = False
        for line in f:
            line = line.rstrip('\n')
            if line == '...':
                body = True
                continue
            if not body or not line or line.startswith('#'):
                continue
            parts = line.split('\t')
            if len(parts) < 2:
                continue
            w = parts[2] if len(parts) > 2 else None
            yield parts[0], parts[1], w


CANT = re.compile(r'Cantonese|\(Cant\.\)')
EQUIV = re.compile(r'Mandarin equivalent: ([^|\]\[)]+)')


def classify(con):
    """cognate: same (an ordinary Mandarin word), partial (Mandarin has the characters but CC-CEDICT marks a
    Cantonese, dialect or literary sense: 係, 睇, 街市), different (Cantonese-only: not in CC-CEDICT, or every sense
    is marked Cantonese: 佢, 嘢, 咗). mandarin_best: the characters themselves, or CC-CEDICT's 'Mandarin equivalent'."""
    senses = {}
    for t, e in con.execute('SELECT trad, english FROM cedict'):
        senses.setdefault(t, []).append(e or '')
    upd = []
    for (h,) in con.execute('SELECT DISTINCT hanzi FROM entry').fetchall():
        es = senses.get(h)
        if not es:
            upd.append(('different', None, h))
            continue
        marked = [bool(CANT.search(e)) for e in es]
        eq = next((m.group(1) for e in es for m in [EQUIV.search(e)] if m), None)
        if all(marked):
            upd.append(('different', eq, h))
        elif any(marked) or any(re.search(r'\((dialect|literary)\)', e) for e in es):
            upd.append(('partial', h, h))
        else:
            upd.append(('same', h, h))
    con.executemany('UPDATE entry SET cognate=?, mandarin_best=? WHERE hanzi=?', upd)


POSWORD = re.compile(r'^\((noun|verb|adjective|adverb|adj\.|adv\.|pronoun|particle|measure word|classifier|'
                     r'conjunction|preposition|interjection|idiom|phrase|expression|[a-z ]+)\)\s*', re.I)


def canto_senses(defs):
    """CC-Canto senses, cleaned: no '(verb)' label, numbered senses split, 'Mandarin equivalent' and cross-references
    dropped (the card has its own Mandarin section), '(Cantonese)' removed (every word here is Cantonese)."""
    out = []
    for d in defs:
        d = POSWORD.sub('', d.strip())
        for s in re.split(r'\s*(?:^|\s)\d+\.\s+', d):
            s = re.sub(r'\s*\(Cantonese\)', '', s).strip(' ;,')
            if not s or s.startswith(('Mandarin equivalent', 'see also', 'see ', 'variant of', 'old variant', 'CL:')):
                continue
            if s.lower() not in {x.lower() for x in out}:
                out.append(s)
    return out


def canto_layer(con, raw):
    """CC-Canto, CC-CEDICT matched by Jyutping, and words.hk, each in its own table (see schema.sql)."""
    import yue_dicts
    nw = 0
    p = os.path.join(raw, 'wordshk')
    zips = sorted(f for f in os.listdir(p) if f.endswith('.zip')) if os.path.isdir(p) else []
    if zips:
        heads, senses, exs = [], [], []
        for e in yue_dicts.wordshk(os.path.join(p, zips[-1])):
            nw += 1
            for h, j in e['heads']:
                j = j.lower()
                if all(jp.is_syllable(s) for s in jp.syllables(j)):
                    heads.append((e['id'], h, jp.key(j), e['pos']))
            for n, s in enumerate(e['senses']):
                senses.append((e['id'], n, s['en'].replace('#', ''), s['yue'].replace('#', '')))
                for x in s['ex']:
                    exs.append((e['id'], n, x['hanzi'], x['jyutping'], x['en'], x['kind']))
        con.executemany('INSERT INTO wordshk VALUES (?,?,?,?)', heads)
        con.executemany('INSERT INTO wordshk_sense VALUES (?,?,?,?)', senses)
        con.executemany('INSERT INTO wordshk_ex VALUES (?,?,?,?,?,?)', exs)
        con.execute('INSERT INTO source VALUES (?,?,?,?,?,?)', (
            'wordshk', 'words.hk 粵典', zips[-1][9:19], 'Non-Commercial Open Data License 1.0', 0,
            'Cantonese and English senses, example sentences'))
    cc = os.path.join(raw, 'cc-canto')
    rows, n_cc = {}, 0
    p = os.path.join(cc, 'cccanto-webdist.txt')
    if os.path.exists(p):
        for trad, j, defs in yue_dicts.cccanto(p):
            if not all(jp.is_syllable(s) for s in jp.syllables(j)):
                continue
            rows.setdefault((trad, jp.key(j), 'cccanto'), []).extend(canto_senses(defs))
    p = os.path.join(cc, 'cccedict-canto-readings.txt')
    if os.path.exists(p):
        eng = {}
        for t, py, e in con.execute('SELECT trad, pinyin, english FROM cedict'):
            eng.setdefault((t, py), e)
        reads = [r for r in yue_dicts.cedict_readings(p) if not r[1][:1].isupper()]
        n_j = {}                  # how many Cantonese readings CC-Canto gives each CC-CEDICT entry
        for trad, py, j in reads:
            n_j.setdefault((trad, py), set()).add(j)
        # an entry read only one way in Cantonese is that reading's own sense (行 xíng -> hang4 'to walk'); an entry
        # with several readings (行 háng -> hong4, hang4 'row') is listed after it
        # two entries with the same Cantonese reading (要 yào 'to want', yāo 'to demand': both jiu3): the one whose
        # English shares more words with words.hk's senses for that reading comes first
        import english
        wbag = {}
        for h, k, en in con.execute('SELECT w.hanzi, w.jkey, s.en FROM wordshk w JOIN wordshk_sense s ON s.id=w.id'):
            wbag.setdefault((h, k), set()).update(english._bag(en))

        def rank(r):
            e = eng.get((r[0], r[1])) or ''
            ws = wbag.get((r[0], jp.key(r[2])), set())
            return (len(n_j[(r[0], r[1])]), -len(english._bag(e.split('; ')[0]) & ws), -len(english._bag(e) & ws))
        for trad, py, j in sorted(reads, key=rank):
            e = eng.get((trad, py))
            if e and all(jp.is_syllable(s) for s in jp.syllables(j)):
                rows.setdefault((trad, jp.key(j), 'cedict'), []).extend(canto_senses(e.split('; ')))
    out = []
    for (t, k, src), ss in rows.items():
        uniq = list(dict.fromkeys(ss))
        if uniq:
            out.append((t, k, '; '.join(uniq), src))
            n_cc += src == 'cccanto'
    con.executemany('INSERT INTO canto VALUES (?,?,?,?)', out)
    con.executemany('INSERT INTO source VALUES (?,?,?,?,?,?)', [
        ('cccanto', 'CC-Canto (Pleco)', '2017', 'CC BY-SA 3.0', 1, 'English for Cantonese words; Jyutping for CC-CEDICT'),
    ])
    print(f'Cantonese dictionaries: {len(out)} CC-Canto/CC-CEDICT rows ({n_cc} CC-Canto), {nw} words.hk entries')


def main(raw, out):
    rime = os.path.join(raw, 'rime-cantonese')
    if os.path.exists(out):
        os.remove(out)
    con = sqlite3.connect(out)
    con.executescript(open(os.path.join(HERE, 'schema.sql'), encoding='utf-8').read())
    con.executemany('INSERT INTO source VALUES (?,?,?,?,?,?)', [
        ('rime', 'rime-cantonese (CanCLID)', '2026', 'CC BY 4.0', 1, 'words + character readings'),
    ])
    seen = set()
    rows = []
    for ch, j, w in rime_rows(os.path.join(rime, 'jyut6ping3.chars.dict.yaml')):
        if not all(jp.is_syllable(s) for s in jp.syllables(j)) or (ch, j) in seen:
            continue
        seen.add((ch, j))
        share = int(w.rstrip('%')) if w and w.endswith('%') else None
        rows.append(('rime', ch, j, jp.key(j), jp.toneless(j), 'char', share))
    for wd, j, _ in rime_rows(os.path.join(rime, 'jyut6ping3.words.dict.yaml')):
        syl = jp.syllables(j)
        if not syl or not all(jp.is_syllable(s) for s in syl) or (wd, j) in seen:
            continue
        seen.add((wd, j))
        rows.append(('rime', wd, j, jp.key(j), jp.toneless(j), 'word' if len(wd) > 1 else 'char', None))
    con.executemany('INSERT INTO entry(source, hanzi, jyutping, jkey, toneless, kind, share) VALUES (?,?,?,?,?,?,?)', rows)

    # frequency: rime's essay list is by characters only; every reading of the characters gets the count
    freq = {}
    with open(os.path.join(rime, 'essay-cantonese.txt'), encoding='utf-8') as f:
        for line in f:
            p = line.rstrip('\n').split('\t')
            if len(p) == 2 and p[1].isdigit():
                freq[p[0]] = int(p[1])
    con.executemany('UPDATE entry SET freq=? WHERE hanzi=?', [(v, k) for k, v in freq.items()])

    # CC-CEDICT, for the Mandarin side of each card
    ced = os.path.join(raw, 'cedict', 'package', 'cedict.json')
    if os.path.exists(ced):
        data = json.load(open(ced, encoding='utf-8'))
        items = data.values() if isinstance(data, dict) else data
        crow = []
        for e in items:
            t = e.get('traditional') or e.get('trad')
            if not t:
                continue
            crow.append((t, e.get('simplified') or e.get('simp'), e.get('pinyin'),
                         '; '.join(e.get('english') or e.get('definitions') or [])
                         if isinstance(e.get('english') or e.get('definitions'), list) else (e.get('english') or '')))
        con.executemany('INSERT INTO cedict VALUES (?,?,?,?)', crow)
        classify(con)

    canto_layer(con, raw)

    # rank: by frequency, one rank per characters (homographs share it)
    ranked = con.execute("""SELECT hanzi, MAX(freq) f FROM entry WHERE freq IS NOT NULL AND kind='word' OR
                            (freq IS NOT NULL AND kind='char') GROUP BY hanzi ORDER BY f DESC""").fetchall()
    con.executemany('UPDATE entry SET freq_rank=? WHERE hanzi=?', [(i + 1, h) for i, (h, _) in enumerate(ranked)])
    con.execute('UPDATE entry SET core=1 WHERE freq_rank <= ?', (CORE_N,))
    con.commit()
    n = con.execute('SELECT COUNT(*) FROM entry').fetchone()[0]
    nc = con.execute('SELECT COUNT(*) FROM cedict').fetchone()[0]
    print(f'yue.db: {n} entries, {len(freq)} frequency rows, {nc} CC-CEDICT rows')


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
