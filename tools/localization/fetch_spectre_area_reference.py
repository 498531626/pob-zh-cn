"""Check missing spectre locations against paired PoEDB area cards."""
import concurrent.futures
import gzip
import json
import re
import urllib.error
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path
from bs4 import BeautifulSoup

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SPECTRES = (ROOT / 'src/Data/Spectres.lua').read_text('utf8')
LOCATIONS = set()
for block in re.findall(r'spawnLocation = \{(.*?)\}', SPECTRES, re.S):
    LOCATIONS.update(re.findall(r'"([^"\n]+)"', block))
AREA_IDS = {}
for area_id, block in re.findall(r'^worldAreas\["([^"]+)"\] = \{\n(.*?)^\}',
                               (ROOT / 'src/Data/WorldAreas.lua').read_text('utf8'), re.M | re.S):
    name = re.search(r'\bname = "([^"]+)"', block)[1]
    base_match = re.search(r'\bbaseName = "([^"]+)"', block)
    if not base_match:
        continue
    base = base_match[1]
    if name in LOCATIONS:
        AREA_IDS.setdefault(base, set()).add(area_id)


def check(name):
    attempts = []
    for slug in dict.fromkeys((name.replace(' ', '_'), name.replace("'", '').replace(' ', '_'))):
        cards = []
        keyed_cards = []
        urls = []
        for language in ('us', 'cn'):
            url = 'https://poedb.tw/' + language + '/' + urllib.parse.quote(slug)
            urls.append(url)
            path = HERE / 'area-reference' / (slug + '-' + language + '.html.gz')
            try:
                if not path.exists():
                    request = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                    with urllib.request.urlopen(request, timeout=25) as response:
                        path.write_bytes(gzip.compress(response.read(), mtime=0))
                soup = BeautifulSoup(gzip.decompress(path.read_bytes()).decode('utf8'), 'html.parser')
                names = {card.get_text(' ', strip=True) for card in soup.select('.itemName')}
                cards.append(names)
                keyed = {}
                for popup in soup.select('.newItemPopup'):
                    title = popup.select_one('.itemName')
                    for prop in popup.select('.property'):
                        match = re.match(r'Id:\s*(.+)$', prop.get_text(' ', strip=True))
                        if match and title:
                            keyed[match[1]] = title.get_text(' ', strip=True)
                keyed_cards.append(keyed)
                attempts.append({'url': url, 'names': sorted(names)})
            except (urllib.error.URLError, TimeoutError) as error:
                attempts.append({'url': url, 'error': str(error)})
                break
        if len(keyed_cards) == 2:
            matched = [key for key in sorted(AREA_IDS.get(name, set()))
                       if keyed_cards[0].get(key) == name and key in keyed_cards[1]]
            chinese = {keyed_cards[1][key] for key in matched}
            if len(chinese) == 1 and re.search('[\u4e00-\u9fff]', next(iter(chinese))):
                return name, {'zh': next(iter(chinese)), 'status': 'paired-poedb-area-id-name',
                              'matched_ids': matched, 'english_source': urls[0], 'source': urls[1],
                              'retrieved': date.today().isoformat(), 'attempts': attempts}
        if len(cards) == 2 and cards[0] == {name} and len(cards[1]) == 1:
            chinese = next(iter(cards[1]))
            if re.search('[\u4e00-\u9fff]', chinese):
                return name, {'zh': chinese, 'status': 'paired-poedb-area-card-name',
                              'english_source': urls[0], 'source': urls[1],
                              'retrieved': date.today().isoformat(), 'attempts': attempts}
    return name, {'status': 'reference-search-unmatched', 'attempts': attempts}


if __name__ == '__main__':
    names = json.loads((HERE / 'spectre-area-literals.json').read_text('utf8'))
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        rows = dict(executor.map(check, sorted(names)))
    (HERE / 'spectre-area-reviewed.json').write_text(
        json.dumps(rows, ensure_ascii=False, indent=2) + '\n', 'utf8')
    print(json.dumps({'queried': len(rows), 'paired': sum('zh' in row for row in rows.values()),
                      'unmatched': [name for name, row in rows.items() if 'zh' not in row]}, ensure_ascii=False))
