"""Cache paired cluster passive cards linked from the existing PoEDB snapshot."""
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import gzip
import hashlib
import json
import os
import time
import urllib.request
from bs4 import BeautifulSoup
from test_locale import ROOT, run

HERE = Path(__file__).resolve().parent
REFERENCE = HERE / 'cluster-reference'


def export_nodes():
    previous = Path.cwd()
    try:
        os.chdir(ROOT / 'src')
        run(r'''
package.path='../runtime/lua/?.lua;'..package.path
local json=require('dkjson')
dofile('GameVersions.lua')
local tree=dofile('TreeData/'..latestTreeVersion..'/tree.lua')
local nodes={}
for id,node in pairs(tree.nodes)do
 if (node.isNotable or node.isKeystone)and not tree.groups[node.group]then
  nodes[#nodes+1]={id=tostring(id),name=node.name,stats=node.stats or {},reminders=node.reminderText or {}}
 end
end
table.sort(nodes,function(a,b)return a.id<b.id end)
local f=assert(io.open('../tools/localization/cluster-source.json','wb'))
f:write(json.encode({tree_version=latestTreeVersion,nodes=nodes},{indent=true}));f:close()
''')
    finally:
        os.chdir(previous)
    path = HERE / 'cluster-source.json'
    inventory = json.loads(path.read_text('utf8'))
    inventory['tree_sha256'] = hashlib.sha256((ROOT / 'src/TreeData' / inventory['tree_version'] / 'tree.lua').read_bytes()).hexdigest()
    path.write_text(json.dumps(inventory, ensure_ascii=False, indent=2) + '\n', 'utf8')
    return inventory


def sources(nodes):
    maps = {}
    for lang in ('us', 'cn'):
        body = gzip.decompress((HERE / f'database-reference/Cluster_Jewel-{lang}.html.gz').read_bytes())
        soup = BeautifulSoup(body, 'html.parser')
        maps[lang] = {a['href'].split('/')[-1]: {'name': a.get_text(strip=True), 'url': a['data-hover']}
                      for a in soup.select('a.PassiveSkills[data-hover][href]')}
    names = {node['name'] for node in nodes}
    result = {slug: {lang: maps[lang][slug] for lang in maps}
              for slug in sorted(maps['us'].keys() & maps['cn'].keys())
              if maps['us'][slug]['name'] in names}
    missing = names - {pair['us']['name'] for pair in result.values()}
    if missing:
        raise ValueError('Missing cluster reference links: ' + repr(sorted(missing)))
    return result


def fetch(slug, lang, info):
    path = REFERENCE / f'{slug}-{lang}.html.gz'
    if path.exists():
        body = gzip.decompress(path.read_bytes())
    else:
        request = urllib.request.Request(info['url'], headers={'User-Agent': 'Mozilla/5.0'})
        for attempt in range(3):
            try:
                with urllib.request.urlopen(request, timeout=30) as response:
                    body = response.read()
                break
            except (OSError, TimeoutError):
                if attempt == 2:
                    raise
                time.sleep(1 + attempt)
        if b'newItemPopup' not in body or b'implicitMod' not in body:
            raise ValueError('Missing passive card: ' + info['url'])
        path.write_bytes(gzip.compress(body, mtime=0))
    return hashlib.sha256(body).hexdigest()


if __name__ == '__main__':
    inventory = export_nodes()
    pairs = sources(inventory['nodes'])
    REFERENCE.mkdir(exist_ok=True)
    failures = []
    with ThreadPoolExecutor(max_workers=8) as pool:
        pending = {pool.submit(fetch, slug, lang, info): (slug, lang)
                   for slug, langs in pairs.items() for lang, info in langs.items()}
        for index, future in enumerate(as_completed(pending), 1):
            slug, lang = pending[future]
            try:
                pairs[slug][lang]['sha256'] = future.result()
            except Exception as exc:
                failures.append([slug, lang, str(exc)])
            if index % 100 == 0:
                print(f'{index}/{len(pending)} cluster cards; failures={len(failures)}', flush=True)
    if failures:
        raise SystemExit(repr(failures))
    manifest = {'retrieved': '2026-11-19', 'tree_version': inventory['tree_version'], 'sources': pairs}
    (REFERENCE / 'sources.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', 'utf8')
    print(f"Cached {len(pairs)} cluster passive pairs for {len(inventory['nodes'])} local nodes", flush=True)
