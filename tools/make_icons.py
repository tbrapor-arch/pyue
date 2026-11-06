"""Draw the app icons (app/pwa/icon-*.png) with Chromium: cobalt square, notebook grid, white 粵 (no margin line: alone it reads as a glitch).

  python3 tools/make_icons.py      (needs Playwright and a Traditional Chinese font such as Noto Sans CJK TC)

Full-bleed squares: phones round or mask the corners themselves; the glyph stays inside the central 60 %
so the same picture works as a maskable icon.
"""
import os
from playwright.sync_api import sync_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'app/pwa')
HTML = '''<html><body style="margin:0"><div id=i style="width:1024px;height:1024px;position:relative;overflow:hidden;
background:#2347B5;background-image:linear-gradient(rgba(255,255,255,.09) 3px,transparent 3px),
linear-gradient(90deg,rgba(255,255,255,.09) 3px,transparent 3px);background-size:85.3px 85.3px;background-position:-2px -2px">
<div style="position:absolute;inset:0;display:grid;place-items:center;font:900 560px/1 'Noto Sans CJK TC','Noto Sans TC',sans-serif;
color:#fff;text-shadow:22px 22px 0 #16307F;padding-bottom:30px">粵</div></div></body></html>'''
with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path=os.environ.get('CHROME') or None, args=['--no-sandbox'])
    for size in (1024, 512, 192, 180):
        p = b.new_page(viewport={'width': 1024, 'height': 1024}, device_scale_factor=size / 1024)
        p.set_content(HTML)
        name = 'apple-touch-icon.png' if size == 180 else f'icon-{size}.png'
        if size == 1024:
            name = 'icon-1024.png'
        p.locator('#i').screenshot(path=os.path.join(OUT, name))
    b.close()
print('icons written to', os.path.relpath(OUT, ROOT))
