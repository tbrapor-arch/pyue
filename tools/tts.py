"""Synthetic Cantonese audio for the 進修 lessons: course/perfectionnement/NN.yaml -> audio/NN/LL.mp3 (LL = line n)

Same pipeline as sy-zy (Azure Speech, one file per dialogue line, made again only when the line changes), with
Microsoft's three Hong Kong Cantonese neural voices:
  zh-HK-HiuMaanNeural (female), zh-HK-HiuGaaiNeural (female), zh-HK-WanLungNeural (male).
There is only one male voice, so the men are told apart by pitch and speed (course/voices.tsv).
The free Azure tier (F0) gives 500,000 characters a month; the 70 lessons are about 50,000.

  AZURE_SPEECH_KEY=… AZURE_SPEECH_REGION=eastasia python3 tools/tts.py     # new or changed lines only
  python3 tools/tts.py --lesson 3 --force                                  # one lesson, again
  python3 tools/tts.py --dry-run                                           # what would be sent, and the cost
  python3 tools/tts.py --backend edge                                      # free Edge endpoint (it has the zh-HK voices)

Who speaks with which voice: course/voices.tsv
  speaker <TAB> voice (HiuMaan|HiuGaai|WanLung) <TAB> pitch (e.g. -10%, optional) <TAB> rate (optional)
A row keyed "NN:speaker" applies to that lesson only (Letter, Host…). A speaker not listed gets HiuGaai.

What is read: the line's characters, without stage directions in brackets （對蓮姐）. The voice uses its own
readings and does not see the Jyutping: when it reads a word wrongly (a changed tone, a rare reading, an English
word), put a respelling in course/tts_fix.tsv (word <TAB> what to send instead), usually a homophone, and run
again: only the lines that change are made again.

audio/index.json records, per line, the text sent and a hash of (voice, pitch, rate, text). build_app.py gives a
line its audio only when that text still matches the lesson, so an edited line goes silent until it is made again.
"""
import argparse, asyncio, glob, hashlib, json, os, re, sys, time, urllib.request, urllib.error
from pathlib import Path
from xml.sax.saxutils import escape

import yaml

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'audio'
INDEX = OUT / 'index.json'
LESSONS = ROOT / 'course/perfectionnement'
VOICES = {'HiuMaan': 'zh-HK-HiuMaanNeural', 'HiuGaai': 'zh-HK-HiuGaaiNeural', 'WanLung': 'zh-HK-WanLungNeural'}
DEFAULT_VOICE = 'HiuGaai'
LOCALE = 'zh-HK'
FORMAT = 'audio-24khz-48kbitrate-mono-mp3'
RATE = '-10%'          # a little slower than normal, for learners; a voices.tsv rate replaces it
STAGE = re.compile(r'（[^）]*）|\([^)]*\)')


def tsv(path):
    p = ROOT / path
    out = {}
    if p.exists():
        for ln in p.read_text(encoding='utf8').splitlines():
            if ln.strip() and not ln.startswith('#'):
                cols = [c.strip() for c in ln.split('\t')]
                out[cols[0]] = cols[1:]
    return out


def fixes():
    return {k: v[0] for k, v in tsv('course/tts_fix.tsv').items() if v}


def spoken(hanzi, fx):
    """lesson characters -> the text the voice reads (stage directions dropped, respellings applied)"""
    t = STAGE.sub('', hanzi or '')
    for w in sorted(fx, key=len, reverse=True):
        t = t.replace(w, fx[w])
    t = re.sub(r'\s+', ' ', t).strip(' ，、')
    return t if re.search(r'[\w]', t) else ''


def voice_for(who, lesson, speaker):
    row = who.get(f'{lesson:02d}:{speaker}') or who.get(speaker) or [DEFAULT_VOICE]
    name = row[0] if row and row[0] in VOICES else DEFAULT_VOICE
    pitch = row[1] if len(row) > 1 and row[1] else ''
    rate = row[2] if len(row) > 2 and row[2] else RATE
    return name, pitch, rate


def ssml(text, voice, pitch, rate):
    attrs = ''.join(f' {k}="{v}"' for k, v in (('pitch', pitch), ('rate', rate)) if v)
    body = escape(text)
    if attrs:
        body = f'<prosody{attrs}>{body}</prosody>'
    return (f'<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="{LOCALE}">'
            f'<voice name="{voice}">{body}</voice></speak>')


def azure(text, voice, pitch, rate):
    key, region = os.environ.get('AZURE_SPEECH_KEY'), os.environ.get('AZURE_SPEECH_REGION')
    if not key or not region:
        sys.exit('tts.py: set AZURE_SPEECH_KEY and AZURE_SPEECH_REGION (Azure portal › Speech service › Keys and Endpoint)')
    req = urllib.request.Request(
        f'https://{region}.tts.speech.microsoft.com/cognitiveservices/v1',
        data=ssml(text, voice, pitch, rate).encode('utf8'), method='POST',
        headers={'Ocp-Apim-Subscription-Key': key, 'Content-Type': 'application/ssml+xml',
                 'X-Microsoft-OutputFormat': FORMAT, 'User-Agent': 'pyue-tts'})
    for attempt in range(5):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < 4:  # free tier: 20 requests a minute
                time.sleep(int(e.headers.get('Retry-After') or 10)); continue
            msg = e.read().decode('utf8', 'replace')[:200]
            sys.exit(f'tts.py: Azure said {e.code} {msg} (is {voice} offered in region {region}?)')


def edge(text, voice, pitch, rate):
    import edge_tts, ssl  # pip install edge-tts
    if os.environ.get('SSL_CERT_FILE'):  # behind a proxy with its own certificate
        import edge_tts.communicate as ec
        ec._SSL_CTX = ssl.create_default_context(cafile=os.environ['SSL_CERT_FILE'])
    proxy = os.environ.get('HTTPS_PROXY') or os.environ.get('https_proxy')
    pitch_hz = '+0Hz'
    if pitch:  # edge-tts takes Hz, not %: about 2 Hz per % around these voices' range
        pitch_hz = f'{int(round(float(pitch.rstrip("%")) * 2)):+d}Hz'
    async def go():
        buf = b''
        async for c in edge_tts.Communicate(text, voice, rate=rate or '+0%', pitch=pitch_hz, proxy=proxy).stream():
            if c['type'] == 'audio':
                buf += c['data']
        return buf
    data = asyncio.run(go())
    if not data:
        sys.exit(f'tts.py: the Edge endpoint returned nothing for {voice}')
    return data


def lessons():
    for p in sorted(glob.glob(str(LESSONS / '[0-9][0-9].yaml'))):
        yield yaml.safe_load(open(p, encoding='utf8'))


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--lesson', type=int, action='append', help='only these lessons (repeatable)')
    ap.add_argument('--force', action='store_true', help='make again even when unchanged')
    ap.add_argument('--dry-run', action='store_true', help='print what would be sent, call nothing')
    ap.add_argument('--backend', choices=('azure', 'edge'), default='azure')
    a = ap.parse_args()

    say = azure if a.backend == 'azure' else edge
    who, fx = tsv('course/voices.tsv'), fixes()
    index = json.loads(INDEX.read_text()) if INDEX.exists() else {}
    made = kept = chars = 0
    for y in lessons():
        n = y['id']
        if a.lesson and n not in a.lesson:
            continue
        entry = {}
        for d in y['dialogue']:
            text = spoken(d.get('hanzi'), fx)
            if not text:
                continue
            name, pitch, rate = voice_for(who, n, d.get('speaker') or '')
            voice = VOICES[name]
            i = d['n']
            h = hashlib.sha1(f'{voice}|{pitch}|{rate}|{text}'.encode('utf8')).hexdigest()[:10]
            f = OUT / f'{n:02d}' / f'{i:02d}.mp3'
            entry[str(i)] = {'h': h, 't': text, 'v': name}
            if not a.force and f.exists() and index.get(str(n), {}).get(str(i), {}).get('h') == h:
                kept += 1; continue
            chars += len(text); made += a.dry_run
            if a.dry_run:
                print(f'{n:02d}/{i:02d}  {name:8} {pitch or "":5} {rate:5}  {d.get("speaker")}: {text}'); continue
            data = say(text, voice, pitch, rate)
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_bytes(data)
            made += 1
            print(f'{n:02d}/{i:02d}  {text}', flush=True)
        if not a.dry_run:
            d_ = OUT / f'{n:02d}'
            for old in d_.glob('*.mp3') if d_.exists() else []:   # lines that no longer exist
                if str(int(old.stem)) not in entry:
                    old.unlink()
            index[str(n)] = entry
            OUT.mkdir(exist_ok=True)   # saved after every lesson, so a stopped run keeps what it made
            INDEX.write_text(json.dumps(dict(sorted(index.items(), key=lambda kv: int(kv[0]))),
                                        ensure_ascii=False, indent=1) + '\n')
    print(f'{"to make" if a.dry_run else "made"}: {chars} characters, {made} files; {kept} unchanged')


if __name__ == '__main__':
    main()
