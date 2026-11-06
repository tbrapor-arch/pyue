"""Tone practice items, built from the course's new words (Practice › Drills).

Cantonese has six tones and no systematic tone change, so instead of Tsheh-tû's tone-change drill the learner sees a
word's characters and its Jyutping without tone numbers, and picks the right tones. Wrong options change one syllable
to the tone it is most often confused with: 2↔5 (the two rising tones), 3↔6 and 4↔6 (mid / low level and falling),
1↔3. A syllable ending in -p -t -k (entering tone) only takes 1, 3 or 6.
Items keep Tsheh-tû's shape: {h, t (shown), s (answer), en, l (lesson id), opts, why}.
"""
import random
import re

NAMES = {'1': 'high level', '2': 'high rising', '3': 'mid level', '4': 'low falling', '5': 'low rising', '6': 'low level'}
CONFUSE = {'1': '3', '2': '5', '3': '6', '4': '6', '5': '2', '6': '3'}
CHECKED_CONFUSE = {'1': '3', '3': '6', '6': '3'}


def _syls(t):
    return re.findall(r'[a-z]+[1-6]', t.lower())


def _swap(s):
    body, tone = s[:-1], s[-1]
    table = CHECKED_CONFUSE if re.search(r'[ptk]$', body) else CONFUSE
    return body + table.get(tone, tone)


def item(hanji, jyut, en, lesson):
    syls = _syls(jyut)
    if not 1 <= len(syls) <= 3 or len(syls) != len(hanji):
        return None
    right = ' '.join(syls)
    rnd = random.Random(right)
    opts = {right}
    for i in range(len(syls)):
        alt = list(syls)
        alt[i] = _swap(alt[i])
        opts.add(' '.join(alt))
    if len(opts) < 3:     # one syllable: add the second most likely confusion
        alt = _swap(_swap(syls[0]))
        if alt != syls[0]:
            opts.add(alt)
        b = syls[0][:-1]
        for t in '123456':
            if len(opts) >= 3:
                break
            if not (re.search(r'[ptk]$', b) and t not in '136'):
                opts.add(b + t)
    if len(opts) < 3:
        return None
    why = [f'{s}: tone {s[-1]}, {NAMES[s[-1]]}' for s in syls]
    return {'h': hanji, 't': ' '.join(s[:-1] for s in syls), 's': right, 'en': en, 'l': lesson,
            'opts': sorted(opts, key=lambda o: rnd.random()), 'why': why}


def build(lessons):
    seen, out = set(), []
    for L in lessons:
        for w in L['new_words']:
            it = item(w['hanji'], w['tailo'], w.get('en') or '', L['id'])
            if it and it['s'] not in seen:
                seen.add(it['s'])
                out.append(it)
    return out
