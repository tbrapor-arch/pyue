"""Turn app/dist into an installable web app in _site/ (used by the GitHub workflow).

  python3 tools/site.py [out-dir]

Adds a proper <head> (home-screen icon, full-screen launch without browser bars, theme colour), the manifest,
the icons, the offline service worker, and the recordings if app/dist/audio exists.
"""
import base64
import hashlib
import os
import re
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, '_site'))
PWA = os.path.join(ROOT, 'app/pwa')
DIST = os.path.join(ROOT, 'app/dist')

body = open(os.path.join(DIST, 'index.html'), encoding='utf-8').read()
build = hashlib.sha1(body.encode()).hexdigest()[:10]


# Content Security Policy: the browser runs only the page's own inline script (allowed by its hash, computed here
# at each build) and the few outside sources listed, and talks only to GitHub's API. Anything injected into the
# page, or loaded from elsewhere, is refused, so it cannot read the sync token kept in this browser.
def script_hashes(html):
    out = []
    for m in re.finditer(r'<script>(.*?)</script>', html, re.S):
        out.append("'sha256-" + base64.b64encode(hashlib.sha256(m.group(1).encode('utf-8')).digest()).decode() + "'")
    if not out:
        sys.exit('site.py: no inline script found, the CSP would block the app')
    return ' '.join(out)


def csp(html, extra):
    rules = {
        'default-src': "'self'",
        'script-src': script_hashes(html),
        'style-src': "'self' 'unsafe-inline' https://fonts.googleapis.com",
        'font-src': "'self' data: https://fonts.gstatic.com",
        'img-src': "'self' data: blob:",
        'media-src': "'self' blob:",
        'connect-src': "'self'",
        'object-src': "'none'",
        'base-uri': "'none'",
    }
    for k, v in extra.items():
        rules[k] = (rules[k] + ' ' + v).strip() if k in rules else v
    return '<meta http-equiv="Content-Security-Policy" content="' + '; '.join(f'{k} {v}' for k, v in rules.items()) + '">\n'


APP_CSP = csp(body, {
    # the private module is run from a blob: URL; the video and music tabs use YouTube's player API
    'script-src': 'blob: https://www.youtube.com https://s.ytimg.com',
    'frame-src': 'https://www.youtube-nocookie.com https://www.youtube.com',
    'connect-src': 'https://api.github.com https://gist.githubusercontent.com',
    'img-src': 'https:',      # podcast and video artwork
    'media-src': 'https:',    # podcast audio, streamed from the host's servers
    'worker-src': "'self'",
    'manifest-src': "'self'",
})
head = '''<!doctype html><html lang="en"><head><meta charset="utf-8">
''' + APP_CSP + '''<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="description" content="A Cantonese perfectionnement course in English, with Jyutping.">
<link rel="manifest" href="manifest.webmanifest">
<link rel="icon" type="image/png" sizes="192x192" href="icon-192.png?v=2">
<link rel="apple-touch-icon" href="apple-touch-icon.png?v=2">
<meta name="theme-color" content="#FCFCF8">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-title" content="pyue">
<meta name="apple-mobile-web-app-status-bar-style" content="default">
<style>html,body{margin:0;padding:0}*{box-sizing:border-box}</style>
</head><body>
'''
os.makedirs(OUT, exist_ok=True)
open(os.path.join(OUT, 'index.html'), 'w', encoding='utf-8').write(head + body + '\n</body></html>\n')
for f in os.listdir(PWA):
    if f == 'sw.js':
        open(os.path.join(OUT, f), 'w').write(open(os.path.join(PWA, f)).read().replace('__BUILD__', build))
    else:
        shutil.copy(os.path.join(PWA, f), OUT)
if os.path.exists(os.path.join(DIST, 'record.html')):
    rec = open(os.path.join(DIST, 'record.html'), encoding='utf-8').read()
    tag = '<meta charset="utf-8">'
    if tag not in rec:
        sys.exit('site.py: record.html has no <meta charset="utf-8"> to put its CSP after')
    rec = rec.replace(tag, tag + '\n' + csp(rec, {'connect-src': 'blob: data:'}).rstrip('\n'), 1)
    open(os.path.join(OUT, 'record.html'), 'w', encoding='utf-8').write(rec)
if os.path.isdir(os.path.join(DIST, 'audio')):
    shutil.copytree(os.path.join(DIST, 'audio'), os.path.join(OUT, 'audio'), dirs_exist_ok=True)
open(os.path.join(OUT, '.nojekyll'), 'w').close()
print(f'{os.path.relpath(OUT, ROOT)}: installable site, build {build}')
