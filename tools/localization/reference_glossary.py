"""Pair names by their identical PoEDB link targets, excluding ambiguous names."""
from collections import defaultdict
from pathlib import Path
import re
import json
from bs4 import BeautifulSoup

HERE = Path(__file__).resolve().parent


def build_glossary():
    choices = defaultdict(dict)
    for page, selector in [('Buff', 'a.BuffDefinitions[href]'),
                           ('The_Pantheon', 'a[data-hover*="PantheonPanelLayout"][href]')]:
        names = {}
        for lang in ('us', 'cn'):
            soup = BeautifulSoup((HERE / f'poedb-{page}-{lang}.html').read_text('utf8'), 'html.parser')
            names[lang] = {a['href'].removeprefix('/' + lang + '/'): a.get_text(strip=True)
                           for a in soup.select(selector)}
        for slug in sorted(names['us'].keys() & names['cn'].keys()):
            en, zh = names['us'][slug], names['cn'][slug]
            if re.search('[\u4e00-\u9fff]', zh):
                choices[en][zh] = {'zh': zh, 'kind': 'game-term', 'status': 'paired-link-target',
                                   'source': 'https://poedb.tw/cn/' + slug,
                                   'english_source': 'https://poedb.tw/us/' + slug}
    # Item and mechanic names mentioned by PoB's configuration help.
    for en, slug in json.loads((HERE / 'term-reference/sources.json').read_text('utf8')).items():
        paths = {lang: HERE / 'term-reference' / f'{slug}-{lang}.html' for lang in ('us','cn')}
        if not all(p.exists() for p in paths.values()):
            continue
        soup = {lang: BeautifulSoup(p.read_text('utf8'),'html.parser') for lang,p in paths.items()}
        es, zs = soup['us'].select('.itemName'), soup['cn'].select('.itemName')
        if es and zs and es[0].get_text(strip=True) == en and re.search('[\u4e00-\u9fff]', zs[0].get_text()):
            zh = zs[0].get_text(strip=True)
            choices[en] = {zh:{'zh':zh,'kind':'game-term','status':'paired-page-name-checked',
                'source':'https://poedb.tw/cn/'+slug,'english_source':'https://poedb.tw/us/'+slug}}
    return {en: next(iter(v.values())) for en, v in choices.items() if len(v) == 1}
