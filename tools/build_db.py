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
