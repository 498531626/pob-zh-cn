"""Refresh missing public paired item reference pages from the saved manifest."""
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import json
import urllib.request
import gzip
import argparse

HERE = Path(__file__).resolve().parent / 'item-reference'


def fetch(slug, language):
    path = HERE / f'{slug}-{language}.html.gz'
    if path.exists() and path.stat().st_size > 2000:
        return
    request = urllib.request.Request(f'https://poedb.tw/{language}/{slug}',
                                     headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(request, timeout=40) as response:
        body = response.read()
    if b'<html' not in body.lower():
        raise ValueError('Expected an HTML reference page')
    path.write_bytes(gzip.compress(body, mtime=0))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--directory', type=Path, default=HERE)
    HERE = parser.parse_args().directory.resolve()
    manifest = json.loads((HERE / 'sources.json').read_text('utf8'))
    failures = []
    with ThreadPoolExecutor(max_workers=6) as pool:
        tasks = {pool.submit(fetch, slug, lang): (slug, lang)
                 for slug in manifest['pages'] + manifest['list_pages'] for lang in ('us', 'cn')}
        for task in as_completed(tasks):
            try:
                task.result()
            except Exception as error:
                failures.append([*tasks[task], str(error)])
    print(json.dumps({'failures': failures}))
    if failures:
        raise SystemExit(1)
