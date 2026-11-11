"""Inventory literal UI labels and render calls, then check the actual Lua translator.

This is a source inventory, not proof of every dynamically assembled screen.
Constructor anchor/type strings and protocols are recorded as technical values.
"""
import json
import os
import re
from pathlib import Path
from test_locale import run, ROOT
from display_formats import SPEC

HERE = Path(__file__).resolve().parent
TOKEN = re.compile(r'--\[(=*)\[.*?\]\1\]|--[^\n]*|\[(=*)\[.*?\]\2\]|"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|[A-Za-z_][\w]*|[^\s]', re.S)
CONSTRUCTORS = {'ButtonControl', 'CheckBoxControl', 'DropDownControl', 'LabelControl'}
TECHNICAL = {'LEFT', 'RIGHT', 'TOP', 'BOTTOM', 'CENTER', 'CENTER_X', 'RIGHT_X',
             'TOPLEFT', 'TOPRIGHT', 'BOTTOMLEFT', 'BOTTOMRIGHT', 'VAR', 'FIXED',
             'DOWN', 'FONTIN', 'FONTIN ITALIC', 'FONTIN SC', 'FONTIN SC ITALIC',
             'HTTP', 'IPv4', 'IPv6', 'SOCKS', 'SOCKS5H', 'Xbox', 'Sony',
             'Maxroll', 'Pastebin.com', 'PastebinP.com', 'PoeNinja', 'Rentry.co',
             'pob.codes', 'pobb.in', 'poedb.tw'} | CONSTRUCTORS


def decode(literal):
    if literal[0] == '[':
        m = re.match(r'\[(=*)\[', literal)
        return literal[m.end():-len(m[0])].removeprefix('\n')
    escapes = {'n': '\n', 'r': '\r', 't': '\t', '\\': '\\', '"': '"', "'": "'"}
    return re.sub(r'\\([nrt\\"\'])', lambda m: escapes[m[1]], literal[1:-1])


def inventory():
    rows = {}
    for directory in ('Classes', 'Modules'):
        for path in sorted((ROOT / 'src' / directory).glob('*.lua')):
            source = path.read_text('utf8')
            tokens = [(m[0], m.start()) for m in TOKEN.finditer(source) if not m[0].startswith('--')]
            selected = set()
            for i, (token, _) in enumerate(tokens):
                if token in ('label', 'title', 'tooltip', 'tooltipText', 'description', 'placeholder') and i+2 < len(tokens) and tokens[i+1][0] == '=':
                    selected.add(i+2)
                call = token in ('AddLine', 'DrawString', 'SetTooltip', 'SetPlaceholder')
                constructor = False
                if token == 'new' and i+2 < len(tokens) and tokens[i+1][0] == '(':
                    call = decode(tokens[i+2][0]) in CONSTRUCTORS if tokens[i+2][0].startswith(('"', "'")) else False
                    constructor = call
                if not call or i+1 >= len(tokens) or tokens[i+1][0] != '(':
                    continue
                depth = 0
                braces = 0
                argument = 1
                for j in range(i+1, len(tokens)):
                    value = tokens[j][0]
                    if value == '(':
                        depth += 1
                    elif value == ')':
                        depth -= 1
                        if depth == 0:
                            break
                    elif value == '{':
                        braces += 1
                    elif value == '}':
                        braces -= 1
                    elif value == ',' and depth == 1 and braces == 0:
                        argument += 1
                        if constructor and argument > 4:
                            break
                    if value.startswith(('"', "'", '[')) and len(value)>1:
                        if not constructor or argument == 4:
                            selected.add(j)
            for i in selected:
                literal, offset = tokens[i]
                if not literal.startswith(('"', "'", '[[')):
                    continue
                english = decode(literal)
                if not re.search('[A-Za-z]{2}', english) or '\\' in english:
                    continue
                row = {'file': path.relative_to(ROOT).as_posix(), 'line': source.count('\n',0,offset)+1,
                       'english': english}
                if english in TECHNICAL or re.fullmatch(r'\^[0-9]|\^x[0-9a-fA-F]{6}',english):
                    row['reason'] = 'Technical identifier, service name, or constructor geometry; preserve original'
                rows[(row['file'], row['line'], english)] = row
    return sorted(rows.values(), key=lambda row: (row['file'],row['line']))


if __name__ == '__main__':
    rows = inventory()
    review = json.loads((HERE/'ui-display-review.json').read_text('utf8'))
    for row in rows:
        if row['english'] in review['technical']:
            row['reason'] = review['technical'][row['english']]
        specs = [m[0] for m in SPEC.finditer(row['english']) if m[0] != '%%']
        if specs:
            row['format_arguments'] = ['' if s.endswith('s') else 83.25 for s in specs]
            if 'No changes from %s' in row['english']:
                row['format_arguments'] = ['allocating', '']
            if 'Price: %s %s' in row['english']:
                row['format_arguments'] = ['3.5', 'chaos']
    (HERE/'display-inventory.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n','utf8')
    os.chdir(ROOT/'src')
    run(r'''
package.cpath='../runtime/?.dll;'..package.cpath
package.path='../runtime/lua/?.lua;'..package.path
function LoadModule(p)return dofile(p..'.lua')end
function IsKeyDown()return false end
function GetScriptPath()return '__ui_audit_no_save__'end
function DrawString()end
function DrawStringWidth()return 1 end
function DrawStringCursorIndex()return 0 end
function SetDrawColor()end
local L=LoadModule('Modules/Localization');L.mode='zh'
local json=require('dkjson')
local f=assert(io.open('../tools/localization/display-inventory.json','rb'));local rows=json.decode(f:read('*a'));f:close()
f=assert(io.open('../tools/localization/ui-display-review.json','rb'));local review=json.decode(f:read('*a'));f:close()
local function plain(s)return (s:gsub('%^x%x%x%x%x%x%x',''):gsub('%^%d',''):match('^%s*(.-)%s*$'))end
for _,example in ipairs(review.examples)do
 L.mode='zh';assert(plain(L:Translate(example.english))==plain(example.chinese),'Assembled UI: '..example.english..' => '..L:Translate(example.english))
 L.mode='en';assert(L:Translate(example.english)==example.english)
 L.mode='bilingual';assert(L:Translate(example.english):find('[\128-\255]'))
end
L.mode='zh'
local seen,pending={},{}
for _,row in ipairs(rows)do
 local s=row.english
 if not row.reason and L:Translate(s)==s then
  if row.format_arguments then
   local ok,rendered=pcall(string.format,s,unpack(row.format_arguments))
   if ok then
    local translated=L:Translate(rendered)
    if translated:find('[\128-\255]')then
     local function numbers(value)local out={};for n in plain(value):gmatch('[%+%-]?%d+%.?%d*')do out[#out+1]=n end;return table.concat(out,'|')end
     assert(numbers(rendered)==numbers(translated),'Printf numeric change: '..s)
     row.reason='Printf source format; representative formatted output translated with numbers preserved'
     row.sample_english=rendered;row.sample_chinese=translated
    end
   end
  end
  if not row.reason then
   for i,example in ipairs(review.examples)do
    if plain(example.english):find(plain(s),1,true)then
     row.reason='Assembled source fragment; complete-message example '..i..' verified in three language modes'
     break
    end
   end
  end
  if not row.reason and not seen[s]then pending[#pending+1]=row;seen[s]=true end
 end
end
table.sort(pending,function(a,b)return a.english<b.english end)
f=assert(io.open('../tools/localization/display-runtime-pending.json','wb'));f:write(json.encode(pending,{indent=true}));f:close()
print('UI source inventory: '..#rows..' occurrences; unresolved literals/fragments: '..#pending)
f=assert(io.open('../tools/localization/display-inventory.json','wb'));f:write(json.encode(rows,{indent=true}));f:close()
assert(#pending==0,'Unresolved UI display text; see display-runtime-pending.json')
''')
