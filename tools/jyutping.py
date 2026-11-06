"""Jyutping helpers: split, validate, normalise.

A Jyutping string here is syllables separated by spaces (the rime/LSHK convention: 'zung1 ji3'). In lesson files a
word may also be written with hyphens or glued ('zung1-ji3', 'zung1ji3'); `syllables()` accepts all three.
"""
import re

INITIALS = ['gw', 'kw', 'ng', 'b', 'p', 'm', 'f', 'd', 't', 'n', 'l', 'g', 'k', 'h', 'z', 'c', 's', 'j', 'w', '']
FINALS = set('''aa aai aau aam aan aang aap aat aak a ai au am an ang ap at ak e ei eu em en eng ep et ek i iu im in
ing ip it ik o oi ou on ong ot ok u ui un ung ut uk oe oen oeng oet oek eoi eon eot yu yun yut m ng'''.split())
SYL = re.compile(r'([a-z]+)([1-6])')


def is_syllable(s):
    m = re.fullmatch(r'([a-z]+)([1-6])', s)
    if not m:
        return False
    body = m.group(1)
    if body in ('m', 'ng'):
        return True
    for ini in INITIALS:
        if body.startswith(ini) and body[len(ini):] in FINALS and body[len(ini):] not in ('m', 'ng'):
            return True
    return False


def syllables(s):
    """'zung1-ji3' / 'zung1 ji3' / 'zung1ji3' -> ['zung1', 'ji3']. Non-syllable runs are dropped."""
    return [a + b for a, b in SYL.findall(s.lower())]


def key(s):
    """Normalised key: syllables joined by '-'."""
    return '-'.join(syllables(s))


def toneless(s):
    return '-'.join(re.sub(r'[1-6]$', '', x) for x in syllables(s))


def superscript(s):
    """'zung1 ji3' -> 'zung¹ ji³' (display option)."""
    return s.translate(str.maketrans('123456', '¹²³⁴⁵⁶'))


if __name__ == '__main__':
    import sys
    for a in sys.argv[1:]:
        print(a, syllables(a), [is_syllable(x) for x in syllables(a)])
