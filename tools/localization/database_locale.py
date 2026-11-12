"""Match display database fields to paired PoEDB names and keyed stat rows."""
from collections import defaultdict
from pathlib import Path
import gzip
import hashlib
import json
import re
from bs4 import BeautifulSoup
from item_locale import plain, shape, numeric_pair, lua_pattern

HERE = Path(__file__).resolve().parent


def monster_pairs(en_path, zh_path):
    """Match the first monster card within a stable variant tab, excluding skills."""
    digest = hashlib.sha256(b'monster-tabs-v2' + en_path.read_bytes() + zh_path.read_bytes()).hexdigest()
    cache_path = HERE/'database-reference/extracted'/f'{digest}.json.gz'
    if cache_path.exists(): return json.loads(gzip.decompress(cache_path.read_bytes()))
    maps = []
    for p in (en_path, zh_path):
        soup = BeautifulSoup(gzip.decompress(p.read_bytes()).decode('utf8'), 'html.parser')
        names = {}
        for tab in soup.select('.tab-pane[id]'):
            card = tab.select_one('.newItemPopup .itemHeader .itemName')
            if card:
                name = plain(card)
                prefix = re.sub(r'[^\w]', '', name)
                key = tab['id'].removeprefix(prefix)
                if key: names[key] = name
        maps.append(names)
    pairs = [[maps[0][key], maps[1][key], 'name'] for key in sorted(maps[0].keys() & maps[1].keys())]
    cache_path.parent.mkdir(exist_ok=True)
    cache_path.write_bytes(gzip.compress(json.dumps(pairs,ensure_ascii=False).encode('utf8'),mtime=0))
    return pairs


def page_pairs(en_path, zh_path):
    """Cache extraction by snapshot hashes; key selection never uses translation."""
    digest = hashlib.sha256(b'keyed-cards-v2'+en_path.read_bytes()+zh_path.read_bytes()).hexdigest()
    cache_path = HERE/'database-reference/extracted'/f'{digest}.json.gz'
    if cache_path.exists():
        return json.loads(gzip.decompress(cache_path.read_bytes()))
    soups = []
    for p in (en_path, zh_path):
        raw = gzip.decompress(p.read_bytes()).decode('utf8')
        soups.append(BeautifulSoup(re.sub(r'<script\b[^>]*>.*?</script>', '', raw, flags=re.S), 'html.parser'))
    pairs = []
    def append(a,b,kind):
        e,z = plain(a),plain(b)
        if e and z and re.search('[\u4e00-\u9fff]',z): pairs.append([e,z,kind])
    links=[]
    for lang,s in zip(('us','cn'),soups):
        choices=defaultdict(set)
        for a in s.select('a[href]'):
            target=a['href'].removeprefix('/'+lang+'/')
            label = a.get_text(' ',strip=True)
            if label: choices[target].add(label)
        links.append({k:next(iter(v))for k,v in choices.items()if len(v)==1})
    for key in sorted(links[0].keys()&links[1].keys()):append(links[0][key],links[1][key],'name')
    # Individual monster/item pages have multiple variants. Use a name only
    # when all displayed cards agree in both locales.
    names=[{plain(n)for n in s.select('.itemName')}for s in soups]
    if len(names[0])==len(names[1])==1:append(next(iter(names[0])),next(iter(names[1])),'name')
    # Enchantments have a stable English row ID in both languages.
    maps=[]
    for s in soups:
        rows={}
        for tr in s.select('tr'):
            cells=tr.find_all('td',recursive=False)
            if len(cells)>2 and cells[1].get_text(strip=True).startswith('Enchantment '):
                rows[cells[1].get_text(strip=True)]=cells[2]
        maps.append(rows)
    for key in sorted(maps[0].keys()&maps[1].keys()):append(maps[0][key],maps[1][key],'stat')
    # Currency/tattoo/pantheon list cards are keyed by the shared item/soul
    # link. Image-only anchors do not create competing empty names.
    cards=[]
    for lang,s in zip(('us','cn'),soups):
        keyed = {}
        for card in s.select('.d-flex.border-top.rounded'):
            a = card.select_one('a[data-hover][href]')
            if a: keyed[a['href'].removeprefix('/'+lang+'/')] = card
        cards.append(keyed)
    for key in sorted(cards[0].keys()&cards[1].keys()):
        a,b=cards[0][key],cards[1][key]
        if a and b:
            es,zs=a.select('.explicitMod'),b.select('.explicitMod')
            if len(es)==len(zs):
                for e,z in zip(es,zs):append(e,z,'stat')
    cache_path.parent.mkdir(exist_ok=True)
    cache_path.write_bytes(gzip.compress(json.dumps(pairs,ensure_ascii=False).encode('utf8'),mtime=0))
    return pairs


def build_database():
    rows=json.loads((HERE/'database-source.json').read_text('utf8'))
    local={r['english'].strip()for r in rows}
    shapes={shape(e)for e in local}
    exact,patterns=defaultdict(dict),defaultdict(dict)
    pairs=0
    monster_slugs = {r['english'].replace(' ', '_').replace("'", ''): r['english'] for r in rows
                     if r['kind'] in ('minion-name', 'spectre-name')}
    for folder in ('database-reference','item-reference'):
        for ep in sorted((HERE/folder).glob('*-us.html.gz')):
            zp=ep.with_name(ep.name.replace('-us.html.gz','-cn.html.gz'))
            if not zp.exists():continue
            slug=ep.name.removesuffix('-us.html.gz')
            matched = page_pairs(ep,zp)
            if folder == 'database-reference' and slug in monster_slugs and not any(
                    en == monster_slugs[slug] for en, zh, kind in matched):
                matched = matched + monster_pairs(ep, zp)
            for en,zh,kind in matched:
                if re.search('[a-zA-Z]{2}',zh):continue
                if kind=='stat' and not numeric_pair(en,zh):continue
                meta={'zh':zh,'kind':'database-'+kind,'status':'paired-local-source',
                      'source':'https://poedb.tw/cn/'+slug,'english_source':'https://poedb.tw/us/'+slug}
                if en in local:exact[en][zh]=meta;pairs+=1
                if kind=='stat' and shape(en)in shapes:
                    e,z,n=numeric_pair(en,zh)
                    if n:patterns[e][z]=dict(meta,en=e,zh=z,values=n,pattern=lua_pattern(e))
    entries={en:next(iter(v.values()))for en,v in exact.items()if len(v)==1}
    templates={en:next(iter(v.values()))for en,v in patterns.items()if len(v)==1}
    reviewed_path=HERE/'database-reviewed.json'
    reviewed=json.loads(reviewed_path.read_text('utf8'))if reviewed_path.exists()else {}
    for en,meta in reviewed.items():
        if '{'in en:
            assert shape(re.sub(r'\{\d+\}','#',en))in shapes,en
            assert sorted(re.findall(r'\{\d+\}',en))==sorted(re.findall(r'\{\d+\}',meta['zh'])),en
            templates[en]=dict(meta,en=en,values=len(re.findall(r'\{\d+\}',en)),pattern=lua_pattern(en))
        else:
            assert en in local,en
            entries[en]=meta
    report={'source_rows':len(rows),'matched_pairs':pairs,'exact_entries':len(entries),'numeric_templates':len(templates),
            'ambiguous_exact':{k:list(v)for k,v in exact.items()if len(v)>1},
            'ambiguous_templates':{k:list(v)for k,v in patterns.items()if len(v)>1}}
    (HERE/'database-coverage.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n','utf8')
    return entries,list(templates.values()),report


if __name__=='__main__':
    entries,templates,report=build_database()
    print(json.dumps({k:v if not isinstance(v,dict)else len(v)for k,v in report.items()}))
