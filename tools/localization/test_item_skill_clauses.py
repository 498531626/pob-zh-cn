"""Check the full local inventory of item-granted and supported skill clauses."""
import json
import os
import re
from pathlib import Path
from test_locale import ROOT, run

HERE = Path(__file__).resolve().parent
rows = [row for name in ('item-source.json', 'database-source.json', 'item-runtime-source.json')
        for row in json.loads((HERE / name).read_text('utf8'))]
patterns = (
    r'Grants [Ll]evel [\d.]+ .+',
    r'Grants (?:Embrace Madness|Summon (?:Greater )?Harbinger of .+)',
    r'Socketed Gems are Supported by Level [\d.]+ .+',
)
clauses = sorted({row['english'].strip() for row in rows
                  if any(re.fullmatch(pattern, row['english'].strip()) for pattern in patterns)})
assert len(clauses) >= 200, 'Item skill inventory is incomplete'
os.chdir(ROOT / 'src')
run('local clauses=' + '{' + ','.join(json.dumps(text, ensure_ascii=False) for text in clauses) + '}\n' + r'''
function LoadModule(p)return dofile(p..'.lua')end
function GetScriptPath()return '__item_skill_clause_test_no_save__'end
function IsKeyDown()return false end
function DrawString()end
function DrawStringWidth()return 1 end
function DrawStringCursorIndex()return 0 end
function SetDrawColor()end
local L=LoadModule('Modules/Localization')
local function numbers(text)
 local values={};for n in text:gmatch('[%+%-]?%d+%.?%d*')do values[#values+1]=tonumber(n)end
 table.sort(values);return table.concat(values,',')
end
for _,en in ipairs(clauses)do
 L.mode='zh';local zh=L:Translate(en)
 assert(zh~=en and not zh:match('%a%a'),'Untranslated item skill clause: '..en..' => '..zh)
 assert(numbers(en)==numbers(zh),'Item skill clause changed numbers: '..en)
 assert(L:Translate('^x8888FF'..en)=='^x8888FF'..zh,'Skill clause colour: '..en)
 L.mode='en';assert(L:Translate(en)==en,'English clause changed: '..en)
end
L.mode='zh'
for _,en in ipairs({'Grants Level 20 Unknown Skill',
 'Grants Level 20 Hatred while Foo is active',
 'Socketed Gems are Supported by Level 20 Unknown Support',
 'Grants Unknown Effect'})do
 assert(L:Translate(en)==en,'Unknown clause was guessed: '..en)
end
assert(L:Translate('Grants Level 17 Aspect of the Cat')=='获得 17 级猫之势')
assert(L:Translate('Grants Level 17 Aspect of the Crab Skill')=='获得 17 级蟹之势技能')
assert(L:Translate('Grants Level (10-20) Hatred')=='获得 (10-20) 级憎恨')
assert(L:Translate('Socketed Gems are Supported by Level 17 Automation Support')=='插槽内的技能石受到 17 级自动化辅助')
assert(L:Translate('Socketed Gems are Supported by Level 20 Added Chaos Damage Support')=='插槽内的宝石受到 20 级附加混沌伤害辅助')
print('All '..#clauses..' item skill clauses: translated names, levels, colours, English switching and unknown fallback passed')
''')
