"""Build display-only translations and a local Microsoft YaHei glyph atlas.

PoEDB inputs are matched by their identical page slug in /cn/ and /us/.
Only names present in this PoB release are enabled. No numeric game data is copied.
"""
from pathlib import Path
import csv
import hashlib
import html
import json
import re
import shutil
from PIL import Image, ImageDraw, ImageFont
from passive_locale import build_passives

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
OUT = ROOT / 'src' / 'Localization'


def build():
    entries = json.loads((HERE / 'ui-terms.json').read_text('utf-8'))
    entries = {k: ({'zh': v, 'kind': 'ui', 'status': 'editorial-ui'} if isinstance(v, str) else v)
               for k, v in entries.items()}
    names = set(re.findall(r'\bname = "([^"]+)"', (ROOT / 'src/Data/Gems.lua').read_text('utf-8')))
    for kind in ('skills', 'supports'):
        maps = []
        for lang, suffix in (('cn', ''), ('us', '-en')):
            text = (HERE / f'poedb-{kind}{suffix}.html').read_text('utf-8')
            pattern = r'<a class="gem_\w+"[^>]*href="/' + lang + r'/([^"#?]+)"[^>]*>([^<>]+)</a>'
            maps.append({slug: html.unescape(label).strip() for slug, label in re.findall(pattern, text)})
        cn, en = maps
        for slug in sorted(cn.keys() & en.keys()):
            base_name = en[slug][:-8] if en[slug].endswith(' Support') else en[slug]
            if (en[slug] not in names and base_name not in names) or not re.search('[\u4e00-\u9fff]', cn[slug]):
                continue
            entries[en[slug]] = {'zh': cn[slug], 'kind': 'gem', 'source': f'https://poedb.tw/cn/{slug}',
                                  'english_source': f'https://poedb.tw/us/{slug}', 'status': 'paired-name'}
            # PoB often displays support names without the redundant Support suffix.
            if en[slug].endswith(' Support'):
                entries.setdefault(en[slug][:-8], dict(entries[en[slug]], alias_of=en[slug]))
    passive_entries, passive_report, passive_contexts = build_passives()
    entries.update(passive_entries)
    OUT.mkdir(exist_ok=True)
    (OUT / 'catalog.json').write_text(json.dumps(entries, ensure_ascii=False, indent=2) + '\n', 'utf-8')
    def lua(s):
        return json.dumps(s, ensure_ascii=False)
    (OUT / 'PassiveContexts.lua').write_text('return {\n' + ''.join(
        f'[{lua(node_id)}] = {{' + ''.join(f'[{lua(en)}]={lua(zh)},' for en, zh in texts.items()) + '},\n'
        for node_id, texts in sorted(passive_contexts.items())) + '}\n', 'utf8')
    (OUT / 'Dictionary.lua').write_text('return {\n' + ''.join(
        f'\t[{lua(en)}] = {lua(v["zh"])},\n' for en, v in sorted(entries.items())) + '}\n', 'utf-8')
    with (OUT / '术语对照.csv').open('w', encoding='utf-8-sig', newline='') as f:
        w = csv.writer(f)
        w.writerow(['English', '简体中文', '类别', '核对状态', '中文来源', '英文来源'])
        for en, v in sorted(entries.items()):
            w.writerow([en, v['zh'], v['kind'], v['status'], v.get('source', ''), v.get('english_source', '')])

    # The font is copied from this PC for local use, not downloaded or installed.
    font_dir = HERE / 'fonts'
    font_dir.mkdir(exist_ok=True)
    font_path = font_dir / 'msyh.ttc'
    if not font_path.exists():
        shutil.copy2(Path('C:/Windows/Fonts/msyh.ttc'), font_path)
    font = ImageFont.truetype(str(font_path), 48, index=0)
    extra = '英文中文对照切换按住临时查看未翻译保留术语参考流亡编年史模式'
    all_text = ''.join(v['zh'] for v in entries.values()) + ''.join(zh for texts in passive_contexts.values() for zh in texts.values()) + extra
    chars = sorted({c for c in all_text if ord(c) > 127})
    cell, cols = 64, 64
    rows = (len(chars) + cols - 1) // cols
    image = Image.new('RGBA', (cols * cell, rows * cell))
    draw = ImageDraw.Draw(image)
    glyphs = []
    for i, ch in enumerate(chars):
        x, y = (i % cols) * cell, (i // cols) * cell
        # Anchor at the glyph's visible top; keep a 48px em for rendering.
        draw.text((x, y), ch, font=font, fill='white', anchor='lt', stroke_width=0)
        glyphs.append(f'\t[{lua(ch)}] = {{{x}, {y}, {font.getlength(ch):.4f}}},\n')
    image.save(OUT / 'ChineseGlyphs.png')
    (OUT / 'Glyphs.lua').write_text(f'return {{size = 48, cell = {cell}, width = {image.width}, height = {image.height}, chars = {{\n' + ''.join(glyphs) + '}}\n', 'utf-8')
    report = {'entries': len(entries), 'gem_names': sum(v['kind'] == 'gem' and 'alias_of' not in v for v in entries.values()),
              'glyphs': len(chars), 'font': 'Microsoft YaHei (local PC copy)',
              'font_sha256': hashlib.sha256(font_path.read_bytes()).hexdigest(),
              'pob_version': '2.67.2', 'name_reference_retrieved': '2026-11-11',
              'passives': passive_report,
              'scope': 'Display text only: UI, gem names, matched 3.29 passive names/stats/masteries; calculation data unchanged'}
    (OUT / 'build-info.json').write_text(json.dumps(report, indent=2) + '\n', 'utf-8')
    print(json.dumps(report), flush=True)


if __name__ == '__main__':
    build()
