"""Inventory and compose display names; never alter calculator identifiers."""
import json
import re
import tempfile
import os
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def format_identifier(value):
    return re.sub(r'([a-z])([0-9])', r'\1 \2',
                  re.sub(r'([a-z0-9]:?)([A-Z])', r'\1 \2', value))


def inventory():
    from test_locale import run
    with tempfile.TemporaryDirectory(prefix='pob-calc-schema-') as tmp:
        target = Path(tmp) / 'schema.json'
        previous = Path.cwd()
        try:
            os.chdir(ROOT / 'src')
            run("package.path='../runtime/lua/?.lua;'..package.path\n"
                "colorCodes=setmetatable({},{__index=function()return ''end})\n"
                "local seen={}\nlocal function scan(t)\n"
                "for k,v in pairs(t)do if k=='modName' then for _,id in ipairs(type(v)=='table'and v or{v})do seen[id]=true end "
                "elseif type(v)=='table'then scan(v)end end end\n"
                "scan(dofile('Modules/CalcSections.lua'))\n"
                "local names={};for id in pairs(seen)do names[#names+1]=id end;table.sort(names)\n"
                "local f=assert(io.open(" + json.dumps(target.as_posix()) + ",'wb'));"
                "f:write(require('dkjson').encode(names));f:close()")
        finally:
            os.chdir(previous)
        schema = json.loads(target.read_text('utf8'))
    names = {name: {'schema'} for name in schema}
    runtime_inventory = HERE / 'calc-runtime-identifiers.json'
    if runtime_inventory.is_file():
        for name in json.loads(runtime_inventory.read_text('utf8')):
            names.setdefault(name, set()).add('runtime-constructor')
    for path in sorted((ROOT / 'src').rglob('*.lua')):
        relative = path.relative_to(ROOT / 'src')
        if relative.parts[0] in ('Localization', 'TreeData'):
            continue
        text = path.read_text('utf8')
        # Literal constructors complement the evaluated schema, including mods
        # only produced by conditional item/skill paths in a particular build.
        for name in re.findall(r'\b(?:mod|flag|NewMod|MergeNewMod|createMod)\(\s*"([A-Za-z0-9_:]+)"\s*(?=[,)])', text):
            names.setdefault(name, set()).add(relative.as_posix())
    return names, schema


def compose(label, known):
    """Only finite reviewed phrases; fail closed when a component is unknown."""
    def translate(value):
        if canonical(value) in known:
            return known[canonical(value)]
        # Colon is structural, notably Condition: / Multiplier:.
        if ': ' in value:
            head, tail = value.split(': ', 1)
            left, right = ('计数' if head == 'Multiplier' else translate(head)), translate(tail)
            if left and right:
                return left + '：' + right
        words = value.split(' ')
        cache = {}
        def part(start):
            if start == len(words):
                return ''
            if start in cache:
                return cache[start]
            for end in range(len(words), start, -1):
                phrase = canonical(' '.join(words[start:end]))
                zh = known.get(phrase)
                if zh is None and re.fullmatch(r'\d+', phrase):
                    zh = phrase
                if zh is not None:
                    rest = part(end)
                    if rest is not None:
                        cache[start] = zh + rest
                        return cache[start]
            cache[start] = None
        return part(0)
    return translate(label)


def canonical(value):
    return re.sub(r"[\s'\-]", '', value).casefold()


def build(write=True):
    names, schema = inventory()
    dictionary = {k: v['zh'] for k, v in json.loads((ROOT / 'src/Localization/catalog.json').read_text('utf8')).items()}
    terms = json.loads((HERE / 'calc-identifier-terms.json').read_text('utf8'))
    known = {canonical(k): v for k, v in dictionary.items()
             if re.fullmatch(r"[A-Za-z0-9 '\-]+", k)
             and re.findall(r'\d+\.?\d*', k) == re.findall(r'\d+\.?\d*', v)}
    known.update({canonical(k): v for k, v in terms.items()})
    translations, missing = {}, []
    for name in sorted(names):
        label = format_identifier(name)
        zh = compose(label, known)
        if not zh or re.search(r'[A-Za-z]', zh.replace('PoB', '')):
            missing.append({'id': name, 'english': label, 'sources': sorted(names[name])})
        else:
            if re.findall(r'\d+\.?\d*', label) != re.findall(r'\d+\.?\d*', zh):
                raise ValueError('Calculation identifier changed numbers: ' + label)
            translations[label] = zh
    report = {'schema_identifiers': len(schema), 'source_identifiers': len(names),
              'translated': len(translations), 'pending': missing,
              'scope': 'Evaluated CalcSections modName schema and all literal modifier constructors in current Lua source. Runtime-generated names are audited separately.'}
    (HERE / 'calc-identifier-coverage.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', 'utf8')
    if write and not missing:
        (ROOT / 'src/Localization/CalcIdentifiers.lua').write_text('return {\n' + ''.join(
            '[' + json.dumps(en, ensure_ascii=False) + ']=' + json.dumps(zh, ensure_ascii=False) + ',\n'
            for en, zh in sorted(translations.items())) + '}\n', 'utf8')
        (ROOT / 'src/Localization/CalcIdentifierTerms.lua').write_text('return {\n' + ''.join(
            '[' + json.dumps(en, ensure_ascii=False) + ']=' + json.dumps(zh, ensure_ascii=False) + ',\n'
            for en, zh in sorted(terms.items())) + '}\n', 'utf8')
    return translations, report


if __name__ == '__main__':
    translations, report = build()
    print('Calculation identifiers:', report['source_identifiers'], 'schema:', report['schema_identifiers'], 'pending:', len(report['pending']))
    if report['pending']:
        raise SystemExit('Untranslated identifiers; see calc-identifier-coverage.json')
