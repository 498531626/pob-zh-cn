"""Cache paired pages for player-granted skills and missing gem variants."""
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import json
import re
import urllib.request
import urllib.parse
import urllib.error

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]

def fetch(slug, lang):
    path = HERE / 'skill-reference' / f'{slug}-{lang}.html'
    if path.exists() and path.stat().st_size > 2000:
        return
    url = 'https://poedb.tw/' + lang + '/' + urllib.parse.quote(slug)
    request = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    try:
        with urllib.request.urlopen(request, timeout=35) as response:
            path.write_bytes(response.read())
    except urllib.error.HTTPError as error:
        if error.code != 404 or "'" not in slug:
            raise
        canonical = slug.replace("'", '')
        request = urllib.request.Request('https://poedb.tw/' + lang + '/' + urllib.parse.quote(canonical), headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(request, timeout=35) as response:
            path.write_bytes(response.read())

if __name__ == '__main__':
    names = set()
    for kind in ('other', 'glove'):
        source = (ROOT / f'src/Data/Skills/{kind}.lua').read_text('utf8')
        names.update(re.findall(r'skills\["[^"]+"\]\s*=\s*\{\s*name\s*=\s*"([^"]+)"', source))
    names.update(row['english'] for row in json.loads((HERE / 'skill-display-pending.json').read_text('utf8'))
                 if row['kind'] in ('effect-name', 'gem-name'))
    names.update(['Added Fire Damage Support', 'Vaal Breach', 'Ravenous', 'Summon Spectral Wolf'])
    # A translated name does not imply the skill's description/stats are covered.
    sources = {name.replace(' ', '_'): name for name in names
               if not (name.startswith('Support') and ' ' not in name)}
    (HERE / 'skill-reference').mkdir(exist_ok=True)
    (HERE / 'skill-reference/sources.json').write_text(json.dumps(sources,indent=2)+'\n','utf8')
    failures = []
    with ThreadPoolExecutor(max_workers=6) as pool:
        pending = {pool.submit(fetch, slug, lang): [slug, lang] for slug in sources for lang in ('cn','us')}
        for future in as_completed(pending):
            try:
                future.result()
            except Exception as error:
                failures.append([*pending[future], str(error)])
    print(json.dumps({'pairs': len(sources), 'failures': failures}),flush=True)
