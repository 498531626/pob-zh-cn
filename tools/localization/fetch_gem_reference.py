"""Cache PoEDB's paired gem cards, by page slug, with bounded concurrency."""
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import json
import re
import time
import urllib.request
from bs4 import BeautifulSoup

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def gem_sources():
    names = set(re.findall(r'\bname = "([^"]+)"', (ROOT / 'src/Data/Gems.lua').read_text('utf8')))
    sources = {}
    for kind in ('skills', 'supports'):
        langs = {}
        for lang, suffix in (('cn', ''), ('us', '-en')):
            page = BeautifulSoup((HERE / f'poedb-{kind}{suffix}.html').read_text('utf8'), 'html.parser')
            langs[lang] = {a['href'].split('/')[-1]: {'name': a.get_text(strip=True), 'url': a['data-hover']}
                           for a in page.select('a[data-hover]')
                           if a.get('href', '').startswith('/' + lang + '/') and a.get_text(strip=True)}
        for slug in sorted(langs['us'].keys() & langs['cn'].keys()):
            en = langs['us'][slug]['name']
            if en in names or en.removesuffix(' Support') in names:
                sources[slug] = {lang: langs[lang][slug] for lang in langs}
    return sources


def fetch(slug, lang, url):
    path = HERE / 'gem-reference' / f'{slug}-{lang}-hover.html'
    if path.exists() and 'gempopup' in path.read_text('utf8').lower():
        return
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=30) as response:
                body = response.read()
            if b'gempopup' not in body.lower():
                raise ValueError('Missing gem card')
            path.write_bytes(body)
            return
        except Exception:
            if attempt == 2:
                raise
            time.sleep(1 + attempt)


if __name__ == '__main__':
    (HERE / 'gem-reference').mkdir(exist_ok=True)
    sources = gem_sources()
    (HERE / 'gem-reference/sources.json').write_text(json.dumps(sources, indent=2, ensure_ascii=False) + '\n', 'utf8')
    with ThreadPoolExecutor(max_workers=6) as pool:
        pending = {pool.submit(fetch, slug, lang, v['url']): (slug, lang)
                   for slug, langs in sources.items() for lang, v in langs.items()}
        failures = []
        for i, future in enumerate(as_completed(pending), 1):
            try:
                future.result()
            except Exception as exc:
                failures.append([*pending[future], str(exc)])
            if i % 100 == 0:
                print(f'{i}/{len(pending)} cached; failures={len(failures)}', flush=True)
    print(json.dumps({'gem_pairs': len(sources), 'failures': failures}), flush=True)
    if failures:
        raise SystemExit(1)
