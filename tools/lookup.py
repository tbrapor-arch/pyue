"""Look up a word by characters or Jyutping.

  python3 -I tools/lookup.py data/build/yue.db 鍾意
  python3 -I tools/lookup.py data/build/yue.db zung1ji3      # exact
  python3 -I tools/lookup.py data/build/yue.db zung ji       # no tone numbers = any tone
"""
import os
import re
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import jyutping as jp  # noqa: E402

COLS = 'hanzi, jyutping, kind, share, freq_rank, cognate, mandarin_best'


def find(con, q):
    if re.search(r'[㐀-鿿\U00020000-\U0003ffff]', q):
        return con.execute(f'SELECT {COLS} FROM entry WHERE hanzi=? ORDER BY COALESCE(share, 100) DESC, freq_rank', (q,)).fetchall()
    if re.search(r'[1-6]', q):
        return con.execute(f'SELECT {COLS} FROM entry WHERE jkey=? ORDER BY freq_rank LIMIT 40', (jp.key(q),)).fetchall()
    t = '-'.join(q.lower().split())
    return con.execute(f'SELECT {COLS} FROM entry WHERE toneless=? ORDER BY freq_rank LIMIT 40', (t,)).fetchall()


def main():
    con = sqlite3.connect(sys.argv[1])
    q = ' '.join(sys.argv[2:])
    rows = find(con, q)
    if not rows:
        print('not found:', q)
    for h, j, k, sh, r, c, m in rows:
        extra = f' {sh}%' if sh is not None else ''
        print(f'{h}\t{j}{extra}\t{k}\trank {r or "-"}\t{c or ""}{" → " + m if m and m != h else ""}')


if __name__ == '__main__':
    main()
