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
from calc_rules import compose
from gem_locale import build_gems, hybrid_gem_names
from reference_glossary import build_glossary
from config_locale import compose_config
from fetch_gem_reference import gem_sources
from config_tooltips import compose_tooltip
from display_formats import compile_formats
from item_locale import build_items
from database_locale import build_database

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
OUT = ROOT / 'src' / 'Localization'


def write_term_csv(entries):
    with (OUT / '术语对照.csv').open('w', encoding='utf-8-sig', newline='') as f:
        w = csv.writer(f)
        w.writerow(['English', '简体中文', '类别', '核对状态', '中文来源', '英文来源'])
        for en, v in sorted(entries.items()):
            # The editable dictionary retains exact source whitespace. Strip
            # line-end padding only in this human-readable spreadsheet export.
            display_en = '\n'.join(line.rstrip() for line in en.split('\n'))
            w.writerow([display_en, v['zh'], v['kind'], v['status'], v.get('source', ''), v.get('english_source', '')])


def build():
    entries = json.loads((HERE / 'ui-terms.json').read_text('utf-8'))
    entries = {k: ({'zh': v, 'kind': 'ui', 'status': 'editorial-ui'} if isinstance(v, str) else v)
               for k, v in entries.items()}
    entries.update({k: {'zh': v, 'kind': 'ui', 'status': 'editorial-ui'}
                    for k, v in json.loads((HERE / 'extra-ui.json').read_text('utf8')).items()})
    entries.update({k: {'zh': v, 'kind': 'ui-detail', 'status': 'source-code-checked'}
                    for k, v in json.loads((HERE / 'detail-ui.json').read_text('utf8')).items()})
    entries.update({k: {'zh': v, 'kind': 'ui-detail', 'status': 'source-code-checked'}
                    for k, v in json.loads((HERE / 'tree-detail-ui.json').read_text('utf8')).items()})
    entries.update({k: {'zh': v, 'kind': 'ui-detail', 'status': 'source-code-checked'}
                    for k, v in json.loads((HERE / 'remaining-ui.json').read_text('utf8')).items()})
    for en, zh in json.loads((HERE / 'calc-notes.json').read_text('utf8')).items():
        meta = {'zh': zh, 'kind': 'calculation-explanation', 'status': 'source-code-checked',
                'source': 'src/Modules/CalcOffence.lua; src/Modules/CalcDefence.lua; src/Modules/CalcPerform.lua'}
        entries.setdefault(en, meta)
        entries.setdefault('(' + en + ')', dict(meta, zh='(' + zh + ')'))
    for terms_file in sorted(HERE.glob('config-terms*.json')):
        entries.update({k: {'zh': v, 'kind': 'config-ui', 'status': 'editorial-ui',
                            'source': 'src/Modules/ConfigOptions.lua; https://poedb.tw/cn/'}
                        for k, v in json.loads(terms_file.read_text('utf8')).items()})
    panels = json.loads((HERE / 'panel-terms.json').read_text('utf8'))
    panels.update(json.loads((HERE / 'calc-terms.json').read_text('utf8')))
    panels.update(json.loads((HERE / 'calc-extra.json').read_text('utf8')))
    calc_source = (ROOT / 'src/Modules/CalcSections.lua').read_text('utf8') + '\n' + (ROOT / 'src/Classes/CalcsTab.lua').read_text('utf8')
    calc_labels = set(json.loads('"' + x + '"') for x in re.findall(r'(?:label|title)\s*=\s*"((?:\\.|[^"\\])*)"', calc_source))
    translations = {k:v['zh'] for k,v in entries.items()}
    translations.update(panels)
    for label in sorted(calc_labels):
        if label not in translations:
            composed = compose(label, translations)
            if composed:
                panels[label] = composed
                translations[label] = composed
    entries.update({k: {'zh': v, 'kind': 'pob-panel', 'status': 'source-code-checked',
                        'source': 'src/Modules/BuildDisplayStats.lua; src/Modules/Build.lua; src/Classes/PassiveTreeView.lua'}
                    for k, v in panels.items()})
    labels = set(re.findall(r'label\s*=\s*"([^"\n]+)"', (ROOT / 'src/Modules/BuildDisplayStats.lua').read_text('utf8')))
    missing_labels = labels - entries.keys()
    if missing_labels:
        raise ValueError(f'Untranslated sidebar labels: {sorted(missing_labels)}')
    names = set(re.findall(r'\bname = "([^"]+)"', (ROOT / 'src/Data/Gems.lua').read_text('utf-8')))
    passive_entries, passive_report, passive_contexts = build_passives()
    entries.update(passive_entries)
    # Select by the actual link target, including unusual gem CSS classes.
    # Regexes for gem colour classes miss Portal and several utility gems.
    for slug, pair in gem_sources().items():
        en, zh = pair['us']['name'], pair['cn']['name']
        if not re.search('[\u4e00-\u9fff]', zh):
            continue
        entries[en] = {'zh': zh, 'kind': 'gem', 'source': f'https://poedb.tw/cn/{slug}',
                       'english_source': f'https://poedb.tw/us/{slug}', 'status': 'paired-name'}
        if en.endswith(' Support'):
            entries[en[:-8]] = dict(entries[en], alias_of=en)
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
    gem_entries, gem_templates, gem_report = build_gems(entries)
    entries.update(gem_entries)
    for name in names:
        if name not in entries and name + ' Support' in entries:
            entries[name] = dict(entries[name + ' Support'], alias_of=name + ' Support')
    for name, base in hybrid_gem_names().items():
        if name not in entries and base in entries:
            entries[name] = dict(entries[base], zh='瓦尔：' + entries[base]['zh'], status='local-hybrid-name-known-base', alias_of=base)
    glossary = build_glossary()
    for en, meta in glossary.items():
        # A buff and a skill can share an English name (e.g. Barkskin); retain
        # the existing skill/UI wording in the general display dictionary.
        if en not in entries or en.startswith('Soul of '):
            entries[en] = meta
    config_source = (ROOT / 'src/Modules/ConfigOptions.lua').read_text('utf8')
    config_labels = set(json.loads('"' + x + '"') for x in re.findall(r'\blabel\s*=\s*"((?:\\.|[^"\\])*)"', config_source))
    for label in sorted(config_labels):
        plain = re.sub(r'\^(?:x[0-9a-fA-F]{6}|\d)', '', label)
        if plain not in entries and plain.rstrip(':') not in entries:
            translated = compose_config(plain, entries, glossary)
            if translated:
                entries[plain] = {'zh': translated, 'kind': 'config-ui', 'status': 'finite-grammar-known-terms',
                                  'source': 'src/Modules/ConfigOptions.lua; https://poedb.tw/cn/Buff'}
    config_pending = sorted(s for s in config_labels if re.search(r'[a-zA-Z]', re.sub(r'\^(?:x[0-9a-fA-F]{6}|\d)', '', s)) and re.sub(r'\^(?:x[0-9a-fA-F]{6}|\d)', '', s).rstrip(':') not in entries
                            and re.sub(r'\^(?:x[0-9a-fA-F]{6}|\d)', '', s) not in entries)
    (HERE / 'config-labels-pending.json').write_text(json.dumps(config_pending, ensure_ascii=False, indent=2) + '\n', 'utf8')
    config_tooltips = set(json.loads('"' + x + '"') for x in re.findall(r'\btooltip\s*=\s*"((?:\\.|[^"\\])*)"', config_source))
    tooltip_pending = set()
    for tooltip in sorted(config_tooltips):
        translated_lines = []
        complete = True
        for raw in tooltip.splitlines():
            line = re.sub(r'\^(?:x[0-9a-fA-F]{6}|\d)', '', raw.strip())
            zh = compose_tooltip(line, entries, glossary) if line else ''
            if zh is None:
                complete = False
                tooltip_pending.add(line)
                translated_lines.append(raw)
            else:
                translated_lines.append(raw[:len(raw)-len(raw.lstrip())] + zh)
                if line:
                    entries.setdefault(line, {'zh': zh, 'kind': 'config-tooltip', 'status': 'source-clauses-reviewed', 'source':'src/Modules/ConfigOptions.lua'})
        if complete:
            plain_tooltip = re.sub(r'\^(?:x[0-9a-fA-F]{6}|\d)', '', tooltip)
            entries[plain_tooltip] = {'zh': '\n'.join(translated_lines), 'kind': 'config-tooltip', 'status': 'source-clauses-reviewed', 'source':'src/Modules/ConfigOptions.lua'}
    (HERE / 'config-tooltips-pending.json').write_text(json.dumps(sorted(tooltip_pending), ensure_ascii=False, indent=2)+'\n','utf8')
    detail_ui = json.loads((HERE / 'gem-ui.json').read_text('utf8'))
    entries.update({k: {'zh': v, 'kind': 'gem-ui', 'status': 'source-code-checked',
                        'source': 'src/Classes/GemTooltip.lua; src/Modules/Build.lua'}
                    for k, v in detail_ui.items()})
    item_ui = json.loads((HERE / 'item-ui.json').read_text('utf8'))
    for k, v in item_ui.items():
        entries.setdefault(k, {'zh': v, 'kind': 'item-ui', 'status': 'source-code-checked',
                        'source': 'src/Classes/ItemsTab.lua; https://poedb.tw/cn/League'}
        )
    database_entries, database_templates, database_report = build_database()
    for en, meta in database_entries.items():
        entries.setdefault(en, meta)
    item_entries, item_templates, item_report = build_items(entries, gem_templates + database_templates)
    item_template_map = {v['en']:v for v in item_templates}
    for template in database_templates:
        item_template_map.setdefault(template['en'], template)
    item_templates = sorted(item_template_map.values(), key=lambda t:(-len(t['en']),t['en']))
    # Existing reviewed UI/gem terminology remains the canonical shared word.
    for en, meta in item_entries.items():
        entries.setdefault(en, meta)
    # Translate() separates leading colour tags before dictionary lookup.
    # Retain source keys for provenance and add the corresponding display body.
    for en, meta in list(entries.items()):
        body = re.sub(r'^(?:\^x[0-9a-fA-F]{6}|\^\d)+', '', en)
        if body != en:
            entries.setdefault(body, dict(meta, zh=re.sub(r'^(?:\^x[0-9a-fA-F]{6}|\^\d)+', '', meta['zh'])))
    missing_calc = calc_labels - entries.keys()
    if missing_calc:
        raise ValueError(f'Untranslated calculation labels: {sorted(missing_calc)}')
    OUT.mkdir(exist_ok=True)
    (OUT / 'catalog.json').write_text(json.dumps(entries, ensure_ascii=False, indent=2) + '\n', 'utf-8')
    def lua(s):
        return json.dumps(s, ensure_ascii=False)
    (OUT / 'ItemDisplayTerms.lua').write_text('return {\n' + ''.join(
        '[' + lua(en) + ']=' + lua(zh) + ',\n' for en, zh in item_ui.items()) + '}\n', 'utf8')
    formats = compile_formats(json.loads((HERE / 'display-formats.json').read_text('utf8')))
    display_terms = json.loads((HERE / 'display-format-terms.json').read_text('utf8'))
    for prefix in ('Ancestral', 'Infernal', 'Intimidating', 'Rallying', 'Seismic', 'Battlemage'):
        name = entries.get(prefix + ' Cry', {}).get('zh')
        if name:
            display_terms[prefix] = name.removesuffix('战吼')
    (OUT / 'DisplayTerms.lua').write_text('return {\n' + ''.join(
        '[' + lua(en) + ']=' + lua(zh) + ',\n' for en, zh in display_terms.items()) + '}\n', 'utf8')
    (OUT / 'DisplayTemplates.lua').write_text('return {\n' + ''.join(
        '{pattern=' + lua(v['pattern']) + ',zh=' + lua(v['zh']) + ',kinds={'
        + ','.join(lua(kind) for kind in v['kinds']) + '}},\n' for v in formats) + '}\n', 'utf8')
    (OUT / 'SkillTemplates.lua').write_text('return {\n' + ''.join(
        '{en=' + lua(v['en']) + ',zh=' + lua(v['zh']) + ',pattern=' + lua(v['pattern'])
        + ',values=' + str(v['values']) + '},\n' for v in gem_templates) + '}\n', 'utf8')
    (OUT / 'ItemTemplates.lua').write_text('return {\n' + ''.join(
        '{en=' + lua(v['en']) + ',zh=' + lua(v['zh']) + ',pattern=' + lua(v['pattern'])
        + ',values=' + str(v['values']) + '},\n' for v in item_templates) + '}\n', 'utf8')
    (OUT / 'PassiveContexts.lua').write_text('return {\n' + ''.join(
        f'[{lua(node_id)}] = {{' + ''.join(f'[{lua(en)}]={lua(zh)},' for en, zh in texts.items()) + '},\n'
        for node_id, texts in sorted(passive_contexts.items())) + '}\n', 'utf8')
    (OUT / 'Dictionary.lua').write_text('return {\n' + ''.join(
        f'\t[{lua(en)}] = {lua(v["zh"])},\n' for en, v in sorted(entries.items())) + '}\n', 'utf-8')
    (OUT / 'PanelLabels.lua').write_text('return {\n' + ''.join(
        f'\t{lua(en)},\n' for en in sorted(labels, key=lambda s: (-len(s), s))) + '}\n', 'utf8')
    (OUT / 'CalcLabels.lua').write_text('return {\n' + ''.join(f'\t{lua(en)},\n' for en in sorted(calc_labels)) + '}\n', 'utf8')
    (OUT / 'ConfigLabels.lua').write_text('return {\n' + ''.join(f'\t{lua(en)},\n' for en in sorted(config_labels)) + '}\n', 'utf8')
    write_term_csv(entries)

    # The font is copied from this PC for local use, not downloaded or installed.
    font_dir = HERE / 'fonts'
    font_dir.mkdir(exist_ok=True)
    font_path = font_dir / 'msyh.ttc'
    if not font_path.exists():
        shutil.copy2(Path('C:/Windows/Fonts/msyh.ttc'), font_path)
    font = ImageFont.truetype(str(font_path), 48, index=0)
    extra = '英文中文对照切换按住临时查看未翻译保留术语参考流亡编年史模式'
    extra += (ROOT / 'src/Modules/Localization.lua').read_text('utf8')
    all_text = ''.join(v['zh'] for v in entries.values()) + ''.join(v['zh'] for v in gem_templates + item_templates) + ''.join(v['zh'] for v in formats) + ''.join(display_terms.values()) + ''.join(zh for texts in passive_contexts.values() for zh in texts.values()) + extra
    chars = sorted({c for c in all_text if ord(c) > 127})
    cell, cols = 64, 64
    rows = (len(chars) + cols - 1) // cols
    image = Image.new('RGBA', (cols * cell, rows * cell))
    draw = ImageDraw.Draw(image)
    glyphs = []
    baseline = max(-font.getbbox(ch, anchor='ls')[1] for ch in chars)
    for i, ch in enumerate(chars):
        x, y = (i % cols) * cell, (i // cols) * cell
        # Share one baseline: anchoring each visible bounding box at the top
        # incorrectly raises punctuation such as 。 and … above the text.
        draw.text((x, y + baseline), ch, font=font, fill='white', anchor='ls', stroke_width=0)
        glyphs.append(f'\t[{lua(ch)}] = {{{x}, {y}, {font.getlength(ch):.4f}}},\n')
    image.save(OUT / 'ChineseGlyphs.png')
    (OUT / 'Glyphs.lua').write_text(f'return {{size = 48, cell = {cell}, width = {image.width}, height = {image.height}, chars = {{\n' + ''.join(glyphs) + '}}\n', 'utf-8')
    report = {'entries': len(entries), 'gem_names': sum(v['kind'] == 'gem' and 'alias_of' not in v for v in entries.values()),
              'glyphs': len(chars), 'font': 'Microsoft YaHei (local PC copy)',
              'font_sha256': hashlib.sha256(font_path.read_bytes()).hexdigest(),
              'pob_version': '2.67.2', 'name_reference_retrieved': '2026-11-11', 'item_reference_retrieved': '2026-11-12',
              'passives': passive_report, 'gem_details': gem_report, 'item_details': item_report,
              'database_details': {k:v if not isinstance(v,dict)else len(v)for k,v in database_report.items()},
              'sidebar_labels': len(labels), 'sidebar_labels_translated': len(labels),
              'calculation_labels': len(calc_labels), 'calculation_labels_translated': len(calc_labels),
              'configuration_labels': len(config_labels), 'configuration_labels_translated': len(config_labels) - len(config_pending),
              'scope': 'Display only: UI/sidebar/calculations/configuration, gem/player-granted skill details, matched 3.29 passives, paired item names/bases/modifiers, essence/currency/monster/pantheon/tattoo/enchantment/cluster/boss preset display fields and finite display clauses. Item/database audits retain pending historic/special/unreviewed text. Coverage counts describe checked sources and fixtures, not every build or historic/jewel-transformed state. Calculation data and user input remain unchanged.'}
    (OUT / 'build-info.json').write_text(json.dumps(report, indent=2) + '\n', 'utf-8')
    print(json.dumps(report), flush=True)


if __name__ == '__main__':
    build()
