"""Compile explicitly reviewed printf display formats, preserving argument order."""
import json
import re

SPEC = re.compile(r'%(?:[-+ #0]*\d*(?:\.\d+)?)[diuoxXfFeEgGsc%]')


def compile_formats(pairs):
    rows = []
    for en, zh in pairs.items():
        # Colours are handled by Localization.lua; templates contain text only.
        en = re.sub(r'\^x[0-9a-fA-F]{6}|\^\d', '', en)
        zh = re.sub(r'\^x[0-9a-fA-F]{6}|\^\d', '', zh)
        specs = [m[0] for m in SPEC.finditer(en) if m[0] != '%%']
        target = [m[0] for m in SPEC.finditer(zh) if m[0] != '%%']
        if specs != target:
            raise ValueError(f'Format argument change: {en!r}')
        if not specs:
            continue
        escaped = []
        last = 0
        kinds = []
        def literal(text):
            return re.sub(r'([%^$().%[\]*+?\-])', r'%\1', text)
        for m in SPEC.finditer(en):
            escaped.append(literal(en[last:m.start()]))
            if m[0] == '%%':
                escaped.append('%%')
            else:
                kinds.append('term' if m[0].endswith('s') else 'number')
                escaped.append('(.-)' if kinds[-1] == 'term' else '([%+%-]?[%d%,%.]+)')
            last = m.end()
        escaped.append(literal(en[last:]))
        index = 0
        def replace(m):
            nonlocal index
            if m[0] == '%%':
                return '%'
            value = '{' + str(index) + '}'
            index += 1
            return value
        rows.append({'pattern': '^'+''.join(escaped)+'$', 'zh': SPEC.sub(replace, zh), 'kinds': kinds, 'english': en})
    return rows
